from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, Request, status

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


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
