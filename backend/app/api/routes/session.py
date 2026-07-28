from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import SessionContext, require_csrf, require_session
from backend.app.core.security import create_session_token, read_session_token, verify_passcode
from backend.app.models.operations import RevokedSession
from backend.app.schemas.session import LoginRequest, SessionResponse


router = APIRouter(prefix="/api/session", tags=["session"])
_COOKIE_NAME = "giftmind_session"
_FAILED_LOGIN_LIMIT = 5
_FAILED_LOGIN_WINDOW = timedelta(minutes=15)


@router.post("/login", response_model=SessionResponse)
async def login(request: Request, body: LoginRequest, response: Response) -> SessionResponse:
    now = datetime.now(UTC)
    ip_address = _client_ip(request)
    attempts: deque[datetime] = request.app.state.failed_logins[ip_address]
    _discard_expired_attempts(attempts, now)
    if len(attempts) >= _FAILED_LOGIN_LIMIT:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed login attempts")
    if not verify_passcode(body.passcode, request.app.state.settings.team_passcode_hash):
        attempts.append(now)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid passcode")

    attempts.clear()
    expires_at = now + timedelta(days=request.app.state.settings.session_days)
    session_id = uuid4()
    token = create_session_token(session_id, expires_at, request.app.state.settings.app_secret)
    payload = read_session_token(token, request.app.state.settings.app_secret)
    assert payload is not None
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=_is_https(request),
        max_age=int((expires_at - now).total_seconds()),
    )
    return SessionResponse(csrf_token=payload["csrf"], expires_at=expires_at)


@router.get("", response_model=SessionResponse)
async def current_session(session: SessionContext = Depends(require_session)) -> SessionResponse:
    return SessionResponse(csrf_token=session.csrf_token, expires_at=session.expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
async def logout(request: Request, response: Response, session: SessionContext = Depends(require_session)) -> None:
    session_factory = request.app.state.session_factory
    async with session_factory() as database_session:
        database_session.add(RevokedSession(session_id=session.session_id, expires_at=session.expires_at))
        await database_session.commit()
    response.delete_cookie(key=_COOKIE_NAME, httponly=True, samesite="lax", secure=_is_https(request))


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",", maxsplit=1)[0].strip()
    return request.client.host if request.client else "unknown"


def _discard_expired_attempts(attempts: deque[datetime], now: datetime) -> None:
    while attempts and attempts[0] <= now - _FAILED_LOGIN_WINDOW:
        attempts.popleft()


def _is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("X-Forwarded-Proto", "").lower() == "https"
