"""
conftest.py

Adds the project root to sys.path so pytest can import the `app` package
without requiring a pip install or a pyproject.toml.
"""
import sys
import os

# Insert the project root (the directory containing this file) at the front
# of sys.path.  This allows `from app.recommendations.scorer import ...` to
# work from any working directory when running pytest.
sys.path.insert(0, os.path.dirname(__file__))
