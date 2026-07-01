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
            '{"theme_tags": ["FOOD", "CAFE"], "budget_tier": "UNDER_30000", "companion_type": "COUPLE", "head_count": 2}'
        )
        from app.services.classifier import classify_query
        result = await classify_query("여자친구랑 강남 맛집 데이트")
        assert ThemeTag.FOOD in result.theme_tags
        assert ThemeTag.CAFE in result.theme_tags
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
            '```json\n{"theme_tags": ["CAFE"], "budget_tier": null, "companion_type": "FRIEND", "head_count": 3}\n```'
        )
        from app.services.classifier import classify_query
        result = await classify_query("친구랑 카페 투어")
        assert ThemeTag.CAFE in result.theme_tags
        assert result.companion_type == CompanionType.FRIEND
        assert result.head_count == 3

    @patch("app.services.classifier.get_llm_provider")
    async def test_unknown_theme_tag_skipped(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"theme_tags": ["FOOD", "UNKNOWN_TAG"], "budget_tier": null, "companion_type": null, "head_count": 2}'
        )
        from app.services.classifier import classify_query
        result = await classify_query("밥 먹을 곳")
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
            '{"theme_tags": ["CAFE"], "budget_tier": null, "companion_type": "COUPLE", "head_count": 2}'
        )
        from app.services.classifier import classify_query
        with pytest.raises(NeedsClarificationError) as exc_info:
            await classify_query("카페 데이트")
        err = exc_info.value
        assert err.missing_fields == ["budget_tier"]

    @patch("app.services.classifier.get_llm_provider")
    async def test_needs_clarification_companion_only_missing(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"theme_tags": ["FOOD"], "budget_tier": "UNDER_30000", "companion_type": null, "head_count": 2}'
        )
        from app.services.classifier import classify_query
        with pytest.raises(NeedsClarificationError) as exc_info:
            await classify_query("맛집 탐방")
        err = exc_info.value
        assert err.missing_fields == ["companion_type"]

    @patch("app.services.classifier.get_llm_provider")
    async def test_no_clarification_when_defaults_provided(self, mock_get):
        mock_get.return_value = _mock_provider(
            '{"theme_tags": ["PARK"], "budget_tier": null, "companion_type": null, "head_count": 2}'
        )
        from app.services.classifier import classify_query
        result = await classify_query(
            "공원 산책",
            default_budget_tier=BudgetTier.UNDER_30000,
            default_companion_type=CompanionType.COUPLE,
        )
        assert result.budget_tier == BudgetTier.UNDER_30000
        assert result.companion_type == CompanionType.COUPLE
