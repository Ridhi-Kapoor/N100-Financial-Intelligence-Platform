"""
Script to compute profitability ratios for every company-year record.

Loads data from processed CSV files:
- profitandloss.csv
- balancesheet.csv
- companies.csv
- sectors.csv

Computes:
- Net Profit Margin (NPM)
- Operating Profit Margin (OPM)
- OPM Validation Flag (compares calculated OPM to raw opm_percentage)
- Return on Equity (ROE)
- Return on Capital Employed (ROCE)
- ROCE Benchmark Status (for Financials sector)
- Return on Assets (ROA)

Saves results to:
data/output/profitability_ratios.csv
"""

import os
from pathlib import Path
import pandas as pd
from src.analytics.ratios import (
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    validate_operating_profit_margin,
    calculate_roe,
    calculate_roce,
    calculate_roa,
    get_financial_sector_roce_benchmark,
)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
OUTPUT_FILE = OUTPUT_DIR / "profitability_ratios.csv"


def load_processed_csv(path: Path) -> pd.DataFrame:
    """
    Load a processed CSV file, dynamically skipping metadata headers if present.
    """
    if not path.exists():
        raise FileNotFoundError(f"Processed file not found at: {path}")

    # Inspect first line to check if it contains the actual headers
    with open(path, "r", encoding="utf-8") as f:
        first_line = f.readline()

    # If the first line starts with standard table headers, read directly.
    # Otherwise, skip the metadata line (header=1).
    if (
        first_line.startswith("id,")
        or first_line.startswith("company_id,")
        or "id," in first_line
    ):
        df = pd.read_csv(path)
    else:
        df = pd.read_csv(path, header=1)

    # Clean column names
    df.columns = [col.strip() for col in df.columns]
    return df


def compute_ebit(pbt_val, interest_val) -> float:
    """
    Helper to calculate EBIT (Earnings Before Interest and Taxes).
    Returns Profit Before Tax + Interest.
    """
    try:
        pbt = float(pbt_val) if pd.notna(pbt_val) else 0.0
    except (ValueError, TypeError):
        pbt = 0.0

    try:
        interest = float(interest_val) if pd.notna(interest_val) else 0.0
    except (ValueError, TypeError):
        interest = 0.0

    return pbt + interest


def main():
    print("Starting profitability ratios calculation...")

    # 1. Load CSVs
    print("Loading processed datasets...")
    pl_df = load_processed_csv(PROCESSED_DIR / "profitandloss.csv")
    bs_df = load_processed_csv(PROCESSED_DIR / "balancesheet.csv")
    companies_df = load_processed_csv(PROCESSED_DIR / "companies.csv")
    sectors_df = load_processed_csv(PROCESSED_DIR / "sectors.csv")

    print(f"Loaded records: P&L={len(pl_df)}, BS={len(bs_df)}, Companies={len(companies_df)}, Sectors={len(sectors_df)}")

    # Clean and cast key columns for merging
    for df in [pl_df, bs_df]:
        df["company_id"] = df["company_id"].astype(str).str.strip()
        df["year"] = df["year"].astype(str).str.strip()

    companies_df["id"] = companies_df["id"].astype(str).str.strip()
    sectors_df["company_id"] = sectors_df["company_id"].astype(str).str.strip()

    # Avoid duplicate records in the base tables
    pl_df = pl_df.drop_duplicates(subset=["company_id", "year"])
    bs_df = bs_df.drop_duplicates(subset=["company_id", "year"])

    # 2. Merge financial datasets
    print("Merging P&L and Balance Sheet datasets...")
    financials_df = pd.merge(
        pl_df,
        bs_df,
        on=["company_id", "year"],
        how="inner",
        suffixes=("_pl", "_bs"),
    )
    print(f"Merged financials records: {len(financials_df)}")

    # Merge company names
    financials_df = pd.merge(
        financials_df,
        companies_df[["id", "company_name"]],
        left_on="company_id",
        right_on="id",
        how="left",
    )

    # Merge sectors
    financials_df = pd.merge(
        financials_df,
        sectors_df[["company_id", "broad_sector"]],
        on="company_id",
        how="left",
    )

    # 3. First pass: Calculate basic ROCE for sector benchmark
    print("Calculating ROCE for financials benchmark...")
    roce_initial = []
    for _, row in financials_df.iterrows():
        ebit = compute_ebit(row.get("profit_before_tax"), row.get("interest"))
        roce_res = calculate_roce(
            ebit=ebit,
            equity_capital=row.get("equity_capital"),
            reserves=row.get("reserves"),
            borrowings=row.get("borrowings"),
            broad_sector=row.get("broad_sector"),
        )
        if isinstance(roce_res, tuple):
            roce_initial.append(roce_res[0])
        else:
            roce_initial.append(roce_res)

    financials_df["roce"] = roce_initial

    # Calculate sector benchmark ROCE for Financials
    financial_sector_benchmark = get_financial_sector_roce_benchmark(financials_df)
    if financial_sector_benchmark is not None:
        print(f"Financials Sector ROCE Benchmark (Average): {financial_sector_benchmark:.2f}%")
    else:
        print("Warning: Could not calculate Financials sector benchmark ROCE.")

    # 4. Second pass: Calculate all profitability ratios
    print("Calculating all profitability ratios...")
    npm_list = []
    opm_list = []
    opm_valid_list = []
    roe_list = []
    roce_list = []
    roce_status_list = []
    roa_list = []

    for _, row in financials_df.iterrows():
        # Net Profit Margin
        npm = calculate_net_profit_margin(row.get("net_profit"), row.get("sales"))
        npm_list.append(npm)

        # Operating Profit Margin
        opm = calculate_operating_profit_margin(
            row.get("operating_profit"), row.get("sales")
        )
        opm_list.append(opm)

        # OPM Validation
        opm_valid = validate_operating_profit_margin(
            calculated_opm=opm,
            source_opm=row.get("opm_percentage"),
            company_id=row.get("company_id"),
            company_name=row.get("company_name"),
            year=row.get("year"),
        )
        opm_valid_list.append(opm_valid)

        # Return on Equity (ROE)
        roe = calculate_roe(
            row.get("net_profit"),
            row.get("equity_capital"),
            row.get("reserves"),
        )
        roe_list.append(roe)

        # Return on Capital Employed (ROCE)
        ebit = compute_ebit(row.get("profit_before_tax"), row.get("interest"))
        roce_res = calculate_roce(
            ebit=ebit,
            equity_capital=row.get("equity_capital"),
            reserves=row.get("reserves"),
            borrowings=row.get("borrowings"),
            broad_sector=row.get("broad_sector"),
            benchmark_roce=financial_sector_benchmark,
        )

        if isinstance(roce_res, tuple):
            roce_list.append(roce_res[0])
            roce_status_list.append(roce_res[1])
        else:
            roce_list.append(roce_res)
            roce_status_list.append(None)

        # Return on Assets (ROA)
        roa = calculate_roa(row.get("net_profit"), row.get("total_assets"))
        roa_list.append(roa)

    # 5. Populate final columns and structure output
    output_df = pd.DataFrame(
        {
            "company_id": financials_df["company_id"],
            "company_name": financials_df["company_name"],
            "year": financials_df["year"],
            "broad_sector": financials_df["broad_sector"],
            "net_profit_margin": npm_list,
            "operating_profit_margin": opm_list,
            "opm_validation_flag": opm_valid_list,
            "return_on_equity": roe_list,
            "return_on_capital_employed": roce_list,
            "roce_benchmark_status": roce_status_list,
            "return_on_assets": roa_list,
        }
    )

    # Sort results for readability
    output_df = output_df.sort_values(by=["company_id", "year"])

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save to CSV
    output_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Results successfully saved to: {OUTPUT_FILE.resolve()}")
    print(f"Total calculated company-year records: {len(output_df)}")


if __name__ == "__main__":
    main()
