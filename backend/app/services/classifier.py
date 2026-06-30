import json
import re
from dataclasses import dataclass, field

from app.models.enums import BudgetTier, CompanionType, ThemeTag
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMMessage

_SYSTEM_PROMPT = """당신은 데이트 코스 추천 서비스의 질의어 분류기입니다.
사용자의 자연어 요청을 분석하여 반드시 다음 JSON 형식으로만 응답하세요.
다른 텍스트는 절대 포함하지 마세요.

응답 형식:
{
  "theme_tags": ["FOOD", "CAFE"],
  "budget_tier": "UNDER_30000",
  "companion_type": "COUPLE",
  "head_count": 2
}

theme_tag 가능 값 (이 12종 외 사용 금지):
FOOD, CAFE, BAR, BOARD_GAME, KARAOKE, ARCADE, PARK, CULTURE, SHOPPING, NIGHT_VIEW, MOVIE, ACTIVITY

budget_tier 가능 값: UNDER_30000, 30000_70000, 70000_150000, OVER_150000, null
companion_type 가능 값: SOLO, FRIEND, COUPLE, FAMILY, null
head_count: 1~10 정수

분류가 완전히 불가한 경우:
{"error": "INVALID_QUERY"}"""


class InvalidQueryError(Exception):
    pass


@dataclass
class QueryClassification:
    theme_tags: list[ThemeTag]
    budget_tier: BudgetTier | None = None
    companion_type: CompanionType | None = None
    head_count: int = 2


async def classify_query(
    query_text: str,
    default_budget_tier: BudgetTier | None = None,
    default_companion_type: CompanionType | None = None,
    default_head_count: int = 2,
) -> QueryClassification:
    provider = get_llm_provider()
    response = await provider.chat([
        LLMMessage(role="system", content=_SYSTEM_PROMPT),
        LLMMessage(role="user", content=query_text),
    ])

    raw = response.content.strip()
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not json_match:
        raise InvalidQueryError(f"LLM returned non-JSON: {raw[:200]}")

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise InvalidQueryError(f"JSON parse error: {e}")

    if data.get("error") == "INVALID_QUERY":
        raise InvalidQueryError("Query could not be classified")

    theme_tags_raw = data.get("theme_tags") or []
    theme_tags = []
    for t in theme_tags_raw:
        try:
            theme_tags.append(ThemeTag(t))
        except ValueError:
            pass

    if not theme_tags:
        raise InvalidQueryError("No valid theme_tags extracted")

    budget_raw = data.get("budget_tier")
    try:
        budget_tier = BudgetTier(budget_raw) if budget_raw else default_budget_tier
    except ValueError:
        budget_tier = default_budget_tier

    companion_raw = data.get("companion_type")
    try:
        companion_type = CompanionType(companion_raw) if companion_raw else default_companion_type
    except ValueError:
        companion_type = default_companion_type

    raw_count = data.get("head_count")
    head_count = max(1, min(10, int(raw_count))) if raw_count else default_head_count

    return QueryClassification(
        theme_tags=theme_tags,
        budget_tier=budget_tier,
        companion_type=companion_type,
        head_count=head_count,
    )
