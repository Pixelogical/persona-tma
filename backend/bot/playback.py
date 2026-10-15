from __future__ import annotations

import asyncio
import logging

from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)

from bot.bot import get_bot, playlist_lock
from config import settings
from database import SessionLocal
from models import Playlist, chat_id_variants

log = logging.getLogger("persona.play")


async def _send_song(user_id: int, song) -> bool:
    """Resend the track to the user's DM (falls back to forwarding the original).

    Songs imported from a Telegram export have no file_id, so forwarding
    the original group message is the only way to deliver them — and the
    Bot API only accepts the -100 supergroup form of the chat id, so try
    every known form of it."""
    bot = get_bot()
    if song.file_id:
        for attempt in (1, 2):
            try:
                await bot.send_audio(
                    chat_id=user_id,
                    audio=song.file_id,
                    title=song.title,
                    performer=song.artist or None,
                )
                return True
            except TelegramRetryAfter as e:
                if attempt == 1:
                    await asyncio.sleep(e.retry_after + 0.5)
                    continue
            except TelegramAPIError:
                break

    last_exc = None
    for from_chat_id in chat_id_variants(song.chat_id):
        try:
            await bot.forward_message(
                chat_id=user_id,
                from_chat_id=from_chat_id,
                message_id=song.message_id,
            )
            return True
        except (TelegramAPIError, TelegramForbiddenError, TelegramBadRequest) as exc:
            last_exc = exc
    log.warning(
        "could not deliver song %s (chat %s, msg %s, file_id %s): %s",
        song.id,
        song.chat_id,
        song.message_id,
        "missing" if not song.file_id else "invalid",
        last_exc,
    )
    return False


# virtual "Tops of Persona" auto-playlist — never touches the DB
TOPS_NAME = "Tops of Persona"
TOPS_LOCK_KEY = -1  # real playlist ids are positive, -1 can never collide
TOPS_DEFAULTS = (4.0, 3, 50, False)  # min_avg, min_votes, max_tracks, shuffle


async def play_songs(user_id: int, name: str, songs: list, lock_key: int) -> dict:
    """Stream an explicit song list into the user's private chat with the bot."""
    if not songs:
        return {"ok": False, "error": "empty", "playlist": name, "started": 0}
    songs = songs[: settings.play_max_songs]

    async with playlist_lock(lock_key):
        bot = get_bot()

        if settings.play_intro:
            try:
                await bot.send_message(
                    user_id,
                    f"▶️ Now playing <b>{name}</b> — {len(songs)} track(s) 🎧",
                )
            except TelegramAPIError as exc:
                log.warning("intro message failed: %s", exc)

        started = skipped = 0
        for index, song in enumerate(songs):
            if index:
                await asyncio.sleep(settings.play_song_interval)
            if await _send_song(user_id, song):
                started += 1
            else:
                skipped += 1

        if started and not skipped:
            closing = f"✅ Playlist <b>{name}</b> finished ({started} tracks)."
        elif started:
            closing = (
                f"✅ Playlist <b>{name}</b> finished ({started} tracks) — "
                f"{skipped} couldn't be delivered."
            )
        else:
            closing = (
                f"⚠️ Couldn't deliver any track from <b>{name}</b>. "
                "These songs were imported from a chat export without a "
                "Telegram file — resend them in the group so I can put "
                "them on the chart properly."
            )
        try:
            await bot.send_message(user_id, closing)
        except TelegramAPIError:
            pass

        log.info(
            "playlist %r streamed to user %s: %s sent, %s skipped",
            name,
            user_id,
            started,
            skipped,
        )
        return {
            "ok": started > 0,
            "playlist": name,
            "started": started,
            "skipped": skipped,
            "interval": settings.play_song_interval,
        }


async def play_playlist(playlist_id: int, user_id: int) -> dict:
    """Stream every song of a stored playlist into the user's private chat."""
    db = SessionLocal()
    try:
        playlist = db.get(Playlist, playlist_id)
        if playlist is None:
            return {"ok": False, "error": "not_found", "playlist": "", "started": 0}
        if playlist_lock(playlist_id).locked():
            return {
                "ok": False,
                "error": "playing",
                "playlist": playlist.name,
                "started": 0,
            }
        songs = [ps.song for ps in playlist.playlist_songs]
        name = playlist.name
    finally:
        db.close()

    return await play_songs(user_id, name, songs, playlist_id)


async def play_tops(
    user_id: int,
    min_avg: float,
    min_votes: int,
    max_tracks: int,
    shuffle: bool,
) -> dict:
    """Stream the filtered "Tops of Persona" auto-playlist."""
    if playlist_lock(TOPS_LOCK_KEY).locked():
        return {"ok": False, "error": "playing", "playlist": TOPS_NAME, "started": 0}
    from crud import tops_songs

    db = SessionLocal()
    try:
        songs = tops_songs(db, min_avg, min_votes, max_tracks, shuffle)
    finally:
        db.close()
    return await play_songs(user_id, TOPS_NAME, songs, TOPS_LOCK_KEY)


def parse_tops_deep_link(payload: str) -> tuple:
    """tops_40_3_50_1 -> (4.0, 3, 50, True); bad payloads fall back to defaults."""
    try:
        _, avg, votes, max_tracks, shuffle = payload.split("_")
        return (
            max(1.0, min(5.0, int(avg) / 10)),
            max(1, min(1000, int(votes))),
            max(1, min(settings.play_max_songs, int(max_tracks))),
            shuffle == "1",
        )
    except ValueError:
        return TOPS_DEFAULTS
