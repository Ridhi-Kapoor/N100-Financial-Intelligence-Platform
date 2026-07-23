"""
Integration Tests for Day 40 API Endpoints and Documentation Exporter.

Tests all 8 required REST API endpoint functionalities, query validation,
error codes (400, 404, 200), and documentation exports.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# 1. Stock Screener Tests
def test_stock_screener_valid_query():
    response = client.get("/api/v1/screener?min_roe=15&max_de=1.5&min_fcf=0")
    assert response.status_code == 200
    data = response.json()
    assert "total_matches" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    if data["results"]:
        first = data["results"][0]
        assert "rank" in first
        assert "company_id" in first
        assert "latest_kpis" in first


def test_stock_screener_invalid_query_params():
    # Negative max_de should return 400
    response = client.get("/api/v1/screener?max_de=-1.0")
    assert response.status_code == 400
    assert "detail" in response.json()

    # Negative max_pe should return 400
    response_pe = client.get("/api/v1/screener?max_pe=-10.0")
    assert response_pe.status_code == 400

    # Out of range min_roe should return 400
    response_roe = client.get("/api/v1/screener?min_roe=5000.0")
    assert response_roe.status_code == 400


# 2. Sector Summary Tests
def test_sectors_summary_endpoint():
    response = client.get("/api/v1/sectors")
    assert response.status_code == 200
    data = response.json()
    assert "total_sectors" in data
    assert "sectors" in data
    assert len(data["sectors"]) > 0
    first_sec = data["sectors"][0]
    assert "sector" in first_sec
    assert "company_count" in first_sec
    assert "median_roe" in first_sec
    assert "median_pe" in first_sec
    assert "median_debt_to_equity" in first_sec


# 3. Sector Companies Tests
def test_sector_companies_valid():
    response = client.get("/api/v1/sectors/Financials/companies")
    assert response.status_code == 200
    data = response.json()
    assert data["sector"] == "Financials"
    assert "companies" in data
    assert len(data["companies"]) > 0
    comp = data["companies"][0]
    assert "company_id" in comp
    assert "latest_kpis" in comp


def test_sector_companies_404():
    response = client.get("/api/v1/sectors/NonExistentSector/companies")
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


# 4. Peer Groups Tests
def test_peer_group_valid():
    response = client.get("/api/v1/peers/IT%20Services")
    assert response.status_code == 200
    data = response.json()
    assert "peer_group_name" in data
    assert "companies" in data
    assert len(data["companies"]) > 0
    comp = data["companies"][0]
    assert "percentile_ranks" in comp
    assert len(comp["percentile_ranks"]) == 10


def test_peer_group_404():
    response = client.get("/api/v1/peers/UnknownPeerGroup")
    assert response.status_code == 404
    assert "unknown" in response.json()["detail"].lower()


# 5. Peer Comparison Radar Tests
def test_peer_comparison_radar_valid():
    response = client.get("/api/v1/companies/INFY/peers/compare")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "INFY"
    assert "metrics" in data
    assert len(data["metrics"]) == 8
    assert "company_values" in data
    assert "peer_group_average" in data
    assert "benchmark_values" in data


def test_peer_comparison_radar_404():
    response = client.get("/api/v1/companies/INVALIDTICKER/peers/compare")
    assert response.status_code == 404


# 6. Historical Valuation Tests
def test_historical_valuation_valid():
    response = client.get("/api/v1/market-cap/RELIANCE")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "RELIANCE"
    assert "history" in data
    assert len(data["history"]) > 0
    first_hist = data["history"][0]
    assert "year" in first_hist
    assert "pe_ratio" in first_hist
    assert "pb_ratio" in first_hist
    assert "ev_ebitda" in first_hist
    assert "dividend_yield_pct" in first_hist


def test_historical_valuation_404():
    response = client.get("/api/v1/market-cap/INVALIDTICKER")
    assert response.status_code == 404


# 7. Portfolio Statistics Tests
def test_portfolio_stats():
    response = client.get("/api/v1/portfolio/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_kpis" in data
    assert data["total_kpis"] == 10
    assert "statistics" in data
    assert len(data["statistics"]) == 10
    stat = data["statistics"][0]
    assert "kpi_name" in stat
    assert "p10" in stat
    assert "p25" in stat
    assert "p50" in stat
    assert "p75" in stat
    assert "p90" in stat
    assert "mean" in stat
    assert "std_dev" in stat


# 8. Company Documents Tests
def test_company_documents_valid():
    response = client.get("/api/v1/companies/INFY/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "INFY"
    assert "documents" in data
    assert len(data["documents"]) > 0
    doc = data["documents"][0]
    assert "annual_report_title" in doc
    assert "report_url" in doc
    assert "is_url_valid" in doc
    assert isinstance(doc["is_url_valid"], bool)


def test_company_documents_404():
    response = client.get("/api/v1/companies/INVALIDTICKER/documents")
    assert response.status_code == 404


# 9. API Documentation & Export Files Tests
def test_api_documentation_exports():
    openapi_file = PROJECT_ROOT / "docs" / "openapi.json"
    postman_file = PROJECT_ROOT / "docs" / "postman_collection.json"

    assert openapi_file.exists(), "docs/openapi.json does not exist."
    assert postman_file.exists(), "docs/postman_collection.json does not exist."

    with open(openapi_file, "r", encoding="utf-8") as f:
        openapi_data = json.load(f)
        assert "openapi" in openapi_data or "swagger" in openapi_data
        assert "paths" in openapi_data
        # Ensure all Day 40 endpoints are present in OpenAPI spec
        paths = openapi_data["paths"]
        assert "/api/v1/screener" in paths
        assert "/api/v1/sectors" in paths
        assert "/api/v1/sectors/{sector}/companies" in paths
        assert "/api/v1/peers/{group_name}" in paths
        assert "/api/v1/companies/{ticker}/peers/compare" in paths
        assert "/api/v1/market-cap/{ticker}" in paths
        assert "/api/v1/portfolio/stats" in paths
        assert "/api/v1/companies/{ticker}/documents" in paths

    with open(postman_file, "r", encoding="utf-8") as f:
        postman_data = json.load(f)
        assert "info" in postman_data
        assert "item" in postman_data
        assert postman_data["info"]["schema"].endswith("v2.1.0/collection.json")
