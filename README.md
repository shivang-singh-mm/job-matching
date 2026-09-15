# Job Match API

A Flask + PostgreSQL REST API for matching candidates with jobs using a transparent, rule-based recommendation system.

## Tech Stack

* Python / Flask
* PostgreSQL
* REST API
* Docker

## Core Features

* Create candidates with skills, years of experience, salary expectations, and locations.
* Create jobs with required skills, experience, salary range, locations, and remote availability.
* Recommend jobs for a candidate.
* Recommend candidates for a job.
* Use configurable scoring weights.
* Return a transparent score breakdown for every recommendation.

## API Endpoints

### Create Candidate

```http
POST /candidates
```

Creates a candidate with their profile, skills, years of experience, salary expectation, and location.

### Create Job

```http
POST /jobs
```

Creates a job with required skills, experience, salary range, location, and remote availability.

### Candidate → Jobs

```http
GET /recommendations/jobs/{candidate_id}
```

Returns the best-matching jobs for a candidate.

Example:

```http
GET /recommendations/jobs/{candidate_id}?nice_to_have_weight=30&location_weight=40&salary_weight=20&experience_weight=10&limit=10
```

### Job → Candidates

```http
GET /recommendations/candidates/{job_id}
```

Returns the best-matching candidates for a job.

Example:

```http
GET /recommendations/candidates/{job_id}?nice_to_have_weight=30&location_weight=40&salary_weight=20&experience_weight=10&limit=10
```

## Recommendation Logic

1. **Must-have skills** are a hard filter. Candidates missing any must-have skill are excluded.
2. Eligible matches are scored on four dimensions. Each produces a score from `0–100`.
3. The API accepts custom weights for each dimension. The four weights must total `100`.

### Nice-to-have score

```text
matched_nice_to_have_skills / total_nice_to_have_skills × 100
```

* If the job has no nice-to-have skills → score = `100`
* Skill comparison is case-insensitive and whitespace-trimmed.

### Location score

```text
Exact city match      → 100
No match, remote OK   → 70
No match, no remote   → 0
```

City comparison is case-insensitive and whitespace-trimmed.

### Experience score

```text
candidate_years >= required_years  → 100
candidate_years < required_years   → (candidate_years / required_years) × 100
No minimum requirement             → 100
No candidate experience on record  → 0
```

Experience is never a hard filter — it only affects the score.

### Salary score

```text
candidate_salary <= salary_max            → 100
candidate_salary == 2 × salary_max        → 0
salary_max < candidate_salary < 2× max   → 100 × (1 − overshoot_ratio)
  where overshoot_ratio = (candidate_salary − salary_max) / salary_max
Missing salary data (either side)        → 50  (neutral)
```

Salary is never a hard filter — it only affects the score.

### Final weighted score

Example weights:

```text
nice_to_have = 30
location     = 40
salary       = 20
experience   = 10
```

Formula:

```text
(nice_to_have_score × nice_to_have_weight / 100)
+ (location_score × location_weight / 100)
+ (salary_score × salary_weight / 100)
+ (experience_score × experience_weight / 100)
```

Results are ranked by final score and returned with a breakdown showing how each factor contributed.


## Running the Project

### Using Docker

```bash
docker compose up --build
```

### Running Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the PostgreSQL connection in `.env`, then run:

```bash
python run.py
```

## Testing

Run the test suite with:

```bash
pytest
```

Tests cover the core recommendation logic, including:

* Must-have skill filtering
* Nice-to-have scoring
* Location scoring
* Experience scoring
* Salary scoring
* Weight calculation

## Assumptions and Future Improvements

* Skill and city matching is case-insensitive and whitespace-trimmed.
* Must-have skills are used only as an eligibility filter.
* Experience is not a hard filter and affects the recommendation score.
* Matching currently uses deterministic rule-based scoring.
* Future improvements could include fuzzy/semantic skill matching, pagination, authentication, and more advanced salary scoring.

## AI Tools & Human Decisions

AI tools were used as a development aid for architecture and implementation suggestions.

One suggestion was to use fixed mathematical weights, such as predefined values like `40/20/20/...`. I overrode this approach because fixed weights would make the system less flexible.

Instead, the API supports **user-configurable weights**, allowing the API consumer to decide the importance of nice-to-have skills, location, salary, and experience for each request.

The final recommendation logic remains deterministic, explainable, and configurable.
