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
    ReactionTypeEmoji,
    WebAppInfo,
)
from sqlalchemy import select

from config import settings
from crud import find_duplicate, get_or_create_user
from database import SessionLocal
from models import Song, Vote, norm_key

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
                    text="Open Persona", web_app=WebAppInfo(url=settings.webapp_url)
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


# ---------------- rate a song by replying with a number ----------------
# Replying to a charted audio with ONLY a number (Persian/Arabic/English
# digits) casts that user's rating: <= 1 means 1 star, > 1 means 5 stars.
# A green tick reaction on the reply confirms it.

_DIGITS_TABLE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_ONLY_NUMBER_RE = re.compile(r"^[+-]?\d{1,9}$")


def parse_rating_number(text: Optional[str]) -> Optional[int]:
    """The text must be nothing but a number; returns that number or None."""
    if not text:
        return None
    cleaned = text.replace("\u200c", "").strip().translate(_DIGITS_TABLE)
    if not _ONLY_NUMBER_RE.match(cleaned):
        return None
    return int(cleaned)


def _replied_song(db, chat_id: int, target: Message) -> Optional[Song]:
    """Chart song behind a replied-to message: match by telegram
    file_unique_id first, then by the stored message id in this chat."""
    unique_id = None
    if target.audio:
        unique_id = target.audio.file_unique_id
    elif target.document:
        meta = extract_meta(target)
        unique_id = meta["file_unique_id"] if meta else None
    if unique_id:
        song = db.scalar(select(Song).where(Song.file_unique_id == unique_id))
        if song:
            return song
    return db.scalar(
        select(Song).where(
            Song.message_id == target.message_id,
            Song.chat_id.in_(_chat_id_candidates(chat_id)),
        )
    )


@router.message(F.chat.type != "private", F.reply_to_message, F.text)
async def rate_by_number_reply(message: Message) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return
    number = parse_rating_number(message.text)
    if number is None:
        return
    if not _chat_matches(message):
        return

    value = 1 if number <= 1 else 5
    db = SessionLocal()
    try:
        song = _replied_song(db, message.chat.id, message.reply_to_message)
        if song is None:
            return  # replied to something that is not on the chart — stay silent
        rater = get_or_create_user(
            db,
            user_id=message.from_user.id,
            first_name=message.from_user.first_name or "",
            last_name=message.from_user.last_name,
            username=message.from_user.username,
        )
        vote = (
            db.query(Vote)
            .filter(Vote.song_id == song.id, Vote.user_id == rater.id)
            .first()
        )
        if vote:
            vote.value = value  # updating a rating earns no extra point
        else:
            db.add(Vote(song_id=song.id, user_id=rater.id, value=value))
            rater.points = (rater.points or 0) + 1
        db.commit()
        log.info(
            "user %s rated song #%s (%s★) via number reply %s",
            rater.id, song.id, value, message.text,
        )
    except Exception:  # pragma: no cover
        log.exception("number-rating failed for message %s", message.message_id)
        return
    finally:
        db.close()

    try:
        await message.react([ReactionTypeEmoji(emoji="✅")])
    except Exception as exc:  # reactions may be disabled in some groups
        log.info("reaction failed in chat %s: %s", message.chat.id, exc)
        try:
            await message.reply(
                f"⭐ Rated <b>{html.escape(song.title)}</b> — {value}★",
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
        except Exception:
            pass


def _chat_id_candidates(cid: int) -> set:
    """Return the id as-is plus its sibling form across the -100 prefix.

    The same group can appear as a basic-group id (-3784999585) or as a
    supergroup id (-1003784999585). Both must be treated as equal.
    """
    bare = str(cid).lstrip("-")
    if bare.startswith("100"):
        return {cid, int("-" + bare[3:])}
    return {cid, int("-100" + bare)}


def _chat_matches(message: Message) -> bool:
    """Decide whether an audio in this chat should be ingested."""
    chat = message.chat
    if chat.type == "private":
        # DMs are always accepted (playlists are delivered here)
        return True

    if settings.search_type == 1:
        # match by group title
        if not settings.group_name:
            return True
        return (chat.title or "").strip() == settings.group_name.strip()

    # search_type == 0 -> match by chat id (supergroup-prefix tolerant)
    if settings.persona_chat_id in (None, 0):
        return True
    if chat.id in _chat_id_candidates(settings.persona_chat_id):
        return True

    log.info(
        "ignoring audio in chat id=%s title=%r (search_type=0, "
        "PERSONA_CHAT_ID=%s — set SEARCH_TYPE=1 + GROUP_NAME to match by name)",
        chat.id,
        chat.title,
        settings.persona_chat_id,
    )
    return False


async def _ingest(message: Message) -> None:
    if not message.from_user or message.from_user.is_bot:
        return
    if not _chat_matches(message):
        return

    meta = extract_meta(message)
    if not meta:
        return

    fallback_artist, fallback_title = parse_name(meta["file_name"])
    title = meta["title"] or fallback_title or meta["file_name"] or "Unknown title"
    artist = meta["performer"] or fallback_artist
    key = norm_key(title, artist)

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

        # duplicate = a song with the same normalized title + artist already
        # on the chart → skip it, don't add a second entry.
        dup = find_duplicate(db, key)
        if dup is not None:
            log.info(
                "skipping duplicate #%s '%s' by %s (already chart song #%s)",
                message.message_id,
                title,
                sender_name,
                dup.id,
            )
            skip_note = (
                "🔁 <b>Already on the chart</b> — "
                f"<b>{html.escape(title)}</b>"
                + (f" — {html.escape(artist)}" if artist else "")
                + "\nSame title & artist, so I didn't add it twice."
            )
            try:
                await message.reply(
                    skip_note,
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
            except Exception as exc:
                log.warning("duplicate reply failed for msg %s: %s", message.message_id, exc)
            return

        song = Song(
            file_id=meta["file_id"],
            file_unique_id=meta["file_unique_id"],
            chat_id=message.chat.id,
            message_id=message.message_id,
            chat_username=message.chat.username,
            title=title[:255],
            artist=artist[:255] if artist else None,
            duration=meta["duration"],
            norm_key=key,
            sender_id=sender.id,
        )
        db.add(song)
        db.commit()
        song_id = song.id
        log.info(
            "registered song #%s '%s' by %s in chat %s",
            song_id,
            title,
            sender_name,
            message.chat.id,
        )
    finally:
        db.close()

    # enrich with cover / listeners from last.fm (best-effort)
    if settings.lastfm_enabled and settings.lastfm_api_key:
        from lastfm import enrich_song

        asyncio.create_task(enrich_song(song_id))

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


# ---------------- DM quote-of-the-day ----------------
# Users land in the DM from the Mini App's "Play" button and often just type
# something. Answer every non-command private message with a FRESH time.ir
# quote (no caching — a repeat quote is not acceptable).


def _is_plain_message(message: Message) -> bool:
    """Fallback gate: private chat, anything a user sends except /commands.
    Audio/documents never reach here — ingest_audio is registered first and
    already replies to those."""
    return not (message.text or "").startswith("/")


async def _fresh_quote() -> Optional[dict]:
    from scrape_quote import scrape_quote  # requests-based -> keep off the loop

    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, scrape_quote, "https://time.ir/")
    except Exception:  # network/parse hiccup
        log.exception("time.ir quote scrape failed")
        return None


@router.message(F.chat.type == "private", _is_plain_message)
async def dm_quote_of_the_day(message: Message) -> None:
    if message.from_user and message.from_user.is_bot:
        return
    quote = await _fresh_quote()
    if not quote:
        await message.reply(
            "🙈 Quote service is unreachable right now — try again in a minute.",
            reply_markup=chart_kb(),
        )
        return
    await message.reply(
        "💫 <i>«{q}»</i>\n\n— <b>{a}</b>".format(
            q=html.escape(quote["quote"]),
            a=html.escape(quote["author"]),
        ),
        reply_markup=chart_kb(),
    )
