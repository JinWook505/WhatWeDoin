import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.deps import get_current_user_optional
from app.main import app


def _place_mock():
    place = MagicMock()
    place.user_rating_count = 0
    place.user_rating_sum = 0
    place.business_hours = None
    place.price_range = None
    return place


def _db_with_existing_report(place, existing_report):
    """db.get(Place, ...) -> place; db.execute(select(PlaceRatingReport)...) -> existing_report"""
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=place)
    mock_db.add = MagicMock()  # Session.add() is sync; avoid unawaited-coroutine warning
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = existing_report
    mock_db.execute = AsyncMock(return_value=execute_result)
    return mock_db


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
async def test_report_place_rating_logged_in_user_first_time_stores_user_id():
    """로그인 사용자의 최초 평가는 user_id로 저장되고 ip_hash는 비워둔다 (course_reviews 패턴)."""
    place = _place_mock()
    mock_db = _db_with_existing_report(place, existing_report=None)

    from app.core.db import get_db
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user_optional] = lambda: {"id": 42}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/places/1/report", json={"rating": 4.0})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    added = mock_db.add.call_args[0][0]
    assert added.user_id == 42
    assert added.ip_hash is None
    assert place.user_rating_count == 1


@pytest.mark.asyncio
async def test_report_place_rating_logged_in_user_resubmit_updates_existing_row():
    """이미 평가한 로그인 사용자가 재평가하면 기존 행을 갱신하고 이중 반영하지 않는다."""
    place = _place_mock()
    place.user_rating_count = 1
    place.user_rating_sum = 8  # rating 4.0 (rating_x2=8) 최초 등록 상태

    existing_report = MagicMock()
    existing_report.rating_x2 = 8
    mock_db = _db_with_existing_report(place, existing_report=existing_report)

    from app.core.db import get_db
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user_optional] = lambda: {"id": 42}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/places/1/report", json={"rating": 5.0})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    mock_db.add.assert_not_called()
    assert existing_report.rating_x2 == 10
    assert place.user_rating_count == 1  # 새 행이 추가되지 않았다
    assert place.user_rating_sum == 10  # 8 - 8 + 10


@pytest.mark.asyncio
async def test_report_place_rating_anonymous_user_stores_ip_hash():
    """비로그인 사용자의 평가는 ip_hash로 저장되고 user_id는 비워둔다."""
    place = _place_mock()
    mock_db = _db_with_existing_report(place, existing_report=None)

    from app.core.db import get_db
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/places/1/report", json={"rating": 3.0})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    added = mock_db.add.call_args[0][0]
    assert added.user_id is None
    assert added.ip_hash is not None


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
