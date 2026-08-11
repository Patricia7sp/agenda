from fastapi import APIRouter

from app.api.v1 import activities, auth, push

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(activities.router)
api_router.include_router(push.router)
