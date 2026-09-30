from __future__ import annotations

import asyncio
import html
import logging
import re
from typing import Optional, Tuple

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Message,
    WebAppInfo,
)

from config import settings
from crud import get_or_create_user
from database import SessionLocal
from models import Song

log = logging.getLogger("persona.handlers")

router = Router()

MP3_MIME_TYPES = {"audio/mpeg", "audio/mp3"}


def parse_name(file_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Fallback parser for 'Artist - Title.mp3' style file names."""
    if not file_name:
        return None, None
    name = re.sub(r"\.(mp3|m4a|aac|ogg|flac|wav)$", "", file_name, flags=re.I)
    if " - " in name:
        artist, title = name.split(" - ", 1)
        return artist.strip() or None, title.strip() or None
    return None, name.strip() or None


def extract_meta(message: Message) -> Optional[dict]:
    """Pull telegram file info out of an audio (or mp3 document) message."""
    if message.audio:
        a = message.audio
        return {
            "file_id": a.file_id,
            "file_unique_id": a.file_unique_id,
            "duration": a.duration or 0,
            "title": a.title,
            "performer": a.performer,
            "file_name": a.file_name,
        }
    doc = message.document
    if doc and (
        (doc.mime_type or "").lower() in MP3_MIME_TYPES
        or (doc.file_name or "").lower().endswith(".mp3")
    ):
        return {
            "file_id": doc.file_id,
            "file_unique_id": doc.file_unique_id,
            "duration": 0,
            "title": None,
            "performer": None,
            "file_name": doc.file_name,
        }
    return None


def chart_kb() -> Optional[InlineKeyboardMarkup]:
    if not settings.webapp_url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎧 Open Chart", web_app=WebAppInfo(url=settings.webapp_url)
                )
            ]
        ]
    )


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: Message, deep_link: str) -> None:
    """t.me/PersonaBot?start=play_<id> — user pressed Start after being
    redirected from the Mini App: stream that playlist right into this chat."""
    db = SessionLocal()
    try:
        get_or_create_user(
            db,
            user_id=message.from_user.id,
            first_name=message.from_user.first_name or "",
            last_name=message.from_user.last_name,
            username=message.from_user.username,
        )
    finally:
        db.close()

    if not deep_link.startswith("play_"):
        await cmd_start(message)
        return
    try:
        playlist_id = int(deep_link.split("_", 1)[1])
    except ValueError:
        await cmd_start(message)
        return

    from bot.playback import play_playlist
    from models import Playlist

    db = SessionLocal()
    try:
        pl = db.get(Playlist, playlist_id)
        name = pl.name if pl else None
        count = len(pl.playlist_songs) if pl else 0
    finally:
        db.close()

    if not name or count == 0:
        await message.answer(
            "🤔 That playlist is gone or empty — open the chart and pick another one!",
            reply_markup=chart_kb(),
        )
        return

    await message.answer(
        f"▶️ Starting your playlist <b>{html.escape(name)}</b> "
        f"({count} track{'s' if count != 1 else ''}) — enjoy! 🎧"
    )
    asyncio.create_task(play_playlist(playlist_id, message.from_user.id))


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 <b>PersonaBot</b> is live.\n\n"
        "Send an <b>MP3 song</b> in the Persona group and it lands on the "
        "chart instantly — rate it ⭐, build playlists and let the top voters "
        "pin their favourites.\n\n"
        "▶️ Press <b>play</b> on any playlist and I will send its tracks "
        "<u>here, in this private chat</u>, one by one.",
        reply_markup=chart_kb(),
    )


@router.message(Command("chart"))
async def cmd_chart(message: Message) -> None:
    await message.answer(
        "📊 The Persona chart is one tap away:", reply_markup=chart_kb()
    )


@router.message(F.content_type.in_({"audio", "document"}))
async def ingest_audio(message: Message) -> None:
    """Register every mp3 in the chart. Never let a failure skip registration."""
    try:
        await _ingest(message)
    except Exception:  # pragma: no cover
        log.exception("failed to ingest message %s", message.message_id)


async def _ingest(message: Message) -> None:
    if not message.from_user or message.from_user.is_bot:
        return
    is_private = message.chat.type == "private"
    if (
        not is_private
        and settings.persona_chat_id
        and message.chat.id != settings.persona_chat_id
    ):
        return

    meta = extract_meta(message)
    if not meta:
        return

    fallback_artist, fallback_title = parse_name(meta["file_name"])
    title = meta["title"] or fallback_title or meta["file_name"] or "Unknown title"
    artist = meta["performer"] or fallback_artist

    db = SessionLocal()
    try:
        sender = get_or_create_user(
            db,
            user_id=message.from_user.id,
            first_name=message.from_user.first_name or "",
            last_name=message.from_user.last_name,
            username=message.from_user.username,
        )
        sender_name = sender.display_name

        # every sent mp3 becomes a new chart entry (re-sends included)
        song = Song(
            file_id=meta["file_id"],
            file_unique_id=meta["file_unique_id"],
            chat_id=message.chat.id,
            message_id=message.message_id,
            chat_username=message.chat.username,
            title=title[:255],
            artist=artist[:255] if artist else None,
            duration=meta["duration"],
            sender_id=sender.id,
        )
        db.add(song)
        db.commit()
        log.info(
            "registered song #%s '%s' by %s in chat %s",
            song.id,
            title,
            sender_name,
            message.chat.id,
        )
    finally:
        db.close()

    note = (
        "🎵 New track on the <b>Persona chart</b>!\n\n"
        f"<b>{html.escape(title)}</b>"
        + (f" — {html.escape(artist)}" if artist else "")
        + f"\n👤 Shared by {html.escape(sender_name)}"
        + (
            f"\n⏱ {meta['duration'] // 60}:{meta['duration'] % 60:02d}"
            if meta["duration"]
            else ""
        )
        + "\n\nRate it ⭐ and add it to your playlist in the app."
    )
    try:
        await message.reply(
            note,
            reply_markup=chart_kb(),
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except Exception as exc:  # reply must never affect registration
        log.warning("ingest reply failed for msg %s: %s", message.message_id, exc)
