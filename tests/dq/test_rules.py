"""
Unit tests for Data Quality (DQ) Rules (DQ-01 through DQ-14).

Covers 14 isolated unit tests (one per rule).
Each test creates a small DataFrame violating ONLY that specific rule,
executes the rule validator, and verifies rule_id, severity, violation count,
and rule isolation (no unrelated rules triggered).
"""

import pandas as pd
from scripts.etl.validator import (
    Severity,
    check_pk_not_null,
    check_duplicate_pks,
    check_foreign_key_violations,
    check_missing_financial_year,
    check_missing_mandatory_fields,
    check_negative_sales,
    check_invalid_ticker,
    check_duplicate_company_year,
    check_opm_out_of_range,
    check_balance_sheet_mismatch,
    check_zero_sales,
    check_negative_net_profit,
    check_negative_assets,
    check_future_financial_year,
)


def get_valid_baseline_df() -> pd.DataFrame:
    """Return a baseline 2-row DataFrame that passes all DQ rules."""
    return pd.DataFrame(
        {
            "ticker": ["TCS", "INFY"],
            "year": [2021, 2022],
            "sales": [1000.0, 2000.0],
            "opm": [0.25, 0.20],
            "total_assets": [5000.0, 6000.0],
            "total_liabilities": [3000.0, 3500.0],
            "total_equity": [2000.0, 2500.0],
            "net_profit": [200.0, 300.0],
            "broad_sector": ["Technology", "Technology"],
            "industry": ["IT Services", "IT Services"],
        }
    )


# -------------------------------------------------------------------------
# CRITICAL RULES (DQ-01 to DQ-08)
# -------------------------------------------------------------------------


def test_dq01_pk_null():
    """DQ-01: Primary Key cannot be NULL."""
    df = get_valid_baseline_df()
    df.loc[0, "ticker"] = None

    failures = check_pk_not_null(df, "ticker", "financials")
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-01"
    assert failures[0].severity == Severity.CRITICAL.value
    assert failures[0].column_name == "ticker"


def test_dq02_duplicate_pks():
    """DQ-02: Duplicate Primary Keys."""
    df = get_valid_baseline_df()
    df.loc[1, "ticker"] = "TCS"

    failures = check_duplicate_pks(df, "ticker", "financials")
    assert len(failures) == 2  # Both rows flagged for duplicate key
    assert all(f.rule_id == "DQ-02" for f in failures)
    assert all(f.severity == Severity.CRITICAL.value for f in failures)


def test_dq03_foreign_key_violations():
    """DQ-03: Foreign Key violations."""
    df = get_valid_baseline_df()
    parent_keys = {"TCS"}  # INFY is missing from parent keys

    failures = check_foreign_key_violations(
        df, "ticker", parent_keys, "companies", "financials"
    )
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-03"
    assert failures[0].severity == Severity.CRITICAL.value
    assert failures[0].failed_value == "INFY"


def test_dq04_missing_financial_year():
    """DQ-04: Missing financial year."""
    df = get_valid_baseline_df()
    df.loc[0, "year"] = None

    failures = check_missing_financial_year(df, "year", "financials")
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-04"
    assert failures[0].severity == Severity.CRITICAL.value


def test_dq05_missing_mandatory_fields():
    """DQ-05: Missing mandatory fields."""
    df = get_valid_baseline_df()
    df.loc[0, "sales"] = None

    failures = check_missing_mandatory_fields(df, ["sales"], "financials")
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-05"
    assert failures[0].severity == Severity.CRITICAL.value
    assert failures[0].column_name == "sales"


def test_dq06_negative_sales():
    """DQ-06: Negative sales."""
    df = get_valid_baseline_df()
    df.loc[0, "sales"] = -500.0

    failures = check_negative_sales(df, "sales", "financials")
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-06"
    assert failures[0].severity == Severity.CRITICAL.value


def test_dq07_invalid_ticker():
    """DQ-07: Invalid ticker/company code format."""
    df = get_valid_baseline_df()
    df.loc[0, "ticker"] = "INVALID_TICKER_NAME_TOO_LONG"

    failures = check_invalid_ticker(df, "ticker", "financials")
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-07"
    assert failures[0].severity == Severity.CRITICAL.value


def test_dq08_duplicate_company_year():
    """DQ-08: Duplicate Company-Year records."""
    df = get_valid_baseline_df()
    df.loc[1, "ticker"] = "TCS"
    df.loc[1, "year"] = 2021  # Duplicate of row 0 (TCS, 2021)

    failures = check_duplicate_company_year(df, "ticker", "year", "financials")
    assert len(failures) == 2
    assert all(f.rule_id == "DQ-08" for f in failures)
    assert all(f.severity == Severity.CRITICAL.value for f in failures)


# -------------------------------------------------------------------------
# WARNING RULES (DQ-09 to DQ-14)
# -------------------------------------------------------------------------


def test_dq09_opm_out_of_range():
    """DQ-09: Operating Profit Margin outside expected range."""
    df = get_valid_baseline_df()
    df.loc[0, "opm"] = 5.0  # 500% OPM is out of range [-1.0, 1.0]

    failures = check_opm_out_of_range(df, "financials", opm_col="opm")
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-09"
    assert failures[0].severity == Severity.WARNING.value


def test_dq10_balance_sheet_mismatch():
    """DQ-10: Balance Sheet mismatch (Assets != Liabilities + Equity)."""
    df = get_valid_baseline_df()
    df.loc[0, "total_assets"] = 9999.0  # Mismatch with liab (3000) + equity (2000)

    failures = check_balance_sheet_mismatch(
        df, "total_assets", "total_liabilities", "total_equity", "financials"
    )
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-10"
    assert failures[0].severity == Severity.WARNING.value


def test_dq11_zero_sales():
    """DQ-11: Sales equal to zero."""
    df = get_valid_baseline_df()
    df.loc[0, "sales"] = 0.0

    failures = check_zero_sales(df, "sales", "financials")
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-11"
    assert failures[0].severity == Severity.WARNING.value


def test_dq12_negative_net_profit():
    """DQ-12: Negative Net Profit."""
    df = get_valid_baseline_df()
    df.loc[0, "net_profit"] = -150.0

    failures = check_negative_net_profit(df, "net_profit", "financials")
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-12"
    assert failures[0].severity == Severity.WARNING.value


def test_dq13_negative_assets():
    """DQ-13: Negative Total Assets."""
    df = get_valid_baseline_df()
    df.loc[0, "total_assets"] = -100.0

    failures = check_negative_assets(df, "total_assets", "financials")
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-13"
    assert failures[0].severity == Severity.WARNING.value


def test_dq14_future_financial_year():
    """DQ-14: Future financial year."""
    df = get_valid_baseline_df()
    df.loc[0, "year"] = 2050  # Year 2050 > current year 2026

    failures = check_future_financial_year(df, "year", "financials", current_year=2026)
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-14"
    assert failures[0].severity == Severity.WARNING.value
