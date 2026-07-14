"""
Script to compute leverage and efficiency ratios for every company-year record.

Loads data from processed CSV files:
- profitandloss.csv
- balancesheet.csv
- sectors.csv

Computes:
- Debt-to-Equity Ratio
- High Leverage Flag
- Interest Coverage Ratio (ICR)
- ICR Label
- ICR Warning Flag
- Net Debt
- Asset Turnover

Saves results to:
data/output/leverage_efficiency_ratios.csv
"""

import logging
import os
from pathlib import Path
import pandas as pd

from src.analytics.ratios import (
    calculate_debt_to_equity,
    get_high_leverage_flag,
    calculate_interest_coverage_ratio,
    get_icr_warning_flag,
    calculate_net_debt,
    calculate_asset_turnover,
)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
OUTPUT_FILE = OUTPUT_DIR / "leverage_efficiency_ratios.csv"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("compute_leverage_ratios")


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


def main():
    logger.info("Starting leverage and efficiency ratios calculation...")

    # 1. Load CSVs
    logger.info("Loading processed datasets...")
    try:
        pl_df = load_processed_csv(PROCESSED_DIR / "profitandloss.csv")
        bs_df = load_processed_csv(PROCESSED_DIR / "balancesheet.csv")
        sectors_df = load_processed_csv(PROCESSED_DIR / "sectors.csv")
    except Exception as e:
        logger.error(f"Error loading datasets: {e}")
        return

    logger.info(
        f"Loaded records: P&L={len(pl_df)}, BS={len(bs_df)}, Sectors={len(sectors_df)}"
    )

    # Clean and cast key columns for merging
    for df in [pl_df, bs_df]:
        df["company_id"] = df["company_id"].astype(str).str.strip()
        df["year"] = df["year"].astype(str).str.strip()

    sectors_df["company_id"] = sectors_df["company_id"].astype(str).str.strip()

    # Avoid duplicate records in the base tables
    pl_df = pl_df.drop_duplicates(subset=["company_id", "year"])
    bs_df = bs_df.drop_duplicates(subset=["company_id", "year"])

    # 2. Merge financial datasets
    logger.info("Merging P&L, Balance Sheet, and Sector datasets...")
    financials_df = pd.merge(
        pl_df,
        bs_df,
        on=["company_id", "year"],
        how="inner",
        suffixes=("_pl", "_bs"),
    )
    logger.info(f"Merged financials records: {len(financials_df)}")

    # Merge sectors
    financials_df = pd.merge(
        financials_df,
        sectors_df[["company_id", "broad_sector"]],
        on="company_id",
        how="left",
    )

    # 3. Calculate all ratios
    logger.info("Calculating leverage and efficiency ratios...")
    debt_to_equity_list = []
    high_leverage_flag_list = []
    icr_list = []
    icr_label_list = []
    icr_warning_list = []
    net_debt_list = []
    asset_turnover_list = []

    for _, row in financials_df.iterrows():
        # Debt-to-Equity
        d_e = calculate_debt_to_equity(
            borrowings=row.get("borrowings"),
            equity_capital=row.get("equity_capital"),
            reserves=row.get("reserves"),
        )
        debt_to_equity_list.append(d_e)

        # High Leverage Flag
        hl_flag = get_high_leverage_flag(
            debt_to_equity=d_e,
            broad_sector=row.get("broad_sector"),
        )
        high_leverage_flag_list.append(hl_flag)

        # Interest Coverage Ratio and Label
        icr, icr_label = calculate_interest_coverage_ratio(
            operating_profit=row.get("operating_profit"),
            other_income=row.get("other_income"),
            interest=row.get("interest"),
        )
        icr_list.append(icr)
        icr_label_list.append(icr_label)

        # ICR Warning
        icr_warn = get_icr_warning_flag(icr=icr, icr_label=icr_label)
        icr_warning_list.append(icr_warn)

        # Net Debt
        net_debt = calculate_net_debt(
            borrowings=row.get("borrowings"),
            investments=row.get("investments"),
        )
        net_debt_list.append(net_debt)

        # Asset Turnover
        asset_turnover = calculate_asset_turnover(
            sales=row.get("sales"),
            total_assets=row.get("total_assets"),
        )
        asset_turnover_list.append(asset_turnover)

    # 4. Populate final columns and structure output
    output_df = pd.DataFrame(
        {
            "company_id": financials_df["company_id"],
            "year": financials_df["year"],
            "debt_to_equity": debt_to_equity_list,
            "high_leverage_flag": high_leverage_flag_list,
            "interest_coverage_ratio": icr_list,
            "icr_label": icr_label_list,
            "icr_warning": icr_warning_list,
            "net_debt": net_debt_list,
            "asset_turnover": asset_turnover_list,
        }
    )

    # Sort results for readability
    output_df = output_df.sort_values(by=["company_id", "year"])

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save to CSV
    output_df.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Results successfully saved to: {OUTPUT_FILE.resolve()}")
    logger.info(f"Total calculated company-year records: {len(output_df)}")


if __name__ == "__main__":
    main()
