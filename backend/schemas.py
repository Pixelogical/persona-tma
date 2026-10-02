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
    avatar: Optional[str] = None
    mbti: str = "XXXX"
    enneagram: str = "XwX"
    socionics: str = "XXX"

    @property
    def display_name(self) -> str:
        name = " ".join(p for p in (self.first_name, self.last_name) if p)
        return name or self.username or f"user{self.id}"


class UserOut(UserBrief):
    created_at: datetime
    bio: Optional[str] = None


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
    duration: int = 0
    created_at: datetime
    sender: SenderOut
    avg: float = 0.0
    votes: int = 0
    my_vote: Optional[int] = None
    link: Optional[str] = None
    listeners: Optional[int] = None  # global listeners (last.fm)
    cover: Optional[str] = None  # cover art url (last.fm)


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


# ---------------- Profile ----------------

MBTI_TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP",
]
SOCIONICS_TYPES = [
    "ILE", "SEI", "ESE", "LII", "EIE", "LSI", "SLE", "IEI",
    "SEE", "ILI", "EII", "ESI", "LSE", "LIE", "SLI", "IEE",
]
ENNEA_TYPES = [
    "1w9", "1w2", "2w1", "2w3", "3w2", "3w4", "4w3", "4w5", "5w4",
    "5w6", "6w5", "6w7", "7w6", "7w8", "8w7", "8w9", "9w8", "9w1",
]


def _clean_choice(value: str, allowed: List[str], default: str) -> str:
    v = (value or "").strip().upper()
    if not v or v in (default.upper(), "XXXX", "XWX", "XXX"):
        return default
    if v not in allowed:
        raise ValueError(f"must be one of {allowed}")
    return v


class ProfileUpdate(BaseModel):
    bio: Optional[str] = Field(default=None, max_length=280)
    mbti: Optional[str] = Field(default=None, max_length=8)
    enneagram: Optional[str] = Field(default=None, max_length=8)
    socionics: Optional[str] = Field(default=None, max_length=8)

    @field_validator("bio")
    @classmethod
    def _bio(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("mbti")
    @classmethod
    def _mbti(cls, v):
        return None if v is None else _clean_choice(v, MBTI_TYPES, "XXXX")

    @field_validator("socionics")
    @classmethod
    def _socionics(cls, v):
        return None if v is None else _clean_choice(v, SOCIONICS_TYPES, "XXX")

    @field_validator("enneagram")
    @classmethod
    def _ennea(cls, v):
        if v is None:
            return None
        raw = (v or "").strip().upper()
        if not raw or raw in ("XWX", "XXX", "X"):
            return "XwX"
        core = raw if "W" in raw else f"{raw[0]}W{raw[-1]}"
        core = core.lower()
        if core in ENNEA_TYPES:
            return core
        raise ValueError(f"enneagram must be one of {ENNEA_TYPES}")


class ProfileOut(BaseModel):
    user: UserOut
    songs_sent: int = 0
    avg_rating: float = 0.0  # over rated songs the user sent
    rated_songs: int = 0
    top_songs: List[SongOut] = []  # up to 3 recent sent songs
    is_me: bool = False


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=280)

    @field_validator("text")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("comment text is required")
        return v


class CommentOut(BaseModel):
    id: int
    text: str
    created_at: datetime
    author: UserBrief
    can_delete: bool = False
