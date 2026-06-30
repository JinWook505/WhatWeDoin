"""Tests for GET /v1/courses cursor encoding and filtering logic."""
from app.routers.courses import _decode_cursor, _encode_cursor


def test_cursor_roundtrip():
    enc = _encode_cursor(82.5, 1234)
    decoded = _decode_cursor(enc)
    assert decoded == (82.5, 1234)


def test_cursor_invalid_returns_none():
    assert _decode_cursor("not-valid-base64!!!") is None


def test_cursor_zero_score():
    enc = _encode_cursor(0.0, 1)
    decoded = _decode_cursor(enc)
    assert decoded == (0.0, 1)
