"""Helpers for Telegram WebApp auth and internal session tokens."""
import base64
import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.parse import parse_qsl

from config import settings


def validate_tma_init_data(init_data: str) -> Optional[dict]:
    """Validate `WebApp.initData` per Telegram docs. Returns the user dict."""
    if not init_data or not settings.bot_token:
        return None

    # values must be URL-decoded before building the check string.
    # keep_blank_values=True is REQUIRED: Telegram signs over every field,
    # including empty ones (e.g. query_id=, start_param=). The default
    # parser drops them, which breaks the hash for clients that send empty
    # fields — notably Telegram Desktop (Android omits them, so it worked).
    params = dict(parse_qsl(init_data, keep_blank_values=True))
    hash_hex = params.pop("hash", None)
    if not hash_hex:
        return None

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )
    secret_key = hmac.new(
        b"WebAppData", settings.bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    computed = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed, hash_hex):
        return None

    # Reject stale logins (24h)
    try:
        if params.get("auth_date") and time.time() - int(params["auth_date"]) > 86400:
            return None
    except ValueError:
        return None

    try:
        user = json.loads(params.get("user", ""))
    except (json.JSONDecodeError, TypeError):
        return None
    return user if user and "id" in user else None


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _sign(payload: bytes) -> bytes:
    return hmac.new(
        settings.secret_key.encode("utf-8"), payload, hashlib.sha256
    ).digest()


def create_session_token(user_id: int) -> str:
    # ~permanent sessions: the Mini App re-issues this silently on every
    # open inside Telegram, and stored tokens survive a year outside it.
    payload = _b64encode(
        json.dumps({"uid": user_id, "exp": int(time.time()) + 365 * 86400}).encode()
    )
    return f"{payload}.{_b64encode(_sign(payload.encode()))}"


def read_session_token(token: str) -> Optional[int]:
    try:
        payload, signature = token.rsplit(".", 1)
        if not hmac.compare_digest(
            _sign(payload.encode()), _b64decode(signature)
        ):
            return None
        data = json.loads(_b64decode(payload))
        if data.get("exp", 0) < time.time():
            return None
        return int(data["uid"])
    except Exception:
        return None


def message_link(chat_username: Optional[str], chat_id: int, message_id: int) -> str:
    """Public t.me link that deep-links to a message inside the group."""
    if chat_username:
        return f"https://t.me/{chat_username}/{message_id}"
    if settings.chat_link_template:
        return settings.chat_link_template.format(
            chat_id=chat_id, message_id=message_id
        )
    # Private chats without a known invite link -> open the chat itself
    return f"https://t.me/c/{str(chat_id)[-10:]}/{message_id}"
