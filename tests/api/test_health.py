"""
Unit and API integration tests for Health Check endpoint.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

EXPECTED_TABLES = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "financial_ratios",
    "market_cap",
    "peer_groups",
    "sectors",
    "stock_prices",
]


def test_health_check_v1_endpoint():
    """Verify GET /api/v1/health returns HTTP 200, status='ok', and all 10 tables."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data.get("status") == "ok"
    assert data.get("version") == "1.0.0"
    assert data.get("db_status") == "connected"
    assert "uptime_seconds" in data

    db_counts = data.get("db_row_counts", {})
    assert len(db_counts) >= 10
    for tbl in EXPECTED_TABLES:
        assert tbl in db_counts, f"Table '{tbl}' is missing from db_row_counts"
        assert db_counts[tbl] > 0, f"Table '{tbl}' row count is non-positive"


def test_health_check_root_endpoint():
    """Verify GET /health returns HTTP 200 and status='ok'."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
