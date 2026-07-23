"""
Script to run the Capital Allocation Report workflow for Day 32.

Validates capital allocation data, generates distribution summary,
integrates with cashflow_intelligence.xlsx, and detects YoY pattern changes.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set stdout encoding for Windows console compatibility
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.analytics.capital_allocation_report import generate_capital_allocation_report


def main():
    print("=" * 70)
    print("      NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM")
    print("           DAY 32: CAPITAL ALLOCATION REPORT")
    print("=" * 70)

    try:
        results = generate_capital_allocation_report(PROJECT_ROOT)

        val_df = results["validation_summary"]
        dist_df = results["distribution_summary"]
        changes_df = results["pattern_changes"]
        paths = results["output_paths"]

        print("\n--- 1. DATA VALIDATION SUMMARY ---")
        print(val_df.to_string(index=False))

        print("\n--- 2. CAPITAL ALLOCATION DISTRIBUTION (LATEST YEAR) ---")
        print(dist_df.to_string(index=False))

        print(f"\n--- 3. CASH FLOW INTELLIGENCE INTEGRATION ---")
        print(f"Updated Excel saved to: {paths['cashflow_intelligence_excel']}")

        print(f"\n--- 4. YoY PATTERN CHANGES DETECTED ---")
        print(f"Total pattern transitions: {len(changes_df)}")
        if not changes_df.empty:
            print("\nSample pattern changes (first 10 records):")
            sample_str = changes_df.head(10).to_string(index=False)
            try:
                print(sample_str)
            except UnicodeEncodeError:
                print(sample_str.encode("ascii", "replace").decode("ascii"))

        print("\n" + "=" * 70)
        print("ALL REPORTS GENERATED SUCCESSFULLY IN THE output/ DIRECTORY:")
        for name, pth in paths.items():
            print(f"  - {name}: {pth}")
        print("=" * 70)

    except Exception as e:
        print(f"\nERROR running Capital Allocation Report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
