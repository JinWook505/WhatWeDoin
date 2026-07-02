import json

import pytest

from scripts.backfill_place_theme_tags import (
    build_batch_prompt,
    chunk,
    parse_batch_response,
)


class TestBuildBatchPrompt:
    def test_uses_korean_category_label(self):
        places = [{"place_id": 1, "name": "노랑저고리 강남점", "category": "FD6"}]
        prompt = build_batch_prompt(places)
        assert "음식점" in prompt
        assert "place_id=1" in prompt
        assert "노랑저고리 강남점" in prompt

    def test_unknown_category_falls_back_to_raw_code(self):
        places = [{"place_id": 2, "name": "테스트장소", "category": "ZZ9"}]
        prompt = build_batch_prompt(places)
        assert "ZZ9" in prompt


class TestParseBatchResponse:
    def test_parses_valid_response(self):
        raw = json.dumps({
            "results": [
                {"place_id": 1, "theme_tags": ["FOOD", "BAR"]},
                {"place_id": 2, "theme_tags": ["CAFE"]},
            ]
        })
        result = parse_batch_response(raw, valid_ids={1, 2})
        assert result == {1: ["FOOD", "BAR"], 2: ["CAFE"]}

    def test_drops_unknown_place_ids(self):
        raw = json.dumps({"results": [{"place_id": 999, "theme_tags": ["FOOD"]}]})
        result = parse_batch_response(raw, valid_ids={1, 2})
        assert result == {}

    def test_drops_invalid_theme_tags(self):
        raw = json.dumps({"results": [{"place_id": 1, "theme_tags": ["FOOD", "NOT_REAL"]}]})
        result = parse_batch_response(raw, valid_ids={1})
        assert result == {1: ["FOOD"]}

    def test_non_json_raises(self):
        with pytest.raises(ValueError):
            parse_batch_response("not json at all", valid_ids={1})

    def test_extracts_json_from_surrounding_text(self):
        raw = 'Sure, here is the result:\n{"results": [{"place_id": 1, "theme_tags": []}]}\nDone.'
        result = parse_batch_response(raw, valid_ids={1})
        assert result == {1: []}


class TestChunk:
    def test_splits_into_batches(self):
        items = [{"place_id": i} for i in range(1, 11)]
        batches = chunk(items, 4)
        assert len(batches) == 3
        assert [len(b) for b in batches] == [4, 4, 2]

    def test_empty_list(self):
        assert chunk([], 4) == []
