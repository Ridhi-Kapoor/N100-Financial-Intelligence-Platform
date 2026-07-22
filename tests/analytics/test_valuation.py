"""
Unit tests for Day 26 Valuation Analytics Module (src/analytics/valuation.py).
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.analytics.valuation import (
    assign_valuation_flag,
    calculate_5yr_median_pe,
    calculate_fcf_yield,
    calculate_pe_vs_sector_median_pct,
    calculate_sector_median_pe,
    export_valuation_results,
    run_valuation_analysis,
)


def test_calculate_fcf_yield_normal():
    # Free Cash Flow = 500 Cr, Market Cap = 10000 Cr -> FCF Yield = (500 / 10000) * 100 = 5.0%
    yield_val = calculate_fcf_yield(500.0, 10000.0)
    assert yield_val == pytest.approx(5.0)


def test_calculate_fcf_yield_negative_and_invalid():
    # Negative FCF
    assert calculate_fcf_yield(-200.0, 10000.0) == pytest.approx(-2.0)
    # Zero or negative Market Cap
    assert calculate_fcf_yield(500.0, 0.0) is None
    assert calculate_fcf_yield(500.0, -100.0) is None
    # None or NaN inputs
    assert calculate_fcf_yield(None, 10000.0) is None
    assert calculate_fcf_yield(500.0, None) is None
    assert calculate_fcf_yield(np.nan, 10000.0) is None


def test_calculate_sector_median_pe():
    data = {
        "broad_sector": ["Financials", "Financials", "Financials", "Technology", "Technology"],
        "pe_ratio": [20.0, 30.0, 40.0, 50.0, 70.0],
    }
    df = pd.DataFrame(data)
    medians = calculate_sector_median_pe(df)
    assert medians["Financials"] == pytest.approx(30.0)
    assert medians["Technology"] == pytest.approx(60.0)


def test_assign_valuation_flag():
    # Sector median P/E = 40.0
    # Caution cutoff: P/E > 1.5 * 40 = 60.0
    # Discount cutoff: P/E < 0.7 * 40 = 28.0

    # Caution case
    assert assign_valuation_flag(65.0, 40.0) == "Caution"
    # Discount case
    assert assign_valuation_flag(25.0, 40.0) == "Discount"
    # Fair cases
    assert assign_valuation_flag(40.0, 40.0) == "Fair"
    assert assign_valuation_flag(50.0, 40.0) == "Fair"
    assert assign_valuation_flag(30.0, 40.0) == "Fair"

    # Edge cases
    assert assign_valuation_flag(None, 40.0) == "Fair"
    assert assign_valuation_flag(50.0, None) == "Fair"
    assert assign_valuation_flag(50.0, 0.0) == "Fair"


def test_calculate_pe_vs_sector_median_pct():
    # Company P/E = 60, Sector Median = 40 -> ((60 - 40) / 40) * 100 = 50%
    assert calculate_pe_vs_sector_median_pct(60.0, 40.0) == pytest.approx(50.0)
    # Company P/E = 20, Sector Median = 40 -> ((20 - 40) / 40) * 100 = -50%
    assert calculate_pe_vs_sector_median_pct(20.0, 40.0) == pytest.approx(-50.0)
    # Invalid inputs
    assert calculate_pe_vs_sector_median_pct(None, 40.0) is None
    assert calculate_pe_vs_sector_median_pct(60.0, 0.0) is None


def test_calculate_5yr_median_pe():
    data = {
        "company_id": ["TCS", "TCS", "TCS", "TCS", "TCS", "TCS"],
        "year": [2019, 2020, 2021, 2022, 2023, 2024],
        "pe_ratio": [25.0, 28.0, 30.0, 32.0, 34.0, 36.0],
    }
    df = pd.DataFrame(data)
    # For latest year 2024, 5-year window is 2020-2024: [28, 30, 32, 34, 36] -> median = 32.0
    med_pe = calculate_5yr_median_pe(df, "TCS", latest_year=2024, years_back=5)
    assert med_pe == pytest.approx(32.0)


def test_run_valuation_analysis_and_export(tmp_path):
    df_summary, df_flags = run_valuation_analysis()

    assert not df_summary.empty
    assert len(df_summary) == 92
    assert "Company ID" in df_summary.columns
    assert "Valuation Flag" in df_summary.columns

    # Verify flags values
    valid_flags = {"Caution", "Discount", "Fair"}
    assert set(df_summary["Valuation Flag"].unique()).issubset(valid_flags)

    # Verify df_flags filtered correctly
    assert set(df_flags["Valuation Flag"].unique()).issubset({"Caution", "Discount"})
    assert len(df_flags) == (df_summary["Valuation Flag"] != "Fair").sum()

    # Test file export
    excel_path, csv_path = export_valuation_results(df_summary, df_flags, output_dir=tmp_path)
    assert excel_path.exists()
    assert csv_path.exists()
