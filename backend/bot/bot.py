import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import BotCommand

from config import settings

log = logging.getLogger("persona.bot")

bot: Optional[Bot] = None
dp = Dispatcher()
_locks: dict = {}  # playlist_id -> asyncio.Lock, prevents double playback


def get_bot() -> Bot:
    if bot is None:
        raise RuntimeError("Bot is not initialised yet")
    return bot


def playlist_lock(playlist_id: int) -> asyncio.Lock:
    if playlist_id not in _locks:
        _locks[playlist_id] = asyncio.Lock()
    return _locks[playlist_id]


def build_bot() -> Bot:
    global bot
    kwargs = {"token": settings.bot_token}
    if settings.proxy:
        log.info("Using proxy: %s", settings.proxy.split("@")[-1])
        kwargs["session"] = AiohttpSession(proxy=settings.proxy)
    _bot = Bot(**kwargs)
    bot = _bot
    return _bot


async def setup_bot() -> None:
    from bot.handlers import router

    _bot = build_bot()
    dp.include_router(router)
    try:
        await _bot.set_my_commands(
            [
                BotCommand(command="start", description="Start PersonaBot"),
                BotCommand(command="chart", description="Open the music chart"),
            ]
        )
    except Exception as exc:  # non fatal
        log.warning("set_my_commands failed: %s", exc)
