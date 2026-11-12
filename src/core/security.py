import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from passlib.context import CryptContext

from src.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_SECONDS = 24 * 60 * 60
REMEMBER_ME_SECONDS = 30 * 24 * 60 * 60

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(raw: str) -> str:
    return _pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return _pwd_context.verify(raw, hashed)


def password_stamp(password_changed_at: Optional[datetime]) -> int:
    """Embedded in tokens; changing the password invalidates older tokens."""
    return int(password_changed_at.timestamp() * 1_000_000) if password_changed_at else 0


def create_access_token(
    admin_id: int, remember_me: bool, password_changed_at: Optional[datetime] = None
) -> tuple[str, int]:
    expires_in = REMEMBER_ME_SECONDS if remember_me else ACCESS_TOKEN_SECONDS
    now = _now()
    claims = {
        "sub": str(admin_id),
        "pwd": password_stamp(password_changed_at),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM), expires_in


def decode_access_claims(token: str) -> tuple[int, int]:
    """Return (admin_id, password stamp); raises jose.JWTError on a bad or expired token."""
    claims = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    try:
        return int(claims["sub"]), int(claims.get("pwd", 0))
    except (KeyError, TypeError, ValueError) as exc:
        raise jwt.JWTError("invalid claims") from exc


def decode_access_token(token: str) -> int:
    """Return the admin id; raises jose.JWTError on a bad or expired token."""
    return decode_access_claims(token)[0]


def hash_one_time_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_one_time_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_one_time_token(raw)
