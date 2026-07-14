"""
Verification script for financial_ratios table.

Prints:
- Total rows
- Missing values count per column
- Duplicate records (based on company_id, year)
- Sample output (first 5 rows)
"""

import sqlite3
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_FILE = PROJECT_ROOT / "data" / "db" / "nifty100.db"


def main():
    print(f"Connecting to database at {DB_FILE}...")
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # Load table into pandas DataFrame
        df = pd.read_sql_query("SELECT * FROM financial_ratios", conn)
        
        print("\n--- DATABASE VERIFICATION SUMMARY ---")
        
        # 1. Total Rows
        total_rows = len(df)
        print(f"Total Rows: {total_rows}")
        
        # 2. Missing Values per column
        print("\n--- Missing Values Count per Column ---")
        missing_counts = df.isnull().sum()
        for col, count in missing_counts.items():
            pct = (count / total_rows) * 100 if total_rows > 0 else 0
            print(f"  {col:30} : {count:5} ({pct:6.2f}%)")
            
        # 3. Duplicate Records
        print("\n--- Duplicate Records Check (by company_id and year) ---")
        # Find duplicates
        duplicates = df[df.duplicated(subset=["company_id", "year"], keep=False)]
        total_duplicates = len(df[df.duplicated(subset=["company_id", "year"])])
        print(f"Total duplicate key records: {total_duplicates}")
        if total_duplicates > 0:
            print("\nSample of duplicate records:")
            print(duplicates[["id", "company_id", "year", "net_profit_margin_pct", "cash_from_operations_cr"]].head(10).to_string())
            
        # 4. Sample Output
        print("\n--- Sample Output (First 5 Rows) ---")
        cols_to_show = [
            "company_id", "year", "net_profit_margin_pct", "return_on_equity_pct", 
            "debt_to_equity", "free_cash_flow_cr", "revenue_cagr_5yr", "composite_quality_score"
        ]
        available_cols = [c for c in cols_to_show if c in df.columns]
        print(df[available_cols].head(5).to_string())
        
        # Row count check
        if total_rows >= 1100:
            print("\n[SUCCESS] Verification passed: Table contains >= 1100 rows.")
        else:
            print("\n[FAILED] Verification failed: Table contains < 1100 rows.")
            
    except Exception as e:
        print(f"Error executing verification: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
