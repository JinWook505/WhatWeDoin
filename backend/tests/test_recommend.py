import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.core.db import get_db
from app.core.deps import require_current_user
from app.services.classifier import QueryClassification, InvalidQueryError, NeedsClarificationError
from app.services.course_generator import GeneratedCourse, GeneratedStage, StageOption, CourseGenerationError
from app.models.enums import ThemeTag, BudgetTier, CompanionType


def _make_session():
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    # Default: any SELECT looks empty (no quota usage, no cache hit) unless a test overrides
    # session.execute itself. Without this, AsyncMock's auto-chained children make
    # `(await session.execute(...)).mappings()` resolve to another coroutine instead of a mock.
    default_result = MagicMock()
    default_result.mappings.return_value.first.return_value = None
    default_result.mappings.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=default_result)
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
    stages=[
        GeneratedStage(stage_label="식사/카페", options=[
            StageOption(place_id=1, description="커피 한 잔"),
            StageOption(place_id=2, description="맛있는 점심"),
        ]),
        GeneratedStage(stage_label="산책", options=[
            StageOption(place_id=3, description="산책"),
        ]),
    ],
    content_hash="abc123",
)


@pytest.mark.asyncio
async def test_recommend_success():
    mock_session = _make_session()

    mapping_result = MagicMock()
    mapping_result.mappings.return_value.all.return_value = []
    mapping_result.mappings.return_value.first.return_value = None
    mock_session.execute = AsyncMock(return_value=mapping_result)
    mock_session.commit = AsyncMock()

    classification = QueryClassification(
        theme_tags=[ThemeTag.FOOD, ThemeTag.CAFE],
        budget_tier=BudgetTier.UNDER_30000,
        companion_type=CompanionType.COUPLE,
        head_count=2,
    )

    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[require_current_user] = lambda: {
        "id": 1, "preferred_budget": None, "preferred_companion_type": None, "preferred_theme_tags": [],
    }

    with (
        patch("app.routers.recommend.classify_query", AsyncMock(return_value=classification)),
        patch("app.routers.recommend.search_candidate_places", AsyncMock(return_value=CANDIDATES)),
        patch("app.routers.recommend.generate_course", AsyncMock(return_value=GENERATED_COURSE)),
        patch("app.routers.recommend.upsert_course", AsyncMock(return_value=(42, 1.2))),
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
    assert len(data["stages"]) == 2
    assert len(data["stages"][0]["options"]) == 2
    assert data["stages"][0]["options"][0]["name"] == "카페A"
    assert data["stages"][0]["options"][0]["lat"] == 37.5
    assert data["stages"][0]["options"][0]["lng"] == 127.0
    assert data["total_walking_distance_km"] == 1.2
    assert data["served_from"] == "LLM"


@pytest.mark.asyncio
async def test_recommend_invalid_query():
    app.dependency_overrides[get_db] = lambda: _make_session()
    app.dependency_overrides[require_current_user] = lambda: {
        "id": 1, "preferred_budget": None, "preferred_companion_type": None, "preferred_theme_tags": [],
    }

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
async def test_recommend_needs_clarification_when_station_unresolved():
    app.dependency_overrides[get_db] = lambda: _make_session()
    app.dependency_overrides[require_current_user] = lambda: {
        "id": 1, "preferred_budget": None, "preferred_companion_type": None, "preferred_theme_tags": [],
    }

    classification = QueryClassification(
        theme_tags=[ThemeTag.FOOD, ThemeTag.CAFE],
        station_name=None,
        budget_tier=BudgetTier.UNDER_30000,
        companion_type=CompanionType.COUPLE,
        head_count=2,
    )

    with patch("app.routers.recommend.classify_query", AsyncMock(return_value=classification)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/courses/recommend",
                json={"query": "맛있는 거 먹고 카페 가고 싶어"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NEEDS_CLARIFICATION"
    assert "station_id" in body["missing_fields"]


@pytest.mark.asyncio
async def test_recommend_needs_clarification_when_station_unsupported():
    """station_name resolves to a real row, but _resolve_station filters is_supported=false
    (e.g. 인천공항) out, so the DB lookup returns no match and clarification is requested
    instead of silently generating a course for an out-of-service-area station."""
    mock_session = _make_session()
    no_match = MagicMock()
    no_match.mappings.return_value.first.return_value = None
    mock_session.execute = AsyncMock(return_value=no_match)
    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[require_current_user] = lambda: {
        "id": 1, "preferred_budget": None, "preferred_companion_type": None, "preferred_theme_tags": [],
    }

    classification = QueryClassification(
        theme_tags=[ThemeTag.FOOD],
        station_name="인천공항1터미널",
        budget_tier=BudgetTier.UNDER_30000,
        companion_type=CompanionType.COUPLE,
        head_count=1,
    )

    with patch("app.routers.recommend.classify_query", AsyncMock(return_value=classification)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/courses/recommend",
                json={"query": "혼자 인천공항 근처에서 밥먹고싶은데 추천좀 해줘"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NEEDS_CLARIFICATION"
    assert "station_id" in body["missing_fields"]


@pytest.mark.asyncio
async def test_recommend_parsed_input_station_name_resolves_station():
    """Regression: the FE clarification-retry step must be able to carry a previously
    resolved station_name through parsed_input (not just a client-picked stationId),
    otherwise a station resolved on the first pass gets dropped on resubmit."""
    mock_session = _make_session()

    quota_row = MagicMock()
    quota_row.mappings.return_value.first.return_value = {"cnt": 0}
    resolved_station = MagicMock()
    resolved_station.mappings.return_value.first.return_value = {
        "station_id": 127, "name": "인천공항1터미널",
    }
    no_cache_hit = MagicMock()
    no_cache_hit.mappings.return_value.first.return_value = None
    mock_session.execute = AsyncMock(side_effect=[quota_row, resolved_station, no_cache_hit])
    mock_session.commit = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[require_current_user] = lambda: {
        "id": 1, "preferred_budget": None, "preferred_companion_type": None, "preferred_theme_tags": [],
    }

    with (
        patch("app.routers.recommend.search_candidate_places", AsyncMock(return_value=[])),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/courses/recommend",
                json={
                    "query": "혼자 인천공항 근처에서 밥먹고싶은데 추천좀 해줘",
                    "parsed_input": {
                        "theme_tags": ["FOOD"],
                        "budget_tier": "UNDER_30000",
                        "companion_type": None,
                        "head_count": 1,
                        "station_name": "인천공항1터미널",
                    },
                },
            )

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NO_CANDIDATES"


@pytest.mark.asyncio
async def test_recommend_no_candidates():
    app.dependency_overrides[get_db] = lambda: _make_session()
    app.dependency_overrides[require_current_user] = lambda: {
        "id": 1, "preferred_budget": None, "preferred_companion_type": None, "preferred_theme_tags": [],
    }

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
    app.dependency_overrides[require_current_user] = lambda: {
        "id": 1, "preferred_budget": None, "preferred_companion_type": None, "preferred_theme_tags": [],
    }

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
    assert response.json()["detail"]["code"] == "LLM_UNAVAILABLE"


@pytest.mark.asyncio
async def test_build_response_from_course_id_includes_lat_lng_and_total_distance():
    """Cache/idempotency replay path (_build_response_from_course_id) must expose the same
    lat/lng + total_walking_distance_km fields as a freshly generated recommend response."""
    from app.routers.recommend import _build_response_from_course_id

    session = AsyncMock()

    course_result = MagicMock()
    course_result.mappings.return_value.first.return_value = {
        "course_id": 42,
        "theme_tags": ["FOOD"],
        "station_id": 1,
        "total_walking_distance_km": 1.2,
        "station_name": "홍대입구",
    }

    place_result = MagicMock()
    place_result.mappings.return_value.all.return_value = [
        {
            "stage_order": 1, "option_index": 1, "stage_label": "식사/카페",
            "walking_distance_from_station_km": 0.1,
            "place_id": 1, "name": "카페A", "category": "CAFE", "address": "서울",
            "lat": 37.5, "lng": 127.0,
            "business_hours": None, "price_range": "1만원대",
            "user_rating_sum": 10, "user_rating_count": 5,
            "map_url": None, "thumbnail_url": None, "description": "커피 한 잔",
        },
    ]

    session.execute = AsyncMock(side_effect=[course_result, place_result])

    result = await _build_response_from_course_id(session, 42, served_from="CACHE")

    assert result is not None
    assert result["total_walking_distance_km"] == 1.2
    assert result["stages"][0]["options"][0]["lat"] == 37.5
    assert result["stages"][0]["options"][0]["lng"] == 127.0
    assert result["served_from"] == "CACHE"
