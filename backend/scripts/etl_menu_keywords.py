#!/usr/bin/env python3
"""
ETL: 카카오 로컬 키워드 검색 API → places 테이블 (메뉴별 보강 수집)

scripts/etl_places.py는 category_group_code(FD6 등) 기반 카테고리 브라우징이라
역당 최대 45건(3페이지×15개)만 수집되어, 교촌치킨/BBQ/굽네치킨 같은 흔한
치킨 프랜차이즈가 순위에 밀려 거의 수집되지 않는 문제가 있었다 (SCRUM-98).
이 스크립트는 카카오 키워드 검색 API(`/v2/local/search/keyword.json`)로
구체적 메뉴 키워드를 역별로 직접 검색해 보강한다.

사용법:
    python -m scripts.etl_menu_keywords [--dry-run] [--station-ids ID1,ID2] [--keywords 치킨,피자]

환경변수:
    KAKAO_REST_API_KEY   카카오 REST API 키 (필수)
    DATABASE_URL         PostgreSQL 연결 URL
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.etl_places import (  # noqa: E402
    MAX_PAGES,
    MAX_RETRIES,
    PAGE_SIZE,
    RADIUS_METERS,
    RATE_LIMIT_SEC,
    RETRY_BASE_DELAY,
    get_supported_stations,
    upsert_places,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

KAKAO_KEYWORD_API_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


class KakaoQuotaExceededError(Exception):
    """Kakao's daily API quota is exhausted — retrying will not help; stop the run."""

# 검색 키워드 → theme_tag 매핑. 키워드 검색은 카테고리 브라우징보다 신호가
# 명확하므로(사용자가 "치킨"으로 검색해 나온 결과) category_group_code 매핑보다
# 이 명시적 매핑을 우선한다.
MENU_KEYWORDS: dict[str, list[str]] = {
    "치킨": ["FOOD", "BAR"],
}


async def fetch_keyword_places(
    client: httpx.AsyncClient,
    api_key: str,
    query: str,
    lng: float,
    lat: float,
    page: int = 1,
) -> tuple[list[dict], bool]:
    """카카오 로컬 키워드 검색 API 호출. (documents, is_end) 반환."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.get(
                KAKAO_KEYWORD_API_URL,
                headers={"Authorization": f"KakaoAK {api_key}"},
                params={
                    "query": query,
                    "x": str(lng),
                    "y": str(lat),
                    "radius": RADIUS_METERS,
                    "size": PAGE_SIZE,
                    "page": page,
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("documents", []), data["meta"]["is_end"]
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400 and "limit" in exc.response.text.lower():
                raise KakaoQuotaExceededError(exc.response.text) from exc
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2**attempt)
                log.warning(
                    "API 오류 (시도 %d/%d): %s — %.1fs 후 재시도",
                    attempt + 1, MAX_RETRIES, exc, delay,
                )
                await asyncio.sleep(delay)
            else:
                log.error("API 최종 실패: %s", exc)
                raise
        except httpx.RequestError as exc:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2**attempt)
                log.warning(
                    "API 오류 (시도 %d/%d): %s — %.1fs 후 재시도",
                    attempt + 1, MAX_RETRIES, exc, delay,
                )
                await asyncio.sleep(delay)
            else:
                log.error("API 최종 실패: %s", exc)
                raise
    return [], True  # unreachable


async def fetch_all_places_for_keyword(
    client: httpx.AsyncClient,
    api_key: str,
    station_name: str,
    keyword: str,
    lng: float,
    lat: float,
) -> list[dict]:
    results: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        if page > 1:
            await asyncio.sleep(RATE_LIMIT_SEC)
        docs, is_end = await fetch_keyword_places(client, api_key, keyword, lng, lat, page)
        results.extend(docs)
        if is_end:
            break
    log.info("  [%s] '%s' 키워드: %d건", station_name, keyword, len(results))
    return results


def build_place_row(doc: dict, theme_tags: list[str]) -> dict:
    """카카오 키워드 검색 응답 document → places 테이블 행 딕셔너리.

    theme_tags는 카테고리 코드가 아니라 검색에 쓴 메뉴 키워드로 명시 배정한다.
    """
    return {
        "external_source": "KAKAO",
        "external_id": doc["id"],
        "name": doc["place_name"],
        "category": doc.get("category_group_code", ""),
        "address": doc.get("road_address_name") or doc.get("address_name", ""),
        "lat": float(doc["y"]),
        "lng": float(doc["x"]),
        "phone": doc.get("phone") or "",
        "map_url": doc.get("place_url") or "",
        "business_hours": None,
        "theme_tags": theme_tags,
        "status": "OPEN",
        "last_synced_at": datetime.now(timezone.utc),
    }


async def main(args: argparse.Namespace) -> None:
    api_key = os.environ.get("KAKAO_REST_API_KEY", "")
    if not api_key and not args.dry_run:
        log.error("KAKAO_REST_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/whatwedoin"
    ).replace("postgresql+asyncpg://", "postgresql://")

    keywords = args.keywords.split(",") if args.keywords else list(MENU_KEYWORDS.keys())
    invalid = [k for k in keywords if k not in MENU_KEYWORDS]
    if invalid:
        log.error("정의되지 않은 키워드: %s (허용: %s)", invalid, list(MENU_KEYWORDS.keys()))
        sys.exit(1)

    station_ids = args.station_ids.split(",") if args.station_ids else None

    log.info("=== 메뉴 키워드 ETL 시작 | dry_run=%s | keywords=%s ===", args.dry_run, keywords)

    conn: asyncpg.Connection = await asyncpg.connect(db_url)
    try:
        stations = await get_supported_stations(conn, station_ids)
        log.info("대상 역: %d개", len(stations))

        total_upserted = 0
        quota_exceeded = False
        async with httpx.AsyncClient() as client:
            for station in stations:
                for keyword in keywords:
                    if args.dry_run and not api_key:
                        log.info("  [dry-run] API 호출 생략")
                        continue

                    try:
                        docs = await fetch_all_places_for_keyword(
                            client, api_key, station["name"], keyword,
                            station["lng"], station["lat"],
                        )
                    except KakaoQuotaExceededError as exc:
                        log.error(
                            "카카오 API 일일 호출 한도 초과 — 재시도 불가, 실행 중단: %s", exc
                        )
                        quota_exceeded = True
                        break

                    theme_tags = MENU_KEYWORDS[keyword]
                    rows = [build_place_row(doc, theme_tags) for doc in docs]
                    upserted = await upsert_places(conn, rows, args.dry_run)
                    total_upserted += upserted

                    await asyncio.sleep(RATE_LIMIT_SEC)
                if quota_exceeded:
                    break

        log.info("=== 메뉴 키워드 ETL 종료: 총 %d건 upsert (quota_exceeded=%s) ===",
                  total_upserted, quota_exceeded)
        if quota_exceeded:
            sys.exit(3)
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="카카오 로컬 키워드 검색 → places 테이블 보강 ETL")
    parser.add_argument("--dry-run", action="store_true", help="API 호출은 수행하되 DB insert를 생략합니다")
    parser.add_argument(
        "--station-ids", metavar="ID1,ID2,...", default="",
        help="처리할 역 station_id 목록 (쉼표 구분, 기본값: 전체 지원 역)",
    )
    parser.add_argument(
        "--keywords", metavar="치킨,피자,...", default="",
        help=f"검색할 메뉴 키워드 (기본값: {','.join(MENU_KEYWORDS.keys())})",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args))
