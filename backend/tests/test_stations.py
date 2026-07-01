"""Tests for stations router helper logic."""
from app.routers.stations import StationResult


def test_station_result_defaults():
    s = StationResult(station_id=1, name="홍대입구", lat=37.557, lng=126.924)
    assert s.lines == []
    assert s.is_supported is True


def test_station_result_with_lines():
    s = StationResult(
        station_id=2, name="강남", lat=37.498, lng=127.028,
        lines=["2호선", "신분당선"], is_supported=True,
    )
    assert "2호선" in s.lines
    assert len(s.lines) == 2
