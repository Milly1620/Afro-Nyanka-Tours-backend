from datetime import datetime, timedelta, timezone

import pytest
from jose import JWTError, jwt

from src.core import security
from src.core.config import Settings
from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_one_time_token,
    hash_password,
    new_one_time_token,
    verify_password,
)


def test_password_roundtrip():
    hashed = hash_password("s3cret!")
    assert verify_password("s3cret!", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_access_token_roundtrip():
    token, expires_in = create_access_token(7, False)
    assert decode_access_token(token) == 7
    assert expires_in == 86400
    assert create_access_token(7, True)[1] == 2592000


def test_expired_token_rejected(monkeypatch):
    monkeypatch.setattr(security, "_now", lambda: datetime.now(timezone.utc) - timedelta(days=2))
    token, _ = create_access_token(7, False)
    monkeypatch.undo()
    with pytest.raises(JWTError):
        decode_access_token(token)


def test_jwt_sub_is_string():
    token, _ = create_access_token(7, False)
    claims = jwt.decode(token, "test-secret", algorithms=["HS256"])
    assert claims["sub"] == "7"


def test_one_time_token_hash_matches():
    raw, hashed = new_one_time_token()
    assert hash_one_time_token(raw) == hashed
    assert raw != hashed


def test_default_secret_rejected_in_prod():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            DATABASE_URL="x",
            debug=False,
            secret_key="your-secret-key-here-change-in-production",
        )


def test_default_secret_allowed_in_debug():
    Settings(
        _env_file=None,
        DATABASE_URL="x",
        debug=True,
        secret_key="your-secret-key-here-change-in-production",
    )
