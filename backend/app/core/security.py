import secrets
from datetime import UTC, datetime
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from itsdangerous import BadData, URLSafeTimedSerializer


_PASSCODE_HASHER = PasswordHasher()
_SESSION_SALT = "giftmind-session"


def hash_passcode(raw: str) -> str:
    return _PASSCODE_HASHER.hash(raw)


def verify_passcode(raw: str, encoded: str) -> bool:
    try:
        return _PASSCODE_HASHER.verify(encoded, raw)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def create_session_token(session_id: UUID, expires_at: datetime, secret: str) -> str:
    return _serializer(secret).dumps(
        {
            "sid": str(session_id),
            "exp": expires_at.astimezone(UTC).isoformat(),
            "csrf": secrets.token_urlsafe(32),
        }
    )


def read_session_token(token: str, secret: str) -> dict[str, str] | None:
    try:
        payload = _serializer(secret).loads(token)
        expires_at = datetime.fromisoformat(payload["exp"])
        UUID(payload["sid"])
        if expires_at <= datetime.now(UTC):
            return None
        if not isinstance(payload["csrf"], str):
            return None
        return payload
    except (BadData, KeyError, TypeError, ValueError):
        return None


def _serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key=secret, salt=_SESSION_SALT)
