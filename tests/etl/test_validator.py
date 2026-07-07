"""
Unit tests for the Data Quality Validator.
"""

import pandas as pd
import pytest
from pathlib import Path
from scripts.etl.validator import (
    DataValidator,
    ValidationFailure,
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
    check_missing_sector,
    check_missing_industry
)

# Helper function to generate a baseline valid DataFrame
def get_valid_df() -> pd.DataFrame:
    return pd.DataFrame({
        "ticker": ["TCS", "INFY", "RELIANCE"],
        "year": [2021, 2022, 2023],
        "sales": [1000.0, 2000.0, 3000.0],
        "opm": [0.25, 0.20, 0.18],
        "total_assets": [5000.0, 6000.0, 7000.0],
        "total_liabilities": [3000.0, 3500.0, 4000.0],
        "total_equity": [2000.0, 2500.0, 3000.0],
        "net_profit": [200.0, 300.0, 400.0],
        "sector": ["Technology", "Technology", "Energy"],
        "industry": ["IT Services", "IT Services", "Oil & Gas"]
    })


# 1. Valid dataset
def test_valid_dataset():
    df = get_valid_df()
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker", "year", "sales"],
        sales_col="sales",
        opm_col="opm",
        assets_col="total_assets",
        liabilities_col="total_liabilities",
        equity_col="total_equity",
        net_profit_col="net_profit",
        sector_col="sector",
        industry_col="industry",
        current_year=2026
    )
    assert len(failures) == 0
    assert len(validator.get_failures()) == 0


# 2. Empty DataFrame
def test_empty_dataframe():
    df = pd.DataFrame()
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker", "year"],
    )
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-05"
    assert failures[0].severity == Severity.CRITICAL.value
    assert "empty" in failures[0].error_message.lower()


# 3. PK NULL
def test_pk_null():
    df = get_valid_df()
    df.loc[1, "ticker"] = None  # Row 2 (index 1) PK is null
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
    )
    dq01_failures = [f for f in failures if f.rule_id == "DQ-01"]
    assert len(dq01_failures) == 1
    assert dq01_failures[0].row_number == 2
    assert dq01_failures[0].column_name == "ticker"
    assert dq01_failures[0].severity == Severity.CRITICAL.value


# 4. Duplicate PK
def test_duplicate_pk():
    df = get_valid_df()
    df.loc[2, "ticker"] = "TCS"  # Row 3 (index 2) ticker duplicated with row 1
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
    )
    dq02_failures = [f for f in failures if f.rule_id == "DQ-02"]
    assert len(dq02_failures) == 2
    assert dq02_failures[0].row_number == 1
    assert dq02_failures[1].row_number == 3
    assert dq02_failures[0].severity == Severity.CRITICAL.value


# 5. FK violation
def test_fk_violation():
    df = get_valid_df()
    parent_keys = {"TCS", "INFY"}  # RELIANCE is missing
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
        fk_col="ticker",
        parent_keys=parent_keys,
        parent_table_name="companies"
    )
    dq03_failures = [f for f in failures if f.rule_id == "DQ-03"]
    assert len(dq03_failures) == 1
    assert dq03_failures[0].row_number == 3
    assert dq03_failures[0].failed_value == "RELIANCE"
    assert dq03_failures[0].severity == Severity.CRITICAL.value


# 6. Missing year
def test_missing_year():
    df = get_valid_df()
    df.loc[0, "year"] = None  # Row 1 (index 0) year missing
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
    )
    dq04_failures = [f for f in failures if f.rule_id == "DQ-04"]
    assert len(dq04_failures) == 1
    assert dq04_failures[0].row_number == 1
    assert dq04_failures[0].severity == Severity.CRITICAL.value


# 7. Missing mandatory fields
def test_missing_mandatory_fields():
    df = get_valid_df()
    df.loc[2, "sales"] = None  # Row 3 sales missing (and it is mandatory)
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker", "sales"],
    )
    dq05_failures = [f for f in failures if f.rule_id == "DQ-05"]
    assert len(dq05_failures) == 1
    assert dq05_failures[0].row_number == 3
    assert dq05_failures[0].column_name == "sales"
    assert dq05_failures[0].severity == Severity.CRITICAL.value


# 8. Negative sales
def test_negative_sales():
    df = get_valid_df()
    df.loc[1, "sales"] = -500.0  # Row 2 negative sales
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
        sales_col="sales"
    )
    dq06_failures = [f for f in failures if f.rule_id == "DQ-06"]
    assert len(dq06_failures) == 1
    assert dq06_failures[0].row_number == 2
    assert dq06_failures[0].failed_value == "-500.0"
    assert dq06_failures[0].severity == Severity.CRITICAL.value


# 9. Duplicate Company-Year
def test_duplicate_company_year():
    df = get_valid_df()
    df.loc[2, "ticker"] = "TCS"
    df.loc[2, "year"] = 2021
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
    )
    dq08_failures = [f for f in failures if f.rule_id == "DQ-08"]
    assert len(dq08_failures) == 2
    assert dq08_failures[0].row_number == 1
    assert dq08_failures[1].row_number == 3
    assert dq08_failures[0].severity == Severity.CRITICAL.value


# 10. Invalid ticker
def test_invalid_ticker():
    df = get_valid_df()
    df.loc[0, "ticker"] = "tcs"  # Lowercase (invalid under standard uppercase check)
    df.loc[1, "ticker"] = "INFY NS"  # Has space
    df.loc[2, "ticker"] = "A" * 15  # Length > 12
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
    )
    dq07_failures = [f for f in failures if f.rule_id == "DQ-07"]
    assert len(dq07_failures) == 3
    assert dq07_failures[0].row_number == 1
    assert dq07_failures[1].row_number == 2
    assert dq07_failures[2].row_number == 3
    assert dq07_failures[0].severity == Severity.CRITICAL.value


# 11. Invalid OPM
def test_invalid_opm():
    df = get_valid_df()
    df.loc[1, "opm"] = 1.5  # Outside [-1.0, 1.0] range
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
        opm_col="opm"
    )
    dq09_failures = [f for f in failures if f.rule_id == "DQ-09"]
    assert len(dq09_failures) == 1
    assert dq09_failures[0].row_number == 2
    assert dq09_failures[0].severity == Severity.WARNING.value


# 12. Balance mismatch
def test_balance_mismatch():
    df = get_valid_df()
    df.loc[1, "total_equity"] = 2000.0
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
        assets_col="total_assets",
        liabilities_col="total_liabilities",
        equity_col="total_equity"
    )
    dq10_failures = [f for f in failures if f.rule_id == "DQ-10"]
    assert len(dq10_failures) == 1
    assert dq10_failures[0].row_number == 2
    assert dq10_failures[0].severity == Severity.WARNING.value


# 13. Zero sales
def test_zero_sales():
    df = get_valid_df()
    df.loc[2, "sales"] = 0.0  # Zero sales
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
        sales_col="sales"
    )
    dq11_failures = [f for f in failures if f.rule_id == "DQ-11"]
    assert len(dq11_failures) == 1
    assert dq11_failures[0].row_number == 3
    assert dq11_failures[0].severity == Severity.WARNING.value


# 14. Negative profit
def test_negative_profit():
    df = get_valid_df()
    df.loc[0, "net_profit"] = -50.0  # Row 1 net profit negative
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
        net_profit_col="net_profit"
    )
    dq12_failures = [f for f in failures if f.rule_id == "DQ-12"]
    assert len(dq12_failures) == 1
    assert dq12_failures[0].row_number == 1
    assert dq12_failures[0].severity == Severity.WARNING.value


# 15. Negative assets
def test_negative_assets():
    df = get_valid_df()
    df.loc[2, "total_assets"] = -100.0  # Negative assets
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
        assets_col="total_assets"
    )
    dq13_failures = [f for f in failures if f.rule_id == "DQ-13"]
    assert len(dq13_failures) == 1
    assert dq13_failures[0].row_number == 3
    assert dq13_failures[0].severity == Severity.WARNING.value


# 16. Future year
def test_future_year():
    df = get_valid_df()
    df.loc[1, "year"] = 2030  # Future year (> 2026)
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
        current_year=2026
    )
    dq14_failures = [f for f in failures if f.rule_id == "DQ-14"]
    assert len(dq14_failures) == 1
    assert dq14_failures[0].row_number == 2
    assert dq14_failures[0].severity == Severity.WARNING.value


# 17. Missing sector
def test_missing_sector():
    df = get_valid_df()
    df.loc[0, "sector"] = ""  # Row 1 empty sector
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
        sector_col="sector"
    )
    dq15_failures = [f for f in failures if f.rule_id == "DQ-15"]
    assert len(dq15_failures) == 1
    assert dq15_failures[0].row_number == 1
    assert dq15_failures[0].severity == Severity.WARNING.value


# 18. Missing industry
def test_missing_industry():
    df = get_valid_df()
    df.loc[2, "industry"] = None  # Row 3 missing industry
    validator = DataValidator()
    failures = validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"],
        industry_col="industry"
    )
    dq16_failures = [f for f in failures if f.rule_id == "DQ-16"]
    assert len(dq16_failures) == 1
    assert dq16_failures[0].row_number == 3
    assert dq16_failures[0].severity == Severity.WARNING.value


# 19. Export CSV
def test_export_csv(tmp_path):
    df = get_valid_df()
    df.loc[0, "ticker"] = None  # Introduce failure
    validator = DataValidator()
    validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"]
    )
    output_file = tmp_path / "failures.csv"
    validator.export_failures(output_file)
    
    assert output_file.exists()
    
    # Read back and verify columns
    failures_df = pd.read_csv(output_file)
    expected_cols = [
        "Rule ID", "Severity", "Table Name", 
        "Row Number", "Column Name", "Failed Value", "Error Message"
    ]
    assert list(failures_df.columns) == expected_cols
    assert len(failures_df) > 0
    assert failures_df.loc[0, "Rule ID"] == "DQ-01"


# 20. No validation failures export
def test_no_validation_failures(tmp_path):
    df = get_valid_df()
    validator = DataValidator()
    validator.validate_dataset(
        df=df,
        table_name="financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker"]
    )
    output_file = tmp_path / "no_failures.csv"
    validator.export_failures(output_file)
    
    assert output_file.exists()
    failures_df = pd.read_csv(output_file)
    assert len(failures_df) == 0
    expected_cols = [
        "Rule ID", "Severity", "Table Name", 
        "Row Number", "Column Name", "Failed Value", "Error Message"
    ]
    assert list(failures_df.columns) == expected_cols


# 21. Standalone function test: check_pk_not_null
def test_standalone_pk_not_null():
    df = pd.DataFrame({"id": [1, None, 3]})
    failures = check_pk_not_null(df, "id", "test_table")
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-01"
    assert failures[0].row_number == 2


# 22. Standalone function test: check_duplicate_pks
def test_standalone_duplicate_pks():
    df = pd.DataFrame({"id": [1, 2, 2, 3]})
    failures = check_duplicate_pks(df, "id", "test_table")
    assert len(failures) == 2
    assert failures[0].rule_id == "DQ-02"
    assert failures[0].row_number == 2
    assert failures[1].row_number == 3


# 23. Standalone function test: check_foreign_key_violations
def test_standalone_fk_violations():
    df = pd.DataFrame({"fk": [10, 20, 30]})
    failures = check_foreign_key_violations(df, "fk", {10, 20}, "parent_table", "test_table")
    assert len(failures) == 1
    assert failures[0].rule_id == "DQ-03"
    assert failures[0].row_number == 3
    assert failures[0].failed_value == "30"
