-- =============================================================================
-- candidates/schema.sql
-- Tables: candidates, candidate_experience, candidate_skills, candidate_locations
-- =============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- -----------------------------------------------------------------------------
-- candidates
-- Core candidate profile.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidates (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 VARCHAR     NOT NULL,
    summary              TEXT,
    expected_salary      DECIMAL,
    years_of_experience  DECIMAL,
    created_at           TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP   NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_years_of_experience CHECK (years_of_experience IS NULL OR years_of_experience >= 0)
);


-- -----------------------------------------------------------------------------
-- candidate_experience
-- Individual employment records for a candidate.
-- Experience duration is derived from start_date / end_date at query time —
-- do NOT store years_of_experience here.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidate_experience (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID        NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    company_name VARCHAR     NOT NULL,
    job_title    VARCHAR     NOT NULL,
    start_date   DATE        NOT NULL,
    end_date     DATE,                          -- NULL means currently employed
    description  TEXT,
    created_at   TIMESTAMP   NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_experience_dates CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_candidate_experience_candidate_id
    ON candidate_experience (candidate_id);


-- -----------------------------------------------------------------------------
-- candidate_skills
-- Skills held by a candidate.
-- Skills are stored directly here — no separate master skills table.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidate_skills (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id      UUID        NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    skill_name        VARCHAR     NOT NULL,
    proficiency_level VARCHAR,                  -- e.g. beginner / intermediate / expert
    created_at        TIMESTAMP   NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_candidate_skill UNIQUE (candidate_id, skill_name)
);

CREATE INDEX IF NOT EXISTS idx_candidate_skills_candidate_id
    ON candidate_skills (candidate_id);

CREATE INDEX IF NOT EXISTS idx_candidate_skills_skill_name
    ON candidate_skills (skill_name);


-- -----------------------------------------------------------------------------
-- candidate_locations
-- Current or preferred cities for a candidate.
-- Only the city is stored — no state or country.
-- location_type: 'current' | 'preferred'
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidate_locations (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id  UUID        NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    city          VARCHAR     NOT NULL,
    location_type VARCHAR     NOT NULL,
    created_at    TIMESTAMP   NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_location_type CHECK (location_type IN ('current', 'preferred')),
    CONSTRAINT uq_candidate_location UNIQUE (candidate_id, city, location_type)
);

CREATE INDEX IF NOT EXISTS idx_candidate_locations_candidate_id
    ON candidate_locations (candidate_id);

CREATE INDEX IF NOT EXISTS idx_candidate_locations_city
    ON candidate_locations (city);
