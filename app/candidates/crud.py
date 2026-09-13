"""
candidates/crud.py

Raw SQL queries for the candidates module.
All functions accept an open psycopg2 connection (with RealDictCursor) and
return plain Python dicts / lists of dicts.

No business logic lives here — only database I/O.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# candidates
# ---------------------------------------------------------------------------

def insert_candidate(conn, name: str, summary: str | None, expected_salary: float, years_of_experience: float | None) -> dict:
    """Insert a row into candidates and return the new record."""
    sql = """
        INSERT INTO candidates (name, summary, expected_salary, years_of_experience)
        VALUES (%s, %s, %s, %s)
        RETURNING id, name, summary, expected_salary, years_of_experience, created_at, updated_at
    """
    with conn.cursor() as cur:
        cur.execute(sql, (name, summary, expected_salary, years_of_experience))
        return dict(cur.fetchone())


def fetch_candidate_by_id(conn, candidate_id: str) -> dict | None:
    """Return a candidate row by primary key, or None if not found."""
    sql = "SELECT id, name, summary, expected_salary, years_of_experience, created_at, updated_at FROM candidates WHERE id = %s"
    with conn.cursor() as cur:
        cur.execute(sql, (candidate_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def fetch_all_candidates(conn) -> list[dict]:
    """Return every candidate row ordered by creation date (newest first)."""
    sql = "SELECT id, name, summary, expected_salary, years_of_experience, created_at, updated_at FROM candidates ORDER BY created_at DESC"
    with conn.cursor() as cur:
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# candidate_skills
# ---------------------------------------------------------------------------

def insert_candidate_skill(conn, candidate_id: str, skill_name: str, proficiency_level: str | None) -> dict:
    sql = """
        INSERT INTO candidate_skills (candidate_id, skill_name, proficiency_level)
        VALUES (%s, %s, %s)
        RETURNING id, candidate_id, skill_name, proficiency_level, created_at
    """
    with conn.cursor() as cur:
        cur.execute(sql, (candidate_id, skill_name, proficiency_level))
        return dict(cur.fetchone())


def fetch_skills_by_candidate(conn, candidate_id: str) -> list[dict]:
    sql = """
        SELECT id, skill_name, proficiency_level, created_at
        FROM candidate_skills
        WHERE candidate_id = %s
        ORDER BY created_at ASC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (candidate_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# candidate_experience
# ---------------------------------------------------------------------------

def insert_candidate_experience(
    conn,
    candidate_id: str,
    company_name: str,
    job_title: str,
    start_date: str,
    end_date: str | None,
    description: str | None,
) -> dict:
    sql = """
        INSERT INTO candidate_experience
            (candidate_id, company_name, job_title, start_date, end_date, description)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, candidate_id, company_name, job_title, start_date, end_date, description, created_at
    """
    with conn.cursor() as cur:
        cur.execute(sql, (candidate_id, company_name, job_title, start_date, end_date, description))
        return dict(cur.fetchone())


def fetch_experience_by_candidate(conn, candidate_id: str) -> list[dict]:
    sql = """
        SELECT id, company_name, job_title, start_date, end_date, description, created_at
        FROM candidate_experience
        WHERE candidate_id = %s
        ORDER BY start_date DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (candidate_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# candidate_locations
# ---------------------------------------------------------------------------

def insert_candidate_location(conn, candidate_id: str, city: str, location_type: str) -> dict:
    sql = """
        INSERT INTO candidate_locations (candidate_id, city, location_type)
        VALUES (%s, %s, %s)
        RETURNING id, candidate_id, city, location_type, created_at
    """
    with conn.cursor() as cur:
        cur.execute(sql, (candidate_id, city, location_type))
        return dict(cur.fetchone())


def fetch_locations_by_candidate(conn, candidate_id: str) -> list[dict]:
    sql = """
        SELECT id, city, location_type, created_at
        FROM candidate_locations
        WHERE candidate_id = %s
        ORDER BY created_at ASC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (candidate_id,))
        return [dict(r) for r in cur.fetchall()]
