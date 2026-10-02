import logging
import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from api.deps import get_current_user
from config import BASE_DIR
from crud import song_to_out
from database import get_db
from models import ProfileComment, Song, User
from schemas import (
    CommentCreate,
    CommentOut,
    ProfileOut,
    ProfileUpdate,
    UserBrief,
    UserOut,
)

log = logging.getLogger("persona.profile")

router = APIRouter(prefix="/api", tags=["profile"])

# served by main.py under /api/static/avatars (goes through the /api proxy)
AVATAR_DIR = BASE_DIR / "data" / "avatars"
AVATAR_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
AVATAR_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _get_user(db: Session, user_id: int) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    return target


def _profile_out(db: Session, target: User, me: User) -> ProfileOut:
    songs = list(
        db.scalars(
            select(Song)
            .where(Song.sender_id == target.id)
            .options(joinedload(Song.sender), selectinload(Song.votes))
        ).all()
    )
    rated = [s for s in songs if s.vote_count]
    avg = round(sum(s.avg_rating for s in rated) / len(rated), 2) if rated else 0.0
    recent = sorted(songs, key=lambda s: s.created_at, reverse=True)[:3]
    return ProfileOut(
        user=UserOut.model_validate(target),
        songs_sent=len(songs),
        avg_rating=avg,
        rated_songs=len(rated),
        top_songs=[song_to_out(db, s, me) for s in recent],
        is_me=target.id == me.id,
    )


@router.get("/users/{user_id}/profile", response_model=ProfileOut)
def get_profile(
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Public profile: stats, 3 recent sent songs, personality types."""
    return _profile_out(db, _get_user(db, user_id), user)


@router.patch("/me/profile", response_model=ProfileOut)
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if value is None and field != "bio":
            continue  # type fields are NOT NULL — null just means "unchanged"
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return _profile_out(db, user, user)


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = AVATAR_TYPES.get((file.content_type or "").lower())
    if not ext:
        raise HTTPException(
            status_code=415, detail="Only JPEG, PNG or WebP images are allowed"
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > AVATAR_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 2 MB)")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    # replace the previous picture
    if user.avatar and "/avatars/" in user.avatar:
        try:
            (AVATAR_DIR / user.avatar.rsplit("/", 1)[-1]).unlink(missing_ok=True)
        except OSError as exc:
            log.warning("old avatar cleanup failed: %s", exc)

    fname = f"{user.id}-{int(time.time())}{ext}"
    (AVATAR_DIR / fname).write_bytes(data)
    user.avatar = f"/api/static/avatars/{fname}"
    db.commit()
    db.refresh(user)
    log.info("user %s updated avatar -> %s", user.id, fname)
    return UserOut.model_validate(user)


def _comment_out(c: ProfileComment, me: User) -> CommentOut:
    return CommentOut(
        id=c.id,
        text=c.text,
        created_at=c.created_at,
        author=UserBrief.model_validate(c.author),
        can_delete=c.author_id == me.id or c.profile_user_id == me.id,
    )


@router.get("/users/{user_id}/comments", response_model=List[CommentOut])
def list_comments(
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_user(db, user_id)
    rows = db.scalars(
        select(ProfileComment)
        .where(ProfileComment.profile_user_id == user_id)
        .options(joinedload(ProfileComment.author))
        .order_by(ProfileComment.created_at.desc())
        .limit(200)
    ).all()
    return [_comment_out(c, user) for c in rows]


@router.post("/users/{user_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    user_id: int,
    payload: CommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_user(db, user_id)
    comment = ProfileComment(
        profile_user_id=user_id, author_id=user.id, text=payload.text
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment.author = user
    return _comment_out(comment, user)


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = db.get(ProfileComment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    # the writer or the profile owner may remove a comment
    if comment.author_id != user.id and comment.profile_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your comment")
    db.delete(comment)
    db.commit()
    return Response(status_code=204)
