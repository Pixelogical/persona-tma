import math
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm import Session

from models import Pin, Song, User, Vote
from schemas import SongOut, UserBrief
from security import message_link

TRENDING_WINDOW_DAYS = 10.0


def get_or_create_user(
    db: Session,
    user_id: int,
    first_name: str = "",
    last_name: Optional[str] = None,
    username: Optional[str] = None,
) -> User:
    user = db.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            first_name=first_name or "",
            last_name=last_name,
            username=username,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        changed = False
        if first_name and user.first_name != first_name:
            user.first_name, changed = first_name, True
        if last_name is not None and user.last_name != last_name:
            user.last_name, changed = last_name, True
        if username and user.username != username:
            user.username, changed = username, True
        if changed:
            db.commit()
            db.refresh(user)
    return user


def find_duplicate(db: Session, key: str) -> Optional[Song]:
    """Song already on the chart with the same normalized title + artist."""
    if not key or key == "|":
        return None
    return db.scalar(select(Song).where(Song.norm_key == key))


def song_to_out(
    db: Session, song: Song, me: Optional[User] = None
) -> SongOut:
    my_vote = None
    if me is not None:
        my_vote = db.scalar(
            select(Vote.value).where(
                Vote.song_id == song.id, Vote.user_id == me.id
            )
        )
    return SongOut(
        id=song.id,
        title=song.title,
        artist=song.artist,
        duration=song.duration,
        created_at=song.created_at,
        sender=UserBrief.model_validate(song.sender),
        avg=round(song.avg_rating, 2),
        votes=song.vote_count,
        my_vote=my_vote,
        link=message_link(song.chat_username, song.chat_id, song.message_id),
        listeners=song.listeners,
        cover=song.cover_url,
    )


def _load_songs(db: Session) -> List[Song]:
    return list(
        db.scalars(
            select(Song)
            .options(
                joinedload(Song.sender),
                selectinload(Song.votes).joinedload(Vote.user),
            )
        ).all()
    )


def _bayesian(song: Song, global_avg: float, m: float = 3.0) -> float:
    v = song.vote_count
    return (v / (v + m)) * song.avg_rating + (m / (v + m)) * global_avg


def sort_songs(db: Session, tab: str) -> List[Song]:
    songs = _load_songs(db)
    now = datetime.utcnow()

    if tab == "new":
        songs.sort(key=lambda s: s.created_at, reverse=True)
        return songs

    if tab == "top":
        all_ratings = [v.value for s in songs for v in s.votes]
        global_avg = (
            sum(all_ratings) / len(all_ratings) if all_ratings else 3.0
        )
        songs.sort(
            key=lambda s: (_bayesian(s, global_avg), s.vote_count), reverse=True
        )
        return songs

    # trending: recent votes weighted by star value + freshness (HN-like decay)
    def score(s: Song) -> float:
        total = 0.0
        for vote in s.votes:
            age_days = max((now - vote.created_at).total_seconds() / 86400.0, 0.0)
            total += vote.value * math.exp(-age_days / TRENDING_WINDOW_DAYS)
        # small boost for freshly added tracks
        age_days = max((now - s.created_at).total_seconds() / 86400.0, 0.0)
        return total + 0.25 * math.exp(-age_days / 3.0)

    songs.sort(key=score, reverse=True)
    return songs


def paginated_songs(
    db: Session,
    tab: str,
    me: Optional[User],
    limit: int,
    offset: int,
) -> List[SongOut]:
    ordered = sort_songs(db, tab)[offset : offset + limit]
    return [song_to_out(db, s, me) for s in ordered]


def top_user_ids(db: Session, n: int = 3) -> List[int]:
    rows = db.execute(
        select(User.id).order_by(User.points.desc(), User.id.asc()).limit(n)
    ).scalars()
    return list(rows)


def user_rank(db: Session, user: User) -> Optional[int]:
    if user.points <= 0:
        return None
    better = db.scalar(
        select(func.count(User.id)).where(User.points > user.points)
    )
    return (better or 0) + 1
