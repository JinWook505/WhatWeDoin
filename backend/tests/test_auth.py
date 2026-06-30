"""Tests for auth service helpers (JWT only — no Kakao API calls)."""
import pytest
from app.services.auth import create_access_token, verify_access_token


def test_access_token_roundtrip():
    token = create_access_token(42)
    assert isinstance(token, str) and len(token) > 10
    user_id = verify_access_token(token)
    assert user_id == 42


def test_invalid_token_returns_none():
    assert verify_access_token("not.a.token") is None


def test_tampered_token_returns_none():
    token = create_access_token(1)
    tampered = token[:-4] + "xxxx"
    assert verify_access_token(tampered) is None


def test_wrong_type_token_returns_none():
    import jwt
    from app.core.config import settings
    from datetime import datetime, timezone, timedelta

    payload = {
        "sub": "99",
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    assert verify_access_token(token) is None
