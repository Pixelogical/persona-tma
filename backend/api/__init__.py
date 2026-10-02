from fastapi import APIRouter

from api import pins, playlists, profile, songs, users

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(songs.router)
api_router.include_router(profile.router)
api_router.include_router(playlists.router)
api_router.include_router(pins.router)
