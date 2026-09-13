"""
candidates/services.py

Business-level orchestration for the candidates module.

Responsibilities:
  - Input validation
  - Coordinating multi-table inserts inside a single transaction
  - Assembling the response shape from crud results

No SQL lives here — all database access goes through crud.py.
"""

from __future__ import annotations

from app.database.connection import get_connection
from app.candidates import crud


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_candidate(candidate: dict, skills: list, experience: list, locations: list) -> dict:
    """Merge a candidate row with its child collections into one response dict."""
    return {
        "id": str(candidate["id"]),
        "name": candidate["name"],
        "summary": candidate["summary"],
        "expected_salary": float(candidate["expected_salary"]) if candidate["expected_salary"] is not None else None,
        "years_of_experience": float(candidate["years_of_experience"]) if candidate["years_of_experience"] is not None else None,
        "skills": [
            {
                "id": str(s["id"]),
                "skill_name": s["skill_name"],
                "proficiency_level": s["proficiency_level"],
                "created_at": s["created_at"].isoformat(),
            }
            for s in skills
        ],
        "experience": [
            {
                "id": str(e["id"]),
                "company_name": e["company_name"],
                "job_title": e["job_title"],
                "start_date": e["start_date"].isoformat() if e["start_date"] else None,
                "end_date": e["end_date"].isoformat() if e["end_date"] else None,
                "description": e["description"],
                "created_at": e["created_at"].isoformat(),
            }
            for e in experience
        ],
        "locations": [
            {
                "id": str(l["id"]),
                "city": l["city"],
                "location_type": l["location_type"],
                "created_at": l["created_at"].isoformat(),
            }
            for l in locations
        ],
        "created_at": candidate["created_at"].isoformat(),
        "updated_at": candidate["updated_at"].isoformat(),
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_create_payload(data: dict) -> list[str]:
    """Return a list of validation error messages, or an empty list if valid."""
    errors = []

    name = data.get("name", "")
    if not isinstance(name, str) or not name.strip():
        errors.append("'name' is required and must be a non-empty string.")

    expected_salary = data.get("expected_salary")
    if expected_salary is None:
        errors.append("'expected_salary' is required.")
    elif not isinstance(expected_salary, (int, float)) or expected_salary < 0:
        errors.append("'expected_salary' must be a non-negative number.")

    years_of_experience = data.get("years_of_experience")
    if years_of_experience is not None:
        if not isinstance(years_of_experience, (int, float)) or years_of_experience < 0:
            errors.append("'years_of_experience' must be a non-negative number.")

    # Optional arrays — validate shape if provided
    for skill in data.get("skills", []):
        if not isinstance(skill.get("skill_name", ""), str) or not skill["skill_name"].strip():
            errors.append("Each skill must have a non-empty 'skill_name'.")
            break

    for exp in data.get("experience", []):
        for required_field in ("company_name", "job_title", "start_date"):
            if not isinstance(exp.get(required_field, ""), str) or not exp[required_field].strip():
                errors.append(f"Each experience entry must have a non-empty '{required_field}'.")
                break

    for loc in data.get("locations", []):
        if not isinstance(loc.get("city", ""), str) or not loc["city"].strip():
            errors.append("Each location must have a non-empty 'city'.")
            break
        if loc.get("location_type") not in ("current", "preferred"):
            errors.append("Each location's 'location_type' must be 'current' or 'preferred'.")
            break

    return errors


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

def create_candidate(data: dict) -> dict:
    """
    Validate input, then insert the candidate and all optional child records
    inside a single database transaction.

    Raises ValueError if validation fails.
    """
    errors = _validate_create_payload(data)
    if errors:
        raise ValueError(errors)

    name = data["name"].strip()
    summary = data.get("summary") or None
    expected_salary = data["expected_salary"]
    years_of_experience = data.get("years_of_experience")  # optional
    skills = data.get("skills") or []
    experience = data.get("experience") or []
    locations = data.get("locations") or []

    with get_connection() as conn:
        try:
            candidate = crud.insert_candidate(conn, name, summary, expected_salary, years_of_experience)
            candidate_id = str(candidate["id"])

            inserted_skills = []
            for s in skills:
                row = crud.insert_candidate_skill(
                    conn,
                    candidate_id,
                    s["skill_name"].strip(),
                    s.get("proficiency_level"),
                )
                inserted_skills.append(row)

            inserted_experience = []
            for e in experience:
                row = crud.insert_candidate_experience(
                    conn,
                    candidate_id,
                    e["company_name"].strip(),
                    e["job_title"].strip(),
                    e["start_date"],
                    e.get("end_date"),
                    e.get("description"),
                )
                inserted_experience.append(row)

            inserted_locations = []
            for loc in locations:
                row = crud.insert_candidate_location(
                    conn,
                    candidate_id,
                    loc["city"].strip(),
                    loc["location_type"],
                )
                inserted_locations.append(row)

            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return _serialize_candidate(candidate, inserted_skills, inserted_experience, inserted_locations)


def get_candidate_by_id(candidate_id: str) -> dict | None:
    """
    Fetch a single candidate with all child records.
    Returns None if the candidate does not exist.
    """
    with get_connection() as conn:
        candidate = crud.fetch_candidate_by_id(conn, candidate_id)
        if candidate is None:
            return None

        skills = crud.fetch_skills_by_candidate(conn, candidate_id)
        experience = crud.fetch_experience_by_candidate(conn, candidate_id)
        locations = crud.fetch_locations_by_candidate(conn, candidate_id)

    return _serialize_candidate(candidate, skills, experience, locations)


def get_all_candidates() -> list[dict]:
    """
    Fetch all candidates with their child records.
    Performs one query per child type (3 extra queries total) to avoid
    row-explosion from JOINs with multiple 1:N relations.
    """
    with get_connection() as conn:
        candidates = crud.fetch_all_candidates(conn)
        if not candidates:
            return []

        candidate_ids = [str(c["id"]) for c in candidates]

        # Fetch all children in bulk — one query per child table
        all_skills = _fetch_children_bulk(conn, candidate_ids, crud.fetch_skills_by_candidate)
        all_experience = _fetch_children_bulk(conn, candidate_ids, crud.fetch_experience_by_candidate)
        all_locations = _fetch_children_bulk(conn, candidate_ids, crud.fetch_locations_by_candidate)

    return [
        _serialize_candidate(
            c,
            all_skills.get(str(c["id"]), []),
            all_experience.get(str(c["id"]), []),
            all_locations.get(str(c["id"]), []),
        )
        for c in candidates
    ]


def _fetch_children_bulk(conn, candidate_ids: list[str], fetch_fn) -> dict[str, list]:
    """
    Call fetch_fn once per candidate_id and group results by candidate_id.
    Returns a dict of {candidate_id: [rows]}.
    """
    result: dict[str, list] = {}
    for cid in candidate_ids:
        result[cid] = fetch_fn(conn, cid)
    return result
