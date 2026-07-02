import json
import logging
import re
from dataclasses import dataclass, field

from app.models.enums import BudgetTier, CompanionType, ThemeTag
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMMessage

logger = logging.getLogger(__name__)

_INVALID_QUERY_MESSAGE = "어떤 하루를 보내고 싶은지 알려주세요"

_SYSTEM_PROMPT = """당신은 데이트 코스 추천 서비스의 질의어 분류기입니다.
사용자의 자연어 요청을 분석하여 반드시 다음 JSON 형식으로만 응답하세요.
다른 텍스트는 절대 포함하지 마세요.

응답 형식:
{
  "station_name": "홍대입구",
  "theme_tags": ["FOOD", "CAFE"],
  "budget_tier": "UNDER_30000",
  "companion_type": "COUPLE",
  "head_count": 2,
  "menu_keyword": null
}

station_name 규칙 (매우 중요):
- 역 이름이 직접 언급된 경우: 그 역 이름 사용 (예: "홍대입구역" → "홍대입구")
- 동네·상권·장소명이 언급된 경우: 가장 가까운 지하철역 이름으로 변환
  예시:
  · 연남동, 홍대 앞, 홍대 거리 → "홍대입구"
  · 합정, 망원동 → "합정"
  · 압구정로데오, 청담동 → "압구정로데오"
  · 이태원, 경리단길 → "이태원"
  · 성수동, 서울숲 → "성수"
  · 건대 앞, 건대입구 → "건대입구"
  · 신촌, 이대 앞 → "신촌"
  · 여의도 → "여의도"
  · 명동 → "명동"
  · 종로, 인사동 → "종각" 또는 "안국"
  · 광화문 → "광화문"
  · 잠실, 롯데월드 → "잠실"
  · 코엑스, 삼성동 → "삼성"
  · 동대문 → "동대문역사문화공원"
  · 서울대입구, 낙성대 → "서울대입구"
  · 수유, 미아 → "수유"
- 위치 언급이 없으면 null

theme_tag 가능 값 (이 12종 외 사용 금지):
FOOD, CAFE, BAR, BOARD_GAME, KARAOKE, ARCADE, PARK, CULTURE, SHOPPING, NIGHT_VIEW, MOVIE, ACTIVITY

theme_tags 개수 규칙 (매우 중요):
- 사용자가 명시적으로 요청한(또는 문맥상 명확히 하나로 좁혀지는) 카테고리만 담으세요.
  예: "밥집만 추천해줘" → ["FOOD"], "카페 가고싶어" → ["CAFE"]
- 사용자가 요청하지 않은 카테고리를 임의로 추가하지 마세요(예: "밥집만"이라고 했는데 CAFE를 덧붙이지 않기).
- "코스 추천해줘", "놀거리 추천해줘"처럼 여러 활동을 아우르는 하루 코스를 원하는 경우에만
  관련 카테고리 2개 이상을 담으세요.

budget_tier 가능 값: UNDER_15000, UNDER_30000, 30000_70000, 70000_150000, OVER_150000, null
  - 인당 1.5만원 이하 → UNDER_15000
  - 인당 3만원 이하 → UNDER_30000
companion_type 가능 값: SOLO, FRIEND, COUPLE, FAMILY, null
head_count: 1~10 정수

menu_keyword (매우 중요):
- 사용자가 구체적인 메뉴/음식을 명시한 경우, 장소 검색에 쓸 짧은 키워드(2~4자, 명사)를 담으세요.
  예: "치맥" → "치킨", "물회 먹고싶어" → "물회", "파스타 먹으러 가고싶어" → "파스타",
      "냉면 맛집" → "냉면"
- 특정 메뉴 언급이 없고 막연히 "밥", "맛집", "먹을 곳"처럼 일반적인 경우는 null.

분류가 완전히 불가한 경우:
{"error": "INVALID_QUERY"}"""


class InvalidQueryError(Exception):
    pass


class NeedsClarificationError(Exception):
    def __init__(self, missing_fields: list[str], partial_parsed_input: dict):
        self.missing_fields = missing_fields
        self.partial_parsed_input = partial_parsed_input
        super().__init__(f"Missing required fields: {missing_fields}")


@dataclass
class QueryClassification:
    theme_tags: list[ThemeTag]
    station_name: str | None = None
    budget_tier: BudgetTier | None = None
    companion_type: CompanionType | None = None
    head_count: int = 2
    menu_keyword: str | None = None


async def classify_query(
    query_text: str,
    default_budget_tier: BudgetTier | None = None,
    default_companion_type: CompanionType | None = None,
    default_head_count: int = 2,
    default_theme_tags: list[ThemeTag] | None = None,
) -> QueryClassification:
    provider = get_llm_provider()
    response = await provider.chat([
        LLMMessage(role="system", content=_SYSTEM_PROMPT),
        LLMMessage(role="user", content=query_text),
    ])

    raw = response.content.strip()
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not json_match:
        logger.warning("Classifier LLM returned non-JSON: %s", raw[:200])
        raise InvalidQueryError(_INVALID_QUERY_MESSAGE)

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.warning("Classifier JSON parse error: %s", e)
        raise InvalidQueryError(_INVALID_QUERY_MESSAGE)

    if data.get("error") == "INVALID_QUERY":
        raise InvalidQueryError(_INVALID_QUERY_MESSAGE)

    theme_tags_raw = data.get("theme_tags") or []
    theme_tags = []
    for t in theme_tags_raw:
        try:
            theme_tags.append(ThemeTag(t))
        except ValueError:
            pass

    if not theme_tags:
        theme_tags = list(default_theme_tags or [])

    if not theme_tags:
        raise InvalidQueryError(_INVALID_QUERY_MESSAGE)

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

    station_name = data.get("station_name") or None
    if station_name:
        station_name = station_name.strip()

    menu_keyword_raw = data.get("menu_keyword")
    menu_keyword = menu_keyword_raw.strip() if isinstance(menu_keyword_raw, str) and menu_keyword_raw.strip() else None

    missing_fields: list[str] = []
    if not station_name:
        missing_fields.append("station_id")
    if companion_type is None:
        missing_fields.append("companion_type")
    if budget_tier is None:
        missing_fields.append("budget_tier")

    if missing_fields:
        partial: dict = {
            "theme_tags": [t.value for t in theme_tags],
            "head_count": head_count,
        }
        if station_name:
            partial["station_name"] = station_name
        if menu_keyword:
            partial["menu_keyword"] = menu_keyword
        raise NeedsClarificationError(missing_fields=missing_fields, partial_parsed_input=partial)

    return QueryClassification(
        theme_tags=theme_tags,
        station_name=station_name,
        budget_tier=budget_tier,
        companion_type=companion_type,
        head_count=head_count,
        menu_keyword=menu_keyword,
    )
