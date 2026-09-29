from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.deps import get_current_user
from config import settings
from crud import get_or_create_user, top_user_ids, user_rank
from database import get_db
from models import Pin, User, Vote
from schemas import (
    DevLoginIn,
    LeaderboardEntry,
    MeOut,
    TelegramLoginIn,
    TokenOut,
    UserBrief,
)
from security import create_session_token, validate_tma_init_data

router = APIRouter(prefix="/api", tags=["users"])


def _me_out(db: Session, user: User, top_ids) -> MeOut:
    return MeOut(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        points=user.points,
        created_at=user.created_at,
        votes_count=db.scalar(select(func.count(Vote.id)).where(Vote.user_id == user.id)) or 0,
        pins_count=db.scalar(select(func.count(Pin.id)).where(Pin.pinned_by_id == user.id)) or 0,
        is_top3=user.id in top_ids,
        rank=user_rank(db, user),
    )


def _issue(db: Session, user: User) -> TokenOut:
    return TokenOut(
        token=create_session_token(user.id),
        user=_me_out(db, user, set(top_user_ids(db))),
    )


@router.post("/auth/telegram", response_model=TokenOut)
def telegram_login(payload: TelegramLoginIn, db: Session = Depends(get_db)):
    tg_user = validate_tma_init_data(payload.init_data)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Invalid Telegram init data")
    user = get_or_create_user(
        db,
        user_id=int(tg_user["id"]),
        first_name=tg_user.get("first_name", ""),
        last_name=tg_user.get("last_name"),
        username=tg_user.get("username"),
    )
    return _issue(db, user)


@router.get("/auth/config")
def auth_config():
    return {"allow_dev_login": settings.allow_dev_login}


@router.get("/auth/dev-users")
def dev_users(db: Session = Depends(get_db)):
    """Quick pick list for using the app in a normal browser."""
    if not settings.allow_dev_login:
        raise HTTPException(status_code=404, detail="Dev login is disabled")
    users = (
        db.query(User)
        .order_by(User.points.desc(), User.id.asc())
        .limit(8)
        .all()
    )
    return [UserBrief.model_validate(u).model_dump() for u in users]


@router.post("/auth/dev-login", response_model=TokenOut)
def dev_login(payload: DevLoginIn, db: Session = Depends(get_db)):
    if not settings.allow_dev_login:
        raise HTTPException(status_code=404, detail="Dev login is disabled")
    user_id = payload.user_id
    if not user_id:
        max_id = db.scalar(select(func.max(User.id))) or 900000000
        user_id = max_id + 1
    first = (payload.first_name or "").strip()
    if db.get(User, user_id) is None:
        first = first or "Guest"
    user = get_or_create_user(
        db,
        user_id=user_id,
        first_name=first,
        username=(payload.username or "").strip().lstrip("@") or None,
    )
    return _issue(db, user)


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _me_out(db, user, set(top_user_ids(db)))


@router.get("/users/top", response_model=List[LeaderboardEntry])
def leaderboard(db: Session = Depends(get_db)):
    rows = db.execute(
        select(User)
        .order_by(User.points.desc(), User.id.asc())
        .limit(3)
    ).scalars().all()
    entries = []
    for rank, u in enumerate(rows, start=1):
        entries.append(
            LeaderboardEntry(
                user=UserBrief.model_validate(u),
                votes_count=db.scalar(
                    select(func.count(Vote.id)).where(Vote.user_id == u.id)
                ) or 0,
                rank=rank,
            )
        )
    return entries
