from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.deps import get_current_user
from crud import paginated_songs, song_genres, song_to_out
from database import get_db
from models import Song, User, Vote
from schemas import GenreOut, SongListOut, SongOut, VoteIn, VoteOut

router = APIRouter(prefix="/api/songs", tags=["songs"])

TABS = ("trending", "new", "top")


@router.get("", response_model=SongListOut)
def list_songs(
    tab: str = Query("trending"),
    genre: str = Query(None, description="only songs in this genre"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tab = tab.lower()
    if tab not in TABS:
        raise HTTPException(status_code=400, detail=f"tab must be one of {TABS}")
    return SongListOut(
        tab=tab,
        songs=paginated_songs(db, tab, user, limit, offset, genre),
    )


@router.get("/genres", response_model=List[GenreOut])
def list_genres(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Genres available on the chart (from last.fm top tags / file meta)."""
    return [GenreOut(**g) for g in song_genres(db)]


@router.get("/{song_id}", response_model=SongOut)
def get_song(
    song_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    song = db.get(Song, song_id)
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    return song_to_out(db, song, user)


@router.post("/{song_id}/reenrich", response_model=SongOut)
async def reenrich_song(
    song_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-run the last.fm lookup for one song right now (ignoring the backoff)
    and return the updated row. Fixes songs stuck with empty tags/genre."""
    if db.get(Song, song_id) is None:
        raise HTTPException(status_code=404, detail="Song not found")
    from lastfm import enrich_song

    await enrich_song(song_id)
    db.expire_all()
    song = db.get(Song, song_id)
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    return song_to_out(db, song, user)


@router.post("/{song_id}/vote", response_model=VoteOut)
def vote_song(
    song_id: int,
    payload: VoteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    song = db.get(Song, song_id)
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")

    vote = (
        db.query(Vote)
        .filter(Vote.song_id == song_id, Vote.user_id == user.id)
        .first()
    )
    # a brand-new vote rewards the voter with 1 point; editing a vote they
    # already cast gives no extra point.
    gained = 0 if vote else 1
    if vote:
        vote.value = payload.value
    else:
        db.add(Vote(song_id=song_id, user_id=user.id, value=payload.value))
        user.points = (user.points or 0) + 1
    db.commit()

    return VoteOut(
        song=song_to_out(db, song, user),
        points=user.points,
        gained=gained,
    )
