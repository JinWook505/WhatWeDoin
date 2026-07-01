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
        UserUpdateRequest(
            preferred_theme_tags=["FOOD", "CAFE", "BAR", "PARK", "MOVIE", "ACTIVITY"]
        )


def test_theme_tags_max_allowed():
    req = UserUpdateRequest(preferred_theme_tags=["FOOD", "CAFE", "BAR", "PARK", "MOVIE"])
    assert len(req.preferred_theme_tags) == 5


def test_theme_tags_invalid_value_rejected():
    with pytest.raises(ValidationError):
        UserUpdateRequest(preferred_theme_tags=["NOT_A_REAL_TAG"])


def test_preferred_companion_type_invalid_rejected():
    with pytest.raises(ValidationError):
        UserUpdateRequest(preferred_companion_type="BESTFRIEND")


def test_preferred_companion_type_valid():
    req = UserUpdateRequest(preferred_companion_type="COUPLE")
    assert req.preferred_companion_type == "COUPLE"


def test_preferred_budget_invalid_rejected():
    with pytest.raises(ValidationError):
        UserUpdateRequest(preferred_budget="BUDGET")


def test_preferred_budget_valid():
    req = UserUpdateRequest(preferred_budget="UNDER_30000")
    assert req.preferred_budget == "UNDER_30000"


def test_gender_invalid_rejected():
    with pytest.raises(ValidationError):
        UserUpdateRequest(gender="X")


def test_gender_valid():
    req = UserUpdateRequest(gender="FEMALE")
    assert req.gender == "FEMALE"


def test_dating_stage_invalid_rejected():
    with pytest.raises(ValidationError):
        UserUpdateRequest(dating_stage="MARRIED")


def test_dating_stage_valid():
    req = UserUpdateRequest(dating_stage="SOME")
    assert req.dating_stage == "SOME"


def test_update_me_theme_tags_inlined_not_bound_as_array_param():
    """Regression test for the asyncpg 'sized iterable container expected' bug:
    asyncpg cannot bind a Python str/list to a bound ARRAY(enum) :param, so
    preferred_theme_tags must be inlined as SQL literals (see course_generator.py
    for the established pattern), not passed through CAST(:ptt AS theme_tag[])."""
    from app.routers.users import update_me
    import inspect
    src = inspect.getsource(update_me)
    assert "CAST(:ptt AS theme_tag[])" not in src
    assert "::theme_tag" in src


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
    assert "withdrawn_at" in src
    assert "recommendation_requests" in src


def test_theme_tags_empty_list_allowed():
    # Empty list means "clear all tags" — should be valid
    req = UserUpdateRequest(preferred_theme_tags=[])
    assert req.preferred_theme_tags == []
