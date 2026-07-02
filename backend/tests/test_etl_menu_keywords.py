"""Unit tests for etl_menu_keywords data/logic (no network or DB required)."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from scripts.etl_menu_keywords import (
    KakaoQuotaExceededError,
    MENU_KEYWORDS,
    build_place_row,
    fetch_keyword_places,
)


class TestMenuKeywords:
    def test_chicken_maps_to_food_and_bar(self):
        assert MENU_KEYWORDS["치킨"] == ["FOOD", "BAR"]


class TestBuildPlaceRow:
    def _doc(self, **overrides):
        doc = {
            "id": "12345",
            "place_name": "교촌치킨 강동점",
            "category_group_code": "FD6",
            "road_address_name": "서울 강동구 성내로 7",
            "address_name": "서울 강동구 성내동 1",
            "x": "127.1237",
            "y": "37.5301",
            "phone": "02-1234-5678",
            "place_url": "http://place.map.kakao.com/12345",
        }
        doc.update(overrides)
        return doc

    def test_assigns_explicit_theme_tags_not_derived_from_category(self):
        row = build_place_row(self._doc(), ["FOOD", "BAR"])
        assert row["theme_tags"] == ["FOOD", "BAR"]
        assert row["category"] == "FD6"
        assert row["name"] == "교촌치킨 강동점"
        assert row["lat"] == 37.5301
        assert row["lng"] == 127.1237
        assert row["external_id"] == "12345"
        assert row["status"] == "OPEN"

    def test_falls_back_to_address_name_without_road_address(self):
        row = build_place_row(self._doc(road_address_name=""), ["FOOD", "BAR"])
        assert row["address"] == "서울 강동구 성내동 1"


class TestFetchKeywordPlacesQuotaHandling:
    async def test_raises_quota_exceeded_without_retrying(self):
        """SCRUM-98: Kakao's daily quota error (400 + 'limit') must fail fast, not burn
        through MAX_RETRIES retries that can never succeed."""
        response = MagicMock()
        response.status_code = 400
        response.text = '{"errorType":"BadRequest","message":"API limit has been exceeded."}'
        error = httpx.HTTPStatusError("400", request=MagicMock(), response=response)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=error)

        with pytest.raises(KakaoQuotaExceededError):
            await fetch_keyword_places(mock_client, "key", "치킨", 127.0, 37.5)

        assert mock_client.get.await_count == 1

    async def test_other_400_errors_still_retry(self, monkeypatch):
        response = MagicMock()
        response.status_code = 400
        response.text = '{"errorType":"BadRequest","message":"invalid parameter"}'
        error = httpx.HTTPStatusError("400", request=MagicMock(), response=response)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=error)
        monkeypatch.setattr("scripts.etl_menu_keywords.asyncio.sleep", AsyncMock())

        with pytest.raises(httpx.HTTPStatusError):
            await fetch_keyword_places(mock_client, "key", "치킨", 127.0, 37.5)

        assert mock_client.get.await_count == 3
