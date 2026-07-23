"""
Unit and API integration tests for Companies API endpoints.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_get_companies_returns_92_companies():
    """Verify GET /companies (and /api/v1/companies) returns 92 companies."""
    for endpoint in ["/companies", "/api/v1/companies"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data.get("total") == 92
        assert len(data.get("companies", [])) == 92


def test_get_company_by_ticker_tcs():
    """Verify GET /companies/TCS returns correct company data."""
    for endpoint in ["/companies/TCS", "/api/v1/companies/TCS"]:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json()
        assert data.get("id") == "TCS"
        assert "Tata Consultancy Services" in data.get("company_name", "")


def test_get_company_by_invalid_ticker_404():
    """Verify GET /companies/INVALID returns HTTP 404."""
    for endpoint in ["/companies/INVALID", "/api/v1/companies/INVALID"]:
        response = client.get(endpoint)
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("detail", "").lower()
