"""
Unit tests for src/analytics/peer.py module.
"""

import sqlite3
from pathlib import Path
import pandas as pd

from src.analytics.peer import (
    load_peer_groups,
    get_company_peer_group,
    get_peer_percentiles_for_company,
    compute_peer_percentiles,
    populate_peer_percentiles_table,
    METRIC_DEFINITIONS,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "db" / "nifty100.db"
EXCEL_PATH = PROJECT_ROOT / "data" / "raw" / "peer_groups.xlsx"


def test_load_peer_groups():
    """Verify loading peer groups Excel file."""
    df = load_peer_groups(excel_path=EXCEL_PATH)
    assert not df.empty
    assert "company_id" in df.columns
    assert "peer_group_name" in df.columns
    assert df["peer_group_name"].nunique() == 11


def test_unassigned_company_message():
    """Verify that unassigned companies return 'No peer group assigned'."""
    unassigned = get_company_peer_group("ZOMATO", excel_path=EXCEL_PATH)
    assert unassigned == "No peer group assigned"

    res = get_peer_percentiles_for_company(
        "ZOMATO", db_path=DB_PATH, excel_path=EXCEL_PATH
    )
    assert res == "No peer group assigned"


def test_assigned_company_peer_group():
    """Verify peer group lookup for assigned companies."""
    pg = get_company_peer_group("HDFCBANK", excel_path=EXCEL_PATH)
    assert pg == "Private Banks"


def test_compute_peer_percentiles_schema_and_counts():
    """Verify compute_peer_percentiles returns valid columns and non-empty data."""
    df = compute_peer_percentiles(db_path=DB_PATH, excel_path=EXCEL_PATH)
    assert not df.empty
    expected_cols = {
        "company_id",
        "peer_group_name",
        "metric",
        "value",
        "percentile_rank",
        "year",
    }
    assert expected_cols.issubset(set(df.columns))

    metrics_present = set(df["metric"].unique())
    for metric_name in METRIC_DEFINITIONS:
        assert metric_name in metrics_present


def test_debt_to_equity_inverse_ranking():
    """Verify Debt-to-Equity inverse percentile ranking (lower value -> higher rank)."""
    df = compute_peer_percentiles(db_path=DB_PATH, excel_path=EXCEL_PATH)
    de_df = df[df["metric"] == "Debt-to-Equity"].dropna(
        subset=["value", "percentile_rank"]
    )

    # Group by peer group and year, check correlation or order
    for (pg, yr), grp in de_df.groupby(["peer_group_name", "year"]):
        if len(grp) >= 2 and grp["value"].nunique() > 1:
            sorted_by_val = grp.sort_values(by="value")
            lowest_de_rank = sorted_by_val.iloc[0]["percentile_rank"]
            highest_de_rank = sorted_by_val.iloc[-1]["percentile_rank"]
            # Lowest Debt-to-Equity must have a higher or equal percentile rank than highest Debt-to-Equity
            assert lowest_de_rank >= highest_de_rank


def test_populate_peer_percentiles_table():
    """Verify database population of peer_percentiles table."""
    count = populate_peer_percentiles_table(db_path=DB_PATH, excel_path=EXCEL_PATH)
    assert count > 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM peer_percentiles;")
    db_count = cursor.fetchone()[0]
    conn.close()

    assert db_count == count


def test_get_peer_percentiles_for_company():
    """Verify fetching peer percentiles DataFrame for a specific assigned company."""
    res = get_peer_percentiles_for_company(
        "HDFCBANK", year="2024", db_path=DB_PATH, excel_path=EXCEL_PATH
    )
    assert isinstance(res, pd.DataFrame)
    assert not res.empty
    assert (res["company_id"] == "HDFCBANK").all()
    assert (res["peer_group_name"] == "Private Banks").all()
