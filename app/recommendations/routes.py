"""
recommendations/routes.py

HTTP endpoint for the recommendation engine.

Responsibilities:
  - Read job_id from the URL.
  - Read and validate query parameters (weights, limit).
  - Delegate to services.
  - Return JSON responses with appropriate HTTP status codes.

No SQL and no scoring logic live here.
Follows the same conventions as candidates/routes.py and jobs/routes.py.
"""

from flask import Blueprint, jsonify, request
import psycopg2

from app.recommendations import services

recommendations_bp = Blueprint("recommendations", __name__)

_DEFAULT_LIMIT = 10
_WEIGHT_PARAMS = ("nice_to_have_weight", "location_weight", "salary_weight", "experience_weight")


# ---------------------------------------------------------------------------
# Parameter parsing & validation
# ---------------------------------------------------------------------------

def _parse_weights(args) -> tuple[dict | None, str | None]:
    """
    Parse the four weight query parameters.

    Returns (weights_dict, None) on success, or (None, error_message) on failure.
    """
    weights = {}
    for param in _WEIGHT_PARAMS:
        raw = args.get(param)
        if raw is None:
            return None, f"Query parameter '{param}' is required."
        try:
            value = float(raw)
        except ValueError:
            return None, f"'{param}' must be a numeric value."
        if value < 0 or value > 100:
            return None, f"'{param}' must be between 0 and 100."
        # Map e.g. "nice_to_have_weight" → "nice_to_have"
        key = param.replace("_weight", "")
        weights[key] = value

    total = sum(weights.values())
    if abs(total - 100) > 1e-6:
        return None, f"The four weights must sum to exactly 100 (got {total})."

    return weights, None


def _parse_limit(args) -> tuple[int | None, str | None]:
    """
    Parse the optional 'limit' query parameter.

    Returns (limit_int, None) on success, or (None, error_message) on failure.
    """
    raw = args.get("limit", str(_DEFAULT_LIMIT))
    try:
        value = int(raw)
    except ValueError:
        return None, "'limit' must be a positive integer."
    if value <= 0:
        return None, "'limit' must be a positive integer."
    return value, None


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@recommendations_bp.route("/candidates/<string:job_id>", methods=["GET"])
def recommend_candidates(job_id: str):
    """
    GET /recommendations/candidates/<job_id>

    Query parameters:
      nice_to_have_weight  (required, 0–100)
      location_weight      (required, 0–100)
      salary_weight        (required, 0–100)
      experience_weight    (required, 0–100)
      limit                (optional, positive int, default 10)

    All four weights must sum to exactly 100.
    """
    # -- Validate weights --------------------------------------------------
    weights, weight_error = _parse_weights(request.args)
    if weight_error:
        return jsonify({"error": "Validation failed.", "details": weight_error}), 400

    # -- Validate limit ----------------------------------------------------
    limit, limit_error = _parse_limit(request.args)
    if limit_error:
        return jsonify({"error": "Validation failed.", "details": limit_error}), 400

    # -- Run recommendation engine ----------------------------------------
    try:
        result = services.get_recommendations(job_id, weights, limit)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except psycopg2.Error as exc:
        return jsonify({"error": "Database error.", "details": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": "An unexpected error occurred.", "details": str(exc)}), 500

    return jsonify(result), 200
