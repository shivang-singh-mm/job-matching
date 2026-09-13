# Job Match API

A Flask + PostgreSQL REST API for matching job candidates to job postings.

## Tech Stack

- **Python / Flask** — web framework
- **PostgreSQL** — database
- **psycopg2** — raw SQL database access (no ORM)

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
│   │   └── schema.sql
│   │
│   └── database/
│       └── connection.py  # PostgreSQL connection management
│
├── tests/
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

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your database credentials

# 4. Create the database
createdb job_match

# 5. Apply schemas
psql -d job_match -f app/candidates/schema.sql
psql -d job_match -f app/jobs/schema.sql

# 6. Run the development server
flask run
```
