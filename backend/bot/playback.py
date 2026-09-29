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
from models import Playlist

log = logging.getLogger("persona.play")


async def _send_song(chat_id: int, song) -> bool:
    """Resend the track as the bot (falls back to forwarding the original)."""
    bot = get_bot()
    try:
        await bot.send_audio(
            chat_id=chat_id,
            audio=song.file_id,
            title=song.title,
            performer=song.artist or None,
        )
        return True
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after + 0.5)
        try:
            await bot.send_audio(
                chat_id=chat_id,
                audio=song.file_id,
                title=song.title,
                performer=song.artist or None,
            )
            return True
        except TelegramAPIError:
            pass
    except TelegramAPIError:
        pass

    try:
        await bot.forward_message(
            chat_id=chat_id, from_chat_id=song.chat_id, message_id=song.message_id
        )
        return True
    except (TelegramAPIError, TelegramForbiddenError, TelegramBadRequest) as exc:
        log.warning("could not deliver song %s: %s", song.id, exc)
        return False


async def play_playlist(playlist_id: int) -> dict:
    """Stream every song of a playlist into the group chat, in order."""
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
        songs = [ps.song for ps in playlist.playlist_songs][: settings.play_max_songs]
        name = playlist.name
    finally:
        db.close()

    if not songs:
        return {"ok": False, "error": "empty", "playlist": name, "started": 0}

    async with playlist_lock(playlist_id):
        chat_id = songs[0].chat_id
        bot = get_bot()

        if settings.play_intro:
            try:
                await bot.send_message(
                    chat_id,
                    f"▶️ Now playing: <b>{name}</b> — {len(songs)} track(s)",
                )
            except TelegramAPIError:
                pass

        started = skipped = 0
        for index, song in enumerate(songs):
            if index:
                await asyncio.sleep(settings.play_song_interval)
            if await _send_song(chat_id, song):
                started += 1
            else:
                skipped += 1
        return {
            "ok": started > 0,
            "playlist": name,
            "started": started,
            "skipped": skipped,
            "interval": settings.play_song_interval,
        }
