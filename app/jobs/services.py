"""
jobs/services.py

Business-level orchestration for the jobs module.

Responsibilities:
  - Input validation
  - Coordinating multi-table inserts inside a single transaction
  - Assembling the response shape from crud results

No SQL lives here — all database access goes through crud.py.
"""

from __future__ import annotations

from app.database.connection import get_connection
from app.jobs import crud


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_job(job: dict, skills: list, locations: list) -> dict:
    """Merge a job row with its child collections into one response dict."""
    serialized_skills = [
        {
            "id": str(s["id"]),
            "skill_name": s["skill_name"],
            "skill_type": s["skill_type"],
            "created_at": s["created_at"].isoformat(),
        }
        for s in skills
    ]
    return {
        "id": str(job["id"]),
        "title": job["title"],
        "company_name": job["company_name"],
        "description": job["description"],
        "min_years_experience": float(job["min_years_experience"]) if job["min_years_experience"] is not None else None,
        "salary_min": float(job["salary_min"]) if job["salary_min"] is not None else None,
        "salary_max": float(job["salary_max"]) if job["salary_max"] is not None else None,
        "remote_allowed": job["remote_allowed"],
        "skills": serialized_skills,
        "required_skills": serialized_skills,
        "locations": [
            {
                "id": str(l["id"]),
                "city": l["city"],
                "created_at": l["created_at"].isoformat(),
            }
            for l in locations
        ],
        "created_at": job["created_at"].isoformat(),
        "updated_at": job["updated_at"].isoformat(),
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_create_payload(data: dict) -> list[str]:
    """Return a list of validation error messages, or an empty list if valid."""
    errors = []

    title = data.get("title", "")
    if not isinstance(title, str) or not title.strip():
        errors.append("'title' is required and must be a non-empty string.")

    company_name = data.get("company_name", "")
    if not isinstance(company_name, str) or not company_name.strip():
        errors.append("'company_name' is required and must be a non-empty string.")

    min_years = data.get("min_years_experience")
    if min_years is None:
        errors.append("'min_years_experience' is required.")
    elif not isinstance(min_years, (int, float)) or min_years < 0:
        errors.append("'min_years_experience' must be a non-negative number.")

    salary_min = data.get("salary_min")
    if salary_min is None:
        errors.append("'salary_min' is required.")
    elif not isinstance(salary_min, (int, float)) or salary_min < 0:
        errors.append("'salary_min' must be a non-negative number.")

    salary_max = data.get("salary_max")
    if salary_max is None:
        errors.append("'salary_max' is required.")
    elif not isinstance(salary_max, (int, float)) or salary_max < 0:
        errors.append("'salary_max' must be a non-negative number.")

    # Cross-field check — only if both values passed their individual checks
    if isinstance(salary_min, (int, float)) and isinstance(salary_max, (int, float)):
        if salary_max < salary_min:
            errors.append("'salary_max' must be greater than or equal to 'salary_min'.")

    remote_allowed = data.get("remote_allowed")
    if remote_allowed is None:
        errors.append("'remote_allowed' is required.")
    elif not isinstance(remote_allowed, bool):
        errors.append("'remote_allowed' must be a boolean.")

    # Optional arrays — validate shape if provided
    valid_skill_types = {"must_have", "nice_to_have"}
    skills_input = data.get("skills") if "skills" in data else data.get("required_skills", [])
    if skills_input:
        for skill in skills_input:
            if not isinstance(skill.get("skill_name", ""), str) or not skill["skill_name"].strip():
                errors.append("Each skill must have a non-empty 'skill_name'.")
                break
            if skill.get("skill_type") not in valid_skill_types:
                errors.append("Each skill's 'skill_type' must be 'must_have' or 'nice_to_have'.")
                break

    for loc in data.get("locations", []):
        if not isinstance(loc.get("city", ""), str) or not loc["city"].strip():
            errors.append("Each location must have a non-empty 'city'.")
            break

    return errors


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

def create_job(data: dict) -> dict:
    """
    Validate input, then insert the job and all optional child records
    inside a single database transaction.

    Raises ValueError if validation fails.
    """
    errors = _validate_create_payload(data)
    if errors:
        raise ValueError(errors)

    title = data["title"].strip()
    company_name = data["company_name"].strip()
    description = data.get("description") or None
    min_years_experience = data["min_years_experience"]
    salary_min = data["salary_min"]
    salary_max = data["salary_max"]
    remote_allowed = data["remote_allowed"]
    required_skills = data.get("skills") if "skills" in data else data.get("required_skills", [])
    locations = data.get("locations") or []

    with get_connection() as conn:
        try:
            job = crud.insert_job(
                conn,
                title,
                company_name,
                description,
                min_years_experience,
                salary_min,
                salary_max,
                remote_allowed,
            )
            job_id = str(job["id"])

            inserted_skills = []
            for s in required_skills:
                row = crud.insert_job_skill(conn, job_id, s["skill_name"].strip(), s["skill_type"])
                inserted_skills.append(row)

            inserted_locations = []
            for loc in locations:
                row = crud.insert_job_location(conn, job_id, loc["city"].strip())
                inserted_locations.append(row)

            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return _serialize_job(job, inserted_skills, inserted_locations)


def get_job_by_id(job_id: str) -> dict | None:
    """
    Fetch a single job with all child records.
    Returns None if the job does not exist.
    """
    with get_connection() as conn:
        job = crud.fetch_job_by_id(conn, job_id)
        if job is None:
            return None

        skills = crud.fetch_skills_by_job(conn, job_id)
        locations = crud.fetch_locations_by_job(conn, job_id)

    return _serialize_job(job, skills, locations)


def get_all_jobs() -> list[dict]:
    """
    Fetch all jobs with their child records.
    Performs one query per child type to avoid row-explosion from JOINs.
    """
    with get_connection() as conn:
        jobs = crud.fetch_all_jobs(conn)
        if not jobs:
            return []

        job_ids = [str(j["id"]) for j in jobs]

        all_skills = _fetch_children_bulk(conn, job_ids, crud.fetch_skills_by_job)
        all_locations = _fetch_children_bulk(conn, job_ids, crud.fetch_locations_by_job)

    return [
        _serialize_job(
            j,
            all_skills.get(str(j["id"]), []),
            all_locations.get(str(j["id"]), []),
        )
        for j in jobs
    ]


def _fetch_children_bulk(conn, job_ids: list[str], fetch_fn) -> dict[str, list]:
    """
    Call fetch_fn once per job_id and group results by job_id.
    Returns a dict of {job_id: [rows]}.
    """
    result: dict[str, list] = {}
    for jid in job_ids:
        result[jid] = fetch_fn(conn, jid)
    return result
