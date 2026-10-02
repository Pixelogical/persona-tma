"""Import songs from a Telegram Desktop export JSON into the Persona chart.

Usage (from the backend dir / container /app):

    python import_songs.py songs.json [--no-enrich]

Reads every message with "media_type": "audio_file" (the export tree is
walked recursively, so results.json / individual chat files both work)
and inserts them exactly like bot/handlers._ingest does:
same norm_key duplicate skip, get_or_create_user for the sender, etc.

After each insert the song is immediately enriched through the app's own
lastfm module (cover art + global listeners from last.fm, 1 req/sec).
Respects LASTFM_ENABLED / LASTFM_API_KEY from .env; --no-enrich skips it
(main.py's backfill scheduler will then pick the songs up on its own).

NOTE: the export has no Telegram file_id, so imported songs show on the
chart but cannot be sent by the bot's playlist "Play" feature.
"""
import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from config import settings
from crud import find_duplicate, get_or_create_user
from database import SessionLocal, init_db
from models import Song, norm_key

_USER_ID_RE = re.compile(r"^user(\d+)$")


def iter_audio_messages(node):
    """Yield every dict in the export tree that looks like an audio message."""
    if isinstance(node, dict):
        if node.get("media_type") == "audio_file":
            yield node
        for value in node.values():
            yield from iter_audio_messages(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_audio_messages(item)


def parse_sender(msg: dict):
    m = _USER_ID_RE.match(msg.get("from_id") or "")
    if not m:
        return None, None
    return int(m.group(1)), (msg.get("from") or "").strip()


def parse_created_at(msg: dict) -> datetime:
    try:
        return datetime.fromisoformat(msg["date"])
    except (KeyError, ValueError):
        return datetime.utcnow()


def enrich_now(db, song: Song) -> None:
    """Fetch cover art + global listeners right after the insert using the
    app's own lastfm module (no-op unless LASTFM_ENABLED + API key are set)."""
    from lastfm import enrich_song

    try:
        asyncio.run(enrich_song(song.id))
    except Exception as exc:  # enrichment must never abort the import
        print(f"  ! last.fm lookup failed: {exc}")
        return
    db.refresh(song)
    cover = "cover ✓" if song.cover_url else "no cover"
    listeners = f"{song.listeners:,} listeners" if song.listeners else "no listeners"
    print(f"  🌐 last.fm: {cover} · {listeners}")
    time.sleep(1.1)  # last.fm rate limit


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("json_file", help="Telegram export JSON (songs.json)")
    ap.add_argument(
        "--no-enrich",
        action="store_true",
        help="skip the inline last.fm cover/listeners lookup",
    )
    ap.add_argument(
        "--chat-username",
        default=None,
        help="public @username of the group (enables t.me deep links for pins)",
    )
    args = ap.parse_args()

    path = Path(args.json_file)
    if not path.is_file():
        print(f"file not found: {path}")
        return 1
    messages = list(iter_audio_messages(json.loads(path.read_text(encoding="utf-8"))))
    print(f"found {len(messages)} audio message(s) in {path.name}")

    init_db()
    chat_id = settings.persona_chat_id or 0

    db = SessionLocal()
    added = 0
    try:
        for msg in messages:
            title = (msg.get("title") or "").strip()
            artist = (msg.get("performer") or "").strip()
            if not title:
                title = (msg.get("file_name") or "Unknown title").rsplit(".", 1)[0]

            key = norm_key(title, artist)
            if find_duplicate(db, key) is not None:
                print(f"skip duplicate   : {title} — {artist}")
                continue

            user_id, display_name = parse_sender(msg)
            if user_id is None:
                print(f"skip no sender id: {title}")
                continue

            message_id = abs(int(msg.get("id") or 0))
            if message_id and db.scalar(
                select(Song).where(Song.message_id == message_id).limit(1)
            ):
                print(f"skip already imported (msg {message_id}): {title}")
                continue

            sender = get_or_create_user(db, user_id=user_id, first_name=display_name)
            song = Song(
                file_id="",  # not present in Telegram exports
                file_unique_id=f"export-{message_id}",
                chat_id=chat_id,
                message_id=message_id,
                chat_username=args.chat_username,
                title=title[:255],
                artist=artist[:255] or None,
                duration=int(msg.get("duration_seconds") or 0),
                norm_key=key,
                sender_id=sender.id,
                created_at=parse_created_at(msg),
            )
            db.add(song)
            db.commit()
            db.refresh(song)
            added += 1
            print(f"added #{song.id:<8}: {title} — {artist}")
            if not args.no_enrich:
                enrich_now(db, song)
    finally:
        db.close()

    print(f"\nimported {added} song(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
