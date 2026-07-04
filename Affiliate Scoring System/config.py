"""
Central place for configurations.

Copy `.env.example` to `.env` and fill in your own values before running
any script that talks to the database.
"""

import os

from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME", "scoring"),
}


def get_connection():
    """Create a MySQL connection using credentials from the environment.

    Raises a clear error instead of connecting with empty/blank credentials,
    so a missing .env file fails loudly rather than silently.
    """
    import mysql.connector as mysql

    if not DB_CONFIG["user"] or not DB_CONFIG["password"]:
        raise RuntimeError(
            "DB_USER / DB_PASSWORD are not set. Copy .env.example to .env "
            "and fill in your local database credentials."
        )
    return mysql.connect(**DB_CONFIG)
