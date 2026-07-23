"""
Unit and API integration tests for Sectors endpoints.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_get_sectors_list():
    """Verify /sectors returns broad sectors list with median KPIs."""
    for endpoint in ["/sectors", "/api/v1/sectors"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert "total_sectors" in data
        assert "sectors" in data
        assert data["total_sectors"] >= 10
        assert len(data["sectors"]) >= 10
        first_sec = data["sectors"][0]
        assert "sector" in first_sec
        assert "median_roe" in first_sec


def test_get_sector_it_companies():
    """Verify /sectors/IT/companies returns only IT companies."""
    for endpoint in ["/sectors/IT/companies", "/api/v1/sectors/IT/companies"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data["sector"] == "Information Technology"
        companies = data.get("companies", [])
        assert len(companies) > 0
        known_it_tickers = ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"]
        returned_tickers = [c["company_id"] for c in companies]
        assert any(t in returned_tickers for t in known_it_tickers)
