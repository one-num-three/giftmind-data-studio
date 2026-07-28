from fastapi import APIRouter

from backend.app.api.routes.session import router as session_router
from backend.app.api.routes.gifts import router as gifts_router


api_router = APIRouter()
api_router.include_router(session_router)
api_router.include_router(gifts_router)
