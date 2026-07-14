"""
Demo Script for presenting financial_ratios table.

Reads Nifty100 SQLite database and displays five companies (TCS, INFY, ABB, COALINDIA, BRITANNIA)
with all computed KPIs for Year 2024 in a presentation-ready format.
"""

import sqlite3
from pathlib import Path
import pandas as pd
from src.analytics.ratios import calculate_roce

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_FILE = PROJECT_ROOT / "data" / "db" / "nifty100.db"


def main():
    print(f"Connecting to Nifty100 Database: {DB_FILE}...")
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # SQL query to load required variables for 5 companies in 2024
        query = """
        SELECT 
            fr.company_id,
            c.company_name,
            fr.year,
            s.broad_sector AS sector,
            fr.revenue_cagr_5yr,
            fr.pat_cagr_5yr,
            fr.eps_cagr_5yr,
            fr.net_profit_margin_pct,
            fr.operating_profit_margin_pct,
            fr.return_on_equity_pct,
            fr.debt_to_equity,
            fr.interest_coverage,
            fr.asset_turnover,
            fr.free_cash_flow_cr,
            fr.cash_from_operations_cr,
            fr.composite_quality_score,
            pl.net_profit,
            pl.profit_before_tax,
            pl.interest,
            bs.equity_capital,
            bs.reserves,
            bs.borrowings
        FROM financial_ratios fr
        JOIN companies c ON fr.company_id = c.id
        JOIN sectors s ON fr.company_id = s.company_id
        LEFT JOIN profitandloss pl ON fr.company_id = pl.company_id AND fr.year = pl.year
        LEFT JOIN balancesheet bs ON fr.company_id = bs.company_id AND fr.year = bs.year
        WHERE fr.year = '2024'
          AND fr.company_id IN ('TCS', 'INFY', 'ABB', 'COALINDIA', 'BRITANNIA')
        GROUP BY fr.company_id
        """
        
        df = pd.read_sql_query(query, conn)
        
        # Calculate ROCE on the fly
        roce_list = []
        for _, row in df.iterrows():
            pbt = row.get("profit_before_tax") or 0.0
            interest = row.get("interest") or 0.0
            ebit = pbt + interest
            roce_res = calculate_roce(
                ebit=ebit,
                equity_capital=row.get("equity_capital"),
                reserves=row.get("reserves"),
                borrowings=row.get("borrowings"),
                broad_sector=row.get("sector")
            )
            roce_val = roce_res[0] if isinstance(roce_res, tuple) else roce_res
            roce_list.append(roce_val)
        
        df["ROCE"] = roce_list
        
        # Select and rename presentation columns
        df_demo = pd.DataFrame()
        df_demo["Company Name"] = df["company_name"]
        df_demo["Revenue CAGR (5Y)"] = df["revenue_cagr_5yr"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        df_demo["PAT CAGR (5Y)"] = df["pat_cagr_5yr"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        df_demo["EPS CAGR (5Y)"] = df["eps_cagr_5yr"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        df_demo["Net Profit Margin"] = df["net_profit_margin_pct"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        df_demo["Operating Profit Margin"] = df["operating_profit_margin_pct"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        df_demo["ROE"] = df["return_on_equity_pct"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        df_demo["ROCE"] = df["ROCE"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        df_demo["Debt-to-Equity"] = df["debt_to_equity"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        df_demo["Interest Coverage Ratio"] = df["interest_coverage"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        df_demo["Asset Turnover"] = df["asset_turnover"].map(lambda x: f"{x:.2f}x" if pd.notna(x) else "N/A")
        df_demo["Free Cash Flow (Cr)"] = df["free_cash_flow_cr"].map(lambda x: f"{x:,.2f}" if pd.notna(x) else "N/A")
        
        # CFO Quality Score is CFO / PAT for the current year
        cfo_qual = []
        for _, row in df.iterrows():
            cfo = row.get("cash_from_operations_cr")
            pat = row.get("net_profit")
            if cfo is not None and pat is not None and pat != 0.0:
                cfo_qual.append(f"{cfo / pat:.2f}")
            else:
                cfo_qual.append("N/A")
        df_demo["CFO Quality Score"] = cfo_qual
        df_demo["Composite Quality Score"] = df["composite_quality_score"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        
        print("\n" + "=" * 120)
        print("                        NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM - COMPUTED KPIS")
        print("                                     DEMO REPORT FOR TEAM LEAD")
        print("=" * 120)
        
        # Transpose the DataFrame for a vertical, polished presentation layout
        df_transposed = df_demo.set_index("Company Name").T
        pd.set_option('display.max_columns', 10)
        pd.set_option('display.width', 1000)
        print(df_transposed.to_string())
        print("=" * 120)
        
    except Exception as e:
        print(f"Error running demo script: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
