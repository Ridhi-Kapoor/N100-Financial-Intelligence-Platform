"""
Health Check Router (GET /api/v1/health).

Provides application status, version, uptime, database connectivity status,
and table row counts across all 10 SQLite database tables.
"""

import logging
import sqlite3
import time
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.database import get_db_connection

logger = logging.getLogger("api_health_router")

router = APIRouter(tags=["Health"])

# App startup timestamp for uptime calculation
START_TIME = time.time()


def get_app_uptime() -> int:
    """
    Calculate application uptime in seconds.
    """
    return int(time.time() - START_TIME)


@router.get(
    "/health", summary="Health Check & System Audit", status_code=status.HTTP_200_OK
)
def get_health_status(
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> Dict[str, Any]:
    """
    System health check endpoint verifying:
    - Application status ('ok')
    - Application version ('1.0.0')
    - System uptime in seconds
    - SQLite database connectivity status
    - Database row counts across all tables
    """
    uptime = get_app_uptime()

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        tables = [row["name"] for row in cursor.fetchall()]

        db_row_counts = {}
        for tbl in sorted(tables):
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM `{tbl}`")
                res = cursor.fetchone()
                db_row_counts[tbl] = res["cnt"] if res else 0
            except Exception as e:
                logger.warning(f"Could not count rows for table {tbl}: {e}")
                db_row_counts[tbl] = -1

        return {
            "status": "ok",
            "version": "1.0.0",
            "uptime_seconds": uptime,
            "db_status": "connected",
            "db_row_counts": db_row_counts,
        }

    except Exception as e:
        logger.error(f"Health check failed due to database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "version": "1.0.0",
                "uptime_seconds": uptime,
                "db_status": "disconnected",
                "error": str(e),
            },
        )
