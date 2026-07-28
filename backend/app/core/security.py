from datetime import UTC, datetime, timedelta
from uuid import UUID

from itsdangerous import BadData, URLSafeTimedSerializer


_SESSION_SALT = "giftmind-session"
_SESSION_DURATION = timedelta(days=7)


def create_session_token(session_id: UUID, expires_at: datetime, secret: str) -> str:
    return _serializer(secret).dumps(
        {
            "sid": str(session_id),
            "iat": (expires_at.astimezone(UTC) - _SESSION_DURATION).isoformat(),
        }
    )


def read_session_token(token: str, secret: str) -> dict[str, str] | None:
    try:
        payload = _serializer(secret).loads(token)
        issued_at = datetime.fromisoformat(payload["iat"])
        UUID(payload["sid"])
        if issued_at.tzinfo is None:
            return None
        expires_at = issued_at.astimezone(UTC) + _SESSION_DURATION
        if expires_at <= datetime.now(UTC):
            return None
        if set(payload) != {"sid", "iat"}:
            return None
        return {"sid": payload["sid"], "expires_at": expires_at.isoformat()}
    except (BadData, KeyError, TypeError, ValueError):
        return None


def _serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key=secret, salt=_SESSION_SALT)
