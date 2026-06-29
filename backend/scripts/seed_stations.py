"""
Seoul subway station seeding script.

Prerequisites:
  - SCRUM-58 완료 (Alembic migration, stations / station_lines table created)
  - DATABASE_URL env var or default postgresql://postgres:postgres@localhost:5432/whatwedoin

Usage:
  cd backend
  DATABASE_URL=postgresql://... python -m scripts.seed_stations
  # or with docker-compose DB:
  python -m scripts.seed_stations

Notes:
  - 재실행 안전: (external_source, external_id) 기준 upsert — 중복 에러 없음
  - 지방 도시(대구·부산 등) 확장 시 STATIONS 목록에 추가 후 동일 스크립트 재실행
"""

import asyncio
import os
import sys
from dataclasses import dataclass


@dataclass
class StationRow:
    name: str
    line: str      # 노선명 — external_id 생성 및 station_lines 적재에 사용
    lat: float
    lng: float
    is_supported: bool

    @property
    def external_id(self) -> str:
        """stable unique ID per station+line (kakao source 기준)"""
        normalized = self.line.replace(" ", "_")
        return f"{self.name}_{normalized}"


# fmt: off
# (name, line, lat, lng, is_supported)
# Coordinates: WGS84 (EPSG:4326)
STATIONS: list[StationRow] = [
    # ── MVP 지원 역 (is_supported=True) ──────────────────────────────────────
    # 코스 추천 서비스 초기 오픈 대상 역
    StationRow("강남",      "2호선",  37.4979, 127.0276, True),
    StationRow("홍대입구",  "2호선",  37.5571, 126.9249, True),
    StationRow("신촌",      "2호선",  37.5553, 126.9363, True),
    StationRow("합정",      "2호선",  37.5494, 126.9143, True),
    StationRow("건대입구",  "2호선",  37.5403, 127.0699, True),
    StationRow("성수",      "2호선",  37.5447, 127.0566, True),
    StationRow("잠실",      "2호선",  37.5133, 127.1001, True),
    StationRow("선릉",      "2호선",  37.5044, 127.0490, True),
    StationRow("역삼",      "2호선",  37.5007, 127.0362, True),
    StationRow("삼성",      "2호선",  37.5088, 127.0633, True),
    StationRow("신사",      "3호선",  37.5147, 127.0200, True),
    StationRow("압구정",    "3호선",  37.5272, 127.0282, True),
    StationRow("안국",      "3호선",  37.5759, 126.9854, True),
    StationRow("경복궁",    "3호선",  37.5759, 126.9749, True),
    StationRow("이태원",    "6호선",  37.5340, 126.9946, True),
    StationRow("한강진",    "6호선",  37.5298, 126.9996, True),
    StationRow("상수",      "6호선",  37.5479, 126.9224, True),
    # 연남동 제거: 독립 역이 아닌 홍대입구역 생활권 (중복)
    StationRow("여의도",    "5호선",  37.5217, 126.9240, True),
    StationRow("당산",      "2호선",  37.5343, 126.9007, True),
    StationRow("명동",      "4호선",  37.5636, 126.9857, True),
    StationRow("동대문",    "1호선",  37.5717, 127.0098, True),
    StationRow("동대문역사문화공원", "2호선", 37.5650, 127.0076, True),
    StationRow("왕십리",    "2호선",  37.5612, 127.0370, True),
    StationRow("강남구청",  "7호선",  37.5148, 127.0407, True),
    StationRow("뚝섬",      "2호선",  37.5482, 127.0440, True),
    StationRow("서울숲",    "수인분당선", 37.5444, 127.0451, True),
    StationRow("종로3가",   "1호선",  37.5710, 126.9922, True),
    StationRow("을지로입구", "2호선", 37.5660, 126.9830, True),
    StationRow("시청",      "1호선",  37.5665, 126.9775, True),
    StationRow("광화문",    "5호선",  37.5715, 126.9768, True),
    StationRow("종각",      "1호선",  37.5702, 126.9830, True),
    StationRow("혜화",      "4호선",  37.5822, 127.0020, True),
    StationRow("낙성대",    "2호선",  37.4764, 126.9637, True),
    StationRow("서울대입구", "2호선", 37.4812, 126.9527, True),
    StationRow("신림",      "2호선",  37.4844, 126.9294, True),
    StationRow("봉은사",    "9호선",  37.5149, 127.0591, True),
    StationRow("청담",      "7호선",  37.5232, 127.0531, True),
    StationRow("강동",      "5호선",  37.5303, 127.1235, True),
    StationRow("천호",      "5호선",  37.5388, 127.1238, True),

    # ── 미지원 역 (is_supported=False) ─────────────────────────────────────
    # 향후 확장 예정; 현재 STATION_NOT_SUPPORTED 응답 반환
    StationRow("신도림",    "1호선",  37.5088, 126.8912, False),
    StationRow("구로디지털단지", "2호선", 37.4852, 126.9013, False),
    StationRow("대림",      "2호선",  37.4929, 126.8958, False),
    StationRow("사당",      "2호선",  37.4763, 126.9815, False),
    StationRow("방배",      "2호선",  37.4817, 126.9978, False),
    StationRow("서초",      "2호선",  37.4836, 127.0116, False),
    StationRow("교대",      "2호선",  37.4934, 127.0141, False),
    StationRow("수서",      "3호선",  37.4875, 127.1022, False),
    StationRow("복정",      "수인분당선", 37.4826, 127.1248, False),
    StationRow("모란",      "수인분당선", 37.4348, 127.1295, False),
    StationRow("판교",      "신분당선", 37.3949, 127.1112, False),
    StationRow("정자",      "신분당선", 37.3598, 127.1072, False),
    StationRow("미금",      "신분당선", 37.3530, 127.0969, False),
    StationRow("동천",      "신분당선", 37.3454, 127.0831, False),
    StationRow("수지구청",  "신분당선", 37.3271, 127.0882, False),
    StationRow("성복",      "신분당선", 37.3166, 127.0750, False),
    StationRow("상현",      "신분당선", 37.2979, 127.0558, False),
    StationRow("광교중앙",  "신분당선", 37.2817, 127.0466, False),
    StationRow("광교",      "신분당선", 37.2749, 127.0445, False),
    StationRow("인천공항1터미널", "공항철도", 37.4491, 126.4517, False),
    StationRow("인천공항2터미널", "공항철도", 37.4656, 126.4282, False),
    StationRow("서울역",    "1호선",  37.5547, 126.9706, False),
    StationRow("용산",      "1호선",  37.5299, 126.9648, False),
    StationRow("노량진",    "1호선",  37.5135, 126.9424, False),
    StationRow("영등포",    "1호선",  37.5159, 126.9070, False),
    StationRow("부천",      "1호선",  37.5038, 126.7866, False),
    StationRow("부평",      "1호선",  37.4897, 126.7234, False),
]
# fmt: on

MVP_SUPPORTED_COUNT = sum(1 for s in STATIONS if s.is_supported)
TOTAL_COUNT = len(STATIONS)


async def seed(database_url: str | None = None) -> None:
    try:
        import asyncpg
    except ImportError:
        print("❌ asyncpg not installed. Run: uv pip install asyncpg", file=sys.stderr)
        sys.exit(1)

    url = database_url or os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/whatwedoin",
    )
    # asyncpg expects postgresql:// (no driver suffix)
    url = url.replace("postgresql+asyncpg://", "postgresql://")

    print(f"Connecting to DB: {url.split('@')[-1]}")
    conn = await asyncpg.connect(url)
    try:
        upserted = 0
        lines_upserted = 0

        for s in STATIONS:
            # stations upsert: (external_source, external_id) 기준
            station_id = await conn.fetchval(
                """
                INSERT INTO stations (external_source, external_id, name, lat, lng, geom, is_supported)
                VALUES (
                    'KAKAO',
                    $1,
                    $2,
                    $3,
                    $4,
                    ST_SetSRID(ST_MakePoint($4, $3), 4326)::geography,
                    $5
                )
                ON CONFLICT (external_source, external_id) DO UPDATE SET
                    name         = EXCLUDED.name,
                    lat          = EXCLUDED.lat,
                    lng          = EXCLUDED.lng,
                    geom         = EXCLUDED.geom,
                    is_supported = EXCLUDED.is_supported
                RETURNING station_id
                """,
                s.external_id,
                s.name,
                s.lat,
                s.lng,
                s.is_supported,
            )
            upserted += 1

            # station_lines upsert: 동일 (station_id, line_no) 중복 시 무시
            await conn.execute(
                """
                INSERT INTO station_lines (station_id, line_no)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                station_id,
                s.line,
            )
            lines_upserted += 1

        # ── 적재 결과 검증 ─────────────────────────────────────────────────
        db_total = await conn.fetchval("SELECT COUNT(*) FROM stations")
        db_supported = await conn.fetchval(
            "SELECT COUNT(*) FROM stations WHERE is_supported = true"
        )
        db_lines = await conn.fetchval("SELECT COUNT(*) FROM station_lines")

        print(
            f"[OK] 적재 완료 -> stations {db_total}개 (is_supported=true {db_supported}개), "
            f"station_lines {db_lines}개"
        )

        if db_supported < MVP_SUPPORTED_COUNT:
            print(
                f"[WARN] 지원 역 {MVP_SUPPORTED_COUNT}개 기대, {db_supported}개 적재됨",
                file=sys.stderr,
            )
            sys.exit(1)

        # 지원 역 목록 출력
        rows = await conn.fetch(
            """
            SELECT s.name,
                   ST_Y(s.geom::geometry) AS lat,
                   ST_X(s.geom::geometry) AS lng,
                   array_agg(sl.line_no ORDER BY sl.line_no) AS lines
            FROM stations s
            LEFT JOIN station_lines sl ON sl.station_id = s.station_id
            WHERE s.is_supported = true
            GROUP BY s.station_id, s.name, s.geom
            ORDER BY s.name
            """
        )
        print("\n지원 역 목록 (is_supported=true):")
        for r in rows:
            lines_str = ", ".join(l for l in r["lines"] if l is not None) if r["lines"] else "-"
            print(f"  {r['name']}  lat={r['lat']:.4f}, lng={r['lng']:.4f}  노선={lines_str}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
