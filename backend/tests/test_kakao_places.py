from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.kakao_places import search_kakao_keyword_live, upsert_kakao_docs


class TestSearchKakaoKeywordLive:
    async def test_returns_documents_on_success(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"documents": [{"place_name": "교촌치킨"}]}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.kakao_places.settings") as mock_settings, \
             patch("httpx.AsyncClient", return_value=mock_client):
            mock_settings.KAKAO_REST_API_KEY = "test-key"
            result = await search_kakao_keyword_live("치킨", 37.5, 127.0)

        assert result == [{"place_name": "교촌치킨"}]

    async def test_returns_empty_list_without_api_key(self):
        with patch("app.services.kakao_places.settings") as mock_settings:
            mock_settings.KAKAO_REST_API_KEY = ""
            result = await search_kakao_keyword_live("치킨", 37.5, 127.0)
        assert result == []

    async def test_returns_empty_list_on_http_error(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectTimeout("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.kakao_places.settings") as mock_settings, \
             patch("httpx.AsyncClient", return_value=mock_client):
            mock_settings.KAKAO_REST_API_KEY = "test-key"
            result = await search_kakao_keyword_live("치킨", 37.5, 127.0)

        assert result == []


class TestUpsertKakaoDocs:
    async def test_empty_docs_returns_empty_without_query(self):
        session = AsyncMock()
        result = await upsert_kakao_docs(session, [], ["FOOD"])
        assert result == []
        session.execute.assert_not_called()

    async def test_upserts_and_returns_candidate_rows(self):
        session = AsyncMock()
        returned_row = MagicMock()
        returned_row.mappings.return_value.first.return_value = {
            "place_id": 42, "name": "교촌치킨 강동점", "category": "FD6",
        }
        session.execute = AsyncMock(return_value=returned_row)

        docs = [{
            "id": "999", "place_name": "교촌치킨 강동점", "category_group_code": "FD6",
            "road_address_name": "서울 강동구", "x": "127.12", "y": "37.53",
            "phone": "02-000-0000", "place_url": "http://place.map.kakao.com/999",
        }]
        result = await upsert_kakao_docs(session, docs, ["FOOD", "BAR"])

        assert result == [{"place_id": 42, "name": "교촌치킨 강동점", "category": "FD6"}]
        call_args = session.execute.call_args
        params = call_args.args[1]
        assert params["name"] == "교촌치킨 강동점"
        assert params["external_id"] == "999"

    async def test_continues_past_individual_doc_failure(self):
        second_call_result = MagicMock()
        second_call_result.mappings.return_value.first.return_value = {
            "place_id": 2, "name": "굽네치킨",
        }
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[Exception("db error"), second_call_result])

        docs = [
            {"id": "1", "place_name": "bad", "x": "127.0", "y": "37.0"},
            {"id": "2", "place_name": "굽네치킨", "x": "127.0", "y": "37.0"},
        ]
        result = await upsert_kakao_docs(session, docs, ["FOOD"])
        assert result == [{"place_id": 2, "name": "굽네치킨"}]
