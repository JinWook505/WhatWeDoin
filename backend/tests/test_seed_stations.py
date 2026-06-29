"""Unit tests for seed_stations data and logic (no DB required)."""

from scripts.seed_stations import STATIONS, MVP_SUPPORTED_COUNT, TOTAL_COUNT, StationRow


def test_all_stations_have_valid_coords():
    for s in STATIONS:
        assert 33.0 <= s.lat <= 38.5, f"{s.name}: lat={s.lat} out of Korea range"
        assert 124.0 <= s.lng <= 132.0, f"{s.name}: lng={s.lng} out of Korea range"


def test_mvp_supported_count_matches():
    count = sum(1 for s in STATIONS if s.is_supported)
    assert count == MVP_SUPPORTED_COUNT
    assert MVP_SUPPORTED_COUNT > 0


def test_total_count_matches():
    assert len(STATIONS) == TOTAL_COUNT


def test_no_duplicate_name_line():
    seen: set[tuple[str, str]] = set()
    for s in STATIONS:
        key = (s.name, s.line)
        assert key not in seen, f"Duplicate station: {s.name} ({s.line})"
        seen.add(key)


def test_all_required_mvp_stations_present():
    required = {"강남", "홍대입구", "신촌", "이태원", "합정", "건대입구", "성수", "잠실"}
    supported_names = {s.name for s in STATIONS if s.is_supported}
    missing = required - supported_names
    assert not missing, f"Missing MVP stations: {missing}"


def test_station_row_fields():
    for s in STATIONS:
        assert isinstance(s, StationRow)
        assert s.name
        assert s.line
        assert isinstance(s.is_supported, bool)
        assert s.external_id


def test_external_ids_are_unique():
    ids = [s.external_id for s in STATIONS]
    assert len(ids) == len(set(ids)), "external_id 중복 발생"
