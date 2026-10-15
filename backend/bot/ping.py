"""Login nudge: DM the chart admins whenever someone opens the Mini App.

Recipients come ONLY from configuration — LOGIN_PING_USERNAMES (resolved
through the users table) and/or LOGIN_PING_USER_ID — never from the
identity of the person logging in, so the nudge can never be steered to
someone else. Fires at most once per user per debounce window, because
the Mini App silently re-authenticates (late initData / expired token).
"""
from __future__ import annotations

import asyncio
import html
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from aiogram.exceptions import TelegramAPIError
from sqlalchemy import func, select

import bot.bot as bot_module
from bot.bot import get_bot
from config import settings
from database import SessionLocal
from models import User

log = logging.getLogger("persona.ping")

DEBOUNCE = timedelta(seconds=90)
_last_ping: Dict[int, datetime] = {}


def admin_chat_ids() -> List[int]:
    ids = set()
    if settings.login_ping_user_id:
        ids.add(int(settings.login_ping_user_id))
    names = [
        u.strip().lstrip("@").lower()
        for u in settings.login_ping_usernames.split(",")
        if u.strip()
    ]
    if names:
        db = SessionLocal()
        try:
            for name in names:
                uid = db.scalar(
                    select(User.id).where(func.lower(User.username) == name)
                )
                if uid:
                    ids.add(uid)
                else:
                    log.info(
                        "login ping: @%s not seen yet — nudges stay off until "
                        "they use the bot once", name,
                    )
        finally:
            db.close()
    return sorted(ids)


def queue_login_ping(user: User) -> None:
    """Fire-and-forget; must never break the login response."""
    if not settings.login_ping_enabled:
        return
    now = datetime.utcnow()
    last = _last_ping.get(user.id)
    if last and now - last < DEBOUNCE:
        return
    _last_ping[user.id] = now
    loop = bot_module.main_loop
    if loop is None or loop.is_closed():
        log.info("login ping skipped: bot loop not running")
        return
    try:
        asyncio.run_coroutine_threadsafe(_ping(user.id), loop)
    except Exception as exc:  # pragma: no cover
        log.info("login ping scheduling failed: %s", exc)


async def _ping(user_id: int) -> None:
    try:
        admins = admin_chat_ids()
        if not admins or user_id in admins:
            return  # admins logging in are not their own page boys
        db = SessionLocal()
        try:
            u = db.get(User, user_id)
            if u is None:
                return
            name = html.escape(u.display_name)
            username = u.username
            points = u.points or 0
            fresh = (datetime.utcnow() - u.created_at) < timedelta(minutes=1)
        finally:
            db.close()

        who = (
            f'<a href="https://t.me/{html.escape(username)}">@{html.escape(username)}</a>'
            if username
            else f"<code>{user_id}</code>"
        )
        from bot.summary import now_tehran

        when = now_tehran().strftime("%d %b %H:%M")
        text = (
            f"🔑 <b>Mini App login</b>" + (" · 🆕 new user" if fresh else "") + "\n"
            f"👤 {name} · {who}\n"
            f"⭐ {points} points · 🕐 {when} Tehran"
        )
        for admin_id in admins:
            try:
                await get_bot().send_message(admin_id, text)
            except TelegramAPIError as exc:
                log.info("login ping to %s failed: %s", admin_id, exc)
    except Exception:  # pragma: no cover — a nudge must never take anything down
        log.exception("login ping crashed")
