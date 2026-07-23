"""
Script to generate the Portfolio Summary PDF for Day 35.

Creates reports/portfolio/portfolio_summary.pdf with 1 page per company,
sorted alphabetically by NSE ticker, featuring top 6 KPI cards, YoY trend indicators,
and multi-year performance charts.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.reports.portfolio import generate_portfolio_summary_pdf


def main():
    print("=" * 70)
    print("      NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM")
    print("           DAY 35: PORTFOLIO SUMMARY PDF")
    print("=" * 70)

    try:
        pdf_path = generate_portfolio_summary_pdf()

        file_size_mb = pdf_path.stat().st_size / (1024 * 1024) if pdf_path.exists() else 0
        print(f"\n--- PORTFOLIO SUMMARY PDF GENERATED ---")
        print(f"File Path: {pdf_path.resolve()}")
        print(f"File Size: {file_size_mb:.2f} MB")

        print("\n" + "=" * 70)
        print("PORTFOLIO SUMMARY PDF SUCCESSFULLY CREATED IN reports/portfolio/")
        print("=" * 70)

    except Exception as e:
        print(f"\nERROR generating Portfolio Summary PDF: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
