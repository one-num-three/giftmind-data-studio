from fastapi import APIRouter

from backend.app.api.routes.session import router as session_router


api_router = APIRouter()
api_router.include_router(session_router)
