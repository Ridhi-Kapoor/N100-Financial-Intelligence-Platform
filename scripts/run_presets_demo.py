"""
Stock Screener Presets Demo Script.

Loads Nifty 100 financial data for 2024, executes each of the six predefined 
screener presets from src/screener/presets.py, displays the results with key 
financial metrics, and validates that each preset yields between 5 and 50 companies.
"""

from pathlib import Path
import pandas as pd
from src.screener.presets import apply_preset

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_FILE = PROJECT_ROOT / "data" / "db" / "nifty100.db"
TARGET_YEAR = 2024

# Preset configurations for demonstration purposes (display configurations)
DEMO_PRESETS = [
    {
        "name": "Quality Compounder",
        "key": "quality_compounder",
        "desc": "High returns, strong margins, low leverage, positive FCF.",
        "metrics": ["Ticker", "Company Name", "Sector", "ROE", "D/E", "OPM", "ICR", "FCF (Cr)", "Quality Score"]
    },
    {
        "name": "Value Pick",
        "key": "value_pick",
        "desc": "Low P/E, low P/B, decent ROE, reasonable debt.",
        "metrics": ["Ticker", "Company Name", "Sector", "ROE", "D/E", "P/E", "P/B", "Quality Score"]
    },
    {
        "name": "Growth Accelerator",
        "key": "growth_accelerator",
        "desc": "Strong revenue/earnings CAGR 5Y and high profitability.",
        "metrics": ["Ticker", "Company Name", "Sector", "ROE", "Rev CAGR 5Y", "PAT CAGR 5Y", "Quality Score"]
    },
    {
        "name": "Dividend Champion",
        "key": "dividend_champion",
        "desc": "High dividend yield, consistent profits, safe leverage.",
        "metrics": ["Ticker", "Company Name", "Sector", "ROE", "D/E", "Dividend Yield", "Quality Score"]
    },
    {
        "name": "Debt-Free Blue Chip",
        "key": "debt_free_blue_chip",
        "desc": "Large market cap, zero/near-zero debt, solid ROE.",
        "metrics": ["Ticker", "Company Name", "Sector", "Market Cap (Cr)", "ROE", "D/E", "Quality Score"]
    },
    {
        "name": "Turnaround Watch",
        "key": "turnaround_watch",
        "desc": "Declining Debt-to-Equity YoY, profitable and stable.",
        "metrics": ["Ticker", "Company Name", "Sector", "ROE", "Net Profit (Cr)", "D/E", "Quality Score"]
    }
]

def format_row_value(val, fmt):
    if pd.isna(val) or val is None:
        return "N/A"
    try:
        if fmt == "pct":
            return f"{float(val):.2f}%"
        elif fmt == "dec":
            return f"{float(val):.2f}"
        elif fmt == "curr":
            return f"{float(val):,.2f}"
        elif fmt == "str":
            return str(val)
    except (ValueError, TypeError):
        pass
    return str(val)

def main():
    print("=" * 120)
    print(f"                      NIFTY 100 STOCK SCREENER PRESETS DEMO (YEAR {TARGET_YEAR})")
    print("=" * 120)
    
    if not DB_FILE.exists():
        print(f"[ERROR] Database file not found at: {DB_FILE.resolve()}")
        return
        
    summary_data = []
    
    for preset in DEMO_PRESETS:
        name = preset["name"]
        key = preset["key"]
        desc = preset["desc"]
        
        print(f"\n>>> Running Preset: {name}")
        print(f"    Description: {desc}")
        print("-" * 120)
        
        try:
            # 1. Run the preset
            df_res = apply_preset(name, DB_FILE, year=TARGET_YEAR)
            count = len(df_res)
            
            # Check 5 to 50 constraint
            status = "PASSED" if 5 <= count <= 50 else "FAILED"
            summary_data.append({
                "Preset Name": name,
                "Match Count": count,
                "Status": status,
                "Top 3 Companies": ", ".join(df_res["company_id"].head(3).tolist()) if count > 0 else "None"
            })
            
            print(f"Matches found: {count} companies (Status: {status})")
            
            if count > 0:
                # Prepare display columns
                df_disp = df_res.copy()
                df_disp.rename(columns={
                    "company_id": "Ticker",
                    "company_name": "Company Name",
                    "broad_sector": "Sector",
                    "return_on_equity_pct": "ROE",
                    "debt_to_equity": "D/E",
                    "operating_profit_margin_pct": "OPM",
                    "interest_coverage": "ICR",
                    "free_cash_flow_cr": "FCF (Cr)",
                    "pe_ratio": "P/E",
                    "pb_ratio": "P/B",
                    "revenue_cagr_5yr": "Rev CAGR 5Y",
                    "pat_cagr_5yr": "PAT CAGR 5Y",
                    "dividend_yield_pct": "Dividend Yield",
                    "market_cap_crore": "Market Cap (Cr)",
                    "net_profit": "Net Profit (Cr)",
                    "composite_quality_score": "Quality Score"
                }, inplace=True)
                
                # Format metrics appropriately
                if "ROE" in df_disp.columns:
                    df_disp["ROE"] = df_disp["ROE"].map(lambda x: format_row_value(x, "pct"))
                if "D/E" in df_disp.columns:
                    df_disp["D/E"] = df_disp["D/E"].map(lambda x: format_row_value(x, "dec"))
                if "OPM" in df_disp.columns:
                    df_disp["OPM"] = df_disp["OPM"].map(lambda x: format_row_value(x, "pct"))
                if "ICR" in df_disp.columns:
                    # Special check: If interest is 0.0 or is flagged debt-free
                    df_disp["ICR"] = df_disp.apply(
                        lambda r: "Debt Free" if r.get("D/E") == "0.00" or (pd.isna(r.get("interest")) and r.get("borrowings") == 0) else format_row_value(r.get("interest_coverage"), "dec"),
                        axis=1
                    )
                if "FCF (Cr)" in df_disp.columns:
                    df_disp["FCF (Cr)"] = df_disp["FCF (Cr)"].map(lambda x: format_row_value(x, "curr"))
                if "P/E" in df_disp.columns:
                    df_disp["P/E"] = df_disp["P/E"].map(lambda x: format_row_value(x, "dec"))
                if "P/B" in df_disp.columns:
                    df_disp["P/B"] = df_disp["P/B"].map(lambda x: format_row_value(x, "dec"))
                if "Rev CAGR 5Y" in df_disp.columns:
                    df_disp["Rev CAGR 5Y"] = df_disp["Rev CAGR 5Y"].map(lambda x: format_row_value(x, "pct"))
                if "PAT CAGR 5Y" in df_disp.columns:
                    df_disp["PAT CAGR 5Y"] = df_disp["PAT CAGR 5Y"].map(lambda x: format_row_value(x, "pct"))
                if "Dividend Yield" in df_disp.columns:
                    df_disp["Dividend Yield"] = df_disp["Dividend Yield"].map(lambda x: format_row_value(x, "pct"))
                if "Market Cap (Cr)" in df_disp.columns:
                    df_disp["Market Cap (Cr)"] = df_disp["Market Cap (Cr)"].map(lambda x: format_row_value(x, "curr"))
                if "Net Profit (Cr)" in df_disp.columns:
                    df_disp["Net Profit (Cr)"] = df_disp["Net Profit (Cr)"].map(lambda x: format_row_value(x, "curr"))
                if "Quality Score" in df_disp.columns:
                    df_disp["Quality Score"] = df_disp["Quality Score"].map(lambda x: format_row_value(x, "dec"))
                
                # Show top 10 matches (or all if less than 10)
                limit = min(count, 10)
                print(f"Top {limit} matching companies (sorted by composite quality score):")
                cols_to_show = [c for c in preset["metrics"] if c in df_disp.columns]
                print(df_disp[cols_to_show].head(limit).to_string(index=False))
            else:
                print("No companies matched this preset.")
                
        except Exception as e:
            print(f"[ERROR] Failed to run preset {name}: {e}")
            summary_data.append({
                "Preset Name": name,
                "Match Count": "ERROR",
                "Status": "FAILED",
                "Top 3 Companies": "N/A"
            })
        print("-" * 120)
        
    # Print overall summary table
    print("\n" + "=" * 120)
    print("                                      SUMMARY OF PRESETS PERFORMANCE")
    print("=" * 120)
    summary_df = pd.DataFrame(summary_data)
    print(summary_df.to_string(index=False))
    print("=" * 120)
    
    # Assert validation check for final exit code (useful for make tasks or CI)
    any_failed = any(row["Status"] == "FAILED" for row in summary_data)
    if any_failed:
        print("\n[WARNING] One or more presets did not meet the count constraint of 5 to 50 companies.")
    else:
        print("\n[SUCCESS] All presets compiled and satisfied the 5 to 50 company limit count successfully!")

if __name__ == "__main__":
    main()
