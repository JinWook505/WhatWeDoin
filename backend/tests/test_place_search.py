from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSearchCandidatePlaces:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        result = MagicMock()
        result.mappings.return_value.all.return_value = [
            {"place_id": 1, "name": "카페A", "user_rating_sum": 0, "user_rating_count": 0,
             "distance_m": 300},
            {"place_id": 2, "name": "식당B", "user_rating_sum": 0, "user_rating_count": 0,
             "distance_m": 500},
            {"place_id": 3, "name": "바C", "user_rating_sum": 0, "user_rating_count": 0,
             "distance_m": 800},
            {"place_id": 4, "name": "공원D", "user_rating_sum": 0, "user_rating_count": 0,
             "distance_m": 900},
            {"place_id": 5, "name": "카라오케E", "user_rating_sum": 0, "user_rating_count": 0,
             "distance_m": 1200},
        ]
        session.execute = AsyncMock(return_value=result)
        return session

    async def test_returns_candidates(self, mock_session):
        from app.services.place_search import search_candidate_places
        results = await search_candidate_places(mock_session, station_id=1)
        assert len(results) == 5
        assert results[0]["place_id"] == 1

    async def test_expands_radius_when_few_results(self):
        """Radius expands 5→7km when fewer than 5 results on first pass."""
        from app.services.place_search import search_candidate_places, _MIN_CANDIDATES

        call_count = 0
        async def fake_query(session, station_id, radius_km, theme_tags, exclude_place_ids, limit):
            nonlocal call_count
            call_count += 1
            if radius_km <= 5.0:
                return [{"place_id": i} for i in range(_MIN_CANDIDATES - 1)]
            return [{"place_id": i} for i in range(10)]

        with patch("app.services.place_search._query", side_effect=fake_query):
            results = await search_candidate_places(MagicMock(), station_id=1)

        assert call_count == 2
        assert len(results) == 10

    async def test_no_expansion_when_enough_results(self):
        """No second query when first pass returns enough candidates."""
        from app.services.place_search import search_candidate_places

        call_count = 0
        async def fake_query(session, station_id, radius_km, theme_tags, exclude_place_ids, limit):
            nonlocal call_count
            call_count += 1
            return [{"place_id": i} for i in range(10)]

        with patch("app.services.place_search._query", side_effect=fake_query):
            await search_candidate_places(MagicMock(), station_id=1)

        assert call_count == 1
