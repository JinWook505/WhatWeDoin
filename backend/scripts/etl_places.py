#!/usr/bin/env python3
"""
ETL: 카카오 로컬 API → places 테이블

지원 역 각각에 대해 카카오 로컬 REST API를 호출하고
반경 7km 장소를 places 테이블에 upsert한다.

사용법:
    python -m scripts.etl_places [--dry-run] [--station-ids ID1,ID2] [--categories FD6,CE7]

환경변수:
    KAKAO_REST_API_KEY   카카오 REST API 키 (필수)
    DATABASE_URL         PostgreSQL 연결 URL
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

KAKAO_API_URL = "https://dapi.kakao.com/v2/local/search/category.json"

CATEGORIES: dict[str, str] = {
    "FD6": "음식점",   # 술집 포함 (Kakao CB4 코드 없음, FD6 하위 분류)
    "CE7": "카페",
    "CT1": "문화시설",
    "AT4": "관광명소",
}

RADIUS_METERS = 7000
PAGE_SIZE = 15
MAX_PAGES = 3
RATE_LIMIT_SEC = 1.0
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0

COVERAGE_MIN_PLACES = 1


async def fetch_category_places(
    client: httpx.AsyncClient,
    api_key: str,
    lng: float,
    lat: float,
    category_code: str,
    page: int = 1,
) -> tuple[list[dict], bool]:
    """카카오 로컬 카테고리 검색 API 호출. (documents, is_end) 반환."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.get(
                KAKAO_API_URL,
                headers={"Authorization": f"KakaoAK {api_key}"},
                params={
                    "category_group_code": category_code,
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
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
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


async def fetch_all_places_for_station(
    client: httpx.AsyncClient,
    api_key: str,
    station_name: str,
    lng: float,
    lat: float,
    categories: list[str],
) -> list[dict]:
    """한 역에 대해 모든 카테고리 장소를 수집한다."""
    results: list[dict] = []

    for category_code in categories:
        category_name = CATEGORIES.get(category_code, category_code)
        page_places: list[dict] = []

        for page in range(1, MAX_PAGES + 1):
            if page > 1:
                await asyncio.sleep(RATE_LIMIT_SEC)

            docs, is_end = await fetch_category_places(
                client, api_key, lng, lat, category_code, page
            )
            page_places.extend(docs)

            if is_end:
                break

        log.info(
            "  [%s] %s(%s): %d건",
            station_name, category_name, category_code, len(page_places),
        )
        results.extend(page_places)

        await asyncio.sleep(RATE_LIMIT_SEC)

    return results


def build_place_row(doc: dict) -> dict:
    """카카오 API 응답 document → places 테이블 행 딕셔너리."""
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
        "business_hours": json.dumps({}),
        "status": "OPEN",
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
    }


# ST_MakePoint(lng, lat) — PostGIS 인자 순서는 x(경도), y(위도)
UPSERT_SQL = """
INSERT INTO places (
    external_source, external_id, name, category, address,
    lat, lng, geom,
    phone, map_url, business_hours, status, last_synced_at
) VALUES (
    $1::oauth_provider, $2, $3, $4, $5,
    $6, $7, ST_SetSRID(ST_MakePoint($7, $6), 4326)::geography,
    $8, $9, $10::jsonb, $11, $12::timestamptz
)
ON CONFLICT (external_source, external_id) DO UPDATE SET
    name           = EXCLUDED.name,
    category       = EXCLUDED.category,
    address        = EXCLUDED.address,
    lat            = EXCLUDED.lat,
    lng            = EXCLUDED.lng,
    geom           = EXCLUDED.geom,
    phone          = EXCLUDED.phone,
    map_url        = EXCLUDED.map_url,
    business_hours = EXCLUDED.business_hours,
    status         = EXCLUDED.status,
    last_synced_at = EXCLUDED.last_synced_at
"""


async def upsert_places(
    conn: asyncpg.Connection, rows: list[dict], dry_run: bool
) -> int:
    """장소 목록을 places 테이블에 upsert. 처리된 행 수 반환."""
    if dry_run:
        log.info("  [dry-run] %d건 upsert 생략", len(rows))
        return len(rows)

    count = 0
    for row in rows:
        await conn.execute(
            UPSERT_SQL,
            row["external_source"],
            row["external_id"],
            row["name"],
            row["category"],
            row["address"],
            row["lat"],
            row["lng"],
            row["phone"],
            row["map_url"],
            row["business_hours"],
            row["status"],
            row["last_synced_at"],
        )
        count += 1
    return count


GET_SUPPORTED_STATIONS_SQL = """
SELECT station_id, name, lat, lng
FROM stations
WHERE is_supported = true
ORDER BY name
"""


async def get_supported_stations(
    conn: asyncpg.Connection, station_ids: Optional[list[str]] = None
) -> list[dict]:
    """DB에서 지원 역 목록 조회. station_ids 지정 시 해당 역만 반환."""
    rows = await conn.fetch(GET_SUPPORTED_STATIONS_SQL)
    stations = [dict(r) for r in rows]

    if station_ids:
        id_set = {int(i) for i in station_ids}
        stations = [s for s in stations if s["station_id"] in id_set]
        if not stations:
            log.error(
                "지정한 station_ids에 해당하는 지원 역이 없습니다: %s", station_ids
            )
            sys.exit(1)

    return stations


COVERAGE_SQL = """
SELECT s.station_id, s.name, COUNT(p.place_id) AS place_count
FROM stations s
LEFT JOIN places p ON ST_DWithin(s.geom, p.geom, 5000)
WHERE s.is_supported = true
GROUP BY s.station_id, s.name
ORDER BY place_count ASC
"""


async def verify_coverage(conn: asyncpg.Connection) -> bool:
    """지원 역 5km 반경에 최소 COVERAGE_MIN_PLACES개 이상의 장소가 있는지 검증."""
    rows = await conn.fetch(COVERAGE_SQL)
    ok = True
    for row in rows:
        count = row["place_count"]
        if count < COVERAGE_MIN_PLACES:
            log.warning("커버리지 부족: %s (장소 %d개)", row["name"], count)
            ok = False
        else:
            log.info("  ✓ %s: %d개", row["name"], count)
    return ok


async def main(args: argparse.Namespace) -> None:
    api_key = os.environ.get("KAKAO_REST_API_KEY", "")
    if not api_key and not args.dry_run:
        log.error("KAKAO_REST_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    if not api_key and args.dry_run:
        log.warning("KAKAO_REST_API_KEY 미설정 — dry-run 모드이므로 API 호출 없이 진행합니다.")

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/whatwedoin",
    )
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    categories = args.categories.split(",") if args.categories else list(CATEGORIES.keys())
    invalid = [c for c in categories if c not in CATEGORIES]
    if invalid:
        log.error(
            "유효하지 않은 카테고리 코드: %s (허용: %s)", invalid, list(CATEGORIES.keys())
        )
        sys.exit(1)

    station_ids = args.station_ids.split(",") if args.station_ids else None

    log.info("=== ETL 시작 | dry_run=%s | categories=%s ===", args.dry_run, categories)

    conn: asyncpg.Connection = await asyncpg.connect(db_url)
    try:
        stations = await get_supported_stations(conn, station_ids)
        log.info("대상 역: %d개", len(stations))

        total_upserted = 0

        async with httpx.AsyncClient() as client:
            for station in stations:
                log.info(
                    "[%s] 장소 수집 시작 (lng=%.5f, lat=%.5f)",
                    station["name"], station["lng"], station["lat"],
                )

                if args.dry_run and not api_key:
                    log.info("  [dry-run] API 호출 생략")
                    continue

                docs = await fetch_all_places_for_station(
                    client,
                    api_key,
                    station["name"],
                    station["lng"],
                    station["lat"],
                    categories,
                )

                rows = [build_place_row(doc) for doc in docs]
                upserted = await upsert_places(conn, rows, args.dry_run)
                total_upserted += upserted
                log.info("  → %d건 upsert 완료", upserted)

        log.info("=== ETL 완료: 총 %d건 upsert ===", total_upserted)

        if not args.dry_run:
            log.info("=== 커버리지 검증 ===")
            ok = await verify_coverage(conn)
            if not ok:
                log.warning("일부 역의 장소 데이터가 부족합니다.")
                sys.exit(2)
            log.info("커버리지 검증 통과")
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="카카오 로컬 API → places 테이블 ETL")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="API 호출은 수행하되 DB insert를 생략합니다",
    )
    parser.add_argument(
        "--station-ids",
        metavar="ID1,ID2,...",
        default="",
        help="처리할 역 station_id 목록 (쉼표 구분, 기본값: 전체 지원 역)",
    )
    parser.add_argument(
        "--categories",
        metavar="FD6,CE7,...",
        default="",
        help=f"수집할 카테고리 코드 (기본값: {','.join(CATEGORIES.keys())})",
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
