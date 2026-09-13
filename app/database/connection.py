import psycopg2
import psycopg2.extras
from flask import current_app


def get_connection():
    """
    Open and return a new psycopg2 connection using the DATABASE_URL from the
    Flask application config.

    The caller is responsible for closing the connection (or use it as a
    context manager — psycopg2 connections support `with` for transaction
    management).

    Returns a connection with RealDictCursor as the default cursor factory so
    that all rows come back as dicts instead of plain tuples.
    """
    return psycopg2.connect(
        current_app.config["DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
