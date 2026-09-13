import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base application configuration loaded from environment variables."""

    DATABASE_URL: str = os.environ["DATABASE_URL"]
    DEBUG: bool = os.getenv("FLASK_DEBUG", "0") == "1"
