"""
SQLite Database Connection Manager & Dependency for FastAPI.

Provides reusable database connectivity to nifty100.db with graceful error handling
and proper connection closing.
"""

import logging
from pathlib import Path
import sqlite3
from typing import Generator, Optional

# Project root path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "db" / "nifty100.db"

logger = logging.getLogger("api_database")


def get_db_path() -> Path:
    """
    Returns the path to SQLite database.
    """
    return DB_PATH


def create_connection(db_file: Optional[Path] = None) -> sqlite3.Connection:
    """
    Create a new SQLite database connection.

    Args:
        db_file: Optional custom Path to SQLite database file.

    Returns:
        sqlite3.Connection instance with Row factory enabled.
    """
    if db_file is None:
        db_file = DB_PATH

    if not db_file.exists():
        logger.error(f"SQLite database file not found at: {db_file}")
        raise FileNotFoundError(f"SQLite database file not found at: {db_file}")

    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise RuntimeError(f"Failed to connect to SQLite database: {e}")


def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI Dependency to yield a reusable SQLite database connection
    and close it automatically upon request completion.

    Yields:
        sqlite3.Connection
    """
    conn = None
    try:
        conn = create_connection()
        yield conn
    except Exception as e:
        logger.error(f"Database dependency session error: {e}")
        raise
    finally:
        if conn is not None:
            conn.close()
