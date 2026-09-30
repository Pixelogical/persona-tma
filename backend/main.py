import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import bot.bot as bot_module
from api import api_router
from bot.bot import dp, setup_bot
from config import BASE_DIR, settings
from database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("persona")

FRONTEND_DIST = (BASE_DIR.parent / "frontend" / "dist").resolve()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    log.info("Database ready")

    if settings.persona_chat_id and settings.persona_chat_id > 0:
        log.warning(
            "PERSONA_CHAT_ID=%s looks like a USER id, not a group id — "
            "group songs will be ignored! Group ids are negative (-100...). "
            "Leave it empty to accept all chats.",
            settings.persona_chat_id,
        )

    poll_task = None
    if settings.bot_token and not settings.disable_polling:
        await setup_bot()
        poll_task = asyncio.create_task(
            dp.start_polling(bot_module.bot, allowed_updates=["message"])
        )
        log.info("Bot polling started")
    else:
        log.warning(
            "Bot polling is disabled (set BOT_TOKEN / DISABLE_POLLING in .env)"
        )

    yield

    if poll_task:
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            log.warning("polling stopped with error: %s", exc)
    if bot_module.bot:
        await bot_module.bot.close()


app = FastAPI(title="PersonaBot", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "bot_ready": bot_module.bot is not None,
        "proxy": bool(settings.proxy),
    }


# Serve the built frontend (npm run build) from the same process,
# so a single tunnel/port can serve everything in production.
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:  # pragma: no cover
    log.info("frontend/dist not found — serving API only")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
