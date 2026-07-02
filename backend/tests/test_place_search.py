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
        async def fake_query(session, station_id, radius_km, theme_tags, exclude_place_ids, limit, menu_keyword=None):
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
        async def fake_query(session, station_id, radius_km, theme_tags, exclude_place_ids, limit, menu_keyword=None):
            nonlocal call_count
            call_count += 1
            return [{"place_id": i} for i in range(10)]

        with patch("app.services.place_search._query", side_effect=fake_query):
            await search_candidate_places(MagicMock(), station_id=1)

        assert call_count == 1

    async def test_menu_keyword_forwarded_to_query(self):
        """SCRUM-97: menu_keyword must reach every _query call (incl. retries)."""
        from app.services.place_search import search_candidate_places

        seen_keywords = []

        async def fake_query(session, station_id, radius_km, theme_tags, exclude_place_ids, limit, menu_keyword=None):
            seen_keywords.append(menu_keyword)
            return [{"place_id": i} for i in range(10)]

        with patch("app.services.place_search._query", side_effect=fake_query), \
             patch("app.services.place_search._live_keyword_fallback", AsyncMock(return_value=[])):
            await search_candidate_places(MagicMock(), station_id=1, menu_keyword="치킨")

        assert seen_keywords == ["치킨"]

    async def test_menu_keyword_boosts_name_match_in_order_clause(self, mock_session):
        from app.services.place_search import search_candidate_places

        with patch("app.services.place_search._live_keyword_fallback", AsyncMock(return_value=[])):
            await search_candidate_places(mock_session, station_id=1, menu_keyword="치킨")

        sql_text = str(mock_session.execute.call_args_list[0].args[0])
        params = mock_session.execute.call_args_list[0].args[1]
        assert "ILIKE" in sql_text
        assert params["menu_kw"] == "%치킨%"

    async def test_no_menu_keyword_omits_ilike_clause(self, mock_session):
        from app.services.place_search import search_candidate_places

        await search_candidate_places(mock_session, station_id=1)

        sql_text = str(mock_session.execute.call_args.args[0])
        params = mock_session.execute.call_args.args[1]
        assert "ILIKE" not in sql_text
        assert "menu_kw" not in params


class TestLiveKeywordFallback:
    async def test_triggers_when_no_local_name_match(self):
        """SCRUM-98: when no local candidate name contains the menu_keyword, fall back
        to a live Kakao keyword search and merge fresh matches to the front."""
        from app.services.place_search import search_candidate_places

        local_results = [{"place_id": 1, "name": "아무거나식당"}]

        async def fake_query(session, station_id, radius_km, theme_tags, exclude_place_ids, limit, menu_keyword=None):
            return local_results

        fresh = [{"place_id": 99, "name": "교촌치킨 강동점"}]
        mock_fallback = AsyncMock(return_value=fresh)

        with patch("app.services.place_search._query", side_effect=fake_query), \
             patch("app.services.place_search._live_keyword_fallback", mock_fallback):
            results = await search_candidate_places(
                MagicMock(), station_id=1, menu_keyword="치킨"
            )

        mock_fallback.assert_awaited_once()
        assert results[0]["place_id"] == 99
        assert results[1]["place_id"] == 1

    async def test_skipped_when_local_name_already_matches(self):
        from app.services.place_search import search_candidate_places

        local_results = [{"place_id": 1, "name": "교촌치킨 강남점"}]

        async def fake_query(session, station_id, radius_km, theme_tags, exclude_place_ids, limit, menu_keyword=None):
            return local_results

        mock_fallback = AsyncMock()

        with patch("app.services.place_search._query", side_effect=fake_query), \
             patch("app.services.place_search._live_keyword_fallback", mock_fallback):
            results = await search_candidate_places(
                MagicMock(), station_id=1, menu_keyword="치킨"
            )

        mock_fallback.assert_not_called()
        assert results == local_results

    async def test_skipped_without_menu_keyword(self):
        from app.services.place_search import search_candidate_places

        local_results = [{"place_id": 1, "name": "아무거나식당"}]

        async def fake_query(session, station_id, radius_km, theme_tags, exclude_place_ids, limit, menu_keyword=None):
            return local_results

        mock_fallback = AsyncMock()

        with patch("app.services.place_search._query", side_effect=fake_query), \
             patch("app.services.place_search._live_keyword_fallback", mock_fallback):
            await search_candidate_places(MagicMock(), station_id=1)

        mock_fallback.assert_not_called()

    async def test_live_keyword_fallback_queries_station_then_upserts(self):
        from app.services.place_search import _live_keyword_fallback

        session = AsyncMock()
        station_result = MagicMock()
        station_result.mappings.return_value.first.return_value = {"lat": 37.53, "lng": 127.12}
        session.execute = AsyncMock(return_value=station_result)

        docs = [{"place_name": "교촌치킨"}]
        upserted = [{"place_id": 99, "name": "교촌치킨"}]

        with patch("app.services.place_search.search_kakao_keyword_live", AsyncMock(return_value=docs)) as mock_search, \
             patch("app.services.place_search.upsert_kakao_docs", AsyncMock(return_value=upserted)) as mock_upsert:
            result = await _live_keyword_fallback(session, station_id=1, menu_keyword="치킨", theme_tags=["FOOD"])

        mock_search.assert_awaited_once_with("치킨", 37.53, 127.12)
        mock_upsert.assert_awaited_once_with(session, docs, ["FOOD"])
        assert result == upserted

    async def test_live_keyword_fallback_returns_empty_when_station_missing(self):
        from app.services.place_search import _live_keyword_fallback

        session = AsyncMock()
        no_station = MagicMock()
        no_station.mappings.return_value.first.return_value = None
        session.execute = AsyncMock(return_value=no_station)

        result = await _live_keyword_fallback(session, station_id=999, menu_keyword="치킨", theme_tags=None)
        assert result == []
