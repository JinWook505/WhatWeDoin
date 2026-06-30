import hashlib
import json
import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import LLMMessage, get_llm_provider
from app.services.place_search import search_candidate_places

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """당신은 서울 지하철 역 기반 데이트 코스 추천 전문가입니다.
제공된 후보 장소 목록에서만 선택하여 3~5개 장소로 구성된 최적의 동선 코스를 만들어 주세요.
반드시 후보 목록에 있는 place_id만 사용해야 합니다.
응답은 반드시 아래 JSON 형식만 반환하고, 마크다운 코드블록 없이 순수 JSON으로 반환하세요.

{
  "title": "코스 제목 (20자 이내)",
  "description": "코스 한 줄 소개 (50자 이내)",
  "places": [
    {"place_id": <int>, "description": "이 장소 방문 이유/활동 (30자 이내)"}
  ]
}"""


@dataclass
class GeneratedCourse:
    title: str
    description: str
    place_ids: list[int]
    place_descriptions: dict[int, str]  # place_id → description
    content_hash: str


class CourseGenerationError(Exception):
    pass


def _compute_content_hash(place_ids: list[int]) -> str:
    return hashlib.sha256(json.dumps(sorted(place_ids)).encode()).hexdigest()


def _build_candidate_prompt(
    query_text: str,
    candidates: list[dict],
    theme_tags: list[str],
    budget_tier: str,
    companion_type: str,
) -> str:
    lines = [
        f"사용자 요청: {query_text}",
        f"테마: {', '.join(theme_tags)}",
        f"예산: {budget_tier}",
        f"동반자: {companion_type}",
        "",
        "후보 장소 목록:",
    ]
    for p in candidates:
        avg_rating = (
            round(p["user_rating_sum"] / 2.0 / p["user_rating_count"], 1)
            if p.get("user_rating_count", 0) > 0
            else None
        )
        rating_str = f", 별점 {avg_rating}" if avg_rating else ""
        lines.append(
            f"- place_id={p['place_id']} / {p['name']} ({p.get('category', '')}) "
            f"/ {p.get('price_range', '가격 미정')}{rating_str}"
        )
    return "\n".join(lines)


def _parse_and_validate(
    raw: str, candidate_ids: set[int]
) -> GeneratedCourse | None:
    try:
        data = json.loads(raw.strip())
        places = data["places"]
        place_ids = [p["place_id"] for p in places]

        # hallucination check
        invalid = [pid for pid in place_ids if pid not in candidate_ids]
        if invalid:
            logger.warning("Hallucinated place_ids: %s", invalid)
            return None

        if not (3 <= len(place_ids) <= 5):
            logger.warning("Course has %d places (expected 3-5)", len(place_ids))
            return None

        return GeneratedCourse(
            title=data["title"],
            description=data["description"],
            place_ids=place_ids,
            place_descriptions={p["place_id"]: p["description"] for p in places},
            content_hash=_compute_content_hash(place_ids),
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
) -> GeneratedCourse | None:
    """Retrieve candidate places and ask LLM to generate a course.

    Returns None if generation fails after 1 retry (raises CourseGenerationError
    if no candidates are found at all).
    """
    if pre_fetched_candidates is not None:
        candidates = pre_fetched_candidates
    else:
        candidates = await search_candidate_places(
            session, station_id, theme_tags=theme_tags,
            exclude_place_ids=exclude_place_ids,
        )
    if not candidates:
        raise CourseGenerationError("NO_CANDIDATES")

    candidate_ids = {c["place_id"] for c in candidates}
    prompt = _build_candidate_prompt(query_text, candidates, theme_tags, budget_tier, companion_type)
    messages = [
        LLMMessage(role="system", content=_SYSTEM_PROMPT),
        LLMMessage(role="user", content=prompt),
    ]

    provider = get_llm_provider()

    for attempt in range(2):
        response = await provider.chat(messages)
        result = _parse_and_validate(response.content, candidate_ids)
        if result:
            logger.info(
                "Course generated (attempt=%d, hash=%s)", attempt + 1, result.content_hash
            )
            return result
        logger.warning("Attempt %d failed, retrying...", attempt + 1)

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
) -> int:
    """Persist course via content_hash UPSERT. Returns course_id."""
    places_json = json.dumps(
        [
            {
                "place_id": pid,
                "description": course.place_descriptions[pid],
                "visit_order": idx + 1,
            }
            for idx, pid in enumerate(course.place_ids)
        ]
    )

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
        RETURNING course_id
    """)

    row = await session.execute(sql, {
        "station_id": station_id,
        "query_text": query_text,
        "places": places_json,
        "content_hash": course.content_hash,
    })
    course_id = row.scalar_one()

    # upsert course_places
    await session.execute(
        text("DELETE FROM course_places WHERE course_id = :cid"),
        {"cid": course_id},
    )
    for idx, pid in enumerate(course.place_ids):
        await session.execute(
            text("""
                INSERT INTO course_places (course_id, visit_order, place_id, description)
                VALUES (:course_id, :visit_order, :place_id, :description)
            """),
            {
                "course_id": course_id,
                "visit_order": idx + 1,
                "place_id": pid,
                "description": course.place_descriptions[pid],
            },
        )

    await session.commit()
    return course_id
