from fastapi import APIRouter

from backend.app.api.routes.dashboard import router as dashboard_router
from backend.app.api.routes.session import router as session_router
from backend.app.api.routes.gifts import router as gifts_router
from backend.app.api.routes.tools import router as tools_router
from backend.app.api.routes.assistant import router as assistant_router


api_router = APIRouter()
api_router.include_router(session_router)
api_router.include_router(gifts_router)
api_router.include_router(tools_router)
api_router.include_router(assistant_router)
api_router.include_router(dashboard_router)
