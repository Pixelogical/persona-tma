"""Daily chart digest.

Every night at 00:00 Tehran time the bot posts an elegant summary to the
group chat: tracks shared that day + the top songs of all time. The same
text can be triggered privately by admins with /summary (debug) — that
variant is answered only in the caller's chat, never in the group.

Timestamps in the DB are naive UTC; "a Tehran day" is converted to UTC
boundaries before querying. Tehran has had no DST since 2022, so if the
tz database is unavailable the fixed +03:30 fallback is exact.
"""
from __future__ import annotations

import asyncio
import html
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramAPIError
from aiogram.types import LinkPreviewOptions
from sqlalchemy.orm import joinedload, selectinload

from bot.bot import get_bot
from config import settings
from crud import _load_songs
from database import SessionLocal
from models import Song, chat_id_variants
from security import message_link

log = logging.getLogger("persona.summary")


def _tehran():
    try:
        return ZoneInfo("Asia/Tehran")
    except Exception:  # missing tzdata — Tehran is a permanent +03:30
        return timezone(timedelta(hours=3, minutes=30))


TEHRAN = _tehran()

MEDALS = ("🥇", "🥈", "🥉")


def now_tehran() -> datetime:
    return datetime.now(TEHRAN)


def previous_tehran_day() -> date:
    """The calendar day that has passed — even when called at exactly
    00:00:xx, when "now" already belongs to the new day."""
    return (now_tehran() - timedelta(days=1)).date()


def tehran_day_bounds_utc(day: date) -> tuple:
    """Naive-UTC [start, end) window covering one Tehran calendar day."""
    start = datetime.combine(day, time.min, tzinfo=TEHRAN)
    end = start + timedelta(days=1)
    utc = timezone.utc
    return (
        start.astimezone(utc).replace(tzinfo=None),
        end.astimezone(utc).replace(tzinfo=None),
    )


def _sender_anchor(song: Song) -> str:
    """Sender name linking to their Telegram profile; songs from members
    without a public username stay plain text."""
    name = html.escape(song.sender.display_name)
    username = song.sender.username
    if username:
        return f'<a href="https://t.me/{html.escape(username)}">{name}</a>'
    return name


def _song_line(song: Song, prefix: str) -> str:
    title = html.escape(song.title)
    if song.artist:
        title += f" — {html.escape(song.artist)}"
    link = message_link(song.chat_username, song.chat_id, song.message_id)
    line = f"{prefix}🎵 <a href=\"{link}\">{title}</a> · {_sender_anchor(song)}"
    if song.vote_count:
        votes = "vote" if song.vote_count == 1 else "votes"
        line += f" · ⭐ {song.avg_rating:.1f} · {song.vote_count} {votes}"
    return line


def build_summary_text(day: date) -> str:
    """The digest message for one Tehran day, as HTML."""
    db = SessionLocal()
    try:
        songs = _load_songs(db)
    finally:
        db.close()

    start, end = tehran_day_bounds_utc(day)
    day_songs = sorted(
        (s for s in songs if start <= s.created_at < end),
        key=lambda s: s.created_at,
    )
    top = sorted(
        (s for s in songs if s.vote_count),
        key=lambda s: (s.avg_rating, s.vote_count),
        reverse=True,
    )[: settings.summary_top_count]

    parts = [f"🌌 <b>Persona — Daily Digest</b>\n🗓 {day:%d %b %Y} · Tehran\n"]

    if day_songs:
        parts.append(f"✨ <b>New today — {len(day_songs)} track(s)</b>")
        for index, song in enumerate(day_songs, 1):
            parts.append(_song_line(song, f"{index}. "))
    else:
        parts.append("🌙 No tracks were shared today.")
    if len(day_songs) > settings.summary_top_count:
        parts.append(f"… and {len(day_songs) - settings.summary_top_count} more 🎶")

    parts.append("")
    if top:
        parts.append("🏆 <b>Top of all time</b>")
        for index, song in enumerate(top):
            prefix = MEDALS[index] if index < 3 else f"{index + 1}."
            parts.append(_song_line(song, f"{prefix} "))
    else:
        parts.append("🏆 Nobody has rated a track yet — cast the first ⭐!")
    return "\n".join(parts)


async def send_daily_summary(target_day: Optional[date] = None) -> bool:
    """Post the digest into the group chat. Default target: the Tehran day
    that has just passed (yesterday's chart activity)."""
    chat = settings.summary_chat_id or settings.persona_chat_id
    if not chat:
        log.warning("summary skipped: no SUMMARY_CHAT_ID / PERSONA_CHAT_ID set")
        return False
    day = target_day or previous_tehran_day()
    text = build_summary_text(day)

    bot = get_bot()
    try:
        await bot.send_message(
            chat_id_variants(chat)[0],
            text,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except TelegramAPIError as exc:
        log.warning("daily summary delivery failed: %s", exc)
        return False
    log.info("daily digest for %s delivered to chat %s", day, chat)
    return True


async def run_summary_scheduler() -> None:
    """Fire shortly after every 00:00 Tehran."""
    while True:
        now = now_tehran()
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        delay = max(30.0, (next_midnight - now).total_seconds())
        log.info("next daily digest in %.0f min", delay / 60)
        await asyncio.sleep(delay)
        try:
            await send_daily_summary()
        except Exception:  # pragma: no cover
            log.exception("daily digest failed")
        await asyncio.sleep(90)  # drift safely past the midnight boundary
