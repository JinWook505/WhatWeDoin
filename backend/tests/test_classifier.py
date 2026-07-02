from unittest.mock import AsyncMock, patch

import pytest

from app.models.enums import BudgetTier, CompanionType, ThemeTag
from app.services.llm.base import LLMResponse
from app.services.classifier import NeedsClarificationError


def _mock_provider(content: str):
    resp = LLMResponse(content=content, model="gemini-3.1-flash-lite", usage={})
    provider = AsyncMock()
    provider.chat = AsyncMock(return_value=resp)
    return provider


class TestClassifyQuery:
    @patch("app.services.classifier.get_llm_provider")
    async def test_basic_classification(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"station_name": "강남", "theme_tags": ["FOOD", "CAFE"], "budget_tier": "UNDER_30000", "companion_type": "COUPLE", "head_count": 2}'
        )
        from app.services.classifier import classify_query
        result = await classify_query("여자친구랑 강남 맛집 데이트")
        assert ThemeTag.FOOD in result.theme_tags
        assert ThemeTag.CAFE in result.theme_tags
        assert result.station_name == "강남"
        assert result.budget_tier == BudgetTier.UNDER_30000
        assert result.companion_type == CompanionType.COUPLE
        assert result.head_count == 2

    @patch("app.services.classifier.get_llm_provider")
    async def test_invalid_query_raises(self, mock_get):
        mock_get.return_value = _mock_provider('{"error": "INVALID_QUERY"}')
        from app.services.classifier import classify_query, InvalidQueryError
        with pytest.raises(InvalidQueryError):
            await classify_query("ㅁㄴㅇㄹ 12345 !@#$")

    @patch("app.services.classifier.get_llm_provider")
    async def test_json_in_codeblock(self, mock_get):
        mock_get.return_value = _mock_provider(
            '```json\n{"station_name": "홍대입구", "theme_tags": ["CAFE"], "budget_tier": "UNDER_30000", "companion_type": "FRIEND", "head_count": 3}\n```'
        )
        from app.services.classifier import classify_query
        result = await classify_query("친구랑 홍대에서 카페 투어")
        assert ThemeTag.CAFE in result.theme_tags
        assert result.companion_type == CompanionType.FRIEND
        assert result.head_count == 3

    @patch("app.services.classifier.get_llm_provider")
    async def test_unknown_theme_tag_skipped(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"station_name": "합정", "theme_tags": ["FOOD", "UNKNOWN_TAG"], "budget_tier": "UNDER_30000", "companion_type": "SOLO", "head_count": 2}'
        )
        from app.services.classifier import classify_query
        result = await classify_query("합정에서 밥 먹을 곳")
        assert result.theme_tags == [ThemeTag.FOOD]

    @patch("app.services.classifier.get_llm_provider")
    async def test_head_count_clamped(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"theme_tags": ["ACTIVITY"], "budget_tier": null, "companion_type": null, "head_count": 99}'
        )
        from app.services.classifier import classify_query
        with pytest.raises(NeedsClarificationError):
            await classify_query("단체 액티비티")

    @patch("app.services.classifier.get_llm_provider")
    async def test_needs_clarification_both_missing(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"theme_tags": ["FOOD"], "budget_tier": null, "companion_type": null, "head_count": 2}'
        )
        from app.services.classifier import classify_query
        with pytest.raises(NeedsClarificationError) as exc_info:
            await classify_query("홍대 맛집")
        err = exc_info.value
        assert "companion_type" in err.missing_fields
        assert "budget_tier" in err.missing_fields
        assert err.partial_parsed_input["theme_tags"] == ["FOOD"]
        assert err.partial_parsed_input["head_count"] == 2

    @patch("app.services.classifier.get_llm_provider")
    async def test_needs_clarification_budget_only_missing(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"station_name": "합정", "theme_tags": ["CAFE"], "budget_tier": null, "companion_type": "COUPLE", "head_count": 2}'
        )
        from app.services.classifier import classify_query
        with pytest.raises(NeedsClarificationError) as exc_info:
            await classify_query("합정에서 카페 데이트")
        err = exc_info.value
        assert err.missing_fields == ["budget_tier"]

    @patch("app.services.classifier.get_llm_provider")
    async def test_needs_clarification_companion_only_missing(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"station_name": "합정", "theme_tags": ["FOOD"], "budget_tier": "UNDER_30000", "companion_type": null, "head_count": 2}'
        )
        from app.services.classifier import classify_query
        with pytest.raises(NeedsClarificationError) as exc_info:
            await classify_query("맛집 탐방")
        err = exc_info.value
        assert err.missing_fields == ["companion_type"]

    @patch("app.services.classifier.get_llm_provider")
    async def test_no_clarification_when_defaults_provided(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"station_name": "여의도", "theme_tags": ["PARK"], "budget_tier": null, "companion_type": null, "head_count": 2}'
        )
        from app.services.classifier import classify_query
        result = await classify_query(
            "여의도에서 공원 산책",
            default_budget_tier=BudgetTier.UNDER_30000,
            default_companion_type=CompanionType.COUPLE,
        )
        assert result.budget_tier == BudgetTier.UNDER_30000
        assert result.companion_type == CompanionType.COUPLE

    @patch("app.services.classifier.get_llm_provider")
    async def test_default_theme_tags_used_when_none_extracted(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"station_name": "여의도", "theme_tags": [], "budget_tier": "UNDER_30000", "companion_type": "SOLO", "head_count": 1}'
        )
        from app.services.classifier import classify_query
        result = await classify_query(
            "여의도에서 놀고 싶어",
            default_theme_tags=[ThemeTag.PARK, ThemeTag.CAFE],
        )
        assert result.theme_tags == [ThemeTag.PARK, ThemeTag.CAFE]

    @patch("app.services.classifier.get_llm_provider")
    async def test_invalid_query_when_no_theme_and_no_default(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"station_name": "여의도", "theme_tags": [], "budget_tier": "UNDER_30000", "companion_type": "SOLO", "head_count": 1}'
        )
        from app.services.classifier import classify_query, InvalidQueryError
        with pytest.raises(InvalidQueryError):
            await classify_query("여의도에서 놀고 싶어")

    @patch("app.services.classifier.get_llm_provider")
    async def test_menu_keyword_extracted(self, mock_get):
        """SCRUM-97: '치맥' → menu_keyword '치킨' so candidate search can prioritize it."""
        mock_get.return_value = _mock_provider(
            '{"station_name": "강동", "theme_tags": ["FOOD", "BAR"], "budget_tier": "UNDER_30000", '
            '"companion_type": "FRIEND", "head_count": 2, "menu_keyword": "치킨"}'
        )
        from app.services.classifier import classify_query
        result = await classify_query("강동에서 치맥할건데 추천해줘")
        assert result.menu_keyword == "치킨"

    @patch("app.services.classifier.get_llm_provider")
    async def test_menu_keyword_null_for_generic_request(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"station_name": "강남", "theme_tags": ["FOOD"], "budget_tier": "UNDER_30000", '
            '"companion_type": "FRIEND", "head_count": 2, "menu_keyword": null}'
        )
        from app.services.classifier import classify_query
        result = await classify_query("강남에서 밥 먹을 곳")
        assert result.menu_keyword is None

    @patch("app.services.classifier.get_llm_provider")
    async def test_menu_keyword_carried_through_needs_clarification(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"theme_tags": ["FOOD"], "budget_tier": "UNDER_30000", "companion_type": "SOLO", '
            '"head_count": 1, "menu_keyword": "치킨"}'
        )
        from app.services.classifier import classify_query
        with pytest.raises(NeedsClarificationError) as exc_info:
            await classify_query("치킨 먹을 곳 추천해줘")
        assert exc_info.value.partial_parsed_input["menu_keyword"] == "치킨"

    @patch("app.services.classifier.get_llm_provider")
    async def test_needs_clarification_station_missing(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"theme_tags": ["FOOD"], "budget_tier": "UNDER_30000", "companion_type": "SOLO", "head_count": 1}'
        )
        from app.services.classifier import classify_query
        with pytest.raises(NeedsClarificationError) as exc_info:
            await classify_query("혼자 밥 먹을 곳 추천해줘")
        assert exc_info.value.missing_fields == ["station_id"]
