"""
Script to run the Company Tearsheet PDF Generator workflow for Day 33.

Generates professional 2-page investment research PDF tearsheets for Nifty 100 constituents.
Default target companies: TCS, HDFCBANK, RELIANCE, SUNPHARMA, TATASTEEL.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.reports.tearsheet import generate_all_tearsheets, generate_tearsheet_pdf


def main():
    parser = argparse.ArgumentParser(description="Generate Company Tearsheet PDFs using ReportLab")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=["TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATASTEEL"],
        help="List of NSE ticker symbols to generate tearsheets for.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="Output directory path for generated PDFs.",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("      NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM")
    print("           DAY 33: COMPANY TEARSHEET GENERATOR")
    print("=" * 70)

    try:
        results = generate_all_tearsheets(tickers=args.tickers, output_dir=args.output_dir)

        print("\n--- GENERATED TEARSHEET PDFS ---")
        for ticker, pdf_path in results.items():
            file_size_kb = pdf_path.stat().st_size / 1024 if pdf_path.exists() else 0
            print(f"  - {ticker:10s} -> {pdf_path} ({file_size_kb:.1f} KB)")

        print("\n" + "=" * 70)
        print(f"SUCCESSFULLY GENERATED {len(results)} COMPANY TEARSHEET PDF(S) IN output/")
        print("=" * 70)

    except Exception as e:
        print(f"\nERROR generating Company Tearsheets: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
