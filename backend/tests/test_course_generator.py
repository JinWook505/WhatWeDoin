import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.course_generator import (
    CourseGenerationError,
    GeneratedCourse,
    _compute_content_hash,
    _parse_and_validate,
)


class TestComputeContentHash:
    def test_deterministic(self):
        assert _compute_content_hash([3, 1, 2]) == _compute_content_hash([1, 2, 3])

    def test_different_sets_differ(self):
        assert _compute_content_hash([1, 2, 3]) != _compute_content_hash([1, 2, 4])


class TestParseAndValidate:
    def _valid_response(self, place_ids: list[int]) -> str:
        return json.dumps({
            "title": "홍대 데이트 코스",
            "description": "감성 가득한 코스",
            "places": [{"place_id": pid, "description": f"장소{pid}"} for pid in place_ids],
        })

    def test_valid_response(self):
        candidate_ids = {1, 2, 3}
        result = _parse_and_validate(self._valid_response([1, 2, 3]), candidate_ids)
        assert result is not None
        assert result.place_ids == [1, 2, 3]
        assert result.content_hash == _compute_content_hash([1, 2, 3])

    def test_hallucinated_place_id_returns_none(self):
        candidate_ids = {1, 2, 3}
        result = _parse_and_validate(self._valid_response([1, 2, 99]), candidate_ids)
        assert result is None

    def test_too_few_places_returns_none(self):
        candidate_ids = {1, 2}
        result = _parse_and_validate(self._valid_response([1, 2]), candidate_ids)
        assert result is None

    def test_invalid_json_returns_none(self):
        assert _parse_and_validate("not json", {1, 2, 3}) is None


class TestGenerateCourse:
    _CANDIDATES = [
        {"place_id": i, "name": f"Place{i}", "category": "CAFE",
         "price_range": "1만원대", "user_rating_sum": 0, "user_rating_count": 0}
        for i in range(1, 8)
    ]
    _CANDIDATE_IDS = {c["place_id"] for c in _CANDIDATES}

    def _llm_response(self, place_ids: list[int]) -> str:
        return json.dumps({
            "title": "테스트 코스",
            "description": "설명",
            "places": [{"place_id": pid, "description": f"장소{pid}"} for pid in place_ids],
        })

    async def test_successful_generation(self):
        from app.services.course_generator import generate_course

        mock_llm = AsyncMock()
        mock_llm.chat.return_value = MagicMock(content=self._llm_response([1, 2, 3]))

        with patch("app.services.course_generator.search_candidate_places",
                   AsyncMock(return_value=self._CANDIDATES)), \
             patch("app.services.course_generator.get_llm_provider", return_value=mock_llm):
            result = await generate_course(
                AsyncMock(), station_id=1,
                theme_tags=["CAFE"], budget_tier="UNDER_30000",
                companion_type="COUPLE", query_text="카페 데이트",
            )

        assert result is not None
        assert result.place_ids == [1, 2, 3]
        assert mock_llm.chat.call_count == 1

    async def test_retries_on_hallucination(self):
        from app.services.course_generator import generate_course

        mock_llm = AsyncMock()
        good_response = MagicMock(content=self._llm_response([1, 2, 3]))
        bad_response = MagicMock(content=self._llm_response([1, 2, 999]))  # hallucinated
        mock_llm.chat.side_effect = [bad_response, good_response]

        with patch("app.services.course_generator.search_candidate_places",
                   AsyncMock(return_value=self._CANDIDATES)), \
             patch("app.services.course_generator.get_llm_provider", return_value=mock_llm):
            result = await generate_course(
                AsyncMock(), station_id=1,
                theme_tags=["CAFE"], budget_tier="UNDER_30000",
                companion_type="COUPLE", query_text="카페 데이트",
            )

        assert result is not None
        assert mock_llm.chat.call_count == 2

    async def test_returns_none_after_two_failures(self):
        from app.services.course_generator import generate_course

        mock_llm = AsyncMock()
        mock_llm.chat.return_value = MagicMock(content=self._llm_response([999]))  # always bad

        with patch("app.services.course_generator.search_candidate_places",
                   AsyncMock(return_value=self._CANDIDATES)), \
             patch("app.services.course_generator.get_llm_provider", return_value=mock_llm):
            result = await generate_course(
                AsyncMock(), station_id=1,
                theme_tags=["CAFE"], budget_tier="UNDER_30000",
                companion_type="COUPLE", query_text="카페 데이트",
            )

        assert result is None
        assert mock_llm.chat.call_count == 2

    async def test_raises_when_no_candidates(self):
        from app.services.course_generator import generate_course

        with patch("app.services.course_generator.search_candidate_places",
                   AsyncMock(return_value=[])):
            with pytest.raises(CourseGenerationError, match="NO_CANDIDATES"):
                await generate_course(
                    AsyncMock(), station_id=1,
                    theme_tags=["CAFE"], budget_tier="UNDER_30000",
                    companion_type="COUPLE", query_text="테스트",
                )
