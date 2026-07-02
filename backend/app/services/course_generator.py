import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category_labels import place_category_label
from app.services.llm import LLMMessage, get_llm_provider
from app.services.llm.base import LLMUnavailableError
from app.services.place_search import search_candidate_places
from app.services.weather import fetch_weather

logger = logging.getLogger(__name__)

_MIN_STAGES = 2
_SINGLE_CATEGORY_MIN_STAGES = 1
_MAX_STAGES = 4
_MIN_OPTIONS_PER_STAGE = 1
_MAX_OPTIONS_PER_STAGE = 3
_MAX_STAGE_LABEL_LEN = 30


def _build_system_prompt(min_stages: int, single_category: bool) -> str:
    single_category_rule = (
        """- 이번 요청은 사용자가 단일 카테고리만 명확히 요청한 경우입니다. 다른 카테고리 단계를
  억지로 추가해 채우지 마세요. 후보가 충분하면 1개 단계로만 코스를 구성해도 됩니다.
"""
        if single_category
        else ""
    )
    return f"""당신은 서울 지하철 역 기반 놀거리 코스 추천 전문가입니다.
오늘의 날씨와 사용자 요청에 맞춰 {min_stages}~{_MAX_STAGES}개의 "단계(stage)"로 하루 코스를 설계하세요.
각 단계는 하나의 활동 유형(예: 저녁 식사, 카페/디저트, 야외 산책, 실내 액티비티)을 나타내며,
제공된 후보 장소 목록에서 서로 다른 장소 {_MIN_OPTIONS_PER_STAGE}~{_MAX_OPTIONS_PER_STAGE}개를
그 단계의 "대안(선택지)"으로 배정하세요. 사용자는 각 단계에서 대안 중 하나를 골라 방문합니다.

규칙:
- 일반적인 "오늘 뭐하지" 요청은 서로 다른 활동 유형으로 단계를 구성하세요. 같은 활동을 억지로
  두 번 반복하지 마세요(예: 식사 단계를 두 개 만들지 마세요).
- 단, 사용자가 "OO 투어"처럼 같은 테마를 명시적으로 반복 요청한 경우(예: "맛집 투어", "카페 투어")는
  예외로, 같은 카테고리의 단계를 여러 개 만들어도 됩니다.
{single_category_rule}- 비/눈 등 날씨가 좋지 않으면 실내 위주 단계로 구성하고 야외 단계(공원 산책, 야경 등)는 피하세요.
- 날씨가 맑고 쾌적하면 야외 단계(공원, 야경, 산책)를 적극적으로 포함해도 좋습니다. 날씨 정보가
  없으면 날씨와 무관하게 구성하세요.
- 각 단계의 대안은 반드시 후보 목록에 있는 place_id만 사용해야 하고, 같은 place_id를 코스 전체에서
  두 번 이상 쓰면 안 됩니다.
- 대안이 정말 부족한 경우가 아니라면 각 단계에 2~3개의 대안을 배정하세요.

응답은 반드시 아래 JSON 형식만 반환하고, 마크다운 코드블록 없이 순수 JSON으로 반환하세요.

{{
  "title": "코스 제목 (20자 이내)",
  "description": "코스 한 줄 소개 (50자 이내)",
  "stages": [
    {{
      "stage_label": "단계 이름 (예: 저녁 식사, {_MAX_STAGE_LABEL_LEN}자 이내)",
      "options": [
        {{"place_id": <int>, "description": "이 장소를 추천하는 이유/활동 (30자 이내)"}}
      ]
    }}
  ]
}}"""


@dataclass
class StageOption:
    place_id: int
    description: str


@dataclass
class GeneratedStage:
    stage_label: str
    options: list[StageOption]


@dataclass
class GeneratedCourse:
    title: str
    description: str
    stages: list[GeneratedStage]
    content_hash: str

    @property
    def all_place_ids(self) -> list[int]:
        return [opt.place_id for stage in self.stages for opt in stage.options]


class CourseGenerationError(Exception):
    pass


def _compute_content_hash(stages: list[GeneratedStage]) -> str:
    structure = [
        {"label": s.stage_label, "options": sorted(opt.place_id for opt in s.options)}
        for s in stages
    ]
    return hashlib.sha256(json.dumps(structure, sort_keys=True).encode()).hexdigest()


def _build_candidate_prompt(
    query_text: str,
    candidates: list[dict],
    theme_tags: list[str],
    budget_tier: str,
    companion_type: str,
    weather: dict | None,
    menu_keyword: str | None = None,
) -> str:
    lines = [
        f"사용자 요청: {query_text}",
        f"테마: {', '.join(theme_tags)}",
        f"예산: {budget_tier}",
        f"동반자: {companion_type}",
    ]
    if menu_keyword:
        lines.append(
            f"사용자가 명시한 메뉴/음식: {menu_keyword} "
            f"— 후보 이름에 이 키워드가 포함된 장소를 최우선으로 선택하세요."
        )
    if weather:
        lines.append(
            f"현재 날씨: {weather.get('description', '')} "
            f"(기온 {weather.get('temp')}°C, {weather.get('main')})"
        )
    else:
        lines.append("현재 날씨: 정보 없음 (날씨와 무관하게 구성하세요)")
    lines += ["", "후보 장소 목록:"]
    for p in candidates:
        avg_rating = (
            round(p["user_rating_sum"] / 2.0 / p["user_rating_count"], 1)
            if p.get("user_rating_count", 0) > 0
            else None
        )
        rating_str = f", 별점 {avg_rating}" if avg_rating else ""
        category_label = place_category_label(p.get("category")) or p.get("category", "")
        lines.append(
            f"- place_id={p['place_id']} / {p['name']} ({category_label}) "
            f"/ {p.get('price_range', '가격 미정')}{rating_str}"
        )
    return "\n".join(lines)


def _parse_and_validate(
    raw: str, candidate_ids: set[int], min_stages: int = _MIN_STAGES
) -> GeneratedCourse | None:
    try:
        data = json.loads(raw.strip())
        stages_data = data["stages"]

        if not (min_stages <= len(stages_data) <= _MAX_STAGES):
            logger.warning("Course has %d stages (expected %d-%d)", len(stages_data), min_stages, _MAX_STAGES)
            return None

        stages: list[GeneratedStage] = []
        all_ids: list[int] = []
        for sd in stages_data:
            label = sd["stage_label"]
            if not label or len(label) > _MAX_STAGE_LABEL_LEN:
                logger.warning("Invalid stage_label: %r", label)
                return None

            opts_data = sd["options"]
            if not (_MIN_OPTIONS_PER_STAGE <= len(opts_data) <= _MAX_OPTIONS_PER_STAGE):
                logger.warning(
                    "Stage '%s' has %d options (expected %d-%d)",
                    label, len(opts_data), _MIN_OPTIONS_PER_STAGE, _MAX_OPTIONS_PER_STAGE,
                )
                return None

            options = [
                StageOption(place_id=o["place_id"], description=o["description"])
                for o in opts_data
            ]
            all_ids.extend(opt.place_id for opt in options)
            stages.append(GeneratedStage(stage_label=label, options=options))

        # hallucination check — every option's place_id across all stages must
        # come from the candidate pool
        invalid = [pid for pid in all_ids if pid not in candidate_ids]
        if invalid:
            logger.warning("Hallucinated place_ids: %s", invalid)
            return None

        if len(all_ids) != len(set(all_ids)):
            logger.warning("Duplicate place_id reused across stages/options")
            return None

        return GeneratedCourse(
            title=data["title"],
            description=data["description"],
            stages=stages,
            content_hash=_compute_content_hash(stages),
        )
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("LLM response parse error: %s", exc)
        return None


async def generate_course(
    session: AsyncSession,
    station_id: int,
    theme_tags: list[str],
    budget_tier: str,
    companion_type: str,
    query_text: str,
    exclude_place_ids: list[int] | None = None,
    pre_fetched_candidates: list[dict] | None = None,
    menu_keyword: str | None = None,
) -> GeneratedCourse | None:
    """Retrieve candidate places and ask LLM to design a staged course.

    Returns None if generation fails after retries (raises CourseGenerationError
    if no candidates are found at all).
    """
    if pre_fetched_candidates is not None:
        candidates = pre_fetched_candidates
    else:
        candidates = await search_candidate_places(
            session, station_id, theme_tags=theme_tags,
            exclude_place_ids=exclude_place_ids, menu_keyword=menu_keyword,
        )
    if not candidates:
        raise CourseGenerationError("NO_CANDIDATES")

    candidate_ids = {c["place_id"] for c in candidates}
    weather = await fetch_weather()
    prompt = _build_candidate_prompt(
        query_text, candidates, theme_tags, budget_tier, companion_type, weather, menu_keyword
    )
    single_category = len(theme_tags) == 1
    min_stages = _SINGLE_CATEGORY_MIN_STAGES if single_category else _MIN_STAGES
    messages = [
        LLMMessage(role="system", content=_build_system_prompt(min_stages, single_category)),
        LLMMessage(role="user", content=prompt),
    ]

    provider = get_llm_provider()

    last_unavailable: LLMUnavailableError | None = None
    for attempt in range(3):
        try:
            response = await provider.chat(messages)
        except LLMUnavailableError as exc:
            last_unavailable = exc
            wait = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s
            logger.warning("LLM unavailable (attempt=%d), retrying in %.1fs: %s", attempt + 1, wait, exc)
            if attempt < 2:
                await asyncio.sleep(wait)
            continue

        result = _parse_and_validate(response.content, candidate_ids, min_stages)
        if result:
            logger.info(
                "Course generated (attempt=%d, hash=%s, stages=%d)",
                attempt + 1, result.content_hash, len(result.stages),
            )
            return result
        logger.warning("Attempt %d parse failed, retrying...", attempt + 1)

    if last_unavailable is not None:
        raise last_unavailable
    return None


async def upsert_course(
    session: AsyncSession,
    station_id: int,
    course: GeneratedCourse,
    theme_tags: list[str],
    budget_tier: str,
    companion_type: str,
    query_text: str,
    candidates: list[dict],
) -> tuple[int, float | None]:
    """Persist course via content_hash UPSERT. Returns course_id."""
    candidates_by_id = {c["place_id"]: c for c in candidates}

    places_json = json.dumps([
        {
            "place_id": opt.place_id,
            "description": opt.description,
            "stage_order": s_idx + 1,
            "option_index": o_idx + 1,
            "stage_label": stage.stage_label,
        }
        for s_idx, stage in enumerate(course.stages)
        for o_idx, opt in enumerate(stage.options)
    ])

    # asyncpg cannot bind custom PostgreSQL enum/array types via :param placeholders.
    # Inline all enum values as SQL literals; bind only plain scalars.
    tag_literals = ", ".join(f"'{t}'::theme_tag" for t in theme_tags)
    budget_literal = f"'{budget_tier}'::budget_tier"
    companion_literal = f"'{companion_type}'::companion_type"

    sql = text(f"""
        INSERT INTO courses
            (station_id, theme_tags, budget_tier, companion_type, query_text,
             places, content_hash, created_at, updated_at)
        VALUES
            (:station_id, ARRAY[{tag_literals}],
             {budget_literal}, {companion_literal}, :query_text,
             CAST(:places AS jsonb), :content_hash, now(), now())
        ON CONFLICT (content_hash) DO UPDATE
            SET updated_at = now()
        RETURNING course_id, total_walking_distance_km
    """)

    row = (
        await session.execute(sql, {
            "station_id": station_id,
            "query_text": query_text,
            "places": places_json,
            "content_hash": course.content_hash,
        })
    ).mappings().one()
    course_id = row["course_id"]
    total_walking_distance_km = (
        float(row["total_walking_distance_km"])
        if row["total_walking_distance_km"] is not None
        else None
    )

    # upsert course_places
    await session.execute(
        text("DELETE FROM course_places WHERE course_id = :cid"),
        {"cid": course_id},
    )
    for s_idx, stage in enumerate(course.stages):
        for o_idx, opt in enumerate(stage.options):
            distance_m = candidates_by_id.get(opt.place_id, {}).get("distance_m")
            distance_km = round(distance_m / 1000, 1) if distance_m is not None else None
            await session.execute(
                text("""
                    INSERT INTO course_places
                        (course_id, stage_order, option_index, stage_label,
                         place_id, description, walking_distance_from_station_km)
                    VALUES
                        (:course_id, :stage_order, :option_index, :stage_label,
                         :place_id, :description, :distance_km)
                """),
                {
                    "course_id": course_id,
                    "stage_order": s_idx + 1,
                    "option_index": o_idx + 1,
                    "stage_label": stage.stage_label,
                    "place_id": opt.place_id,
                    "description": opt.description,
                    "distance_km": distance_km,
                },
            )

    await session.commit()
    return course_id, total_walking_distance_km
