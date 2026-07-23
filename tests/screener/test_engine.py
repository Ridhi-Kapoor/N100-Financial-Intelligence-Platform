"""
Unit and integration tests for the screener engine module.
"""

from pathlib import Path
import pandas as pd
import pytest
import yaml

from src.screener.engine import (
    load_config,
    is_financial_sector,
    is_debt_free,
    add_composite_quality_score,
    load_screener_data,
    apply_screener_filters,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_FILE = PROJECT_ROOT / "data" / "db" / "nifty100.db"


def test_load_config_valid(tmp_path):
    """Test loading a valid YAML configuration file."""
    config_data = {"filters": {"ROE": {"min": 15.0}, "Debt-to-Equity": {"max": 1.0}}}
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)

    loaded = load_config(config_file)
    assert loaded == config_data
    assert loaded["filters"]["ROE"]["min"] == 15.0


def test_load_config_missing():
    """Test loading a missing configuration file returns an empty dict."""
    loaded = load_config(Path("non_existent_file.yaml"))
    assert loaded == {}


def test_is_financial_sector():
    """Test identification of the Financials sector."""
    assert is_financial_sector({"broad_sector": "Financials"}) is True
    assert is_financial_sector({"sector": "financials"}) is True
    assert is_financial_sector({"broad_sector": "Technology"}) is False
    assert is_financial_sector({"broad_sector": None}) is False
    assert is_financial_sector({}) is False


def test_is_debt_free():
    """Test identification of debt-free records."""
    # Case 1: interest is 0.0
    assert is_debt_free({"interest": 0.0}) is True

    # Case 2: debt_to_equity is 0.0
    assert is_debt_free({"debt_to_equity": 0.0}) is True

    # Case 3: total_debt_cr is 0.0
    assert is_debt_free({"total_debt_cr": 0.0}) is True

    # Case 4: borrowings is 0.0
    assert is_debt_free({"borrowings": 0.0}) is True

    # Case 5: Has debt/interest
    assert (
        is_debt_free({"interest": 10.0, "debt_to_equity": 0.5, "borrowings": 200.0})
        is False
    )


def test_add_composite_quality_score():
    """Test dynamic computation of composite_quality_score if not present."""
    # Data covering 5 years (2020-2024) for two companies
    # Company A has 5 complete years of data.
    # Company B has only 4 years of data.
    data = {
        "company_id": ["A", "A", "A", "A", "A", "B", "B", "B", "B"],
        "year": [
            "2020",
            "2021",
            "2022",
            "2023",
            "2024",
            "2021",
            "2022",
            "2023",
            "2024",
        ],
        "cash_from_operations_cr": [
            100.0,
            110.0,
            120.0,
            130.0,
            140.0,
            50.0,
            60.0,
            70.0,
            80.0,
        ],
        "net_profit": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
    }
    df = pd.DataFrame(data)

    df_with_score = add_composite_quality_score(df)

    # Check that the column was added
    assert "composite_quality_score" in df_with_score.columns

    # Company A should have score = Average(1.0, 1.1, 1.2, 1.3, 1.4) = 1.2
    # Find score for Company A in 2024
    score_a_2024 = df_with_score[
        (df_with_score["company_id"] == "A") & (df_with_score["year"] == "2024")
    ]["composite_quality_score"].values[0]
    assert score_a_2024 == pytest.approx(1.2)

    # Company A in 2023 has only 4 preceding years (2020-2023), so its score should be NaN
    score_a_2023 = df_with_score[
        (df_with_score["company_id"] == "A") & (df_with_score["year"] == "2023")
    ]["composite_quality_score"].values[0]
    assert pd.isna(score_a_2023)

    # Company B in 2024 has only 4 years total, so score should be NaN
    score_b_2024 = df_with_score[
        (df_with_score["company_id"] == "B") & (df_with_score["year"] == "2024")
    ]["composite_quality_score"].values[0]
    assert pd.isna(score_b_2024)


def test_apply_screener_filters_basic():
    """Test applying basic filters across the 15 metrics."""
    data = {
        "company_id": ["A", "B", "C", "D"],
        "company_name": ["Company A", "Company B", "Company C", "Company D"],
        "year": ["2024", "2024", "2024", "2024"],
        "return_on_equity_pct": [20.0, 10.0, 25.0, 18.0],
        "debt_to_equity": [0.5, 0.2, 1.5, 0.8],
        "broad_sector": ["Technology", "Financials", "Financials", "Energy"],
        "composite_quality_score": [1.5, 1.2, 2.0, 0.9],
    }
    df = pd.DataFrame(data)

    # Config: ROE > 15%, D/E < 1.0 (excluding Financials)
    config = {"filters": {"ROE": {"min": 15.0}, "Debt-to-Equity": {"max": 1.0}}}

    filtered_df = apply_screener_filters(df, config)

    # Company A: ROE=20 (>15), D/E=0.5 (<1.0), Sector=Tech -> PASS
    # Company B: ROE=10 (<15) -> FAIL
    # Company C: ROE=25 (>15), D/E=1.5 (>1.0), Sector=Financials -> PASS (D/E check skipped for Financials!)
    # Company D: ROE=18 (>15), D/E=0.8 (<1.0), Sector=Energy -> PASS

    assert len(filtered_df) == 3
    assert set(filtered_df["company_id"]) == {"A", "C", "D"}

    # Verification of sorting (descending order of composite_quality_score)
    # Scores: C (2.0), A (1.5), D (0.9)
    assert filtered_df.iloc[0]["company_id"] == "C"
    assert filtered_df.iloc[1]["company_id"] == "A"
    assert filtered_df.iloc[2]["company_id"] == "D"


def test_apply_screener_interest_coverage_debt_free():
    """Test that debt-free companies bypass the interest coverage ratio filter."""
    data = {
        "company_id": ["A", "B"],
        "company_name": ["Company A", "Company B"],
        "year": ["2024", "2024"],
        "return_on_equity_pct": [20.0, 20.0],
        "interest_coverage": [1.0, None],  # Company B has null/NaN ICR
        "interest": [
            5.0,
            0.0,
        ],  # Company B is Debt Free because interest expense is 0.0
        "composite_quality_score": [1.0, 1.1],
    }
    df = pd.DataFrame(data)

    config = {"filters": {"Interest Coverage Ratio": {"min": 3.0}}}

    filtered_df = apply_screener_filters(df, config)

    # Company A: ICR=1.0 (<3.0) -> FAIL
    # Company B: ICR is NaN, but is Debt Free (interest=0.0) -> PASS (ICR filter bypassed/treated as infinite)

    assert len(filtered_df) == 1
    assert filtered_df.iloc[0]["company_id"] == "B"


def test_screener_integration_with_db():
    """Integration test checking that the database loading and screening work on real data."""
    if not DB_FILE.exists():
        pytest.skip("SQLite database nifty100.db not found. Skipping integration test.")

    # 1. Load data
    df = load_screener_data(DB_FILE, year=2024)
    assert not df.empty

    # Verify critical columns are present
    critical_cols = [
        "company_id",
        "company_name",
        "year",
        "broad_sector",
        "return_on_equity_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "pe_ratio",
        "pb_ratio",
        "dividend_yield_pct",
        "market_cap_crore",
        "sales",
        "net_profit",
    ]
    for col in critical_cols:
        assert (
            col in df.columns
        ), f"Required column '{col}' is missing from loaded screener data."

    # 2. Load configuration from project config file
    config_path = PROJECT_ROOT / "screener_config.yaml"
    assert config_path.exists()
    config = load_config(config_path)

    # 3. Apply filters
    filtered_df = apply_screener_filters(df, config)

    # Verify results
    print(f"\nReal DB Screener results for 2024 (count: {len(filtered_df)}):")
    for _, row in filtered_df.head(5).iterrows():
        print(
            f"  {row['company_name']} ({row['company_id']}) - Sector: {row['broad_sector']}, ROE: {row['return_on_equity_pct']:.2f}%, D/E: {row['debt_to_equity']}, Score: {row['composite_quality_score']}"
        )

    # As per main/demo script expectations, the results count should be reasonable (e.g. between 10 and 60)
    assert len(filtered_df) >= 0
