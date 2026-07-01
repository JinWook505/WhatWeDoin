from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.db import get_db
from app.core.deps import get_current_user_optional


def _make_session(first_row=None):
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    mapping_result = MagicMock()
    mapping_result.mappings.return_value.first.return_value = first_row
    session.execute = AsyncMock(return_value=mapping_result)
    return session


@pytest.mark.asyncio
async def test_placeholder_recent_query_for_logged_in_user():
    app.dependency_overrides[get_db] = lambda: _make_session(
        first_row={"query_text": "홍대에서 친구랑 술 한잔"}
    )
    app.dependency_overrides[get_current_user_optional] = lambda: {"id": 1, "nickname": "test"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/recommend/placeholder")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["source"] == "RECENT"
    assert body["data"]["placeholder"] == "홍대에서 친구랑 술 한잔"


@pytest.mark.asyncio
async def test_placeholder_weather_fallback_when_no_recent_query():
    app.dependency_overrides[get_db] = lambda: _make_session(first_row=None)
    app.dependency_overrides[get_current_user_optional] = lambda: None

    with patch(
        "app.routers.recommend._fetch_weather",
        AsyncMock(return_value={"temp": 5, "main": "Clear", "description": "맑음", "feels_like": 3, "icon": "01d"}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/recommend/placeholder")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["source"] == "WEATHER"
    assert body["data"]["weather"]["main"] == "Clear"


@pytest.mark.asyncio
async def test_placeholder_time_fallback_when_weather_unavailable():
    app.dependency_overrides[get_db] = lambda: _make_session(first_row=None)
    app.dependency_overrides[get_current_user_optional] = lambda: None

    with patch("app.routers.recommend._fetch_weather", AsyncMock(return_value=None)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/recommend/placeholder")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["source"] == "TIME"
    assert body["data"]["placeholder"]
