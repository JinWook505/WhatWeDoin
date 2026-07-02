import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.course_generator import (
    CourseGenerationError,
    GeneratedStage,
    StageOption,
    _build_candidate_prompt,
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

    def test_single_stage_rejected_by_default_min_stages(self):
        candidate_ids = {1, 2}
        result = _parse_and_validate(self._valid_response([("식사", [1, 2])]), candidate_ids)
        assert result is None

    def test_single_stage_accepted_with_min_stages_one(self):
        """SCRUM-95: single-category requests pass min_stages=1 to allow a 1-stage course."""
        candidate_ids = {1, 2}
        result = _parse_and_validate(
            self._valid_response([("밥집", [1, 2])]), candidate_ids, min_stages=1
        )
        assert result is not None
        assert len(result.stages) == 1


class TestBuildCandidatePrompt:
    def test_uses_korean_category_label_not_raw_code(self):
        """SCRUM-96: raw Kakao category_group_code (e.g. FD6) is meaningless to the LLM;
        the prompt must send the translated Korean label instead."""
        candidates = [
            {"place_id": 1, "name": "노랑저고리 강남점", "category": "FD6",
             "price_range": "3만원대", "user_rating_sum": 0, "user_rating_count": 0},
        ]
        prompt = _build_candidate_prompt(
            "밥집만 추천해줘", candidates, ["FOOD"], "UNDER_30000", "FAMILY", None
        )
        assert "음식점" in prompt
        assert "FD6" not in prompt

    def test_menu_keyword_adds_priority_instruction(self):
        """SCRUM-97: an explicit menu_keyword (e.g. '치킨' from '치맥') must tell the LLM
        to prioritize name-matching candidates when a genuine match exists."""
        candidates = [
            {"place_id": 1, "name": "교촌치킨 강동점", "category": "FD6",
             "price_range": "3만원대", "user_rating_sum": 0, "user_rating_count": 0},
        ]
        prompt = _build_candidate_prompt(
            "강동에서 치맥할건데 추천해줘", candidates, ["FOOD", "BAR"],
            "UNDER_30000", "FRIEND", None, menu_keyword="치킨",
        )
        assert "치킨" in prompt
        assert "최우선" in prompt
        assert "일치하는 장소가 없습니다" not in prompt

    def test_menu_keyword_with_no_name_match_warns_against_false_claim(self):
        """SCRUM-98: when no candidate name actually contains the menu_keyword, the LLM
        must be told not to fabricate that menu for an unrelated place (e.g. labeling
        '마곡닭한마리' — a whole-chicken hot pot, not fried chicken — as a '치킨' spot)."""
        candidates = [
            {"place_id": 1, "name": "마곡닭한마리 강동직영점", "category": "FD6",
             "price_range": "3만원대", "user_rating_sum": 0, "user_rating_count": 0},
        ]
        prompt = _build_candidate_prompt(
            "강동에서 치맥할건데 추천해줘", candidates, ["FOOD", "BAR"],
            "UNDER_30000", "FRIEND", None, menu_keyword="치킨",
        )
        assert "일치하는 장소가 없습니다" in prompt
        assert "단정하지 마세요" in prompt
        assert "최우선으로 선택하세요" not in prompt

    def test_no_menu_keyword_omits_priority_instruction(self):
        candidates = [
            {"place_id": 1, "name": "노랑저고리 강남점", "category": "FD6",
             "price_range": "3만원대", "user_rating_sum": 0, "user_rating_count": 0},
        ]
        prompt = _build_candidate_prompt(
            "밥집만 추천해줘", candidates, ["FOOD"], "UNDER_30000", "FAMILY", None
        )
        assert "최우선" not in prompt


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

    async def test_single_category_theme_tags_allows_one_stage_course(self):
        """SCRUM-95: a single theme_tag (e.g. 밥집만 추천해줘 → ["FOOD"]) should let the
        LLM's 1-stage response validate instead of being rejected for too-few-stages."""
        from app.services.course_generator import generate_course

        mock_llm = AsyncMock()
        mock_llm.chat.return_value = MagicMock(
            content=self._llm_response([("밥집", [1, 2, 3])])
        )

        with patch("app.services.course_generator.search_candidate_places",
                   AsyncMock(return_value=self._CANDIDATES)), \
             patch("app.services.course_generator.get_llm_provider", return_value=mock_llm), \
             patch("app.services.course_generator.fetch_weather", AsyncMock(return_value=None)):
            result = await generate_course(
                AsyncMock(), station_id=1,
                theme_tags=["FOOD"], budget_tier="UNDER_30000",
                companion_type="COUPLE", query_text="밥집만 추천해줘",
            )

        assert result is not None
        assert len(result.stages) == 1
        assert mock_llm.chat.call_count == 1

    async def test_multi_category_theme_tags_still_requires_two_stages(self):
        """General/compound requests (2+ theme_tags) keep the existing 2-stage minimum:
        a 1-stage LLM response should be rejected and retried until exhausted."""
        from app.services.course_generator import generate_course

        mock_llm = AsyncMock()
        mock_llm.chat.return_value = MagicMock(
            content=self._llm_response([("밥집", [1, 2])])
        )

        with patch("app.services.course_generator.search_candidate_places",
                   AsyncMock(return_value=self._CANDIDATES)), \
             patch("app.services.course_generator.get_llm_provider", return_value=mock_llm), \
             patch("app.services.course_generator.fetch_weather", AsyncMock(return_value=None)):
            result = await generate_course(
                AsyncMock(), station_id=1,
                theme_tags=["FOOD", "CAFE"], budget_tier="UNDER_30000",
                companion_type="COUPLE", query_text="맛집이랑 카페 코스 추천해줘",
            )

        assert result is None
        assert mock_llm.chat.call_count == 3

    async def test_menu_keyword_forwarded_to_candidate_search(self):
        """SCRUM-97: when generate_course fetches its own candidates (no pre_fetched_candidates),
        menu_keyword must reach search_candidate_places for name-priority boosting."""
        from app.services.course_generator import generate_course

        mock_llm = AsyncMock()
        mock_llm.chat.return_value = MagicMock(
            content=self._llm_response([("치맥", [1, 2, 3])])
        )
        mock_search = AsyncMock(return_value=self._CANDIDATES)

        with patch("app.services.course_generator.search_candidate_places", mock_search), \
             patch("app.services.course_generator.get_llm_provider", return_value=mock_llm), \
             patch("app.services.course_generator.fetch_weather", AsyncMock(return_value=None)):
            await generate_course(
                AsyncMock(), station_id=1,
                theme_tags=["FOOD"], budget_tier="UNDER_30000",
                companion_type="FRIEND", query_text="강동에서 치맥할건데 추천해줘",
                menu_keyword="치킨",
            )

        assert mock_search.call_args.kwargs["menu_keyword"] == "치킨"

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
