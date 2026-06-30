"""Tests for review validation and bayesian score calculation."""
import pytest
from pydantic import ValidationError

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
