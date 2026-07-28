import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import read_session_token
from backend.app.models.operations import RevokedSession


@dataclass(frozen=True)
class SessionContext:
    session_id: UUID
    csrf_token: str
    expires_at: datetime
    authenticated: bool = True


async def require_session(request: Request) -> SessionContext:
    token = request.cookies.get("giftmind_session")
    payload = read_session_token(token, request.app.state.settings.app_secret) if token else None
    if payload is None:
        raise _unauthorized()

    session_id = UUID(payload["sid"])
    expires_at = datetime.fromisoformat(payload["exp"])
    session_factory = request.app.state.session_factory
    async with session_factory() as database_session:
        revoked = await database_session.get(RevokedSession, session_id)
    if revoked is not None:
        raise _unauthorized()
    if expires_at <= datetime.now(UTC):
        raise _unauthorized()
    return SessionContext(session_id=session_id, csrf_token=payload["csrf"], expires_at=expires_at)


async def require_csrf(
    request: Request, session: SessionContext = Depends(require_session)
) -> None:
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        supplied = request.headers.get("X-CSRF-Token")
        if supplied is None or not secrets.compare_digest(supplied, session.csrf_token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
