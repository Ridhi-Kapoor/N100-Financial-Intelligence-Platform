"""
Integration test to verify Streamlit dashboard and FastAPI backend alignment.
Checks that screener query results match between API and dashboard engine data loader.
"""

from fastapi.testclient import TestClient
import pandas as pd

from src.api.main import app
from src.screener.engine import load_screener_data
from src.api.services import DB_PATH

client = TestClient(app)


def test_dashboard_screener_matches_api_response():
    """
    Verify that screener results shown in Streamlit match the /api/v1/screener API response.
    """
    min_roe_val = 15.0

    # 1. Fetch API response from FastAPI backend
    api_resp = client.get(f"/api/v1/screener?min_roe={min_roe_val}")
    assert api_resp.status_code == 200
    api_data = api_resp.json()
    api_results = api_data.get("results", [])
    api_company_ids = [item["company_id"] for item in api_results]

    # 2. Load and filter data using Streamlit dashboard engine pipeline
    df_base = load_screener_data(DB_PATH)
    assert not df_base.empty, "Screener base data is empty"

    # Deduplicate to latest year per company (matching API logic)
    df_base["year_num"] = pd.to_numeric(df_base["year"], errors="coerce")
    df_latest = (
        df_base.sort_values("year_num").groupby("company_id").last().reset_index()
    )

    # Filter with min_roe
    df_filtered = df_latest[
        df_latest["return_on_equity_pct"].astype(float) >= min_roe_val
    ]
    dashboard_company_ids = df_filtered["company_id"].astype(str).str.strip().tolist()

    # 3. Assert total match count and company IDs align
    assert len(api_company_ids) == len(dashboard_company_ids)
    assert set(api_company_ids) == set(dashboard_company_ids)


def test_dashboard_backend_connectivity():
    """Verify backend connectivity status endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["db_status"] == "connected"
    assert data["status"] == "ok"
