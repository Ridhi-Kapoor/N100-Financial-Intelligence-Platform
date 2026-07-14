"""
Script to compute CAGR metrics for every company-year record.

Loads data from processed CSV files:
- profitandloss.csv

Computes 3-year, 5-year, and 10-year CAGR and flags for:
- Revenue (sales)
- PAT (net_profit)
- EPS (eps)

Saves results to:
data/output/cagr_metrics.csv
"""

import logging
from pathlib import Path
import pandas as pd

from src.analytics.cagr import compute_dataframe_cagr

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
OUTPUT_FILE = OUTPUT_DIR / "cagr_metrics.csv"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("compute_cagr_metrics")


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
    logger.info("Starting CAGR metrics calculation...")

    # 1. Load P&L CSV
    logger.info("Loading processed P&L dataset...")
    try:
        pl_df = load_processed_csv(PROCESSED_DIR / "profitandloss.csv")
    except Exception as e:
        logger.error(f"Error loading P&L dataset: {e}")
        return

    logger.info(f"Loaded {len(pl_df)} P&L records.")

    # Clean company_id and year
    pl_df["company_id"] = pl_df["company_id"].astype(str).str.strip()
    pl_df["year"] = pd.to_numeric(pl_df["year"], errors="coerce")

    # Drop duplicate records in the base table
    pl_df = pl_df.drop_duplicates(subset=["company_id", "year"]).dropna(subset=["company_id", "year"])
    
    # Sort for readability and consistency
    pl_df = pl_df.sort_values(by=["company_id", "year"]).reset_index(drop=True)

    # 2. Compute CAGRs
    logger.info("Calculating CAGR metrics for Revenue, PAT, and EPS...")
    
    periods = [3, 5, 10]
    metrics = {
        "sales": "revenue",
        "net_profit": "pat",
        "eps": "eps"
    }

    # Dict to hold computed lists
    cagr_results = {
        "company_id": pl_df["company_id"],
        "year": pl_df["year"].astype(int)
    }

    for metric_col, prefix in metrics.items():
        for n in periods:
            val_col = f"{prefix}_cagr_{n}yr"
            flag_col = f"{prefix}_cagr_{n}yr_flag"
            
            logger.info(f"Computing {n}-year CAGR for {prefix} ({metric_col})...")
            vals, flags = compute_dataframe_cagr(
                df=pl_df,
                metric_col=metric_col,
                n_years=n,
                output_val_col=val_col,
                output_flag_col=flag_col
            )
            cagr_results[val_col] = vals
            cagr_results[flag_col] = flags

    # 3. Create output DataFrame
    output_df = pd.DataFrame(cagr_results)

    # Sort results
    output_df = output_df.sort_values(by=["company_id", "year"])

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save to CSV
    output_df.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"CAGR metrics successfully saved to: {OUTPUT_FILE.resolve()}")
    logger.info(f"Total calculated company-year records: {len(output_df)}")


if __name__ == "__main__":
    main()
