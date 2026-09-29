from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: Optional[str] = None
    first_name: str = ""
    last_name: Optional[str] = None
    points: int = 0

    @property
    def display_name(self) -> str:
        name = " ".join(p for p in (self.first_name, self.last_name) if p)
        return name or self.username or f"user{self.id}"


class UserOut(UserBrief):
    created_at: datetime


class MeOut(UserOut):
    votes_count: int = 0
    pins_count: int = 0
    is_top3: bool = False
    rank: Optional[int] = None


class DevLoginIn(BaseModel):
    user_id: Optional[int] = None
    first_name: Optional[str] = Field(default=None, max_length=64)
    username: Optional[str] = Field(default=None, max_length=32)


class TelegramLoginIn(BaseModel):
    init_data: str


class TokenOut(BaseModel):
    token: str
    user: MeOut


class SenderOut(UserBrief):
    pass


class SongOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    artist: Optional[str] = None
    genre: Optional[str] = None
    duration: int = 0
    created_at: datetime
    sender: SenderOut
    avg: float = 0.0
    votes: int = 0
    my_vote: Optional[int] = None
    link: Optional[str] = None


class SongListOut(BaseModel):
    tab: str
    songs: List[SongOut]


class VoteIn(BaseModel):
    value: int = Field(ge=1, le=5)

    @field_validator("value")
    @classmethod
    def _range(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("stars must be between 1 and 5")
        return v


class VoteOut(BaseModel):
    song: SongOut
    points: int
    gained: int = 1


class PlaylistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("playlist name is required")
        return v


class PlaylistOut(BaseModel):
    id: int
    name: str
    owner: UserBrief
    created_at: datetime
    song_count: int = 0
    avg: float = 0.0
    song_ids: List[int] = []
    is_mine: bool = False


class PlaylistSongOut(BaseModel):
    position: int
    song: SongOut


class PlaylistDetailOut(PlaylistOut):
    songs: List[PlaylistSongOut] = []


class PlaylistAddIn(BaseModel):
    song_id: int


class PlayOut(BaseModel):
    ok: bool
    playlist: str
    started: int
    skipped: int = 0
    interval: float


class PinOut(BaseModel):
    id: int
    song: SongOut
    pinned_by: UserBrief
    link: str
    created_at: datetime
    can_remove: bool = False


class PinCreate(BaseModel):
    song_id: int


class LeaderboardEntry(BaseModel):
    user: UserBrief
    votes_count: int = 0
    rank: int
