-- =============================================================================
-- jobs/schema.sql
-- Tables: jobs, job_skills, job_locations
-- =============================================================================

-- Enable UUID generation (safe to run multiple times)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- -----------------------------------------------------------------------------
-- jobs
-- Core job posting.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title                VARCHAR     NOT NULL,
    company_name         VARCHAR     NOT NULL,
    description          TEXT,
    min_years_experience DECIMAL,
    salary_min           DECIMAL,
    salary_max           DECIMAL,
    remote_allowed       BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP   NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_salary_range CHECK (
        salary_min IS NULL OR salary_max IS NULL OR salary_max >= salary_min
    ),
    CONSTRAINT chk_min_years_experience CHECK (
        min_years_experience IS NULL OR min_years_experience >= 0
    )
);


-- -----------------------------------------------------------------------------
-- job_skills
-- Skills required by a job.
-- Skills are stored directly here — no separate master skills table.
-- skill_type: 'must_have' | 'nice_to_have'
--   must_have    → hard filter in the recommendation algorithm
--   nice_to_have → contributes positively to match score
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_skills (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id     UUID        NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_name VARCHAR     NOT NULL,
    skill_type VARCHAR     NOT NULL,
    created_at TIMESTAMP   NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_skill_type CHECK (skill_type IN ('must_have', 'nice_to_have')),
    CONSTRAINT uq_job_skill UNIQUE (job_id, skill_name)
);

CREATE INDEX IF NOT EXISTS idx_job_skills_job_id
    ON job_skills (job_id);

CREATE INDEX IF NOT EXISTS idx_job_skills_skill_name
    ON job_skills (skill_name);


-- -----------------------------------------------------------------------------
-- job_locations
-- Cities where the job is available.
-- Only the city is stored — no state or country.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_locations (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id     UUID        NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    city       VARCHAR     NOT NULL,
    created_at TIMESTAMP   NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_job_location UNIQUE (job_id, city)
);

CREATE INDEX IF NOT EXISTS idx_job_locations_job_id
    ON job_locations (job_id);

CREATE INDEX IF NOT EXISTS idx_job_locations_city
    ON job_locations (city);
