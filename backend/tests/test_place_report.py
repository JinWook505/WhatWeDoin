import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app


@pytest.mark.asyncio
async def test_report_place_rating_invalid_range():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/places/1/report", json={"rating": 0.5})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_report_place_rating_invalid_step():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/places/1/report", json={"rating": 3.3})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_report_place_not_found():
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)

    with patch("app.routers.places.get_db", return_value=mock_db):
        from app.core.db import get_db
        app.dependency_overrides[get_db] = lambda: mock_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/v1/places/9999/report", json={"price_range": "1만원대"})

        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "PLACE_NOT_FOUND"
