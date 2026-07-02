#!/usr/bin/env python3
"""
백필: places.theme_tags — 장소 이름 기반 LLM 분류

places 테이블의 theme_tags가 전부 비어있어(카카오 API가 세부 카테고리를
제공하지 않아 category_group_code만으로는 FOOD/BAR 등을 구분할 수 없음),
장소 이름(+category 라벨)을 LLM에 배치로 보내 12종 theme_tag 중 해당하는
태그를 분류해 채운다. 예: "OO호프", "OO치킨" 같은 이름은 카카오 코드상
FD6(음식점)로만 잡히지만 실제로는 FOOD 뿐 아니라 BAR로도 분류돼야
"치맥" 같은 메뉴 특화 요청의 후보 필터링이 제대로 동작한다.

사용법:
    python -m scripts.backfill_place_theme_tags [--dry-run] [--batch-size 40] [--reclassify]

환경변수:
    DATABASE_URL   PostgreSQL 연결 URL
    (LLM 관련 환경변수는 app.core.config.settings 참고)
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys

import asyncpg

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.category_labels import place_category_label  # noqa: E402
from app.models.enums import ThemeTag  # noqa: E402
from app.services.llm import LLMMessage, get_llm_provider  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

_VALID_TAGS = {t.value for t in ThemeTag}

_SYSTEM_PROMPT = f"""당신은 장소 이름을 보고 테마를 분류하는 전문가입니다.
아래 장소 목록 각각에 대해, 이름과 카테고리를 참고하여 다음 12종 theme_tag 중
해당하는 태그를 1개 이상 배정하세요 (해당 사항이 전혀 없으면 빈 배열).

theme_tag 종류: {', '.join(sorted(_VALID_TAGS))}

분류 힌트:
- 이름에 "호프", "포차", "펍", "와인바", "이자카야" 등이 있으면 BAR를 포함하세요
  (술과 함께 식사도 가능한 곳이면 FOOD도 함께 포함).
- 이름에 "치킨", "통닭", "노래방", "코인노래" 등 구체적 업종이 드러나면
  그에 맞는 태그(FOOD/BAR, KARAOKE 등)를 반영하세요.
- 카테고리가 "카페"이면 기본적으로 CAFE. 다만 "북카페", "보드게임카페" 등
  이름에 특정 활동이 드러나면 BOARD_GAME 등을 추가하세요.
- 카테고리가 "음식점"이면 기본적으로 FOOD.
- 판단이 애매하면 카테고리 기준의 무난한 태그 1개만 배정하세요.

반드시 아래 JSON 형식으로만 응답하고 다른 텍스트는 포함하지 마세요:
{{"results": [{{"place_id": <int>, "theme_tags": ["FOOD", "BAR"]}}, ...]}}
입력받은 모든 place_id에 대해 빠짐없이 결과를 포함하세요."""


def build_batch_prompt(places: list[dict]) -> str:
    lines = ["다음 장소들을 분류하세요:"]
    for p in places:
        label = place_category_label(p.get("category")) or p.get("category") or "미분류"
        lines.append(f"- place_id={p['place_id']} / {p['name']} ({label})")
    return "\n".join(lines)


def parse_batch_response(raw: str, valid_ids: set[int]) -> dict[int, list[str]]:
    """LLM 응답을 {place_id: [theme_tag, ...]}로 파싱. 잘못된 place_id/태그는 무시."""
    match = re.search(r"\{.*\}", raw.strip(), re.DOTALL)
    if not match:
        raise ValueError(f"Non-JSON LLM response: {raw[:200]!r}")
    data = json.loads(match.group())

    out: dict[int, list[str]] = {}
    for item in data.get("results", []):
        pid = item.get("place_id")
        if pid not in valid_ids:
            continue
        tags = [t for t in (item.get("theme_tags") or []) if t in _VALID_TAGS]
        out[pid] = tags
    return out


_MAX_RETRIES = 5
_RETRY_BASE_DELAY = 10.0
# Gemini free-tier gemini-3.1-flash-lite: 15 requests/min → stay safely under that.
_RATE_LIMIT_SEC = 5.0


async def classify_batch(places: list[dict]) -> dict[int, list[str]]:
    provider = get_llm_provider()
    valid_ids = {p["place_id"] for p in places}

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = await provider.chat([
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(role="user", content=build_batch_prompt(places)),
            ])
            return parse_batch_response(response.content, valid_ids)
        except Exception as exc:
            last_exc = exc
            is_rate_limit = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
            if not is_rate_limit or attempt == _MAX_RETRIES - 1:
                raise
            delay = _RETRY_BASE_DELAY * (attempt + 1)
            log.warning(
                "레이트리밋 (시도 %d/%d), %.0fs 후 재시도: %s",
                attempt + 1, _MAX_RETRIES, delay, exc,
            )
            await asyncio.sleep(delay)
    raise last_exc  # unreachable


def chunk(items: list[dict], size: int) -> list[list[dict]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


SELECT_UNTAGGED_SQL = """
SELECT place_id, name, category
FROM places
WHERE status = 'OPEN' {reclassify_clause}
ORDER BY place_id
"""

UPDATE_THEME_TAGS_SQL = """
UPDATE places SET theme_tags = $2::theme_tag[], updated_at = now()
WHERE place_id = $1
"""


async def run(batch_size: int, dry_run: bool, reclassify: bool) -> None:
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/whatwedoin"
    ).replace("postgresql+asyncpg://", "postgresql://")

    conn: asyncpg.Connection = await asyncpg.connect(db_url)
    try:
        reclassify_clause = "" if reclassify else "AND (theme_tags IS NULL OR theme_tags = '{}')"
        rows = await conn.fetch(SELECT_UNTAGGED_SQL.format(reclassify_clause=reclassify_clause))
        places = [dict(r) for r in rows]
        log.info("대상 장소: %d개 (batch_size=%d, dry_run=%s)", len(places), batch_size, dry_run)

        total_tagged = 0
        batches = chunk(places, batch_size)
        for i, batch in enumerate(batches):
            if i > 0:
                await asyncio.sleep(_RATE_LIMIT_SEC)
            try:
                results = await classify_batch(batch)
            except Exception as exc:
                log.error("배치 분류 실패 (place_id=%s...): %s", batch[0]["place_id"], exc)
                continue

            for p in batch:
                tags = results.get(p["place_id"], [])
                log.info("  place_id=%d %s -> %s", p["place_id"], p["name"], tags)
                if not dry_run:
                    await conn.execute(UPDATE_THEME_TAGS_SQL, p["place_id"], tags)
                total_tagged += 1

        log.info("=== 백필 완료: %d개 장소 처리 ===", total_tagged)
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="places.theme_tags LLM 백필")
    parser.add_argument("--dry-run", action="store_true", help="LLM 분류만 수행하고 DB는 갱신하지 않습니다")
    parser.add_argument("--batch-size", type=int, default=40, help="LLM 호출당 장소 수 (기본 40)")
    parser.add_argument(
        "--reclassify", action="store_true",
        help="이미 theme_tags가 채워진 장소도 다시 분류합니다 (기본: 빈 장소만)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.batch_size, args.dry_run, args.reclassify))
