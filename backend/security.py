"""Helpers for Telegram WebApp auth and internal session tokens."""
import base64
import hashlib
import hmac
import json
import time
from typing import Iterator, Optional
from urllib.parse import parse_qsl, unquote, unquote_plus

from config import settings


def _pairs(init_data: str):
    out = []
    for chunk in init_data.split("&"):
        if not chunk:
            continue
        key, _, value = chunk.partition("=")
        if key in ("hash", "secret") or not key:
            continue
        out.append((key, value))
    return out


def _check_candidates(init_data: str) -> Iterator[str]:
    """Telegram clients encode initData values inconsistently: Android is
    effectively single-encoded, Desktop/Web double-encodes (the docs say to
    decode values TWICE). Try every interpretation; an HMAC-SHA256 match on
    any of them can only come from a genuine Telegram signature."""
    raw = _pairs(init_data)
    yield "\n".join(f"{k}={v}" for k, v in sorted(raw))
    yield "\n".join(
        f"{k}={unquote_plus(v)}" for k, v in sorted(raw)
    )
    yield "\n".join(
        f"{k}={unquote_plus(unquote(v))}" for k, v in sorted(raw)
    )


def validate_tma_init_data(init_data: str) -> Optional[dict]:
    """Validate `WebApp.initData` per Telegram docs. Returns the user dict."""
    if not init_data or not settings.bot_token:
        return None

    # keep_blank_values=True is REQUIRED: empty fields (query_id=,
    # start_param=) are part of the signature — Desktop sends them.
    params = dict(parse_qsl(init_data, keep_blank_values=True))
    hash_hex = (params.pop("hash", None) or "").strip()
    if not hash_hex:
        return None

    secret_key = hmac.new(
        b"WebAppData", settings.bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    verified = any(
        hmac.compare_digest(
            hmac.new(secret_key, cand.encode("utf-8"), hashlib.sha256).hexdigest(),
            hash_hex,
        )
        for cand in _check_candidates(init_data)
    )
    if not verified:
        return None

    # Reject clearly ancient logins. Kept generous (7 days): Telegram Desktop
    # reuses one initData blob for a long time, so a tight window would lock
    # desktop users out while Android keeps working.
    try:
        if params.get("auth_date") and time.time() - int(params["auth_date"]) > 7 * 86400:
            return None
    except ValueError:
        return None

    user = _parse_user_field(params.get("user", ""))
    return user if user and "id" in user else None


def _parse_user_field(raw: str) -> Optional[dict]:
    """The `user` JSON may be single- or double-encoded depending on client."""
    for attempt in (raw, unquote_plus(raw), unquote_plus(unquote(raw))):
        try:
            user = json.loads(attempt)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(user, dict) and "id" in user:
            return user
    return None


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
