"""
Screener Engine Runner.

Queries the nifty100 database, applies filter thresholds from
screener_config.yaml using the screener engine, and displays the matching
companies sorted by their composite quality score.
"""

from pathlib import Path
import pandas as pd
from src.screener.engine import (
    load_config,
    load_screener_data,
    apply_screener_filters
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_FILE = PROJECT_ROOT / "data" / "db" / "nifty100.db"
CONFIG_FILE = PROJECT_ROOT / "screener_config.yaml"


def main():
    print("=" * 110)
    print("                      NIFTY 100 STOCK SCREENER (ENGINE RUNNER)")
    print("=" * 110)
    
    # 1. Load config
    print(f"Loading screener config from: {CONFIG_FILE.resolve()}")
    try:
        config = load_config(CONFIG_FILE)
        active_filters = config.get("filters", {})
        print(f"Loaded {len(active_filters)} active filters:")
        for metric, criteria in active_filters.items():
            print(f"  - {metric}: {criteria}")
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}")
        return

    # 2. Load financial data
    print(f"\nLoading and merging data from SQLite database: {DB_FILE.resolve()}")
    try:
        df_raw = load_screener_data(DB_FILE, year=2024)
        print(f"Loaded {len(df_raw)} records for the year 2024.")
    except Exception as e:
        print(f"[ERROR] Failed to load database: {e}")
        return

    # 3. Apply screener filters
    print("\nApplying screener filters...")
    try:
        df_filtered = apply_screener_filters(df_raw, config)
    except Exception as e:
        print(f"[ERROR] Error applying filters: {e}")
        return

    # 4. Display results
    print("\n=== SCREENER RESULTS (YEAR 2024) ===")
    print(f"Total Companies Matching Filters: {len(df_filtered)}")
    print("=" * 110)

    if not df_filtered.empty:
        # Select key display columns
        display_cols = [
            "company_id",
            "company_name",
            "broad_sector",
            "return_on_equity_pct",
            "debt_to_equity",
            "pe_ratio",
            "market_cap_crore",
            "composite_quality_score"
        ]
        
        # Ensure columns exist in output
        available_cols = [c for c in display_cols if c in df_filtered.columns]
        df_display = df_filtered[available_cols].copy()
        
        # Rename columns for presentation
        df_display.rename(columns={
            "company_id": "Ticker",
            "company_name": "Company Name",
            "broad_sector": "Sector",
            "return_on_equity_pct": "ROE",
            "debt_to_equity": "D/E",
            "pe_ratio": "P/E",
            "market_cap_crore": "Market Cap (Cr)",
            "composite_quality_score": "Quality Score"
        }, inplace=True)

        # Format numeric values
        if "ROE" in df_display.columns:
            df_display["ROE"] = df_display["ROE"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
        if "D/E" in df_display.columns:
            df_display["D/E"] = df_display["D/E"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        if "P/E" in df_display.columns:
            df_display["P/E"] = df_display["P/E"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        if "Market Cap (Cr)" in df_display.columns:
            df_display["Market Cap (Cr)"] = df_display["Market Cap (Cr)"].map(lambda x: f"{x:,.2f}" if pd.notna(x) else "N/A")
        if "Quality Score" in df_display.columns:
            df_display["Quality Score"] = df_display["Quality Score"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")

        print(df_display.to_string(index=False))
    else:
        print("No companies matched the filters.")
    
    print("=" * 110)

    # 5. Validation checks
    # As per typical screener checks, a reasonable yield of companies is 15-50 for high quality
    if 10 <= len(df_filtered) <= 60:
        print(f"\n[SUCCESS] Screener result count of {len(df_filtered)} is valid.")
    else:
        print(f"\n[WARNING] Screener result count of {len(df_filtered)} might be too restrictive or loose.")


if __name__ == "__main__":
    main()
