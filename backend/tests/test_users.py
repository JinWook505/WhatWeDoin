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


# ---------------------------------------------------------------------------
# DELETE /v1/users/me — withdrawal anonymisation logic checks
# ---------------------------------------------------------------------------

def test_withdrawal_anonymisation_sql_shape():
    """Verify the anonymisation SQL targets the right column names (no DB needed)."""
    from app.routers.users import delete_me
    import inspect
    src = inspect.getsource(delete_me)
    assert "status" in src and "WITHDRAWN" in src
    assert "oauth_id" in src and "withdrawn_" in src
    assert "nickname" in src and "탈퇴한 사용자" in src
    assert "email" in src
    assert "profile_image_url" in src


def test_theme_tags_empty_list_allowed():
    # Empty list means "clear all tags" — should be valid
    req = UserUpdateRequest(preferred_theme_tags=[])
    assert req.preferred_theme_tags == []
