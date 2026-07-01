import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.core.db import get_db
from app.services.classifier import QueryClassification, InvalidQueryError, NeedsClarificationError
from app.services.course_generator import GeneratedCourse, CourseGenerationError
from app.models.enums import ThemeTag, BudgetTier, CompanionType


def _make_session():
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


CANDIDATES = [
    {"place_id": 1, "name": "카페A", "category": "CAFE", "price_range": "1만원대",
     "user_rating_sum": 10, "user_rating_count": 5, "address": "서울", "lat": 37.5, "lng": 127.0,
     "business_hours": None, "map_url": None, "thumbnail_url": None, "distance_m": 100},
    {"place_id": 2, "name": "식당B", "category": "FOOD", "price_range": "2만원대",
     "user_rating_sum": 8, "user_rating_count": 4, "address": "서울", "lat": 37.5, "lng": 127.0,
     "business_hours": None, "map_url": None, "thumbnail_url": None, "distance_m": 200},
    {"place_id": 3, "name": "공원C", "category": "PARK", "price_range": None,
     "user_rating_sum": 0, "user_rating_count": 0, "address": "서울", "lat": 37.5, "lng": 127.0,
     "business_hours": None, "map_url": None, "thumbnail_url": None, "distance_m": 300},
]

GENERATED_COURSE = GeneratedCourse(
    title="즐거운 홍대 코스",
    description="카페, 밥, 공원을 즐기는 코스",
    place_ids=[1, 2, 3],
    place_descriptions={1: "커피 한 잔", 2: "맛있는 점심", 3: "산책"},
    content_hash="abc123",
)

PLACE_ROWS = [
    {"place_id": 1, "name": "카페A", "category": "CAFE", "address": "서울",
     "business_hours": None, "price_range": "1만원대", "user_rating_sum": 10,
     "user_rating_count": 5, "map_url": None, "thumbnail_url": None},
    {"place_id": 2, "name": "식당B", "category": "FOOD", "address": "서울",
     "business_hours": None, "price_range": "2만원대", "user_rating_sum": 8,
     "user_rating_count": 4, "map_url": None, "thumbnail_url": None},
    {"place_id": 3, "name": "공원C", "category": "PARK", "address": "서울",
     "business_hours": None, "price_range": None, "user_rating_sum": 0,
     "user_rating_count": 0, "map_url": None, "thumbnail_url": None},
]


@pytest.mark.asyncio
async def test_recommend_success():
    mock_session = _make_session()

    mapping_result = MagicMock()
    mapping_result.mappings.return_value.all.return_value = PLACE_ROWS
    mock_session.execute = AsyncMock(return_value=mapping_result)
    mock_session.commit = AsyncMock()

    classification = QueryClassification(
        theme_tags=[ThemeTag.FOOD, ThemeTag.CAFE],
        budget_tier=BudgetTier.UNDER_30000,
        companion_type=CompanionType.COUPLE,
        head_count=2,
    )

    app.dependency_overrides[get_db] = lambda: mock_session

    with (
        patch("app.routers.recommend.classify_query", AsyncMock(return_value=classification)),
        patch("app.routers.recommend.search_candidate_places", AsyncMock(return_value=CANDIDATES)),
        patch("app.routers.recommend.generate_course", AsyncMock(return_value=GENERATED_COURSE)),
        patch("app.routers.recommend.upsert_course", AsyncMock(return_value=42)),
        patch("app.routers.recommend._fetch_place_map", AsyncMock(return_value={
            row["place_id"]: row for row in PLACE_ROWS
        })),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/courses/recommend",
                json={"station_id": 1, "query": "홍대에서 맛있는 거 먹고 카페 가고 싶어"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["course_id"] == 42
    assert data["title"] == "즐거운 홍대 코스"
    assert len(data["places"]) == 3
    assert data["served_from"] == "LLM"


@pytest.mark.asyncio
async def test_recommend_invalid_query():
    app.dependency_overrides[get_db] = lambda: _make_session()

    with patch(
        "app.routers.recommend.classify_query",
        AsyncMock(side_effect=InvalidQueryError("분류 불가")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/courses/recommend",
                json={"station_id": 1, "query": "???"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_QUERY"


@pytest.mark.asyncio
async def test_recommend_no_candidates():
    app.dependency_overrides[get_db] = lambda: _make_session()

    classification = QueryClassification(
        theme_tags=[ThemeTag.FOOD],
        budget_tier=None,
        companion_type=None,
        head_count=2,
    )

    with (
        patch("app.routers.recommend.classify_query", AsyncMock(return_value=classification)),
        patch("app.routers.recommend.search_candidate_places", AsyncMock(return_value=[])),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/courses/recommend",
                json={"station_id": 999, "query": "맛집"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NO_CANDIDATES"


@pytest.mark.asyncio
async def test_recommend_generation_failed():
    app.dependency_overrides[get_db] = lambda: _make_session()

    classification = QueryClassification(
        theme_tags=[ThemeTag.FOOD],
        budget_tier=None,
        companion_type=None,
        head_count=2,
    )

    with (
        patch("app.routers.recommend.classify_query", AsyncMock(return_value=classification)),
        patch("app.routers.recommend.search_candidate_places", AsyncMock(return_value=CANDIDATES)),
        patch("app.routers.recommend.generate_course", AsyncMock(return_value=None)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/courses/recommend",
                json={"station_id": 1, "query": "맛집"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "GENERATION_FAILED"
