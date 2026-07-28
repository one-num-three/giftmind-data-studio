import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from backend.app.api.deps import SessionContext, require_session
from backend.app.core.security import create_session_token
from backend.app.schemas.session import LoginRequest, SessionResponse


router = APIRouter(prefix="/api/session", tags=["session"])
_COOKIE_NAME = "giftmind_session"
_SESSION_DURATION = timedelta(days=7)


@router.post("/login", response_model=SessionResponse)
async def login(request: Request, body: LoginRequest, response: Response) -> SessionResponse:
    if not secrets.compare_digest(body.passcode, request.app.state.settings.team_passcode):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid passcode")

    now = datetime.now(UTC)
    expires_at = now + _SESSION_DURATION
    session_id = uuid4()
    token = create_session_token(session_id, expires_at, request.app.state.settings.app_secret)
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        secure=_is_https(request),
        max_age=int((expires_at - now).total_seconds()),
    )
    return SessionResponse(authenticated=True, expires_at=expires_at)


@router.get("", response_model=SessionResponse)
async def current_session(session: SessionContext = Depends(require_session)) -> SessionResponse:
    return SessionResponse(authenticated=True, expires_at=session.expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response) -> None:
    response.delete_cookie(key=_COOKIE_NAME, httponly=True, samesite="strict", secure=_is_https(request))


def _is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("X-Forwarded-Proto", "").lower() == "https"
