"""Python script to execute database data quality audit checks.

Performs verification of row counts, year-wise data coverage, checks for missing,
duplicate, invalid, or negative values, and verifies foreign key integrity.
"""

import os
import sqlite3
import pandas as pd

# Constants matching workspace structure
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(WORKSPACE_DIR, "data", "db", "nifty100.db")


def run_query(conn, query, title):
    """Executes a SQL query and prints it formatted as a pandas DataFrame."""
    print("=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)
    try:
        df = pd.read_sql_query(query, conn)
        if df.empty:
            print("No issues or records found.")
        else:
            print(df.to_string(index=False))
    except Exception as e:
        print(f"Error executing query: {e}")
    print("\n")


def run_audit():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Please run the ETL pipeline first.")
        return

    print("Connecting to database:", DB_PATH)
    conn = sqlite3.connect(DB_PATH)

    try:
        # 1. Random 5 companies
        run_query(
            conn,
            "SELECT id AS ticker, company_name, website, roce_percentage, roe_percentage FROM companies ORDER BY RANDOM() LIMIT 5;",
            "1. Randomly Selected 5 Companies"
        )

        # 2. Year-wise coverage
        print("=" * 80)
        print(" 2. YEAR-WISE DATA COVERAGE")
        print("=" * 80)
        
        tables_coverage = {
            "Profit & Loss": "SELECT year, COUNT(*) AS pl_record_count FROM profitandloss GROUP BY year ORDER BY year;",
            "Balance Sheet": "SELECT year, COUNT(*) AS bs_record_count FROM balancesheet GROUP BY year ORDER BY year;",
            "Cash Flow": "SELECT year, COUNT(*) AS cf_record_count FROM cashflow GROUP BY year ORDER BY year;",
            "Stock Prices (Yearly)": "SELECT SUBSTR(date, 1, 4) AS year, COUNT(*) AS stock_record_count FROM stock_prices GROUP BY year ORDER BY year;"
        }
        for name, query in tables_coverage.items():
            print(f"--- {name} ---")
            df = pd.read_sql_query(query, conn)
            print(df.to_string(index=False))
            print()

        # 3. Companies with < 5 years of financial data
        query_low_data = """
        SELECT c.id AS ticker, c.company_name,
               COALESCE(pl.cnt, 0) AS pl_years,
               COALESCE(bs.cnt, 0) AS bs_years,
               COALESCE(cf.cnt, 0) AS cf_years
        FROM companies c
        LEFT JOIN (SELECT company_id, COUNT(DISTINCT year) AS cnt FROM profitandloss WHERE year != 'TTM' GROUP BY company_id) pl ON c.id = pl.company_id
        LEFT JOIN (SELECT company_id, COUNT(DISTINCT year) AS cnt FROM balancesheet GROUP BY company_id) bs ON c.id = bs.company_id
        LEFT JOIN (SELECT company_id, COUNT(DISTINCT year) AS cnt FROM cashflow GROUP BY company_id) cf ON c.id = cf.company_id
        WHERE pl_years < 5 OR bs_years < 5 OR cf_years < 5
        ORDER BY ticker;
        """
        run_query(
            conn,
            query_low_data,
            "3. Companies with Fewer than 5 Years of Financial Data"
        )

        # 4a. Missing values (NULL or empty string)
        query_missing = """
        SELECT 'companies' AS table_name, 'face_value' AS col_name, COUNT(*) AS null_count FROM companies WHERE face_value IS NULL OR face_value = ''
        UNION ALL
        SELECT 'profitandloss', 'sales', COUNT(*) FROM profitandloss WHERE sales IS NULL
        UNION ALL
        SELECT 'profitandloss', 'net_profit', COUNT(*) FROM profitandloss WHERE net_profit IS NULL
        UNION ALL
        SELECT 'balancesheet', 'total_assets', COUNT(*) FROM balancesheet WHERE total_assets IS NULL
        UNION ALL
        SELECT 'balancesheet', 'total_liabilities', COUNT(*) FROM balancesheet WHERE total_liabilities IS NULL
        UNION ALL
        SELECT 'cashflow', 'net_cash_flow', COUNT(*) FROM cashflow WHERE net_cash_flow IS NULL
        UNION ALL
        SELECT 'stock_prices', 'close_price', COUNT(*) FROM stock_prices WHERE close_price IS NULL;
        """
        run_query(
            conn,
            query_missing,
            "4a. Missing Values Check (NULL / Empty)"
        )

        # 4b. Duplicate records
        query_duplicates = """
        SELECT 'profitandloss' AS table_name, company_id, year AS key_value, COUNT(*) AS occurrence_count
        FROM profitandloss GROUP BY company_id, year HAVING COUNT(*) > 1
        UNION ALL
        SELECT 'balancesheet', company_id, year, COUNT(*) FROM balancesheet GROUP BY company_id, year HAVING COUNT(*) > 1
        UNION ALL
        SELECT 'cashflow', company_id, year, COUNT(*) FROM cashflow GROUP BY company_id, year HAVING COUNT(*) > 1
        UNION ALL
        SELECT 'stock_prices', company_id, date, COUNT(*) FROM stock_prices GROUP BY company_id, date HAVING COUNT(*) > 1;
        """
        run_query(
            conn,
            query_duplicates,
            "4b. Duplicate Records Check on Ticker + Year/Date"
        )

        # 4c. Invalid years
        query_invalid_years = """
        SELECT 'profitandloss' AS table_name, company_id, year, COUNT(*) AS occurrence_count
        FROM profitandloss WHERE year NOT GLOB '[12][09][0-9][0-9]' AND year != 'TTM' GROUP BY company_id, year
        UNION ALL
        SELECT 'balancesheet', company_id, year, COUNT(*) FROM balancesheet WHERE year NOT GLOB '[12][09][0-9][0-9]' AND year != 'TTM' GROUP BY company_id, year
        UNION ALL
        SELECT 'cashflow', company_id, year, COUNT(*) FROM cashflow WHERE year NOT GLOB '[12][09][0-9][0-9]' AND year != 'TTM' GROUP BY company_id, year
        UNION ALL
        SELECT 'financial_ratios', company_id, year, COUNT(*) FROM financial_ratios WHERE year NOT GLOB '[12][09][0-9][0-9]' AND year != 'TTM' GROUP BY company_id, year;
        """
        run_query(
            conn,
            query_invalid_years,
            "4c. Invalid Years Check (Non-standard Years / Non-TTM)"
        )

        # 4d. Negative financial values
        query_negative = """
        SELECT 'profitandloss' AS table_name, 'sales' AS col_name, company_id, year, sales AS value FROM profitandloss WHERE sales < 0
        UNION ALL
        SELECT 'profitandloss', 'expenses', company_id, year, expenses FROM profitandloss WHERE expenses < 0
        UNION ALL
        SELECT 'balancesheet', 'total_assets', company_id, year, total_assets FROM balancesheet WHERE total_assets < 0
        UNION ALL
        SELECT 'balancesheet', 'total_liabilities', company_id, year, total_liabilities FROM balancesheet WHERE total_liabilities < 0;
        """
        run_query(
            conn,
            query_negative,
            "4d. Negative Values in Columns That Should Strictly Be Positive"
        )

        # 5. Foreign Key Check
        print("=" * 80)
        print(" 5. FOREIGN KEY INTEGRITY CHECK")
        print("=" * 80)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_key_check;")
        violations = cursor.fetchall()
        if violations:
            print(f"Found {len(violations)} foreign key violations!")
            for v in violations:
                print(f"Table: {v[0]}, RowID: {v[1]}, Parent Table: {v[2]}, FKey Index: {v[3]}")
        else:
            print("Foreign Key Integrity: OK (0 violations found).")
        print("\n")

        # 6. Database Row Counts
        query_row_counts = """
        SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
        UNION ALL
        SELECT 'profitandloss', COUNT(*) FROM profitandloss
        UNION ALL
        SELECT 'balancesheet', COUNT(*) FROM balancesheet
        UNION ALL
        SELECT 'cashflow', COUNT(*) FROM cashflow
        UNION ALL
        SELECT 'analysis', COUNT(*) FROM analysis
        UNION ALL
        SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
        UNION ALL
        SELECT 'market_cap', COUNT(*) FROM market_cap
        UNION ALL
        SELECT 'peer_groups', COUNT(*) FROM peer_groups
        UNION ALL
        SELECT 'sectors', COUNT(*) FROM sectors
        UNION ALL
        SELECT 'stock_prices', COUNT(*) FROM stock_prices;
        """
        run_query(
            conn,
            query_row_counts,
            "6. SQLite Database Table Row Counts"
        )

    except Exception as e:
        print(f"An error occurred during audit execution: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    run_audit()
