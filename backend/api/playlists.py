from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from api.deps import get_current_user
from bot.bot import playlist_lock
from bot.playback import play_playlist
from config import settings
from crud import song_to_out
from database import get_db
from models import Playlist, PlaylistSong, Song, User
from schemas import (
    PlayOut,
    PlaylistAddIn,
    PlaylistCreate,
    PlaylistDetailOut,
    PlaylistOut,
    PlaylistSongOut,
)

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


def _playlist_out(db: Session, pl: Playlist, me: User = None) -> PlaylistOut:
    songs = [ps.song for ps in pl.playlist_songs]
    rated = [s for s in songs if s.vote_count]
    avg = (
        round(sum(s.avg_rating for s in rated) / len(rated), 2) if rated else 0.0
    )
    return PlaylistOut(
        id=pl.id,
        name=pl.name,
        owner=_owner(pl),
        created_at=pl.created_at,
        song_count=len(songs),
        avg=avg,
        song_ids=[s.id for s in songs],
        is_mine=bool(me and pl.owner_id == me.id),
    )


def _owner(pl: Playlist):
    from schemas import UserBrief

    return UserBrief.model_validate(pl.owner)


def _get_playlist(db: Session, playlist_id: int) -> Playlist:
    pl = (
        db.query(Playlist)
        .options(
            joinedload(Playlist.playlist_songs).joinedload(PlaylistSong.song).joinedload(
                Song.sender
            ),
            joinedload(Playlist.playlist_songs).joinedload(PlaylistSong.song).joinedload(
                Song.votes
            ),
            joinedload(Playlist.owner),
        )
        .filter(Playlist.id == playlist_id)
        .first()
    )
    if pl is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return pl


@router.get("", response_model=List[PlaylistOut])
def list_playlists(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    # playlists are public — everyone sees everyone's lists
    playlists = (
        db.query(Playlist)
        .options(
            joinedload(Playlist.playlist_songs).joinedload(PlaylistSong.song).joinedload(
                Song.votes
            ),
            joinedload(Playlist.owner),
        )
        .order_by(Playlist.created_at.desc())
        .all()
    )
    return [_playlist_out(db, p, user) for p in playlists]


@router.post("", response_model=PlaylistOut, status_code=201)
def create_playlist(
    payload: PlaylistCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pl = Playlist(name=payload.name[:120], owner_id=user.id)
    db.add(pl)
    db.commit()
    db.refresh(pl)
    return _playlist_out(db, pl, user)


@router.get("/{playlist_id}", response_model=PlaylistDetailOut)
def get_playlist(
    playlist_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pl = _get_playlist(db, playlist_id)
    detail = _playlist_out(db, pl, user).model_dump()
    detail["songs"] = [
        PlaylistSongOut(position=ps.position, song=song_to_out(db, ps.song, user))
        for ps in pl.playlist_songs
    ]
    return PlaylistDetailOut(**detail)


@router.delete("/{playlist_id}", status_code=204)
def delete_playlist(
    playlist_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pl = db.get(Playlist, playlist_id)
    if pl is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if pl.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can delete")
    db.delete(pl)
    db.commit()


@router.post("/{playlist_id}/songs", response_model=PlaylistDetailOut, status_code=201)
def add_song(
    playlist_id: int,
    payload: PlaylistAddIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pl = _get_playlist(db, playlist_id)
    song = db.get(Song, payload.song_id)
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    exists = (
        db.query(PlaylistSong)
        .filter_by(playlist_id=playlist_id, song_id=song.id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Song already in playlist")
    max_pos = (
        db.query(PlaylistSong)
        .filter_by(playlist_id=playlist_id)
        .count()
    )
    db.add(PlaylistSong(playlist_id=playlist_id, song_id=song.id, position=max_pos))
    db.commit()
    return get_playlist(playlist_id, user, db)


@router.delete(
    "/{playlist_id}/songs/{song_id}", response_model=PlaylistDetailOut
)
def remove_song(
    playlist_id: int,
    song_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pl = db.get(Playlist, playlist_id)
    if pl is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if pl.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can edit")
    link = (
        db.query(PlaylistSong)
        .filter_by(playlist_id=playlist_id, song_id=song_id)
        .first()
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Song not in playlist")
    db.delete(link)
    db.flush()  # make the delete visible so renumbering sees the real rows
    # renumber positions so playback order stays dense
    remaining = (
        db.query(PlaylistSong)
        .filter_by(playlist_id=playlist_id)
        .order_by(PlaylistSong.position)
        .all()
    )
    for index, item in enumerate(remaining):
        item.position = index
    db.commit()
    return _get_and_render(playlist_id, user, db)


def _get_and_render(playlist_id: int, user: User, db: Session):
    pl = _get_playlist(db, playlist_id)
    detail = _playlist_out(db, pl, user).model_dump()
    detail["songs"] = [
        PlaylistSongOut(
            position=ps.position, song=song_to_out(db, ps.song, user)
        ).model_dump()
        for ps in pl.playlist_songs
    ]
    return PlaylistDetailOut(**detail)


@router.post("/{playlist_id}/play", response_model=PlayOut)
async def start_playback(
    playlist_id: int,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream every track of the playlist into the user's DM with the bot."""
    from aiogram.exceptions import TelegramForbiddenError

    from bot.bot import get_bot

    pl = db.get(Playlist, playlist_id)
    if pl is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    songs = (
        db.query(PlaylistSong)
        .filter_by(playlist_id=playlist_id)
        .order_by(PlaylistSong.position)
        .all()
    )
    if not songs:
        raise HTTPException(status_code=400, detail="Playlist is empty")
    if playlist_lock(playlist_id).locked():
        raise HTTPException(
            status_code=409, detail="This playlist is already playing"
        )

    # the bot can only DM people who have opened it at least once —
    # hand the frontend a deep link so it can redirect them to press Start.
    # The bot auto-plays the playlist when they do (see bot/handlers.py).
    try:
        await get_bot().send_chat_action(user.id, "typing")
    except TelegramForbiddenError:
        try:
            start_link = f"https://t.me/{get_bot().me.username}?start=play_{playlist_id}"
        except Exception:
            start_link = None
        raise HTTPException(
            status_code=409,
            detail={
                "msg": "You need to press Start in the bot's private chat first",
                "need_start": True,
                "start_link": start_link,
                "playlist_id": playlist_id,
            },
        )
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Bot is not running")

    background.add_task(play_playlist, playlist_id, user.id)
    return PlayOut(
        ok=True,
        playlist=pl.name,
        started=min(len(songs), settings.play_max_songs),
        interval=settings.play_song_interval,
    )
