from flask import Flask

from app.config import Config
from app.candidates.routes import candidates_bp
from app.jobs.routes import jobs_bp


def create_app() -> Flask:
    """Application factory — create and configure the Flask app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(candidates_bp, url_prefix="/candidates")
    app.register_blueprint(jobs_bp, url_prefix="/jobs")

    return app
