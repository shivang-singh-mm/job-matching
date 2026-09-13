"""
jobs/routes.py

HTTP endpoints for the jobs module.

Responsibilities:
  - Parse request JSON
  - Delegate to services
  - Format and return JSON responses with appropriate HTTP status codes

No SQL and no business logic live here.
"""

from flask import Blueprint, jsonify, request
import psycopg2

from app.jobs import services

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("", methods=["POST"])
def create_job():
    """POST /jobs — create a new job posting."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    try:
        job = services.create_job(data)
    except ValueError as exc:
        return jsonify({"error": "Validation failed.", "details": exc.args[0]}), 400
    except psycopg2.Error as exc:
        return jsonify({"error": "Database error.", "details": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": "An unexpected error occurred.", "details": str(exc)}), 500

    return jsonify(job), 201


@jobs_bp.route("", methods=["GET"])
def list_jobs():
    """GET /jobs — return all job postings."""
    try:
        jobs = services.get_all_jobs()
    except psycopg2.Error as exc:
        return jsonify({"error": "Database error.", "details": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": "An unexpected error occurred.", "details": str(exc)}), 500

    return jsonify(jobs), 200


@jobs_bp.route("/<string:job_id>", methods=["GET"])
def get_job(job_id: str):
    """GET /jobs/:id — return a single job posting."""
    try:
        job = services.get_job_by_id(job_id)
    except psycopg2.Error as exc:
        return jsonify({"error": "Database error.", "details": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": "An unexpected error occurred.", "details": str(exc)}), 500

    if job is None:
        return jsonify({"error": f"Job '{job_id}' not found."}), 404

    return jsonify(job), 200
