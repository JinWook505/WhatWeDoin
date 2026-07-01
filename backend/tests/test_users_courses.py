"""Tests for GET /v1/users/me/courses (내가 생성한 코스, D-25)."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.core.db import get_db
from app.core.deps import require_current_user
from app.main import app
from app.routers.users import _decode_courses_cursor, _encode_courses_cursor, list_my_courses


def _make_session(rows=None):
    session = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows or []
    session.execute = AsyncMock(return_value=result)
    return session


def test_cursor_roundtrip():
    enc = _encode_courses_cursor("2026-07-01T00:00:00+00:00", 42)
    assert _decode_courses_cursor(enc) == ("2026-07-01T00:00:00+00:00", 42)


def test_cursor_invalid_returns_none():
    assert _decode_courses_cursor("not-valid-base64!!!") is None


def test_list_my_courses_uses_recommendation_requests_not_a_courses_owner_column():
    """Regression guard: courses has no owner column (dedup'd by content_hash),
    so "my courses" must be derived via recommendation_requests.user_id (D-25)."""
    import inspect
    src = inspect.getsource(list_my_courses)
    assert "recommendation_requests" in src
    assert "WHERE user_id = :uid" in src


@pytest.mark.asyncio
async def test_requires_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/users/me/courses")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_returns_courses_for_logged_in_user():
    app.dependency_overrides[get_db] = lambda: _make_session(rows=[])
    app.dependency_overrides[require_current_user] = lambda: {"id": 1, "nickname": "test"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/users/me/courses")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["courses"] == []
    assert body["data"]["next_cursor"] is None


@pytest.mark.asyncio
async def test_invalid_cursor_returns_400():
    app.dependency_overrides[get_db] = lambda: _make_session(rows=[])
    app.dependency_overrides[require_current_user] = lambda: {"id": 1, "nickname": "test"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/users/me/courses", params={"cursor": "not-valid!!"})

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_CURSOR"
