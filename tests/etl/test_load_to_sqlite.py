"""Unit tests for the SQLite database loader and auditor.

Tests database loading, row count verification, audit report generation,
missing files, empty CSV files, and foreign key validation.
"""

import csv
import os
import sqlite3
import pytest
from typing import Generator

from scripts.etl.load_to_sqlite import load_all_data, read_csv


@pytest.fixture
def temp_workspace(tmp_path) -> Generator[dict, None, None]:
    """Sets up a temporary workspace with mock CSV files and SQL schema."""
    # Create directory structure
    db_dir = tmp_path / "data" / "db"
    db_dir.mkdir(parents=True, exist_ok=True)

    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    output_dir = tmp_path / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sql_dir = tmp_path / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)

    db_path = db_dir / "nifty100.db"
    schema_path = sql_dir / "schema.sql"
    audit_path = output_dir / "load_audit.csv"

    # Write a clean, simplified schema containing all 10 tables for testing
    schema_content = """
    PRAGMA foreign_keys = ON;
    
    DROP TABLE IF EXISTS stock_prices;
    DROP TABLE IF EXISTS sectors;
    DROP TABLE IF EXISTS peer_groups;
    DROP TABLE IF EXISTS market_cap;
    DROP TABLE IF EXISTS financial_ratios;
    DROP TABLE IF EXISTS analysis;
    DROP TABLE IF EXISTS cashflow;
    DROP TABLE IF EXISTS balancesheet;
    DROP TABLE IF EXISTS profitandloss;
    DROP TABLE IF EXISTS companies;
    
    CREATE TABLE companies (
        id TEXT PRIMARY KEY,
        company_logo TEXT,
        company_name TEXT,
        chart_link TEXT,
        about_company TEXT,
        website TEXT,
        nse_profile TEXT,
        bse_profile TEXT,
        face_value REAL,
        book_value REAL,
        roce_percentage REAL,
        roe_percentage REAL
    );
    
    CREATE TABLE profitandloss (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        year TEXT NOT NULL,
        sales REAL,
        expenses REAL,
        operating_profit REAL,
        opm_percentage REAL,
        other_income REAL,
        interest REAL,
        depreciation REAL,
        profit_before_tax REAL,
        tax_percentage REAL,
        net_profit REAL,
        eps REAL,
        dividend_payout REAL,
        FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
    );
    
    CREATE TABLE balancesheet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        year TEXT NOT NULL,
        equity_capital REAL,
        reserves REAL,
        borrowings REAL,
        other_liabilities REAL,
        total_liabilities REAL,
        fixed_assets REAL,
        cwip REAL,
        investments REAL,
        other_asset REAL,
        total_assets REAL,
        FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
    );
    
    CREATE TABLE cashflow (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        year TEXT NOT NULL,
        operating_activity REAL,
        investing_activity REAL,
        financing_activity REAL,
        net_cash_flow REAL,
        FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
    );
    
    CREATE TABLE analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        compounded_sales_growth TEXT,
        compounded_profit_growth TEXT,
        stock_price_cagr TEXT,
        roe TEXT,
        FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
    );
    
    CREATE TABLE financial_ratios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        year TEXT NOT NULL,
        net_profit_margin_pct REAL,
        operating_profit_margin_pct REAL,
        return_on_equity_pct REAL,
        debt_to_equity REAL,
        interest_coverage REAL,
        asset_turnover REAL,
        free_cash_flow_cr REAL,
        capex_cr REAL,
        earnings_per_share REAL,
        book_value_per_share REAL,
        dividend_payout_ratio_pct REAL,
        total_debt_cr REAL,
        cash_from_operations_cr REAL,
        FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
    );
    
    CREATE TABLE market_cap (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        year INTEGER NOT NULL,
        market_cap_crore REAL,
        enterprise_value_crore REAL,
        pe_ratio REAL,
        pb_ratio REAL,
        ev_ebitda REAL,
        dividend_yield_pct REAL,
        FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
    );
    
    CREATE TABLE peer_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peer_group_name TEXT NOT NULL,
        company_id TEXT NOT NULL,
        is_benchmark TEXT,
        FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
    );
    
    CREATE TABLE sectors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        broad_sector TEXT,
        sub_sector TEXT,
        index_weight_pct REAL,
        market_cap_category TEXT,
        FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
    );
    
    CREATE TABLE stock_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        date TEXT NOT NULL,
        open_price REAL,
        high_price REAL,
        low_price REAL,
        close_price REAL,
        volume INTEGER,
        adjusted_close REAL,
        FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
    );
    """
    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(schema_content)

    # Helper to write mock CSVs
    def write_csv_file(filename: str, content: str):
        filepath = processed_dir / filename
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    # Standard Mock CSV Content
    write_csv_file(
        "companies.csv",
        "id,company_name,face_value\n"
        "ABB,Abbott India Ltd,10.0\n"
        "TCS,Tata Consultancy Services,1.0\n",
    )

    write_csv_file(
        "profitandloss.csv",
        "id,company_id,year,sales,net_profit\n"
        "1,ABB,2024,1000.0,150.0\n"
        "2,TCS,2024,5000.0,900.0\n",
    )

    # Dummy content for other tables so the loader does not complain about missing files
    dummy_headers = "id,company_id,year\n"
    other_tables = [
        "balancesheet",
        "cashflow",
        "analysis",
        "financial_ratios",
        "market_cap",
        "peer_groups",
        "sectors",
        "stock_prices",
    ]
    for tbl in other_tables:
        if tbl == "stock_prices":
            write_csv_file(
                f"{tbl}.csv", "id,company_id,date,close_price\n1,ABB,2024-01-01,150.0\n"
            )
        elif tbl == "sectors":
            write_csv_file(
                f"{tbl}.csv", "id,company_id,broad_sector\n1,ABB,Industrials\n"
            )
        elif tbl == "peer_groups":
            write_csv_file(
                f"{tbl}.csv", "id,peer_group_name,company_id\n1,Private Banks,ABB\n"
            )
        else:
            write_csv_file(f"{tbl}.csv", dummy_headers + "1,ABB,2024\n")

    yield {
        "db_path": str(db_path),
        "schema_path": str(schema_path),
        "processed_dir": str(processed_dir),
        "audit_path": str(audit_path),
        "write_csv": write_csv_file,
    }


def test_successful_load(temp_workspace):
    """Tests loading the database successfully with valid datasets."""
    res = load_all_data(
        db_path=temp_workspace["db_path"],
        schema_path=temp_workspace["schema_path"],
        processed_dir=temp_workspace["processed_dir"],
        audit_output_path=temp_workspace["audit_path"],
    )
    assert res is True

    # Verify rows in database
    conn = sqlite3.connect(temp_workspace["db_path"])
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM companies")
    assert cursor.fetchone()[0] == 2

    cursor.execute("SELECT COUNT(*) FROM profitandloss")
    assert cursor.fetchone()[0] == 2
    conn.close()

    # Verify audit CSV was generated and is valid
    assert os.path.exists(temp_workspace["audit_path"])
    with open(temp_workspace["audit_path"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)
        assert len(records) == 10
        # Check specific table status
        comp_rec = next(r for r in records if r["table_name"] == "companies")
        assert comp_rec["row_count"] == "2"
        assert comp_rec["load_status"] == "Success"


def test_row_counts_verification(temp_workspace):
    """Tests that the row counts verify correctly against CSV records."""
    # Write a new profitandloss CSV with 3 rows
    temp_workspace["write_csv"](
        "profitandloss.csv",
        "id,company_id,year,sales,net_profit\n"
        "1,ABB,2024,1000.0,150.0\n"
        "2,TCS,2024,5000.0,900.0\n"
        "3,TCS,2023,4500.0,800.0\n",
    )

    res = load_all_data(
        db_path=temp_workspace["db_path"],
        schema_path=temp_workspace["schema_path"],
        processed_dir=temp_workspace["processed_dir"],
        audit_output_path=temp_workspace["audit_path"],
    )
    assert res is True

    # Verify count in database is 3
    conn = sqlite3.connect(temp_workspace["db_path"])
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM profitandloss")
    assert cursor.fetchone()[0] == 3
    conn.close()


def test_missing_csv_file(temp_workspace):
    """Tests behavior when one of the CSV files is missing."""
    # Remove a CSV file
    os.remove(os.path.join(temp_workspace["processed_dir"], "profitandloss.csv"))

    res = load_all_data(
        db_path=temp_workspace["db_path"],
        schema_path=temp_workspace["schema_path"],
        processed_dir=temp_workspace["processed_dir"],
        audit_output_path=temp_workspace["audit_path"],
    )
    assert res is False

    # Check audit log contains Failure status for profitandloss
    with open(temp_workspace["audit_path"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)
        pl_rec = next(r for r in records if r["table_name"] == "profitandloss")
        assert "Failed" in pl_rec["load_status"]


def test_empty_csv_file(temp_workspace):
    """Tests loading with an empty CSV file or CSV containing only headers."""
    # Write profitandloss.csv with only headers
    temp_workspace["write_csv"](
        "profitandloss.csv", "id,company_id,year,sales,net_profit\n"
    )

    res = load_all_data(
        db_path=temp_workspace["db_path"],
        schema_path=temp_workspace["schema_path"],
        processed_dir=temp_workspace["processed_dir"],
        audit_output_path=temp_workspace["audit_path"],
    )
    # Loading empty child table is valid
    assert res is True

    conn = sqlite3.connect(temp_workspace["db_path"])
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM profitandloss")
    assert cursor.fetchone()[0] == 0
    conn.close()

    # Audit log should show 0 rows
    with open(temp_workspace["audit_path"], "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)
        pl_rec = next(r for r in records if r["table_name"] == "profitandloss")
        assert pl_rec["row_count"] == "0"
        assert pl_rec["load_status"] == "Success"


def test_foreign_key_validation(temp_workspace):
    """Tests that SQLite triggers and catches Foreign Key constraint violations."""
    # Load valid data first
    load_all_data(
        db_path=temp_workspace["db_path"],
        schema_path=temp_workspace["schema_path"],
        processed_dir=temp_workspace["processed_dir"],
        audit_output_path=temp_workspace["audit_path"],
    )

    # 1. Test standard FK enforcement on direct insertion with a connection
    # containing active FK check
    conn_enforced = sqlite3.connect(temp_workspace["db_path"])
    conn_enforced.execute("PRAGMA foreign_keys = ON;")
    with pytest.raises(sqlite3.IntegrityError):
        conn_enforced.execute(
            "INSERT INTO profitandloss (company_id, year, sales) "
            "VALUES ('INVALID_TICKER', '2024', 500)"
        )
    conn_enforced.close()

    # 2. Test manual insertion with FK check disabled, then running validation check.
    # Set isolation_level=None to ensure auto-commit (no active transaction blocks pragma change)
    conn_bypass = sqlite3.connect(temp_workspace["db_path"], isolation_level=None)
    conn_bypass.execute("PRAGMA foreign_keys = OFF;")
    conn_bypass.execute(
        "INSERT INTO profitandloss (company_id, year, sales) "
        "VALUES ('INVALID_TICKER', '2024', 500)"
    )
    conn_bypass.close()

    # Open connection again to verify foreign_key_check catches it
    conn_check = sqlite3.connect(temp_workspace["db_path"])
    cursor = conn_check.cursor()
    cursor.execute("PRAGMA foreign_key_check;")
    violations = cursor.fetchall()

    # Verify that a violation is detected
    assert len(violations) > 0
    # violation tuple format: (table_name, rowid, parent_table, fkid)
    assert violations[0][0] == "profitandloss"
    assert violations[0][2] == "companies"
    conn_check.close()


def test_read_csv_header_skipping(temp_workspace):
    """Tests that read_csv correctly detects and skips title headers."""
    # Write a CSV with a title comment on line 1
    temp_workspace["write_csv"](
        "companies.csv",
        "Bluestock Fintech - Companies Title,Unnamed: 1,Unnamed: 2\n"
        "id,company_name,face_value\n"
        "ABB,Abbott India Ltd,10.0\n",
    )

    headers, rows = read_csv(
        os.path.join(temp_workspace["processed_dir"], "companies.csv")
    )
    assert headers == ["id", "company_name", "face_value"]
    assert len(rows) == 1
    assert rows[0] == ["ABB", "Abbott India Ltd", "10.0"]
