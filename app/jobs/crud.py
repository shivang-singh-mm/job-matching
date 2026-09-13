"""
jobs/crud.py

Raw SQL queries for the jobs module.
All functions accept an open psycopg2 connection (with RealDictCursor) and
return plain Python dicts / lists of dicts.

No business logic lives here — only database I/O.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# jobs
# ---------------------------------------------------------------------------

def insert_job(
    conn,
    title: str,
    company_name: str,
    description: str | None,
    min_years_experience: float,
    salary_min: float,
    salary_max: float,
    remote_allowed: bool,
) -> dict:
    """Insert a row into jobs and return the new record."""
    sql = """
        INSERT INTO jobs
            (title, company_name, description, min_years_experience, salary_min, salary_max, remote_allowed)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, title, company_name, description,
                  min_years_experience, salary_min, salary_max,
                  remote_allowed, created_at, updated_at
    """
    with conn.cursor() as cur:
        cur.execute(sql, (title, company_name, description, min_years_experience, salary_min, salary_max, remote_allowed))
        return dict(cur.fetchone())


def fetch_job_by_id(conn, job_id: str) -> dict | None:
    """Return a job row by primary key, or None if not found."""
    sql = """
        SELECT id, title, company_name, description,
               min_years_experience, salary_min, salary_max,
               remote_allowed, created_at, updated_at
        FROM jobs
        WHERE id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (job_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def fetch_all_jobs(conn) -> list[dict]:
    """Return every job row ordered by creation date (newest first)."""
    sql = """
        SELECT id, title, company_name, description,
               min_years_experience, salary_min, salary_max,
               remote_allowed, created_at, updated_at
        FROM jobs
        ORDER BY created_at DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# job_skills
# ---------------------------------------------------------------------------

def insert_job_skill(conn, job_id: str, skill_name: str, skill_type: str) -> dict:
    sql = """
        INSERT INTO job_skills (job_id, skill_name, skill_type)
        VALUES (%s, %s, %s)
        RETURNING id, job_id, skill_name, skill_type, created_at
    """
    with conn.cursor() as cur:
        cur.execute(sql, (job_id, skill_name, skill_type))
        return dict(cur.fetchone())


def fetch_skills_by_job(conn, job_id: str) -> list[dict]:
    sql = """
        SELECT id, skill_name, skill_type, created_at
        FROM job_skills
        WHERE job_id = %s
        ORDER BY skill_type, skill_name ASC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (job_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# job_locations
# ---------------------------------------------------------------------------

def insert_job_location(conn, job_id: str, city: str) -> dict:
    sql = """
        INSERT INTO job_locations (job_id, city)
        VALUES (%s, %s)
        RETURNING id, job_id, city, created_at
    """
    with conn.cursor() as cur:
        cur.execute(sql, (job_id, city))
        return dict(cur.fetchone())


def fetch_locations_by_job(conn, job_id: str) -> list[dict]:
    sql = """
        SELECT id, city, created_at
        FROM job_locations
        WHERE job_id = %s
        ORDER BY city ASC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (job_id,))
        return [dict(r) for r in cur.fetchall()]
