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
    bot_token: str = "1858481331:AAFYDXqiWrnxegbgZRL6fp6EOT5VP2mCzYs"
    api_id: int = 0
    api_hash: str = ""

    use_proxy: bool = False
    proxy_url: str = ""

    # Only ingest audio from this chat when set (e.g. -1001234567890).
    # Group ids are matched tolerant of the supergroup form:
    # -3784999585 and -1003784999585 are treated as the SAME group.
    persona_chat_id: Optional[int] = -3784999585
    # How to decide which chat songs come from:
    #   0 = match by PERSONA_CHAT_ID (default)
    #   1 = match by GROUP_NAME (chat title, case/whitespace insensitive)
    search_type: int = 0
    group_name: str = "Persona"
    # Permanent invite link for private groups, used to build message links
    chat_link_template: str = ""
    webapp_url: str = "https://excuse-oval-ear-bacteria.trycloudflare.com"

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
    def _blank_chat_id_is_none(cls, v):
        # a blank PERSONA_CHAT_ID= in .env must mean "disabled", not a crash
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("search_type", mode="before")
    @classmethod
    def _blank_search_type_is_zero(cls, v):
        if isinstance(v, str) and not v.strip():
            return 0
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
