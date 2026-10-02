"""Best-effort song metadata enrichment from last.fm (no auth needed —
only the API key). Resilient by design: browser-like headers, optional
proxy, explicit status handling, an artist-tags fallback and a periodic
backfill that retries songs which were still un-enriched."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from config import settings

log = logging.getLogger("persona.lastfm")

LASTFM_URL = "https://ws.audioscrobbler.com/2.0/"
IMAGE_SIZES = ("extralarge", "large", "medium", "small")
# last.fm's edge rejects bare library clients (HTTP 403 HTML) — pose as a
# normal browser.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}
RETRY_AFTER = timedelta(hours=6)  # retry a failed lookup at most this often


def _enabled() -> bool:
    return bool(settings.lastfm_enabled and settings.lastfm_api_key)


async def _call(method: str, **params) -> Optional[dict]:
    if not _enabled():
        return None
    query = {"method": method, "autocorrect": "1", "format": "json",
             "api_key": settings.lastfm_api_key, **params}
    kwargs = {"timeout": 12, "headers": HEADERS}
    if settings.proxy:  # reuse the Telegram proxy for last.fm too when set
        kwargs["proxy"] = settings.proxy
    try:
        async with httpx.AsyncClient(**kwargs) as client:
            resp = await client.get(LASTFM_URL, params=query)
    except Exception as exc:  # network errors must never break the bot
        log.info("last.fm %s request failed: %s", method, exc)
        return None
    if resp.status_code != 200:
        log.info("last.fm %s -> HTTP %s (blocked/unavailable?)", method, resp.status_code)
        return None
    try:
        data = resp.json()
    except ValueError:
        log.info("last.fm %s -> non-JSON response", method)
        return None
    return data if isinstance(data, dict) else None


def _tags_of(data: dict, limit: int = 6) -> List[str]:
    toptags = data.get("toptags") or {}
    raw = toptags.get("tag") or []
    if isinstance(raw, dict):
        raw = [raw]
    tags: List[str] = []
    for t in raw:
        name = (t.get("name") or "").strip() if isinstance(t, dict) else ""
        if name and name.lower() != "seen live" and name.lower() not in tags:
            tags.append(name)
        if len(tags) >= limit:
            break
    return tags


def _best_image(owner: dict) -> Optional[str]:
    images = owner.get("image") or []
    if isinstance(images, dict):
        images = [images]
    by_size = {
        i.get("size"): i.get("#text")
        for i in images
        if isinstance(i, dict) and i.get("#text")
    }
    for size in IMAGE_SIZES:
        if by_size.get(size):
            return by_size[size]
    return None


async def lookup_track(artist: Optional[str], title: str) -> Optional[dict]:
    """Return {listeners, cover, tags[]} or None when the track is unknown."""
    if not _enabled() or not title:
        return None
    data = await _call("track.getinfo", artist=(artist or "").strip(), track=title.strip())
    track = data.get("track") if data else None
    if not track or data.get("error"):
        return None
    try:
        listeners = int(track.get("listeners") or 0)
    except (TypeError, ValueError):
        listeners = 0
    cover = _best_image(track)
    if not cover and isinstance(track.get("album"), dict):
        cover = _best_image(track["album"])
    return {"listeners": listeners, "cover": cover, "tags": _tags_of(track)}


async def lookup_artist_tags(artist: str) -> List[str]:
    """Fallback: many tracks (e.g. Persian titles) are not on last.fm under
    their latinised name, but the artist page usually has genre tags."""
    if not _enabled() or not artist:
        return []
    data = await _call("artist.getinfo", artist=artist.strip())
    artist_obj = data.get("artist") if data else None
    if not artist_obj or data.get("error"):
        return []
    return _tags_of(artist_obj)


async def enrich_song(song_id: int) -> None:
    """Fetch last.fm data for a stored song; persist what was found. Always
    stamps enriched_at so failed lookups are retried only after a backoff."""
    if not _enabled():
        return

    from database import SessionLocal
    from models import Song

    db = SessionLocal()
    try:
        song = db.get(Song, song_id)
        if song is None:
            return
        artist, title = song.artist, song.title
    finally:
        db.close()

    meta = await lookup_track(artist, title)
    tags = list(meta["tags"]) if meta else []
    if not tags and artist:
        tags = await lookup_artist_tags(artist)  # fallback: artist genres

    db = SessionLocal()
    try:
        song = db.get(Song, song_id)
        if song is None:
            return
        song.enriched_at = datetime.utcnow()
        changed = True
        if meta:
            if meta["listeners"] and not song.listeners:
                song.listeners = meta["listeners"]
            if meta["cover"] and not song.cover_url:
                song.cover_url = meta["cover"][:512]
        if tags:
            song.tags = ",".join(tags)[:255]
            if not song.genre:
                song.genre = tags[0][:64]
        if changed:
            db.commit()
            log.info(
                "last.fm song %s: genre=%s listeners=%s cover=%s tags=%s",
                song_id, song.genre, song.listeners, bool(song.cover_url), song.tags,
            )
    finally:
        db.close()


async def enrich_pending_once(limit: int = 8) -> int:
    """One backfill sweep: songs still missing a genre, most recent first."""
    from sqlalchemy import or_, select

    from database import SessionLocal
    from models import Song

    db = SessionLocal()
    try:
        stale = datetime.utcnow() - RETRY_AFTER
        ids = list(
            db.scalars(
                select(Song.id)
                .where(or_(Song.genre.is_(None), Song.genre == ""))
                .where(
                    or_(Song.enriched_at.is_(None), Song.enriched_at < stale)
                )
                .order_by(Song.id.desc())
                .limit(limit)
            )
        )
    finally:
        db.close()

    for sid in ids:
        await enrich_song(sid)
        await asyncio.sleep(1.5)  # stay well under last.fm rate limits
    return len(ids)


async def run_enrichment_scheduler() -> None:
    """Background loop: picks up songs whose enrichment failed at ingest."""
    await asyncio.sleep(20)  # let the app settle after startup
    while True:
        try:
            n = await enrich_pending_once()
            if n:
                log.info("last.fm backfill swept %d untagged song(s)", n)
        except Exception as exc:  # pragma: no cover
            log.warning("last.fm backfill failed: %s", exc)
        await asyncio.sleep(1800)  # every 30 minutes
