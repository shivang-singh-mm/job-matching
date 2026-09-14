"""
tests/test_recommendation.py

Unit tests for the recommendation/scoring system.

These tests exercise only pure Python functions — no database, no Flask app,
and no HTTP requests are required.  All tests run in complete isolation.

Modules under test:
  app/recommendations/scorer.py   — individual dimension scoring functions
  app/recommendations/services.py — must-have filter helper
  app/recommendations/routes.py   — weight/limit parameter parsing
"""

import pytest

# ---------------------------------------------------------------------------
# Imports — scorer functions (pure, no I/O)
# ---------------------------------------------------------------------------
from app.recommendations.scorer import (
    calculate_nice_to_have_score,
    calculate_location_score,
    calculate_salary_score,
    calculate_experience_score,
    calculate_final_score,
)

# ---------------------------------------------------------------------------
# Imports — must-have filter (pure, no I/O)
# ---------------------------------------------------------------------------
from app.recommendations.services import _passes_must_have_filter

# ---------------------------------------------------------------------------
# Imports — route-layer parameter parsing (pure, no Flask context needed)
# ---------------------------------------------------------------------------
from app.recommendations.routes import _parse_weights, _parse_limit


# ===========================================================================
# 1. Must-have skill hard filter
# ===========================================================================

class TestMustHaveFilter:
    """_passes_must_have_filter is the shared gate for both recommendation
    directions — tested once, applies to both job→candidate and
    candidate→job flows."""

    def test_candidate_with_all_must_have_skills_passes(self):
        candidate_skills = {"python", "fastapi", "postgresql"}
        must_have = ["Python", "FastAPI"]
        assert _passes_must_have_filter(candidate_skills, must_have) is True

    def test_candidate_missing_one_must_have_skill_is_excluded(self):
        candidate_skills = {"python", "fastapi"}
        must_have = ["Python", "FastAPI", "PostgreSQL"]
        assert _passes_must_have_filter(candidate_skills, must_have) is False

    def test_candidate_missing_all_must_have_skills_is_excluded(self):
        candidate_skills = {"java", "spring"}
        must_have = ["Python", "FastAPI"]
        assert _passes_must_have_filter(candidate_skills, must_have) is False

    def test_no_must_have_skills_means_every_candidate_passes(self):
        """When a job has no must-have requirements every candidate is eligible."""
        candidate_skills = {"python"}
        must_have = []
        assert _passes_must_have_filter(candidate_skills, must_have) is True

    def test_must_have_comparison_is_case_insensitive(self):
        """Must-have skills must match regardless of case."""
        # The filter receives candidate skills already normalised by the
        # service layer, but the must_have list comes raw from the DB.
        candidate_skills = {"python", "fastapi"}
        must_have = ["PYTHON", "FastAPI"]
        assert _passes_must_have_filter(candidate_skills, must_have) is True

    def test_must_have_comparison_ignores_surrounding_whitespace(self):
        candidate_skills = {"python", "docker"}
        must_have = ["  Python  ", " Docker "]
        assert _passes_must_have_filter(candidate_skills, must_have) is True

    def test_candidate_with_extra_skills_beyond_must_have_passes(self):
        """Having more skills than required must not cause failure."""
        candidate_skills = {"python", "fastapi", "redis", "aws", "docker"}
        must_have = ["Python"]
        assert _passes_must_have_filter(candidate_skills, must_have) is True


# ===========================================================================
# 2. Nice-to-have scoring
# ===========================================================================

class TestNiceToHaveScore:

    def test_all_nice_to_have_matched_returns_100(self):
        score = calculate_nice_to_have_score(
            job_nice_to_have_skills=["Redis", "Docker"],
            candidate_skills=["Redis", "Docker", "Python"],
        )
        assert score == 100.0

    def test_partial_match_returns_proportional_score(self):
        # 2 of 4 matched → 50
        score = calculate_nice_to_have_score(
            job_nice_to_have_skills=["Redis", "Docker", "AWS", "Kafka"],
            candidate_skills=["Redis", "Docker"],
        )
        assert score == pytest.approx(50.0)

    def test_one_of_three_matched(self):
        score = calculate_nice_to_have_score(
            job_nice_to_have_skills=["Redis", "Docker", "AWS"],
            candidate_skills=["Redis"],
        )
        assert score == pytest.approx(100 / 3)

    def test_no_skills_matched_returns_zero(self):
        score = calculate_nice_to_have_score(
            job_nice_to_have_skills=["Redis", "Docker"],
            candidate_skills=["Java", "Spring"],
        )
        assert score == 0.0

    def test_no_nice_to_have_skills_returns_100(self):
        """No optional requirements → nothing to penalise → full score."""
        score = calculate_nice_to_have_score(
            job_nice_to_have_skills=[],
            candidate_skills=["Python"],
        )
        assert score == 100.0

    def test_matching_is_case_insensitive(self):
        score = calculate_nice_to_have_score(
            job_nice_to_have_skills=["Redis", "Docker"],
            candidate_skills=["REDIS", "docker"],
        )
        assert score == 100.0

    def test_matching_ignores_surrounding_whitespace(self):
        score = calculate_nice_to_have_score(
            job_nice_to_have_skills=["  Redis  "],
            candidate_skills=["Redis"],
        )
        assert score == 100.0

    def test_more_matched_skills_gives_higher_score(self):
        """Monotonicity — each additional matched skill increases the score."""
        score_none = calculate_nice_to_have_score(["A", "B", "C", "D"], [])
        score_two  = calculate_nice_to_have_score(["A", "B", "C", "D"], ["A", "B"])
        score_all  = calculate_nice_to_have_score(["A", "B", "C", "D"], ["A", "B", "C", "D"])
        assert score_none < score_two < score_all


# ===========================================================================
# 3. Location scoring
# ===========================================================================

class TestLocationScore:

    def test_exact_city_match_returns_100(self):
        score = calculate_location_score(
            job_cities=["Gurugram"],
            remote_allowed=False,
            candidate_cities=["Gurugram"],
        )
        assert score == 100.0

    def test_no_match_remote_allowed_returns_70(self):
        score = calculate_location_score(
            job_cities=["Gurugram"],
            remote_allowed=True,
            candidate_cities=["Noida"],
        )
        assert score == 70.0

    def test_no_match_remote_not_allowed_returns_0(self):
        score = calculate_location_score(
            job_cities=["Gurugram"],
            remote_allowed=False,
            candidate_cities=["Noida"],
        )
        assert score == 0.0

    def test_city_comparison_is_case_insensitive(self):
        score = calculate_location_score(
            job_cities=["Gurugram"],
            remote_allowed=False,
            candidate_cities=["gurugram"],
        )
        assert score == 100.0

    def test_city_comparison_ignores_surrounding_whitespace(self):
        score = calculate_location_score(
            job_cities=["  Gurugram  "],
            remote_allowed=False,
            candidate_cities=["Gurugram"],
        )
        assert score == 100.0

    def test_exact_match_takes_priority_over_remote(self):
        """City match should return 100 even when remote is also allowed."""
        score = calculate_location_score(
            job_cities=["Gurugram"],
            remote_allowed=True,
            candidate_cities=["Gurugram"],
        )
        assert score == 100.0

    def test_candidate_with_multiple_cities_one_matching(self):
        score = calculate_location_score(
            job_cities=["Gurugram"],
            remote_allowed=False,
            candidate_cities=["Mumbai", "Gurugram"],
        )
        assert score == 100.0

    def test_job_with_multiple_cities_one_matching(self):
        score = calculate_location_score(
            job_cities=["Gurugram", "Bangalore"],
            remote_allowed=False,
            candidate_cities=["Bangalore"],
        )
        assert score == 100.0

    def test_empty_candidate_cities_no_remote(self):
        score = calculate_location_score(
            job_cities=["Gurugram"],
            remote_allowed=False,
            candidate_cities=[],
        )
        assert score == 0.0

    def test_empty_candidate_cities_with_remote(self):
        score = calculate_location_score(
            job_cities=["Gurugram"],
            remote_allowed=True,
            candidate_cities=[],
        )
        assert score == 70.0


# ===========================================================================
# 4. Experience scoring
# ===========================================================================

class TestExperienceScore:

    def test_candidate_meets_exact_requirement_returns_100(self):
        score = calculate_experience_score(candidate_years=4, job_min_years=4)
        assert score == 100.0

    def test_candidate_exceeds_requirement_returns_100(self):
        score = calculate_experience_score(candidate_years=6, job_min_years=4)
        assert score == 100.0

    def test_candidate_below_requirement_gets_proportional_score(self):
        # 2 / 4 * 100 = 50
        score = calculate_experience_score(candidate_years=2, job_min_years=4)
        assert score == pytest.approx(50.0)

    def test_candidate_one_year_of_four_required(self):
        # 1 / 4 * 100 = 25
        score = calculate_experience_score(candidate_years=1, job_min_years=4)
        assert score == pytest.approx(25.0)

    def test_no_minimum_experience_required_returns_100(self):
        score = calculate_experience_score(candidate_years=0, job_min_years=None)
        assert score == 100.0

    def test_zero_minimum_experience_required_returns_100(self):
        score = calculate_experience_score(candidate_years=0, job_min_years=0)
        assert score == 100.0

    def test_missing_candidate_experience_returns_0(self):
        score = calculate_experience_score(candidate_years=None, job_min_years=4)
        assert score == 0.0

    def test_proportional_score_increases_with_experience(self):
        """More experience always produces a higher or equal score."""
        score_1yr = calculate_experience_score(candidate_years=1, job_min_years=5)
        score_3yr = calculate_experience_score(candidate_years=3, job_min_years=5)
        score_5yr = calculate_experience_score(candidate_years=5, job_min_years=5)
        assert score_1yr < score_3yr < score_5yr


# ===========================================================================
# 5. Salary scoring
# ===========================================================================

class TestSalaryScore:

    def test_salary_within_range_returns_100(self):
        score = calculate_salary_score(
            candidate_expected_salary=1_000_000,
            job_salary_min=800_000,
            job_salary_max=1_400_000,
        )
        assert score == 100.0

    def test_salary_exactly_at_max_returns_100(self):
        score = calculate_salary_score(
            candidate_expected_salary=1_400_000,
            job_salary_min=800_000,
            job_salary_max=1_400_000,
        )
        assert score == 100.0

    def test_salary_below_min_returns_100(self):
        """Candidate asking below the floor is still a full score — good for employer."""
        score = calculate_salary_score(
            candidate_expected_salary=600_000,
            job_salary_min=800_000,
            job_salary_max=1_400_000,
        )
        assert score == 100.0

    def test_salary_above_max_returns_reduced_score(self):
        """Candidate asking above the ceiling — score must be below 100."""
        score = calculate_salary_score(
            candidate_expected_salary=1_600_000,
            job_salary_min=800_000,
            job_salary_max=1_400_000,
        )
        assert score < 100.0
        assert score >= 0.0

    def test_extreme_salary_overshoot_returns_zero_or_near_zero(self):
        """
        The implementation reaches 0 when expected == 2 × salary_max.
        Expected = 2_800_000, salary_max = 1_400_000 → overshoot_ratio = 1.0 → score = 0.
        """
        score = calculate_salary_score(
            candidate_expected_salary=2_800_000,
            job_salary_min=800_000,
            job_salary_max=1_400_000,
        )
        assert score == pytest.approx(0.0)

    def test_higher_overshoot_means_lower_score(self):
        """Monotonicity — asking for more above the ceiling always lowers the score."""
        score_slight = calculate_salary_score(1_500_000, 800_000, 1_400_000)
        score_large  = calculate_salary_score(2_000_000, 800_000, 1_400_000)
        assert score_slight > score_large

    def test_null_candidate_salary_returns_neutral(self):
        score = calculate_salary_score(
            candidate_expected_salary=None,
            job_salary_min=800_000,
            job_salary_max=1_400_000,
        )
        assert score == 50.0

    def test_null_job_salary_min_returns_neutral(self):
        score = calculate_salary_score(
            candidate_expected_salary=1_000_000,
            job_salary_min=None,
            job_salary_max=1_400_000,
        )
        assert score == 50.0

    def test_null_job_salary_max_returns_neutral(self):
        score = calculate_salary_score(
            candidate_expected_salary=1_000_000,
            job_salary_min=800_000,
            job_salary_max=None,
        )
        assert score == 50.0

    def test_all_null_salary_values_returns_neutral(self):
        score = calculate_salary_score(None, None, None)
        assert score == 50.0

    def test_salary_score_is_non_negative(self):
        """Score must never go below zero, even with an extreme overshoot."""
        score = calculate_salary_score(
            candidate_expected_salary=999_999_999,
            job_salary_min=100_000,
            job_salary_max=200_000,
        )
        assert score >= 0.0


# ===========================================================================
# 6. Final weighted score calculation
# ===========================================================================

class TestFinalScore:

    def test_equal_weights_and_equal_scores(self):
        """All scores 100, all weights 25 → final = 100."""
        score = calculate_final_score(100, 100, 100, 100, 25, 25, 25, 25)
        assert score == 100.0

    def test_all_scores_zero_returns_zero(self):
        score = calculate_final_score(0, 0, 0, 0, 25, 25, 25, 25)
        assert score == 0.0

    def test_manual_calculation_matches_formula(self):
        """
        nice_to_have_score=50, location_score=100, salary_score=80, experience_score=60
        weights: 30, 30, 20, 20
        expected = 50*30/100 + 100*30/100 + 80*20/100 + 60*20/100
                 = 15 + 30 + 16 + 12 = 73.0
        """
        score = calculate_final_score(
            nice_to_have_score=50,
            location_score=100,
            salary_score=80,
            experience_score=60,
            nice_to_have_weight=30,
            location_weight=30,
            salary_weight=20,
            experience_weight=20,
        )
        assert score == pytest.approx(73.0)

    def test_result_rounded_to_two_decimal_places(self):
        """The implementation rounds to 2 dp."""
        score = calculate_final_score(33.33, 33.33, 33.33, 33.33, 25, 25, 25, 25)
        # 4 * (33.33 * 25 / 100) = 4 * 8.3325 = 33.33
        assert score == round(score, 2)

    def test_changing_weights_changes_score(self):
        """The same raw scores yield a different final score when weights change."""
        score_a = calculate_final_score(100, 0, 100, 0, 50, 50, 0, 0)   # only NTH + location
        score_b = calculate_final_score(100, 0, 100, 0, 0, 0, 50, 50)   # only salary + experience
        # score_a: 100*50/100 + 0 = 50 ;  score_b: 100*50/100 + 0 = 50 — pick different case
        score_c = calculate_final_score(100, 50, 0, 0, 50, 50, 0, 0)    # NTH=100, loc=50
        score_d = calculate_final_score(100, 50, 0, 0, 0, 0, 50, 50)    # sal=0, exp=0
        assert score_c != score_d

    def test_higher_weight_on_stronger_score_raises_total(self):
        """Giving more weight to the dimension where the candidate scores higher
        must produce a higher final score."""
        # location=100, salary=0; vary where the weight goes
        score_weight_location = calculate_final_score(50, 100, 0, 50, 25, 50, 0, 25)
        score_weight_salary   = calculate_final_score(50, 100, 0, 50, 25, 0, 50, 25)
        assert score_weight_location > score_weight_salary

    def test_final_score_stays_within_0_and_100(self):
        """Edge-case: mix of 0 and 100 scores never leaves the [0, 100] range."""
        for nth, loc, sal, exp in [
            (0, 0, 0, 0),
            (100, 100, 100, 100),
            (100, 0, 100, 0),
            (0, 100, 0, 100),
        ]:
            score = calculate_final_score(nth, loc, sal, exp, 25, 25, 25, 25)
            assert 0.0 <= score <= 100.0


# ===========================================================================
# 7. Weight parameter validation (route layer helpers)
# ===========================================================================

class TestParseWeights:
    """_parse_weights operates on a plain dict (mimicking Flask's request.args)
    so no Flask application context is needed."""

    def _args(self, nth=30, loc=30, sal=20, exp=20):
        return {
            "nice_to_have_weight": str(nth),
            "location_weight": str(loc),
            "salary_weight": str(sal),
            "experience_weight": str(exp),
        }

    def test_valid_weights_summing_to_100_are_accepted(self):
        weights, error = _parse_weights(self._args())
        assert error is None
        assert weights == {
            "nice_to_have": 30.0,
            "location": 30.0,
            "salary": 20.0,
            "experience": 20.0,
        }

    def test_missing_nice_to_have_weight_is_rejected(self):
        args = self._args()
        del args["nice_to_have_weight"]
        weights, error = _parse_weights(args)
        assert weights is None
        assert error is not None
        assert "nice_to_have_weight" in error

    def test_missing_location_weight_is_rejected(self):
        args = self._args()
        del args["location_weight"]
        weights, error = _parse_weights(args)
        assert weights is None
        assert error is not None

    def test_missing_salary_weight_is_rejected(self):
        args = self._args()
        del args["salary_weight"]
        weights, error = _parse_weights(args)
        assert weights is None
        assert error is not None

    def test_missing_experience_weight_is_rejected(self):
        args = self._args()
        del args["experience_weight"]
        weights, error = _parse_weights(args)
        assert weights is None
        assert error is not None

    def test_non_numeric_weight_is_rejected(self):
        args = self._args()
        args["nice_to_have_weight"] = "abc"
        weights, error = _parse_weights(args)
        assert weights is None
        assert error is not None

    def test_negative_weight_is_rejected(self):
        args = self._args(nth=-10, loc=40, sal=40, exp=30)
        weights, error = _parse_weights(args)
        assert weights is None
        assert error is not None

    def test_weight_above_100_is_rejected(self):
        args = self._args(nth=110, loc=0, sal=0, exp=0)
        weights, error = _parse_weights(args)
        assert weights is None
        assert error is not None

    def test_weights_not_summing_to_100_are_rejected(self):
        args = self._args(nth=25, loc=25, sal=25, exp=10)  # total = 85
        weights, error = _parse_weights(args)
        assert weights is None
        assert "100" in error

    def test_weights_summing_to_more_than_100_are_rejected(self):
        args = self._args(nth=30, loc=30, sal=30, exp=30)  # total = 120
        weights, error = _parse_weights(args)
        assert weights is None
        assert error is not None

    def test_float_weights_accepted(self):
        """Weights with decimal points should be accepted if they total 100."""
        args = {
            "nice_to_have_weight": "33.33",
            "location_weight": "33.33",
            "salary_weight": "33.34",
            "experience_weight": "0",
        }
        weights, error = _parse_weights(args)
        assert error is None
        assert weights is not None


class TestParseLimit:

    def test_default_limit_is_10_when_not_supplied(self):
        limit, error = _parse_limit({})
        assert error is None
        assert limit == 10

    def test_valid_positive_integer_is_accepted(self):
        limit, error = _parse_limit({"limit": "5"})
        assert error is None
        assert limit == 5

    def test_zero_limit_is_rejected(self):
        limit, error = _parse_limit({"limit": "0"})
        assert limit is None
        assert error is not None

    def test_negative_limit_is_rejected(self):
        limit, error = _parse_limit({"limit": "-1"})
        assert limit is None
        assert error is not None

    def test_non_integer_limit_is_rejected(self):
        limit, error = _parse_limit({"limit": "abc"})
        assert limit is None
        assert error is not None

    def test_float_limit_is_rejected(self):
        """A float string like '5.5' should not be accepted as a limit."""
        limit, error = _parse_limit({"limit": "5.5"})
        assert limit is None
        assert error is not None
