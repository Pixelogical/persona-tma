from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from config import settings
from crud import get_or_create_user
from database import SessionLocal
from models import Song

log = logging.getLogger("persona.handlers")

router = Router()

MP3_MIME_TYPES = {"audio/mpeg", "audio/mp3", "audio/mp4"}


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
            "mime": a.mime_type,
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
            "mime": doc.mime_type,
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


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 <b>PersonaBot</b> is live.\n\n"
        "Send an <b>MP3 song</b> in the group and I will add it to the "
        "Persona chart automatically — rate it with stars, build playlists "
        "and let the top voters pin their favourites.",
        reply_markup=chart_kb(),
    )


@router.message(Command("chart"))
async def cmd_chart(message: Message) -> None:
    await message.answer(
        "📊 The Persona chart is one tap away:", reply_markup=chart_kb()
    )


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def ingest_audio(message: Message, bot: Bot) -> None:
    if settings.persona_chat_id and message.chat.id != settings.persona_chat_id:
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

        existing = db.query(Song).filter_by(file_unique_id=meta["file_unique_id"]).first()
        if existing:
            # Same song re-uploaded -> refresh its location so pins stay valid
            existing.chat_id = message.chat.id
            existing.message_id = message.message_id
            existing.chat_username = message.chat.username
            db.commit()
            note = (
                f"🔁 <b>{title}</b>"
                + (f" — {artist}" if artist else "")
                + " is already on the chart — I updated its location."
            )
        else:
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
            note = (
                "🎵 New track on the <b>Persona chart</b>!\n\n"
                f"<b>{title}</b>"
                + (f" — {artist}" if artist else "")
                + f"\n👤 Shared by {sender_name}"
                + (
                    f"\n⏱ {meta['duration'] // 60}:{meta['duration'] % 60:02d}"
                    if meta["duration"]
                    else ""
                )
                + "\n\nRate it ⭐ and add it to your playlist in the app."
            )
    finally:
        db.close()

    await message.reply(note, reply_markup=chart_kb(), disable_web_page_preview=True)
