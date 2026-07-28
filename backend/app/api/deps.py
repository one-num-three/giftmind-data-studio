from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from collections.abc import AsyncGenerator

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.core.security import read_session_token


@dataclass(frozen=True)
class SessionContext:
    session_id: UUID
    expires_at: datetime
    authenticated: bool = True


async def require_session(request: Request) -> SessionContext:
    token = request.cookies.get("giftmind_session")
    payload = read_session_token(token, request.app.state.settings.app_secret) if token else None
    if payload is None:
        raise _unauthorized()

    return SessionContext(
        session_id=UUID(payload["sid"]),
        expires_at=datetime.fromisoformat(payload["expires_at"]),
    )


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession]:
    """Yield an app-scoped database session without introducing user state."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
