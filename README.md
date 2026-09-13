# Job Match API

A Flask + PostgreSQL REST API for matching candidates with jobs using a transparent, rule-based recommendation system.

## Tech Stack

* Python / Flask
* PostgreSQL
* psycopg2 (raw SQL — no ORM)
* Docker / Docker Compose

## Project Structure

```
job-match-api/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   │
│   ├── candidates/        # Candidate profiles, experience, skills, locations
│   │   ├── routes.py
│   │   ├── services.py
│   │   ├── crud.py
│   │   └── schema.sql
│   │
│   ├── jobs/              # Job postings, required skills, locations
│   │   ├── routes.py
│   │   ├── services.py
│   │   ├── crud.py
│   │   └── schema.sql
│   │
│   ├── recommendations/   # Matching and scoring logic
│   │   ├── routes.py
│   │   ├── services.py
│   │   ├── crud.py
│   │   ├── scorer.py
│   │   └── schema.sql
│   │
│   └── database/
│       └── connection.py
│
├── tests/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt
├── .env.example
└── run.py
```

## Database Schema

Seven core tables across two schema files:

| File | Tables |
|---|---|
| `app/candidates/schema.sql` | `candidates`, `candidate_experience`, `candidate_skills`, `candidate_locations` |
| `app/jobs/schema.sql` | `jobs`, `job_skills`, `job_locations` |

Recommendations are computed dynamically — no persistence table needed.

---

## Running with Docker (recommended)

Docker Compose starts both the Flask API and a PostgreSQL database.
The schemas are applied automatically on first start.

### 1. Start all services

```bash
docker compose up --build
```

The API will be available at `http://localhost:5000`.
PostgreSQL will be available at `localhost:5432`.

### 2. Start in detached mode (background)

```bash
docker compose up --build -d
```

### 3. Stop all services

```bash
docker compose down
```

### 4. Stop and delete all data (reset the database)

```bash
docker compose down -v
```

### 5. View logs

```bash
# All services
docker compose logs -f

# API only
docker compose logs -f api

# Database only
docker compose logs -f db
```

### 6. Rebuild after code changes

```bash
docker compose up --build
```

### Docker environment

The `docker-compose.yml` pre-configures:

| Variable | Value |
|---|---|
| `POSTGRES_DB` | `job_match` |
| `POSTGRES_USER` | `job_match_user` |
| `POSTGRES_PASSWORD` | `job_match_password` |
| `DATABASE_URL` | `postgresql://job_match_user:job_match_password@db:5432/job_match` |

> The database credentials in `docker-compose.yml` are for local development only.
> Use environment variables or secrets management for any deployed environment.

---

## Running locally (without Docker)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL to your local PostgreSQL connection string

# 4. Create the database
createdb job_match

# 5. Apply schemas
psql -d job_match -f app/candidates/schema.sql
psql -d job_match -f app/jobs/schema.sql

# 6. Run the development server
flask run
```

---

## Core Features

* Create and manage candidates with skills, experience, salary expectations, and locations.
* Create and manage jobs with required skills, experience, salary range, locations, and remote availability.
* Recommend candidates for a job using a configurable scoring system.
* Return a transparent score breakdown for every recommendation.

---

## Recommendation Logic

1. **Must-have skills** are a hard filter. Candidates missing any must-have skill are excluded.
2. Eligible candidates are scored on:

   * Nice-to-have skills
   * Location
   * Salary compatibility
   * Experience

3. Each factor produces a score from `0–100`.
4. The API accepts custom weights for each factor. The four weights must total `100`.

Example:

```text
nice_to_have = 30
location     = 40
salary       = 20
experience   = 10
```

Final score:

```text
(nice_to_have_score × weight)
+ (location_score × weight)
+ (salary_score × weight)
+ (experience_score × weight)
```

The results are ranked by final score and returned with a breakdown showing how each factor contributed.

## Recommendation API

```http
GET /recommendations/candidates/{job_id}
```

Example:

```http
GET /recommendations/candidates/{job_id}?nice_to_have_weight=30&location_weight=40&salary_weight=20&experience_weight=10&limit=10
```

The API returns the ranked candidates, their final score, and individual scoring breakdown.

---

## AI Tools & Human Decisions

AI tools were used as a development aid for architecture and implementation suggestions.

One suggestion was to use a fixed mathematical weighting approach, such as predefined weights like `40/20/20/...`. I overrode this approach because it would make the recommendation system less flexible. Instead, I implemented **user-configurable weights**, allowing the API consumer to decide how much importance to give nice-to-have skills, location, salary, and experience for each request.

The final recommendation logic therefore remains deterministic, explainable, and configurable.
