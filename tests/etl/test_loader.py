"""
Unit tests for ETL loader functionality.

Covers 10 unit tests verifying reading source files, row count calculation,
column header parsing, missing file handling, empty file detection,
format/delimiter handling, duplicate PK checking, data type preservation,
SQLite database loading, and audit log generation.
"""

import sqlite3
import pandas as pd
import pytest

from scripts.etl.loader import validate_dataframe
from scripts.etl.load_to_sqlite import (
    read_csv,
    clean_val,
    generate_audit_csv,
    load_all_data,
)
from scripts.etl.validator import check_duplicate_pks


def test_loader_reads_source_file_successfully(tmp_path):
    """1. Verify reading source file successfully."""
    csv_file = tmp_path / "companies.csv"
    csv_file.write_text(
        "id,company_name\nTCS,Tata Consultancy Services\nINFY,Infosys\n",
        encoding="utf-8",
    )
    headers, rows = read_csv(str(csv_file))
    assert headers == ["id", "company_name"]
    assert len(rows) == 2


def test_loader_produces_correct_row_count(tmp_path):
    """2. Verify loader produces correct row count."""
    csv_file = tmp_path / "test_data.csv"
    data_lines = ["id,val"] + [f"ID_{i},{i}" for i in range(15)]
    csv_file.write_text("\n".join(data_lines) + "\n", encoding="utf-8")
    headers, rows = read_csv(str(csv_file))
    assert len(rows) == 15


def test_loader_produces_expected_column_names(tmp_path):
    """3. Verify expected column names are extracted and stripped."""
    csv_file = tmp_path / "test_cols.csv"
    csv_file.write_text(" id , company_id , sales \n1,TCS,100\n", encoding="utf-8")
    headers, rows = read_csv(str(csv_file))
    assert headers == ["id", "company_id", "sales"]


def test_loader_handles_missing_files_gracefully(tmp_path):
    """4. Verify missing files raise FileNotFoundError gracefully."""
    missing_file = tmp_path / "non_existent.csv"
    with pytest.raises(FileNotFoundError):
        read_csv(str(missing_file))


def test_loader_detects_empty_files(tmp_path):
    """5. Verify detection of empty files / DataFrames."""
    empty_df = pd.DataFrame()
    with pytest.raises(ValueError, match="empty"):
        validate_dataframe(empty_df)

    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("", encoding="utf-8")
    headers, rows = read_csv(str(empty_csv))
    assert headers == []
    assert rows == []


def test_loader_handles_incorrect_formats(tmp_path):
    """6. Verify handling of title headers/comments before actual CSV headers."""
    csv_file = tmp_path / "title_header.csv"
    csv_file.write_text(
        "Nifty100 Title Line\nid,company_name\nTCS,Tata Consultancy\n", encoding="utf-8"
    )
    headers, rows = read_csv(str(csv_file))
    assert headers == ["id", "company_name"]
    assert len(rows) == 1
    assert rows[0] == ["TCS", "Tata Consultancy"]


def test_loader_rejects_duplicate_primary_keys():
    """7. Verify primary key duplication checking."""
    df_dup = pd.DataFrame(
        {"id": ["TCS", "TCS", "INFY"], "company_name": ["Tata", "Tata Corp", "Infosys"]}
    )
    failures = check_duplicate_pks(df_dup, "id", "companies")
    assert len(failures) > 0
    assert failures[0].rule_id == "DQ-02"


def test_loader_preserves_expected_data_types():
    """8. Verify data type conversion and cleanup for schema loading."""
    assert clean_val(" 1500.50 ", "sales", "profitandloss") == 1500.50
    assert clean_val("2021", "year", "profitandloss") == "2021"
    assert clean_val("N/A", "sales", "profitandloss") is None
    assert clean_val("NaN", "expenses", "profitandloss") is None
    assert clean_val("", "net_profit", "profitandloss") is None


def test_loader_loads_data_into_correct_sqlite_tables(tmp_path):
    """9. Verify loading data into correct SQLite database tables."""
    db_path = tmp_path / "test.db"
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    audit_path = tmp_path / "audit.csv"

    # Create dummy schema
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text(
        "CREATE TABLE companies (id TEXT PRIMARY KEY, company_name TEXT);\n"
        "CREATE TABLE profitandloss (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT, year TEXT, sales REAL);\n"
        "CREATE TABLE balancesheet (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT, year TEXT);\n"
        "CREATE TABLE cashflow (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT, year TEXT);\n"
        "CREATE TABLE analysis (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT);\n"
        "CREATE TABLE financial_ratios (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT, year TEXT);\n"
        "CREATE TABLE market_cap (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT, year INTEGER);\n"
        "CREATE TABLE peer_groups (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT);\n"
        "CREATE TABLE sectors (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT);\n"
        "CREATE TABLE stock_prices (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT);\n",
        encoding="utf-8",
    )

    # Populate processed CSVs
    (processed_dir / "companies.csv").write_text(
        "id,company_name\nTCS,Tata Consultancy\n", encoding="utf-8"
    )
    (processed_dir / "profitandloss.csv").write_text(
        "id,company_id,year,sales\n1,TCS,2021,1000.0\n", encoding="utf-8"
    )
    for tbl in [
        "balancesheet",
        "cashflow",
        "analysis",
        "financial_ratios",
        "market_cap",
        "peer_groups",
        "sectors",
        "stock_prices",
    ]:
        (processed_dir / f"{tbl}.csv").write_text(
            "id,company_id\n1,TCS\n", encoding="utf-8"
        )

    success = load_all_data(
        db_path=str(db_path),
        schema_path=str(schema_path),
        processed_dir=str(processed_dir),
        audit_output_path=str(audit_path),
    )

    assert success is True
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT company_name FROM companies WHERE id='TCS';")
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "Tata Consultancy"


def test_loader_produces_expected_audit_information(tmp_path):
    """10. Verify audit information CSV generation."""
    audit_file = tmp_path / "audit_test.csv"
    records = [
        {
            "table_name": "companies",
            "source_file": "companies.csv",
            "row_count": 100,
            "load_status": "Success",
        },
        {
            "table_name": "profitandloss",
            "source_file": "profitandloss.csv",
            "row_count": 500,
            "load_status": "Success",
        },
    ]
    generate_audit_csv(str(audit_file), records)
    assert audit_file.exists()
    audit_df = pd.read_csv(audit_file)
    assert len(audit_df) == 2
    assert "table_name" in audit_df.columns
    assert audit_df.iloc[0]["table_name"] == "companies"
    assert audit_df.iloc[0]["row_count"] == 100
