from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.deps import get_current_user
from crud import song_to_out, top_user_ids
from database import get_db
from models import Pin, Song, User
from schemas import PinCreate, PinOut, SongOut, UserBrief
from security import message_link

router = APIRouter(prefix="/api/pins", tags=["pins"])


def _pin_out(db: Session, pin: Pin, me: User) -> PinOut:
    return PinOut(
        id=pin.id,
        song=song_to_out(db, pin.song),
        pinned_by=UserBrief.model_validate(pin.pinned_by),
        link=pin.link,
        created_at=pin.created_at,
        can_remove=pin.pinned_by_id == me.id,
    )


def _query(db: Session):
    return db.query(Pin).options(
        joinedload(Pin.song).joinedload(Song.sender),
        joinedload(Pin.song).joinedload(Song.votes),
        joinedload(Pin.pinned_by),
    )


@router.get("", response_model=List[PinOut])
def list_pins(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Pinned songs are public to everyone."""
    pins = _query(db).order_by(Pin.created_at.desc()).all()
    return [_pin_out(db, p, user) for p in pins]


@router.post("", response_model=PinOut, status_code=201)
def pin_song(
    payload: PinCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.id not in top_user_ids(db):
        raise HTTPException(
            status_code=403,
            detail="Only the top 3 voters can pin songs",
        )
    song = (
        db.query(Song)
        .options(joinedload(Song.sender), joinedload(Song.votes))
        .filter(Song.id == payload.song_id)
        .first()
    )
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")

    # one active pin per user: re-pinning moves their card to the new song
    db.query(Pin).filter(Pin.pinned_by_id == user.id).delete()

    pin = Pin(
        song_id=song.id,
        pinned_by_id=user.id,
        link=message_link(song.chat_username, song.chat_id, song.message_id),
    )
    db.add(pin)
    db.commit()
    db.refresh(pin)
    return _pin_out(db, _query(db).filter(Pin.id == pin.id).first(), user)


@router.delete("/{pin_id}", status_code=204)
def unpin(
    pin_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pin = db.get(Pin, pin_id)
    if pin is None:
        raise HTTPException(status_code=404, detail="Pin not found")
    if pin.pinned_by_id != user.id:
        raise HTTPException(status_code=403, detail="You can remove only your own pin")
    db.delete(pin)
    db.commit()
