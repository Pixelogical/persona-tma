from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), default="")
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    votes: Mapped[List["Vote"]] = relationship(back_populates="user")
    songs: Mapped[List["Song"]] = relationship(back_populates="sender")
    playlists: Mapped[List["Playlist"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

    @property
    def display_name(self) -> str:
        name = " ".join(p for p in (self.first_name, self.last_name) if p)
        return name or self.username or f"user{self.id}"


class Song(Base):
    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[str] = mapped_column(String(512))
    file_unique_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True
    )
    chat_id: Mapped[int] = mapped_column(Integer, index=True)
    message_id: Mapped[int] = mapped_column(Integer)
    chat_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    title: Mapped[str] = mapped_column(String(255), default="Unknown title")
    artist: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    genre: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    duration: Mapped[int] = mapped_column(Integer, default=0)

    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    sender: Mapped["User"] = relationship(back_populates="songs")
    votes: Mapped[List["Vote"]] = relationship(
        back_populates="song", cascade="all, delete-orphan"
    )
    playlist_links: Mapped[List["PlaylistSong"]] = relationship(
        back_populates="song", cascade="all, delete-orphan"
    )

    @property
    def avg_rating(self) -> float:
        if not self.votes:
            return 0.0
        return sum(v.value for v in self.votes) / len(self.votes)

    @property
    def vote_count(self) -> int:
        return len(self.votes)


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("song_id", "user_id", name="uq_vote_song_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    value: Mapped[int] = mapped_column(Integer)  # 1..5 stars
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    song: Mapped["Song"] = relationship(back_populates="votes")
    user: Mapped["User"] = relationship(back_populates="votes")


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped["User"] = relationship(back_populates="playlists")
    playlist_songs: Mapped[List["PlaylistSong"]] = relationship(
        back_populates="playlist",
        cascade="all, delete-orphan",
        order_by="PlaylistSong.position",
    )

    @property
    def songs(self) -> List["Song"]:
        return [ps.song for ps in self.playlist_songs]


class PlaylistSong(Base):
    __tablename__ = "playlist_songs"
    __table_args__ = (
        UniqueConstraint("playlist_id", "song_id", name="uq_playlist_song"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    playlist_id: Mapped[int] = mapped_column(
        ForeignKey("playlists.id"), index=True
    )
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    playlist: Mapped["Playlist"] = relationship(back_populates="playlist_songs")
    song: Mapped["Song"] = relationship(back_populates="playlist_links")


class Pin(Base):
    __tablename__ = "pins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), index=True)
    pinned_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    link: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    song: Mapped["Song"] = relationship()
    pinned_by: Mapped["User"] = relationship()
