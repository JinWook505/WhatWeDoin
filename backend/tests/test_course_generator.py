import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.course_generator import (
    CourseGenerationError,
    GeneratedStage,
    StageOption,
    _compute_content_hash,
    _parse_and_validate,
)


def _stage(label: str, place_ids: list[int]) -> GeneratedStage:
    return GeneratedStage(
        stage_label=label,
        options=[StageOption(place_id=pid, description=f"장소{pid}") for pid in place_ids],
    )


class TestComputeContentHash:
    def test_deterministic_option_order_within_stage(self):
        a = [_stage("식사", [3, 1, 2])]
        b = [_stage("식사", [1, 2, 3])]
        assert _compute_content_hash(a) == _compute_content_hash(b)

    def test_different_options_differ(self):
        a = [_stage("식사", [1, 2, 3])]
        b = [_stage("식사", [1, 2, 4])]
        assert _compute_content_hash(a) != _compute_content_hash(b)

    def test_stage_order_matters(self):
        """Stage sequence is meaningful (1단계 식사 → 2단계 카페 != 그 반대)."""
        a = [_stage("식사", [1]), _stage("카페", [2])]
        b = [_stage("카페", [2]), _stage("식사", [1])]
        assert _compute_content_hash(a) != _compute_content_hash(b)

    def test_different_labels_differ(self):
        a = [_stage("식사", [1])]
        b = [_stage("디저트", [1])]
        assert _compute_content_hash(a) != _compute_content_hash(b)


class TestParseAndValidate:
    def _valid_response(self, stages: list[tuple[str, list[int]]]) -> str:
        return json.dumps({
            "title": "홍대 데이트 코스",
            "description": "감성 가득한 코스",
            "stages": [
                {
                    "stage_label": label,
                    "options": [{"place_id": pid, "description": f"장소{pid}"} for pid in ids],
                }
                for label, ids in stages
            ],
        })

    def test_valid_multi_option_response(self):
        candidate_ids = {1, 2, 3, 4}
        result = _parse_and_validate(
            self._valid_response([("저녁 식사", [1, 2]), ("카페", [3, 4])]), candidate_ids
        )
        assert result is not None
        assert len(result.stages) == 2
        assert result.stages[0].stage_label == "저녁 식사"
        assert [o.place_id for o in result.stages[0].options] == [1, 2]
        assert result.all_place_ids == [1, 2, 3, 4]

    def test_single_option_stage_allowed(self):
        """A stage with genuinely no alternatives (1 option) should still validate."""
        candidate_ids = {1, 2}
        result = _parse_and_validate(
            self._valid_response([("저녁 식사", [1]), ("카페", [2])]), candidate_ids
        )
        assert result is not None

    def test_hallucinated_place_id_in_any_stage_returns_none(self):
        candidate_ids = {1, 2, 3}
        result = _parse_and_validate(
            self._valid_response([("저녁 식사", [1, 2]), ("카페", [99])]), candidate_ids
        )
        assert result is None

    def test_too_few_stages_returns_none(self):
        candidate_ids = {1, 2}
        result = _parse_and_validate(self._valid_response([("식사", [1, 2])]), candidate_ids)
        assert result is None

    def test_too_many_stages_returns_none(self):
        candidate_ids = {1, 2, 3, 4, 5}
        stages = [(f"단계{i}", [i]) for i in range(1, 6)]  # 5 stages, max is 4
        result = _parse_and_validate(self._valid_response(stages), candidate_ids)
        assert result is None

    def test_too_many_options_in_one_stage_returns_none(self):
        candidate_ids = {1, 2, 3, 4, 5}
        result = _parse_and_validate(
            self._valid_response([("식사", [1, 2, 3, 4]), ("카페", [5])]), candidate_ids
        )
        assert result is None

    def test_duplicate_place_id_across_stages_returns_none(self):
        candidate_ids = {1, 2}
        result = _parse_and_validate(
            self._valid_response([("식사", [1]), ("카페", [1, 2])]), candidate_ids
        )
        assert result is None

    def test_stage_label_too_long_returns_none(self):
        candidate_ids = {1, 2}
        long_label = "가" * 31
        result = _parse_and_validate(
            self._valid_response([(long_label, [1]), ("카페", [2])]), candidate_ids
        )
        assert result is None

    def test_invalid_json_returns_none(self):
        assert _parse_and_validate("not json", {1, 2, 3}) is None


class TestGenerateCourse:
    _CANDIDATES = [
        {"place_id": i, "name": f"Place{i}", "category": "CAFE",
         "price_range": "1만원대", "user_rating_sum": 0, "user_rating_count": 0,
         "distance_m": 500.0}
        for i in range(1, 8)
    ]

    def _llm_response(self, stages: list[tuple[str, list[int]]]) -> str:
        return json.dumps({
            "title": "테스트 코스",
            "description": "설명",
            "stages": [
                {
                    "stage_label": label,
                    "options": [{"place_id": pid, "description": f"장소{pid}"} for pid in ids],
                }
                for label, ids in stages
            ],
        })

    async def test_successful_generation_fetches_weather(self):
        from app.services.course_generator import generate_course

        mock_llm = AsyncMock()
        mock_llm.chat.return_value = MagicMock(
            content=self._llm_response([("저녁 식사", [1, 2]), ("카페", [3])])
        )
        mock_weather = AsyncMock(return_value={"temp": 22.0, "main": "Clear", "description": "맑음"})

        with patch("app.services.course_generator.search_candidate_places",
                   AsyncMock(return_value=self._CANDIDATES)), \
             patch("app.services.course_generator.get_llm_provider", return_value=mock_llm), \
             patch("app.services.course_generator.fetch_weather", mock_weather):
            result = await generate_course(
                AsyncMock(), station_id=1,
                theme_tags=["CAFE"], budget_tier="UNDER_30000",
                companion_type="COUPLE", query_text="카페 데이트",
            )

        assert result is not None
        assert len(result.stages) == 2
        assert mock_llm.chat.call_count == 1
        mock_weather.assert_awaited_once()
        # weather context reached the LLM prompt
        prompt = mock_llm.chat.call_args[0][0][1].content
        assert "맑음" in prompt

    async def test_retries_on_hallucination(self):
        from app.services.course_generator import generate_course

        mock_llm = AsyncMock()
        good_response = MagicMock(content=self._llm_response([("식사", [1, 2]), ("카페", [3])]))
        bad_response = MagicMock(content=self._llm_response([("식사", [1, 999]), ("카페", [3])]))
        mock_llm.chat.side_effect = [bad_response, good_response]

        with patch("app.services.course_generator.search_candidate_places",
                   AsyncMock(return_value=self._CANDIDATES)), \
             patch("app.services.course_generator.get_llm_provider", return_value=mock_llm), \
             patch("app.services.course_generator.fetch_weather", AsyncMock(return_value=None)):
            result = await generate_course(
                AsyncMock(), station_id=1,
                theme_tags=["CAFE"], budget_tier="UNDER_30000",
                companion_type="COUPLE", query_text="카페 데이트",
            )

        assert result is not None
        assert mock_llm.chat.call_count == 2

    async def test_returns_none_after_all_retries_exhausted(self):
        from app.services.course_generator import generate_course

        mock_llm = AsyncMock()
        mock_llm.chat.return_value = MagicMock(
            content=self._llm_response([("식사", [999]), ("카페", [3])])
        )

        with patch("app.services.course_generator.search_candidate_places",
                   AsyncMock(return_value=self._CANDIDATES)), \
             patch("app.services.course_generator.get_llm_provider", return_value=mock_llm), \
             patch("app.services.course_generator.fetch_weather", AsyncMock(return_value=None)):
            result = await generate_course(
                AsyncMock(), station_id=1,
                theme_tags=["CAFE"], budget_tier="UNDER_30000",
                companion_type="COUPLE", query_text="카페 데이트",
            )

        assert result is None
        assert mock_llm.chat.call_count == 3  # generate_course retries 3 times total

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
