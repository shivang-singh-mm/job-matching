"""
recommendations/crud.py

Raw SQL queries for the recommendations module.

All functions accept an open psycopg2 connection (with RealDictCursor) and
return plain Python dicts / lists of dicts.

No business logic lives here — only database I/O.
Follows the same conventions as candidates/crud.py and jobs/crud.py.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Job data (reuse job tables — no new tables created)
# ---------------------------------------------------------------------------

def fetch_job_for_recommendation(conn, job_id: str) -> dict | None:
    """
    Return the core job row needed for recommendation scoring.
    Returns None if not found.
    """
    sql = """
        SELECT id, title, company_name, description,
               min_years_experience, salary_min, salary_max,
               remote_allowed
        FROM jobs
        WHERE id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (job_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def fetch_job_skills_for_recommendation(conn, job_id: str) -> list[dict]:
    """
    Return all skill rows for a job.
    Each row: {skill_name, skill_type}
    """
    sql = """
        SELECT skill_name, skill_type
        FROM job_skills
        WHERE job_id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (job_id,))
        return [dict(r) for r in cur.fetchall()]


def fetch_job_locations_for_recommendation(conn, job_id: str) -> list[dict]:
    """
    Return all location rows for a job.
    Each row: {city}
    """
    sql = """
        SELECT city
        FROM job_locations
        WHERE job_id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (job_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Candidate data — bulk fetches to avoid N+1 queries
# ---------------------------------------------------------------------------

def fetch_all_candidates_for_recommendation(conn) -> list[dict]:
    """
    Return every candidate with the fields needed for scoring.
    """
    sql = """
        SELECT id, name, summary, expected_salary, years_of_experience
        FROM candidates
        ORDER BY id ASC
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


def fetch_all_candidate_skills_bulk(conn, candidate_ids: list[str]) -> list[dict]:
    """
    Return skill rows for all given candidate IDs in one query.
    Each row: {candidate_id, skill_name, proficiency_level}

    Used to populate a {candidate_id -> [skills]} map without N+1 queries.
    """
    if not candidate_ids:
        return []
    sql = """
        SELECT candidate_id, skill_name, proficiency_level
        FROM candidate_skills
        WHERE candidate_id = ANY(%s)
    """
    with conn.cursor() as cur:
        cur.execute(sql, (candidate_ids,))
        return [dict(r) for r in cur.fetchall()]


def fetch_all_candidate_locations_bulk(conn, candidate_ids: list[str]) -> list[dict]:
    """
    Return location rows for all given candidate IDs in one query.
    Each row: {candidate_id, city, location_type}

    Used to populate a {candidate_id -> [locations]} map without N+1 queries.
    """
    if not candidate_ids:
        return []
    sql = """
        SELECT candidate_id, city, location_type
        FROM candidate_locations
        WHERE candidate_id = ANY(%s)
    """
    with conn.cursor() as cur:
        cur.execute(sql, (candidate_ids,))
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Job data — bulk fetches for candidate → job recommendation direction
# ---------------------------------------------------------------------------

def fetch_candidate_for_recommendation(conn, candidate_id: str) -> dict | None:
    """
    Return the candidate row needed for recommendation scoring.
    Returns None if not found.
    """
    sql = """
        SELECT id, name, summary, expected_salary, years_of_experience
        FROM candidates
        WHERE id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (candidate_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def fetch_all_jobs_for_recommendation(conn) -> list[dict]:
    """
    Return every job with the fields needed for scoring.
    """
    sql = """
        SELECT id, title, company_name, description,
               min_years_experience, salary_min, salary_max,
               remote_allowed
        FROM jobs
        ORDER BY id ASC
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


def fetch_all_job_skills_bulk(conn, job_ids: list[str]) -> list[dict]:
    """
    Return skill rows for all given job IDs in one query.
    Each row: {job_id, skill_name, skill_type}

    Used to populate a {job_id -> [skills]} map without N+1 queries.
    """
    if not job_ids:
        return []
    sql = """
        SELECT job_id, skill_name, skill_type
        FROM job_skills
        WHERE job_id = ANY(%s)
    """
    with conn.cursor() as cur:
        cur.execute(sql, (job_ids,))
        return [dict(r) for r in cur.fetchall()]


def fetch_all_job_locations_bulk(conn, job_ids: list[str]) -> list[dict]:
    """
    Return location rows for all given job IDs in one query.
    Each row: {job_id, city}

    Used to populate a {job_id -> [locations]} map without N+1 queries.
    """
    if not job_ids:
        return []
    sql = """
        SELECT job_id, city
        FROM job_locations
        WHERE job_id = ANY(%s)
    """
    with conn.cursor() as cur:
        cur.execute(sql, (job_ids,))
        return [dict(r) for r in cur.fetchall()]
