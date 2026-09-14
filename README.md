# Job Match API

A Flask + PostgreSQL REST API for matching candidates with jobs using a transparent, rule-based recommendation system.

## Tech Stack

* Python / Flask
* PostgreSQL
* REST API
* Docker

## Core Features

* Create and manage candidates with skills, experience, salary expectations, and locations.
* Create and manage jobs with required skills, experience, salary range, locations, and remote availability.
* Recommend jobs for a candidate.
* Recommend candidates for a job.
* Use configurable scoring weights.
* Return a transparent score breakdown for every recommendation.

## Recommendation Logic

1. **Must-have skills** are a hard filter. Candidates or jobs that do not satisfy all must-have skills are excluded.
2. Eligible matches are scored on:

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
(nice_to_have_score × nice_to_have_weight / 100)
+ (location_score × location_weight / 100)
+ (salary_score × salary_weight / 100)
+ (experience_score × experience_weight / 100)
```

Results are ranked by final score and returned with a breakdown showing the contribution of each factor.

## Recommendation APIs

### Candidate → Jobs

```http
GET /recommendations/jobs/{candidate_id}
```

Example:

```http
GET /recommendations/jobs/{candidate_id}?nice_to_have_weight=30&location_weight=40&salary_weight=20&experience_weight=10&limit=10
```

Returns the best-matching jobs for the selected candidate.

### Job → Candidates

```http
GET /recommendations/candidates/{job_id}
```

Example:

```http
GET /recommendations/candidates/{job_id}?nice_to_have_weight=30&location_weight=40&salary_weight=20&experience_weight=10&limit=10
```

Returns the best-matching candidates for the selected job.

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

Configure the PostgreSQL connection using the `.env` file, then run:

```bash
python run.py
```

## Assumptions and Future Improvements

* Skill and city matching is case-insensitive and whitespace-trimmed.
* Matching currently uses deterministic rule-based scoring.
* Future improvements could include fuzzy skill matching, semantic skill matching, pagination, authentication, and more advanced salary scoring.

## AI Tools & Human Decisions

AI tools were used as a development aid for architecture and implementation suggestions.

One suggestion was to use fixed mathematical weights, such as predefined values like `40/20/20/...`. I overrode this approach because fixed weights would make the system less flexible.

Instead, the API supports **user-configurable weights**, allowing the API consumer to decide the importance of nice-to-have skills, location, salary, and experience for each request.

The final recommendation logic remains deterministic, explainable, and configurable.
