"""Tests for GET /v1/courses cursor encoding and filtering logic."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.core.db import get_db
from app.main import app
from app.routers.courses import _decode_cursor, _encode_cursor, list_courses


def test_cursor_roundtrip():
    enc = _encode_cursor(82.5, 1234)
    decoded = _decode_cursor(enc)
    assert decoded == (82.5, 1234)


def test_cursor_invalid_returns_none():
    assert _decode_cursor("not-valid-base64!!!") is None


def test_cursor_zero_score():
    enc = _encode_cursor(0.0, 1)
    decoded = _decode_cursor(enc)
    assert decoded == (0.0, 1)


def _make_session(rows=None):
    session = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows or []
    session.execute = AsyncMock(return_value=result)
    return session


def test_theme_array_filter_inlined_not_bound_as_array_param():
    """Regression test for the asyncpg 'sized iterable container expected' bug:
    asyncpg cannot bind a Python str/list to a bound ARRAY(enum) :param, so
    the theme filter must inline validated ThemeTag literals directly into
    the SQL, not pass them through CAST(:themes AS theme_tag[])."""
    import inspect
    src = inspect.getsource(list_courses)
    assert "CAST(:themes AS theme_tag[])" not in src
    assert "::theme_tag" in src


@pytest.mark.asyncio
async def test_invalid_theme_returns_400():
    app.dependency_overrides[get_db] = lambda: _make_session()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/courses", params={"theme": "NOT_A_REAL_TAG"})
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_THEME"


@pytest.mark.asyncio
async def test_invalid_budget_tier_returns_400():
    app.dependency_overrides[get_db] = lambda: _make_session()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/courses", params={"budget_tier": "BUDGET"})
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_BUDGET_TIER"


@pytest.mark.asyncio
async def test_invalid_companion_type_returns_400():
    app.dependency_overrides[get_db] = lambda: _make_session()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/courses", params={"companion_type": "BESTFRIEND"})
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_COMPANION_TYPE"


@pytest.mark.asyncio
async def test_valid_theme_filter_queries_successfully():
    app.dependency_overrides[get_db] = lambda: _make_session(rows=[])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/courses", params={"theme": ["FOOD", "CAFE"]})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["courses"] == []


@pytest.mark.asyncio
async def test_course_detail_og_title_uses_korean_theme_labels():
    """D-24: SEO og.title/description must not leak raw enum codes like 'BAR'."""
    course_row = {
        "course_id": 7, "station_id": 1, "theme_tags": ["BAR", "KARAOKE"],
        "budget_tier": "UNDER_30000", "companion_type": "COUPLE", "head_count": 2,
        "total_walking_distance_km": None, "bayesian_score": 0, "rating_count": 0,
        "rating_sum": 0, "created_at": None, "station_name": "강남",
    }
    session = AsyncMock()
    course_result = MagicMock()
    course_result.mappings.return_value.first.return_value = course_row
    places_result = MagicMock()
    places_result.mappings.return_value.all.return_value = []
    session.execute = AsyncMock(side_effect=[course_result, places_result])

    app.dependency_overrides[get_db] = lambda: session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/courses/7")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    og_title = response.json()["data"]["og"]["title"]
    assert "BAR" not in og_title and "KARAOKE" not in og_title
    assert "술집" in og_title and "노래방" in og_title


@pytest.mark.asyncio
async def test_course_detail_place_category_uses_korean_label():
    """D-24: places.category stores a raw Kakao category_group_code (e.g. 'FD6');
    the API response must translate it, not leak the raw code to the client."""
    course_row = {
        "course_id": 7, "station_id": 1, "theme_tags": ["FOOD"],
        "budget_tier": "UNDER_30000", "companion_type": "COUPLE", "head_count": 2,
        "total_walking_distance_km": None, "bayesian_score": 0, "rating_count": 0,
        "rating_sum": 0, "created_at": None, "station_name": "강남",
    }
    place_row = {
        "visit_order": 1, "place_id": 1, "description": "", "walking_distance_to_next_km": None,
        "name": "테스트 식당", "category": "FD6", "address": None, "lat": None, "lng": None,
        "price_range": None, "business_hours": None, "map_url": None,
        "user_rating_sum": 0, "user_rating_count": 0, "status": "OPEN", "last_synced_at": None,
    }
    session = AsyncMock()
    course_result = MagicMock()
    course_result.mappings.return_value.first.return_value = course_row
    places_result = MagicMock()
    places_result.mappings.return_value.all.return_value = [place_row]
    session.execute = AsyncMock(side_effect=[course_result, places_result])

    app.dependency_overrides[get_db] = lambda: session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/courses/7")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    places = response.json()["data"]["places"]
    assert places[0]["category"] == "음식점"
