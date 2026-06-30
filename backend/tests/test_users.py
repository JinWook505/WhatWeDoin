"""Tests for users router logic."""
import pytest
from pydantic import ValidationError

from app.routers.users import UserUpdateRequest


def test_nickname_too_short():
    with pytest.raises(ValidationError):
        UserUpdateRequest(nickname="a")


def test_nickname_too_long():
    with pytest.raises(ValidationError):
        UserUpdateRequest(nickname="a" * 21)


def test_nickname_valid():
    req = UserUpdateRequest(nickname="홍길동")
    assert req.nickname == "홍길동"


def test_nickname_stripped():
    req = UserUpdateRequest(nickname="  홍길동  ")
    assert req.nickname == "홍길동"


def test_theme_tags_too_many():
    with pytest.raises(ValidationError):
        UserUpdateRequest(preferred_theme_tags=["a", "b", "c", "d", "e", "f"])


def test_theme_tags_max_allowed():
    req = UserUpdateRequest(preferred_theme_tags=["a", "b", "c", "d", "e"])
    assert len(req.preferred_theme_tags) == 5


def test_empty_request_allowed():
    req = UserUpdateRequest()
    assert req.nickname is None
    assert req.preferred_theme_tags is None
