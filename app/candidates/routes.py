"""
candidates/routes.py

HTTP endpoints for the candidates module.

Responsibilities:
  - Parse request JSON
  - Delegate to services
  - Format and return JSON responses with appropriate HTTP status codes

No SQL and no business logic live here.
"""

from flask import Blueprint, jsonify, request
import psycopg2

from app.candidates import services

candidates_bp = Blueprint("candidates", __name__)


@candidates_bp.route("", methods=["POST"])
def create_candidate():
    """POST /candidates — create a new candidate profile."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    try:
        candidate = services.create_candidate(data)
    except ValueError as exc:
        return jsonify({"error": "Validation failed.", "details": exc.args[0]}), 400
    except psycopg2.Error as exc:
        return jsonify({"error": "Database error.", "details": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": "An unexpected error occurred.", "details": str(exc)}), 500

    return jsonify(candidate), 201


@candidates_bp.route("", methods=["GET"])
def list_candidates():
    """GET /candidates — return all candidates."""
    try:
        candidates = services.get_all_candidates()
    except psycopg2.Error as exc:
        return jsonify({"error": "Database error.", "details": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": "An unexpected error occurred.", "details": str(exc)}), 500

    return jsonify(candidates), 200


@candidates_bp.route("/<string:candidate_id>", methods=["GET"])
def get_candidate(candidate_id: str):
    """GET /candidates/:id — return a single candidate."""
    try:
        candidate = services.get_candidate_by_id(candidate_id)
    except psycopg2.Error as exc:
        return jsonify({"error": "Database error.", "details": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": "An unexpected error occurred.", "details": str(exc)}), 500

    if candidate is None:
        return jsonify({"error": f"Candidate '{candidate_id}' not found."}), 404

    return jsonify(candidate), 200
