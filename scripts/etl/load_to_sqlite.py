"""Script to load processed CSV files into a SQLite database.

This script executes the SQL schema, reads processed CSV data from data/processed,
cleans the data, ensures referential integrity by adding stub records for missing
companies, inserts all records into the respective SQLite tables, verifies row
counts, checks for foreign key violations, and outputs an audit log.
"""

import csv
import logging
import os
import sqlite3
import sys
from typing import Any, Dict, List, Set, Tuple

# Set up logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("load_to_sqlite")

# Constants matching folder structure
WORKSPACE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
DB_PATH = os.path.join(WORKSPACE_DIR, "data", "db", "nifty100.db")
SCHEMA_PATH = os.path.join(WORKSPACE_DIR, "sql", "schema.sql")
PROCESSED_DIR = os.path.join(WORKSPACE_DIR, "data", "processed")
AUDIT_OUTPUT_PATH = os.path.join(
    WORKSPACE_DIR, "data", "output", "load_audit.csv"
)

# Define schemas for each table to handle type conversions
TABLE_SCHEMAS: Dict[str, Dict[str, str]] = {
    "companies": {
        "id": "TEXT",
        "company_logo": "TEXT",
        "company_name": "TEXT",
        "chart_link": "TEXT",
        "about_company": "TEXT",
        "website": "TEXT",
        "nse_profile": "TEXT",
        "bse_profile": "TEXT",
        "face_value": "REAL",
        "book_value": "REAL",
        "roce_percentage": "REAL",
        "roe_percentage": "REAL",
    },
    "profitandloss": {
        "id": "INTEGER",
        "company_id": "TEXT",
        "year": "TEXT",
        "sales": "REAL",
        "expenses": "REAL",
        "operating_profit": "REAL",
        "opm_percentage": "REAL",
        "other_income": "REAL",
        "interest": "REAL",
        "depreciation": "REAL",
        "profit_before_tax": "REAL",
        "tax_percentage": "REAL",
        "net_profit": "REAL",
        "eps": "REAL",
        "dividend_payout": "REAL",
    },
    "balancesheet": {
        "id": "INTEGER",
        "company_id": "TEXT",
        "year": "TEXT",
        "equity_capital": "REAL",
        "reserves": "REAL",
        "borrowings": "REAL",
        "other_liabilities": "REAL",
        "total_liabilities": "REAL",
        "fixed_assets": "REAL",
        "cwip": "REAL",
        "investments": "REAL",
        "other_asset": "REAL",
        "total_assets": "REAL",
    },
    "cashflow": {
        "id": "INTEGER",
        "company_id": "TEXT",
        "year": "TEXT",
        "operating_activity": "REAL",
        "investing_activity": "REAL",
        "financing_activity": "REAL",
        "net_cash_flow": "REAL",
    },
    "analysis": {
        "id": "INTEGER",
        "company_id": "TEXT",
        "compounded_sales_growth": "TEXT",
        "compounded_profit_growth": "TEXT",
        "stock_price_cagr": "TEXT",
        "roe": "TEXT",
    },
    "financial_ratios": {
        "id": "INTEGER",
        "company_id": "TEXT",
        "year": "TEXT",
        "net_profit_margin_pct": "REAL",
        "operating_profit_margin_pct": "REAL",
        "return_on_equity_pct": "REAL",
        "debt_to_equity": "REAL",
        "interest_coverage": "REAL",
        "asset_turnover": "REAL",
        "free_cash_flow_cr": "REAL",
        "capex_cr": "REAL",
        "earnings_per_share": "REAL",
        "book_value_per_share": "REAL",
        "dividend_payout_ratio_pct": "REAL",
        "total_debt_cr": "REAL",
        "cash_from_operations_cr": "REAL",
    },
    "market_cap": {
        "id": "INTEGER",
        "company_id": "TEXT",
        "year": "INTEGER",
        "market_cap_crore": "REAL",
        "enterprise_value_crore": "REAL",
        "pe_ratio": "REAL",
        "pb_ratio": "REAL",
        "ev_ebitda": "REAL",
        "dividend_yield_pct": "REAL",
    },
    "peer_groups": {
        "id": "INTEGER",
        "peer_group_name": "TEXT",
        "company_id": "TEXT",
        "is_benchmark": "TEXT",
    },
    "sectors": {
        "id": "INTEGER",
        "company_id": "TEXT",
        "broad_sector": "TEXT",
        "sub_sector": "TEXT",
        "index_weight_pct": "REAL",
        "market_cap_category": "TEXT",
    },
    "stock_prices": {
        "id": "INTEGER",
        "company_id": "TEXT",
        "date": "TEXT",
        "open_price": "REAL",
        "high_price": "REAL",
        "low_price": "REAL",
        "close_price": "REAL",
        "volume": "INTEGER",
        "adjusted_close": "REAL",
    },
}


def clean_val(val: str, col_name: str, table_name: str) -> Any:
    """Cleans and converts raw string values based on schema definitions.

    Converts empty fields, 'nan', 'none', and 'n/a' to Python None (NULL in SQL).
    Converts numbers to floats or integers as specified in the schema.
    """
    val = val.strip()
    if val == "" or val.lower() in ("nan", "none", "null", "n/a"):
        return None

    col_type = TABLE_SCHEMAS[table_name].get(col_name, "TEXT")
    if col_type == "INTEGER":
        try:
            return int(float(val))
        except ValueError:
            return None
    elif col_type == "REAL":
        try:
            return float(val)
        except ValueError:
            return None
    return val


def read_csv(filepath: str) -> Tuple[List[str], List[List[str]]]:
    """Reads a CSV file, automatically skipping any title/comment header if present.

    Detects if the first line starts with 'id', using it as header. If not, it skips
    the first line and uses the second line as the header.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            first_row = next(reader)
        except StopIteration:
            return [], []

        first_col = first_row[0].strip() if first_row else ""
        if first_col == "id":
            # First row is the header
            headers = [h.strip() for h in first_row]
            rows = [[cell.strip() for cell in row] for row in reader if row]
        else:
            # First row is a comment/title, second row is the header
            try:
                second_row = next(reader)
                headers = [h.strip() for h in second_row]
                rows = [[cell.strip() for cell in row] for row in reader if row]
            except StopIteration:
                return [], []

    return headers, rows


def generate_audit_csv(
    audit_path: str, audit_records: List[Dict[str, Any]]
) -> None:
    """Writes the database load audit details into a CSV file."""
    audit_dir = os.path.dirname(audit_path)
    if audit_dir and not os.path.exists(audit_dir):
        os.makedirs(audit_dir, exist_ok=True)

    headers = ["table_name", "source_file", "row_count", "load_status"]
    with open(audit_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for rec in audit_records:
            writer.writerow(
                {
                    "table_name": rec.get("table_name", ""),
                    "source_file": rec.get("source_file", ""),
                    "row_count": rec.get("row_count", 0),
                    "load_status": rec.get("load_status", ""),
                }
            )
    logger.info(f"Generated audit report at: {audit_path}")


def load_all_data(
    db_path: str = DB_PATH,
    schema_path: str = SCHEMA_PATH,
    processed_dir: str = PROCESSED_DIR,
    audit_output_path: str = AUDIT_OUTPUT_PATH,
) -> bool:
    """Executes schema creation and loads all processed CSV files into the database.

    Returns:
        True if all files loaded and verified successfully, False otherwise.
    """
    logger.info("=" * 60)
    logger.info("Starting ETL Pipeline: SQLite Loader & Auditor")
    logger.info("=" * 60)

    # Create directory for database if it doesn't exist
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created database directory: {db_dir}")

    tables_to_load = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "financial_ratios",
        "market_cap",
        "peer_groups",
        "sectors",
        "stock_prices",
    ]

    csv_data: Dict[str, Tuple[List[str], List[List[str]]]] = {}
    all_referenced_company_ids: Set[str] = set()
    audit_records: List[Dict[str, Any]] = []
    has_errors = False

    # 1. Read all CSVs first
    logger.info("Reading and parsing CSV files...")
    for table in tables_to_load:
        csv_filename = f"{table}.csv"
        csv_path = os.path.join(processed_dir, csv_filename)
        try:
            headers, rows = read_csv(csv_path)
            csv_data[table] = (headers, rows)
            logger.info(f"  - Parsed {csv_filename} ({len(rows)} rows)")

            # If not companies, collect referenced company IDs to ensure FK validation
            if table != "companies" and "company_id" in headers:
                c_idx = headers.index("company_id")
                for r in rows:
                    if len(r) > c_idx and r[c_idx]:
                        all_referenced_company_ids.add(r[c_idx])
        except Exception as e:
            logger.error(f"Failed reading CSV file {csv_filename}: {e}")
            audit_records.append(
                {
                    "table_name": table,
                    "source_file": csv_filename,
                    "row_count": 0,
                    "load_status": f"Failed: File Read Error - {e}",
                }
            )
            has_errors = True

    if has_errors:
        generate_audit_csv(audit_output_path, audit_records)
        logger.error("ETL process aborted due to file read errors.")
        return False

    # 2. Check referential integrity and inject stubs if necessary
    comp_headers, comp_rows = csv_data["companies"]
    if "id" not in comp_headers:
        logger.error("companies.csv must contain an 'id' column.")
        return False
    comp_id_idx = comp_headers.index("id")
    existing_company_ids = {
        r[comp_id_idx] for r in comp_rows if len(r) > comp_id_idx
    }

    # Identify missing companies that need stub records
    missing_company_ids = all_referenced_company_ids - existing_company_ids
    if missing_company_ids:
        logger.warning(
            f"Identified {len(missing_company_ids)} missing companies in financial tables: {sorted(list(missing_company_ids))}"
        )
        logger.warning("Generating stub profiles in companies table to enforce foreign keys.")

        for missing_id in sorted(list(missing_company_ids)):
            stub_row = ["" for _ in comp_headers]
            stub_row[comp_id_idx] = missing_id
            if "company_name" in comp_headers:
                name_idx = comp_headers.index("company_name")
                stub_row[name_idx] = f"{missing_id} (Stub)"
            comp_rows.append(stub_row)

    # 3. Connect to database and execute schema.sql
    logger.info(f"Connecting to SQLite database: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        # Enable foreign key support before executing schema or loading data
        conn.execute("PRAGMA foreign_keys = ON;")

        # Read and execute schema
        if not os.path.exists(schema_path):
            raise FileNotFoundError(
                f"Schema file not found at: {schema_path}"
            )

        with open(schema_path, "r", encoding="utf-8") as sf:
            schema_sql = sf.read()

        conn.executescript(schema_sql)
        logger.info("Schema initialization (schema.sql) executed successfully.")

        # 4. Insert data for each table in order (companies first)
        for table in tables_to_load:
            csv_filename = f"{table}.csv"
            headers, rows = csv_data[table]
            if not headers:
                logger.warning(f"No headers found for table '{table}', skipping.")
                audit_records.append(
                    {
                        "table_name": table,
                        "source_file": csv_filename,
                        "row_count": 0,
                        "load_status": "Skipped: Empty CSV File",
                    }
                )
                continue

            table_schema = TABLE_SCHEMAS[table]
            clean_headers = []
            col_indices = []
            for idx, col in enumerate(headers):
                if col in table_schema:
                    clean_headers.append(col)
                    col_indices.append(idx)

            if not clean_headers:
                logger.warning(f"No columns matched schema for table '{table}', skipping.")
                audit_records.append(
                    {
                        "table_name": table,
                        "source_file": csv_filename,
                        "row_count": 0,
                        "load_status": "Skipped: No column matches",
                    }
                )
                continue

            # Prepare insert statement
            columns_str = ", ".join(clean_headers)
            placeholders = ", ".join(["?"] * len(clean_headers))
            insert_query = (
                f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
            )

            # Clean and prepare values
            records_to_insert = []
            for r in rows:
                if len(r) < len(headers):
                    r = r + [""] * (len(headers) - len(r))

                cleaned_row = []
                for idx in col_indices:
                    cleaned_row.append(clean_val(r[idx], headers[idx], table))
                records_to_insert.append(cleaned_row)

            # Perform bulk insert
            cursor = conn.cursor()
            cursor.executemany(insert_query, records_to_insert)
            conn.commit()

            # 5. Verification check: Verify SQLite row counts match expected count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            db_count = cursor.fetchone()[0]

            if db_count == len(records_to_insert):
                load_status = "Success"
                logger.info(f"Loaded and verified {db_count} records into table '{table}'.")
            else:
                load_status = f"Mismatch: CSV={len(records_to_insert)}, DB={db_count}"
                logger.error(f"Row count mismatch in table '{table}': CSV has {len(records_to_insert)} rows, SQLite has {db_count} rows.")
                has_errors = True

            audit_records.append(
                {
                    "table_name": table,
                    "source_file": csv_filename,
                    "row_count": db_count,
                    "load_status": load_status,
                }
            )

        # 6. Run foreign key validation check
        logger.info("Executing database Foreign Key validation check...")
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = cursor.fetchall()
        if fk_violations:
            logger.error(f"Foreign Key validation failed! Found {len(fk_violations)} violations.")
            for violation in fk_violations[:5]:
                logger.error(f"  Violation in table '{violation[0]}' (rowid={violation[1]}) referencing parent table '{violation[2]}' (fkid={violation[3]})")
            raise sqlite3.IntegrityError(f"Foreign Key check failed with {len(fk_violations)} violations.")
        else:
            logger.info("Foreign Key validation succeeded: Zero violations found.")

    except Exception as e:
        conn.rollback()
        logger.fatal(f"Database loading transaction aborted: {e}")
        # Mark remaining tables as failed in audit
        for table in tables_to_load:
            if not any(r["table_name"] == table for r in audit_records):
                audit_records.append(
                    {
                        "table_name": table,
                        "source_file": f"{table}.csv",
                        "row_count": 0,
                        "load_status": f"Failed: Database Error - {e}",
                    }
                )
        generate_audit_csv(audit_output_path, audit_records)
        return False
    finally:
        conn.close()
        logger.info("Database connection closed.")

    # 7. Write load audit file
    generate_audit_csv(audit_output_path, audit_records)

    # 8. Print loading summary table in console
    print("\n" + "=" * 80)
    print(f"{'DATABASE LOADING SUMMARY':^80}")
    print("=" * 80)
    print(f" {'Table Name':<20} | {'Source CSV File':<20} | {'Row Count':<10} | {'Load Status':<20}")
    print("-" * 80)
    for rec in audit_records:
        print(f" {rec['table_name']:<20} | {rec['source_file']:<20} | {rec['row_count']:<10} | {rec['load_status']:<20}")
    print("=" * 80 + "\n")

    return not has_errors


if __name__ == "__main__":
    success = load_all_data()
    sys.exit(0 if success else 1)
