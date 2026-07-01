"""Tests for review validation and bayesian score calculation."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

from app.core.db import get_db
from app.core.deps import get_current_user_optional
from app.main import app
from app.routers.reviews import ReviewRequest, _recalc_bayesian


def test_score_valid():
    r = ReviewRequest(score=85)
    assert r.score == 85


def test_score_not_multiple_of_5():
    with pytest.raises(ValidationError):
        ReviewRequest(score=83)


def test_score_out_of_range_high():
    with pytest.raises(ValidationError):
        ReviewRequest(score=105)


def test_score_out_of_range_low():
    with pytest.raises(ValidationError):
        ReviewRequest(score=-5)


def test_score_zero_allowed():
    r = ReviewRequest(score=0)
    assert r.score == 0


def test_score_100_allowed():
    r = ReviewRequest(score=100)
    assert r.score == 100


def test_bayesian_no_reviews():
    # (5*50 + 0) / (5 + 0) = 50
    assert _recalc_bayesian(0, 0) == 50.0


def test_bayesian_one_review_100():
    # (5*50 + 100) / (5 + 1) = 350/6 ≈ 58.33
    result = _recalc_bayesian(100, 1)
    assert abs(result - 58.333) < 0.01


def test_bayesian_many_reviews():
    # (5*50 + 850) / (5 + 10) = 1100/15 ≈ 73.33
    result = _recalc_bayesian(850, 10)
    assert abs(result - 73.333) < 0.01


def _make_session(summary_row, review_rows):
    session = AsyncMock()
    summary_result = MagicMock()
    summary_result.mappings.return_value.first.return_value = summary_row
    reviews_result = MagicMock()
    reviews_result.mappings.return_value.all.return_value = review_rows
    session.execute = AsyncMock(side_effect=[summary_result, reviews_result])
    return session


@pytest.mark.asyncio
async def test_review_list_includes_author_name_for_logged_in_user():
    summary_row = {"bayesian_score": 82.0, "rating_count": 1, "rating_sum": 90}
    review_row = {
        "id": 1, "score": 90, "comment": "좋아요", "links": "[]", "created_at": None,
        "user_id": 5, "ip_hash": None, "nickname": "홍길동",
    }
    app.dependency_overrides[get_db] = lambda: _make_session(summary_row, [review_row])
    app.dependency_overrides[get_current_user_optional] = lambda: None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/courses/1/reviews")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    review = response.json()["data"]["reviews"][0]
    assert review["author_name"] == "홍길동"


@pytest.mark.asyncio
async def test_review_list_author_name_anonymous_for_ip_based_review():
    summary_row = {"bayesian_score": 50.0, "rating_count": 1, "rating_sum": 50}
    review_row = {
        "id": 2, "score": 50, "comment": None, "links": "[]", "created_at": None,
        "user_id": None, "ip_hash": "abc123", "nickname": None,
    }
    app.dependency_overrides[get_db] = lambda: _make_session(summary_row, [review_row])
    app.dependency_overrides[get_current_user_optional] = lambda: None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/courses/1/reviews")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    review = response.json()["data"]["reviews"][0]
    assert review["author_name"] == "비로그인"
