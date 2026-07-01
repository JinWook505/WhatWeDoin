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
async def test_report_place_business_hours_text_persisted():
    """Regression test: FE sends {business_hours_text: str}. The Pydantic model
    used to declare `business_hours: dict` (wrong field name), so this payload
    was silently dropped (BaseModel ignores unknown fields by default) and
    business hour reports never persisted despite returning success=True."""
    place = MagicMock()
    place.user_rating_count = 0
    place.user_rating_sum = 0
    place.business_hours = None
    place.price_range = None

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=place)

    from app.core.db import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/places/1/report",
            json={"business_hours_text": "월~금 11:00-22:00, 주말 휴무"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert place.business_hours == "월~금 11:00-22:00, 주말 휴무"


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
