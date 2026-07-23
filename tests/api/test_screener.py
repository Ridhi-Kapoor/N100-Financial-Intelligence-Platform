"""
Unit and API integration tests for Stock Screener endpoints.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_screener_min_roe_15_filter():
    """Verify min_roe=15 returns only companies with ROE >= 15."""
    for endpoint in ["/screener?min_roe=15", "/api/v1/screener?min_roe=15"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        results = data["results"]
        assert len(results) > 0
        for item in results:
            roe = item["latest_kpis"]["roe"]
            if roe is not None:
                assert roe >= 15.0, f"Company {item['company_id']} has ROE {roe} < 15.0"


def test_screener_invalid_query_params():
    """Verify invalid query parameters return HTTP 400."""
    invalid_endpoints = [
        "/screener?max_de=-1.0",
        "/api/v1/screener?max_pe=-5.0",
        "/api/v1/screener?min_roe=5000.0",
        "/api/v1/screener?min_rev_cagr_5yr=-500.0",
    ]
    for endpoint in invalid_endpoints:
        response = client.get(endpoint)
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
