"""Best-effort song metadata enrichment from last.fm (no auth needed for
track.getInfo — only the API key is required)."""
import logging
from typing import List, Optional

import httpx

from config import settings

log = logging.getLogger("persona.lastfm")

LASTFM_URL = "https://ws.audioscrobbler.com/2.0/"
IMAGE_SIZES = ("extralarge", "large", "medium", "small")


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


async def lookup_track(
    artist: Optional[str], title: str
) -> Optional[dict]:
    """Return {listeners, cover, tags[]} or None when unavailable."""
    if not settings.lastfm_enabled or not settings.lastfm_api_key or not title:
        return None

    params = {
        "method": "track.getinfo",
        "artist": (artist or "").strip(),
        "track": title.strip(),
        "autocorrect": "1",
        "format": "json",
        "api_key": settings.lastfm_api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(LASTFM_URL, params=params)
            data = resp.json()
    except Exception as exc:  # network / JSON errors must never break the bot
        log.info("last.fm request failed: %s", exc)
        return None

    track = data.get("track") if isinstance(data, dict) else None
    if not track or data.get("error"):
        return None

    toptags = track.get("toptags") or {}
    raw_tags = toptags.get("tag") or []
    if isinstance(raw_tags, dict):
        raw_tags = [raw_tags]
    tags: List[str] = []
    for t in raw_tags:
        name = (t.get("name") or "").strip() if isinstance(t, dict) else ""
        if name and name.lower() not in ("seen live",):
            tags.append(name)
        if len(tags) >= 6:
            break

    try:
        listeners = int(track.get("listeners") or 0)
    except (TypeError, ValueError):
        listeners = 0

    cover = _best_image(track)
    if not cover and isinstance(track.get("album"), dict):
        cover = _best_image(track["album"])

    return {"listeners": listeners, "cover": cover, "tags": tags}


async def enrich_song(song_id: int) -> None:
    """Fetch last.fm data for a stored song and persist genre/listeners/cover."""
    if not settings.lastfm_enabled or not settings.lastfm_api_key:
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
    if not meta:
        log.info("last.fm: no data for '%s' — '%s'", artist, title)
        return

    db = SessionLocal()
    try:
        song = db.get(Song, song_id)
        if song is None:
            return
        changed = False
        if meta["listeners"] and not song.listeners:
            song.listeners = meta["listeners"]
            changed = True
        if meta["cover"] and not song.cover_url:
            song.cover_url = meta["cover"][:512]
            changed = True
        if meta["tags"]:
            song.tags = ",".join(meta["tags"])[:255]
            if not song.genre:
                song.genre = meta["tags"][0][:64]
            changed = True
        if changed:
            db.commit()
            log.info(
                "last.fm enriched song %s: genre=%s listeners=%s cover=%s",
                song_id,
                song.genre,
                song.listeners,
                bool(song.cover_url),
            )
    finally:
        db.close()
