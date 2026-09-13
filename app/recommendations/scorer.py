"""
recommendations/scorer.py

Pure, stateless scoring functions for the recommendation engine.

Rules:
  - No database queries here.
  - Every function accepts plain Python values and returns a float in [0, 100].
  - All string comparisons are case-insensitive and whitespace-trimmed.
  - The scoring logic is isolated here so it can be changed without touching
    the service or route layer.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalise(value: str) -> str:
    """Lowercase + strip a string for consistent comparison."""
    return value.strip().lower()


def _normalise_set(values: list[str]) -> set[str]:
    return {_normalise(v) for v in values}


# ---------------------------------------------------------------------------
# Individual dimension scores  (each returns float in [0, 100])
# ---------------------------------------------------------------------------

def calculate_nice_to_have_score(
    job_nice_to_have_skills: list[str],
    candidate_skills: list[str],
) -> float:
    """
    Proportion of the job's nice-to-have skills that the candidate possesses.

    Returns 100 if the job has no nice-to-have skills (no optional requirements
    the candidate can fail).
    """
    if not job_nice_to_have_skills:
        return 100.0

    job_set = _normalise_set(job_nice_to_have_skills)
    candidate_set = _normalise_set(candidate_skills)
    matched = len(job_set & candidate_set)
    return round(matched / len(job_set) * 100, 10)


def calculate_location_score(
    job_cities: list[str],
    remote_allowed: bool,
    candidate_cities: list[str],
) -> float:
    """
    Priority:
      Exact city match  → 100
      Remote allowed    → 70
      No match          → 0
    """
    job_city_set = _normalise_set(job_cities)
    candidate_city_set = _normalise_set(candidate_cities)

    if job_city_set & candidate_city_set:
        return 100.0

    if remote_allowed:
        return 70.0

    return 0.0


def calculate_salary_score(
    candidate_expected_salary: float | None,
    job_salary_min: float | None,
    job_salary_max: float | None,
) -> float:
    """
    Salary fit score (0–100). Salary is never a hard filter.

    Behaviour:
      - Missing salary data on either side → neutral score of 50.
      - Candidate salary within [salary_min, salary_max] → 100.
      - Candidate salary below salary_min → 100  (under-asking is fine for
        the employer; the candidate may negotiate up).
      - Candidate salary above salary_max → score decreases linearly from 100
        at salary_max toward 0 as the gap widens.  The score reaches 0 when
        the candidate expects 2× the job's maximum (an extreme overshoot).

    The formula is isolated here and can be replaced without touching any
    other layer.
    """
    # Insufficient information — return neutral
    if candidate_expected_salary is None or job_salary_min is None or job_salary_max is None:
        return 50.0

    salary_max = float(job_salary_max)
    salary_min = float(job_salary_min)
    expected = float(candidate_expected_salary)

    # Candidate asks for at or below the range — full score
    if expected <= salary_max:
        return 100.0

    # Candidate asks above salary_max — linear penalty
    # Score reaches 0 when expected == 2 * salary_max (100 % overshoot)
    if salary_max == 0:
        return 0.0

    overshoot_ratio = (expected - salary_max) / salary_max  # 0 → 1 as expected → 2×max
    score = max(0.0, 100.0 * (1.0 - overshoot_ratio))
    return round(score, 10)


def calculate_experience_score(
    candidate_years: float | None,
    job_min_years: float | None,
) -> float:
    """
    Experience fit score (0–100). Experience is never a hard filter.

    Behaviour:
      - No job minimum → 100 (no requirement to miss).
      - Candidate meets or exceeds requirement → 100.
      - Candidate below requirement → (candidate_years / required) * 100.
      - Missing candidate years → 0 (no information to award points).
    """
    if job_min_years is None or float(job_min_years) == 0:
        return 100.0

    if candidate_years is None:
        return 0.0

    required = float(job_min_years)
    actual = float(candidate_years)

    if actual >= required:
        return 100.0

    return round(actual / required * 100, 10)


def calculate_final_score(
    nice_to_have_score: float,
    location_score: float,
    salary_score: float,
    experience_score: float,
    nice_to_have_weight: float,
    location_weight: float,
    salary_weight: float,
    experience_weight: float,
) -> float:
    """
    Weighted combination of the four dimension scores.

    Because the four weights must sum to exactly 100, the result is always
    in [0, 100].  Rounded to 2 decimal places.
    """
    score = (
        nice_to_have_score * nice_to_have_weight / 100
        + location_score * location_weight / 100
        + salary_score * salary_weight / 100
        + experience_score * experience_weight / 100
    )
    return round(score, 2)
