"""
Integration tests for FastAPI application server, CORS, middleware, and router registration.
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "documentation" in data
    assert data["documentation"] == "/docs"


def test_openapi_docs_accessible():
    response = client.get("/docs")
    assert response.status_code == 200


def test_cors_headers_present():
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/v1/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in [
        "*",
        "http://localhost:3000",
    ]


def test_all_routers_registered():
    routes = [
        "/api/v1/companies/",
        "/api/v1/screener/",
        "/api/v1/sectors/",
        "/api/v1/peers/TCS",
        "/api/v1/valuation/RELIANCE",
        "/api/v1/portfolio/clusters",
        "/api/v1/documents/tearsheet/INFY",
    ]

    for route in routes:
        res = client.get(route)
        assert res.status_code == 200
