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
from lastfm import run_enrichment_scheduler

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

    if settings.search_type == 1:
        log.info(
            "Ingest matching: by GROUP_NAME = %r", settings.group_name or "(any)"
        )
    elif settings.persona_chat_id:
        log.info(
            "Ingest matching: by chat id = %s (also accepts its -100/short form)",
            settings.persona_chat_id,
        )
        if settings.persona_chat_id > 0:
            log.warning(
                "PERSONA_CHAT_ID=%s looks like a USER id, not a group id — "
                "group songs will be ignored! Group ids are negative.",
                settings.persona_chat_id,
            )
    else:
        log.info("Ingest matching: all chats accepted")

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

    # retry last.fm enrichment for songs that had no luck at ingest time
    enrich_task = None
    if settings.lastfm_enabled and settings.lastfm_api_key:
        enrich_task = asyncio.create_task(run_enrichment_scheduler())
        log.info("last.fm backfill scheduler started")

    yield

    if enrich_task:
        enrich_task.cancel()
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


# uploaded profile pictures — under /api so the vite proxy covers it
from api.profile import AVATAR_DIR  # noqa: E402

AVATAR_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/static/avatars", StaticFiles(directory=AVATAR_DIR), name="avatars")


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
