"""
Screener Preview Script.

Queries the financial_ratios table in nifty100.db for the year 2024.
Filters:
- ROE > 15%
- Debt-to-Equity < 1.0 (excluding Financial sector companies from this restriction)

Displays:
- company_id
- company_name
- sector
- ROE
- Debt-to-Equity
- Composite Quality Score
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
        
        # SQL query to get data for year 2024 grouped by company to eliminate duplicates
        query = """
        SELECT 
            fr.company_id,
            c.company_name,
            s.broad_sector AS sector,
            MAX(fr.return_on_equity_pct) AS ROE,
            MIN(fr.debt_to_equity) AS [Debt-to-Equity],
            MAX(fr.composite_quality_score) AS [Composite Quality Score]
        FROM financial_ratios fr
        JOIN companies c ON fr.company_id = c.id
        JOIN sectors s ON fr.company_id = s.company_id
        WHERE fr.year = '2024'
          AND fr.return_on_equity_pct > 15.0
          AND (fr.debt_to_equity < 1.0 OR s.broad_sector = 'Financials')
        GROUP BY fr.company_id, c.company_name, s.broad_sector
        """
        
        df = pd.read_sql_query(query, conn)
        
        # Sort by ROE descending for better readability
        df = df.sort_values(by="ROE", ascending=False).reset_index(drop=True)
        
        print("\n=== SCREENER RESULTS (YEAR 2024) ===")
        print(f"Total Unique Companies Matching Filters: {len(df)}")
        print("Filters applied: ROE > 15%, Debt-to-Equity < 1.0 (excluding Financials)")
        print("=" * 110)
        
        # Format columns for display
        df_display = df.copy()
        df_display["ROE"] = df_display["ROE"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        df_display["Debt-to-Equity"] = df_display["Debt-to-Equity"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        df_display["Composite Quality Score"] = df_display["Composite Quality Score"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        
        print(df_display.to_string(index=False))
        print("=" * 110)
        
        # Verify result count is between 15 and 50
        if 15 <= len(df) <= 50:
            print("\n[SUCCESS] Screener result count is valid (between 15 and 50).")
        else:
            print(f"\n[FAILED] Screener result count {len(df)} is outside the allowed 15-50 range.")
            
    except Exception as e:
        print(f"Error running screener: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
