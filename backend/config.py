"""Central configuration for PersonaBot.

Every value can be overridden through environment variables or a
`backend/.env` file (see `backend/.env.example`).
"""
from pathlib import Path
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------------- Telegram ----------------
    # NEVER hardcode the token here — put it in backend/.env (gitignored)
    bot_token: str = ""
    api_id: int = 0
    api_hash: str = ""

    use_proxy: bool = False
    proxy_url: str = ""

    # Only ingest audio from this chat when set. MUST be the GROUP id,
    # which is always NEGATIVE (e.g. -1001234567890). A positive id is a
    # private user chat. Leave empty to accept any chat (recommended).
    persona_chat_id: Optional[int] = None
    # Permanent invite link for private groups, used to build message links
    chat_link_template: str = ""
    webapp_url: str = ""

    # ---------------- Database ----------------
    database_url: str = "sqlite:///./data/persona.db"

    # ---------------- Server ----------------
    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: str = "*"

    secret_key: str = "change-me-please"
    allow_dev_login: bool = True
    disable_polling: bool = False

    # ---------------- Playback ----------------
    play_song_interval: float = 1.5
    play_max_songs: int = 50
    play_intro: bool = True

    @field_validator("persona_chat_id", mode="before")
    @classmethod
    def _empty_is_none(cls, v):
        # PERSONA_CHAT_ID= (blank in .env) must mean "disabled", not a crash
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @property
    def proxy(self) -> Optional[str]:
        if self.use_proxy and self.proxy_url:
            return self.proxy_url
        return None

    @property
    def cors_origin_list(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
