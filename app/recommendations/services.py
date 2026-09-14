"""
recommendations/services.py

Orchestration layer for the recommendation engine.

Responsibilities:
  - Fetch job and candidate data (via crud).
  - Apply the must-have skill hard filter.
  - Call scoring functions (via scorer).
  - Rank and limit results.
  - Build the response payload.

No SQL lives here — all database access goes through crud.py.
No HTTP concerns live here — those belong in routes.py.
"""

from __future__ import annotations

from app.database.connection import get_connection
from app.recommendations import crud
from app.recommendations import scorer as sc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalise(value: str) -> str:
    return value.strip().lower()


def _group_by_candidate(rows: list[dict], key: str = "candidate_id") -> dict[str, list[dict]]:
    """
    Group a flat list of rows into a dict keyed by candidate_id.
    E.g. [{candidate_id: 'x', skill_name: 'Python'}, ...] →
         {'x': [{skill_name: 'Python'}, ...]}
    """
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        cid = str(row[key])
        grouped.setdefault(cid, []).append(row)
    return grouped


def _passes_must_have_filter(
    candidate_skill_names: set[str],
    must_have_skills: list[str],
) -> bool:
    """Return True if the candidate holds every must-have skill."""
    required = {_normalise(s) for s in must_have_skills}
    return required.issubset(candidate_skill_names)


def _build_breakdown(
    nice_to_have_score: float,
    location_score: float,
    salary_score: float,
    experience_score: float,
    weights: dict,
) -> dict:
    """Assemble the per-dimension breakdown section of the response."""
    return {
        "nice_to_have": {
            "score": round(nice_to_have_score, 2),
            "weight": weights["nice_to_have"],
            "weighted_score": round(nice_to_have_score * weights["nice_to_have"] / 100, 2),
        },
        "location": {
            "score": round(location_score, 2),
            "weight": weights["location"],
            "weighted_score": round(location_score * weights["location"] / 100, 2),
        },
        "salary": {
            "score": round(salary_score, 2),
            "weight": weights["salary"],
            "weighted_score": round(salary_score * weights["salary"] / 100, 2),
        },
        "experience": {
            "score": round(experience_score, 2),
            "weight": weights["experience"],
            "weighted_score": round(experience_score * weights["experience"] / 100, 2),
        },
    }


# ---------------------------------------------------------------------------
# Public service function
# ---------------------------------------------------------------------------

def get_recommendations(job_id: str, weights: dict, limit: int) -> dict:
    """
    Main entry point for the recommendation engine.

    Parameters
    ----------
    job_id  : UUID string of the target job.
    weights : dict with keys nice_to_have, location, salary, experience
              (each a float; all four must sum to 100).
    limit   : maximum number of candidates to return.

    Returns
    -------
    Response dict ready to be JSON-serialised by the route layer.

    Raises
    ------
    LookupError  if the job does not exist.
    """
    with get_connection() as conn:
        # ------------------------------------------------------------------
        # 1. Fetch job
        # ------------------------------------------------------------------
        job = crud.fetch_job_for_recommendation(conn, job_id)
        if job is None:
            raise LookupError(f"Job '{job_id}' not found.")

        job_skills_rows = crud.fetch_job_skills_for_recommendation(conn, job_id)
        job_locations_rows = crud.fetch_job_locations_for_recommendation(conn, job_id)

        # ------------------------------------------------------------------
        # 2. Fetch candidates + child data (bulk — no N+1)
        # ------------------------------------------------------------------
        candidates = crud.fetch_all_candidates_for_recommendation(conn)

        if not candidates:
            return _build_response(job, job_skills_rows, job_locations_rows, weights, [], 0)

        candidate_ids = [str(c["id"]) for c in candidates]

        all_skill_rows = crud.fetch_all_candidate_skills_bulk(conn, candidate_ids)
        all_location_rows = crud.fetch_all_candidate_locations_bulk(conn, candidate_ids)

    # Group child rows by candidate_id — outside the connection context
    skills_by_candidate = _group_by_candidate(all_skill_rows)
    locations_by_candidate = _group_by_candidate(all_location_rows)

    # ------------------------------------------------------------------
    # 3. Derive job skill sets
    # ------------------------------------------------------------------
    must_have_skills = [r["skill_name"] for r in job_skills_rows if r["skill_type"] == "must_have"]
    nice_to_have_skills = [r["skill_name"] for r in job_skills_rows if r["skill_type"] == "nice_to_have"]
    job_cities = [r["city"] for r in job_locations_rows]
    remote_allowed: bool = bool(job["remote_allowed"])

    # ------------------------------------------------------------------
    # 4. Score each candidate
    # ------------------------------------------------------------------
    scored: list[dict] = []

    for candidate in candidates:
        cid = str(candidate["id"])

        candidate_skill_rows = skills_by_candidate.get(cid, [])
        candidate_location_rows = locations_by_candidate.get(cid, [])

        candidate_skill_names_normalised = {
            _normalise(r["skill_name"]) for r in candidate_skill_rows
        }
        candidate_skill_names_raw = [r["skill_name"] for r in candidate_skill_rows]
        candidate_cities = [r["city"] for r in candidate_location_rows]

        # Hard filter — must-have skills
        if not _passes_must_have_filter(candidate_skill_names_normalised, must_have_skills):
            continue

        # Dimension scores
        nth_score = sc.calculate_nice_to_have_score(nice_to_have_skills, candidate_skill_names_raw)
        loc_score = sc.calculate_location_score(job_cities, remote_allowed, candidate_cities)
        sal_score = sc.calculate_salary_score(
            candidate["expected_salary"],
            job["salary_min"],
            job["salary_max"],
        )
        exp_score = sc.calculate_experience_score(
            candidate["years_of_experience"],
            job["min_years_experience"],
        )

        final = sc.calculate_final_score(
            nth_score, loc_score, sal_score, exp_score,
            weights["nice_to_have"], weights["location"],
            weights["salary"], weights["experience"],
        )

        scored.append({
            "candidate": {
                "id": cid,
                "name": candidate["name"],
                "summary": candidate["summary"],
                "expected_salary": float(candidate["expected_salary"]) if candidate["expected_salary"] is not None else None,
                "years_of_experience": float(candidate["years_of_experience"]) if candidate["years_of_experience"] is not None else None,
            },
            "score": final,
            "breakdown": _build_breakdown(nth_score, loc_score, sal_score, exp_score, weights),
            # Secondary sort key stored temporarily — removed before response
            "_candidate_id": cid,
        })

    # ------------------------------------------------------------------
    # 5. Rank — descending score, then ascending candidate_id for stability
    # ------------------------------------------------------------------
    scored.sort(key=lambda r: (-r["score"], r["_candidate_id"]))

    # Apply limit
    ranked = scored[:limit]

    # Strip internal sort key
    for r in ranked:
        del r["_candidate_id"]

    return _build_response(job, job_skills_rows, job_locations_rows, weights, ranked, len(scored))


# ---------------------------------------------------------------------------
# Response builder
# ---------------------------------------------------------------------------

def _build_response(
    job: dict,
    job_skills_rows: list[dict],
    job_locations_rows: list[dict],
    weights: dict,
    results: list[dict],
    total_results: int,
) -> dict:
    return {
        "job": {
            "id": str(job["id"]),
            "title": job["title"],
            "company_name": job["company_name"],
            "description": job["description"],
            "min_years_experience": float(job["min_years_experience"]) if job["min_years_experience"] is not None else None,
            "salary_min": float(job["salary_min"]) if job["salary_min"] is not None else None,
            "salary_max": float(job["salary_max"]) if job["salary_max"] is not None else None,
            "remote_allowed": job["remote_allowed"],
            "skills": [
                {"skill_name": r["skill_name"], "skill_type": r["skill_type"]}
                for r in job_skills_rows
            ],
            "required_skills": [
                {"skill_name": r["skill_name"], "skill_type": r["skill_type"]}
                for r in job_skills_rows
            ],
            "locations": [r["city"] for r in job_locations_rows],
        },
        "weights": {
            "nice_to_have": weights["nice_to_have"],
            "location": weights["location"],
            "salary": weights["salary"],
            "experience": weights["experience"],
        },
        "results": results,
        "total_results": total_results,
    }


# ---------------------------------------------------------------------------
# Candidate → Job recommendation
# ---------------------------------------------------------------------------

def get_job_recommendations(candidate_id: str, weights: dict, limit: int) -> dict:
    """
    Given a candidate, return the best-matching jobs ranked by the same
    four-dimension scoring system used by get_recommendations().

    Parameters
    ----------
    candidate_id : UUID string of the target candidate.
    weights      : dict with keys nice_to_have, location, salary, experience
                   (each a float; all four must sum to 100).
    limit        : maximum number of jobs to return.

    Returns
    -------
    Response dict ready to be JSON-serialised by the route layer.

    Raises
    ------
    LookupError  if the candidate does not exist.
    """
    with get_connection() as conn:
        # ------------------------------------------------------------------
        # 1. Fetch the candidate
        # ------------------------------------------------------------------
        candidate = crud.fetch_candidate_for_recommendation(conn, candidate_id)
        if candidate is None:
            raise LookupError(f"Candidate '{candidate_id}' not found.")

        candidate_skill_rows = crud.fetch_all_candidate_skills_bulk(conn, [candidate_id])
        candidate_location_rows = crud.fetch_all_candidate_locations_bulk(conn, [candidate_id])

        # ------------------------------------------------------------------
        # 2. Fetch all jobs + child data in bulk (no N+1)
        # ------------------------------------------------------------------
        jobs = crud.fetch_all_jobs_for_recommendation(conn)

        if not jobs:
            return _build_job_response(candidate, candidate_skill_rows, candidate_location_rows, weights, [], 0)

        job_ids = [str(j["id"]) for j in jobs]

        all_job_skill_rows = crud.fetch_all_job_skills_bulk(conn, job_ids)
        all_job_location_rows = crud.fetch_all_job_locations_bulk(conn, job_ids)

    # Group job child rows by job_id — outside the connection context
    skills_by_job = _group_by_job(all_job_skill_rows)
    locations_by_job = _group_by_job(all_job_location_rows)

    # ------------------------------------------------------------------
    # 3. Derive candidate data for scoring
    # ------------------------------------------------------------------
    candidate_skill_names_normalised = {
        _normalise(r["skill_name"]) for r in candidate_skill_rows
    }
    candidate_skill_names_raw = [r["skill_name"] for r in candidate_skill_rows]
    candidate_cities = [r["city"] for r in candidate_location_rows]

    # ------------------------------------------------------------------
    # 4. Score each job
    # ------------------------------------------------------------------
    scored: list[dict] = []

    for job in jobs:
        jid = str(job["id"])

        job_skill_rows = skills_by_job.get(jid, [])
        job_location_rows = locations_by_job.get(jid, [])

        must_have_skills = [r["skill_name"] for r in job_skill_rows if r["skill_type"] == "must_have"]
        nice_to_have_skills = [r["skill_name"] for r in job_skill_rows if r["skill_type"] == "nice_to_have"]
        job_cities = [r["city"] for r in job_location_rows]
        remote_allowed: bool = bool(job["remote_allowed"])

        # Hard filter — candidate must have every must-have skill for this job
        if not _passes_must_have_filter(candidate_skill_names_normalised, must_have_skills):
            continue

        # Dimension scores — reuse scorer functions unchanged
        nth_score = sc.calculate_nice_to_have_score(nice_to_have_skills, candidate_skill_names_raw)
        loc_score = sc.calculate_location_score(job_cities, remote_allowed, candidate_cities)
        sal_score = sc.calculate_salary_score(
            candidate["expected_salary"],
            job["salary_min"],
            job["salary_max"],
        )
        exp_score = sc.calculate_experience_score(
            candidate["years_of_experience"],
            job["min_years_experience"],
        )

        final = sc.calculate_final_score(
            nth_score, loc_score, sal_score, exp_score,
            weights["nice_to_have"], weights["location"],
            weights["salary"], weights["experience"],
        )

        scored.append({
            "job": {
                "id": jid,
                "title": job["title"],
                "company_name": job["company_name"],
                "description": job["description"],
                "min_years_experience": float(job["min_years_experience"]) if job["min_years_experience"] is not None else None,
                "salary_min": float(job["salary_min"]) if job["salary_min"] is not None else None,
                "salary_max": float(job["salary_max"]) if job["salary_max"] is not None else None,
                "remote_allowed": job["remote_allowed"],
                "skills": [
                    {"skill_name": r["skill_name"], "skill_type": r["skill_type"]}
                    for r in job_skill_rows
                ],
                "required_skills": [
                    {"skill_name": r["skill_name"], "skill_type": r["skill_type"]}
                    for r in job_skill_rows
                ],
                "locations": [r["city"] for r in job_location_rows],
            },
            "final_score": final,
            "breakdown": _build_breakdown(nth_score, loc_score, sal_score, exp_score, weights),
            # Secondary sort key — removed before returning
            "_job_id": jid,
        })

    # ------------------------------------------------------------------
    # 5. Rank — descending score, then ascending job_id for stability
    # ------------------------------------------------------------------
    scored.sort(key=lambda r: (-r["final_score"], r["_job_id"]))

    ranked = scored[:limit]

    for r in ranked:
        del r["_job_id"]

    return _build_job_response(candidate, candidate_skill_rows, candidate_location_rows, weights, ranked, len(scored))


def _group_by_job(rows: list[dict], key: str = "job_id") -> dict[str, list[dict]]:
    """
    Group a flat list of job-child rows into a dict keyed by job_id.
    Mirrors _group_by_candidate() for the job direction.
    """
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        jid = str(row[key])
        grouped.setdefault(jid, []).append(row)
    return grouped


def _build_job_response(
    candidate: dict,
    candidate_skill_rows: list[dict],
    candidate_location_rows: list[dict],
    weights: dict,
    results: list[dict],
    total_results: int,
) -> dict:
    return {
        "candidate": {
            "id": str(candidate["id"]),
            "name": candidate["name"],
            "summary": candidate["summary"],
            "expected_salary": float(candidate["expected_salary"]) if candidate["expected_salary"] is not None else None,
            "years_of_experience": float(candidate["years_of_experience"]) if candidate["years_of_experience"] is not None else None,
            "skills": [r["skill_name"] for r in candidate_skill_rows],
            "locations": [r["city"] for r in candidate_location_rows],
        },
        "weights": {
            "nice_to_have": weights["nice_to_have"],
            "location": weights["location"],
            "salary": weights["salary"],
            "experience": weights["experience"],
        },
        "results": results,
        "total_results": total_results,
    }
