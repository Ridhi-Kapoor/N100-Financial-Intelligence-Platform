"""
Script to compute Capital Allocation Pattern Classifier for every company-year record.

Loads data from processed CSV files:
- cashflow.csv
- profitandloss.csv

Computes signs of CFO, CFI, CFF, and classifies the capital allocation pattern.

Saves results to:
data/output/capital_allocation.csv
"""

import logging
from pathlib import Path
import pandas as pd

from src.analytics.cashflow import classify_capital_allocation

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
OUTPUT_FILE = OUTPUT_DIR / "capital_allocation.csv"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("compute_capital_allocation")


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
    logger.info("Starting Capital Allocation Pattern calculation...")

    # 1. Load CSVs
    logger.info("Loading processed datasets...")
    try:
        cf_df = load_processed_csv(PROCESSED_DIR / "cashflow.csv")
        pl_df = load_processed_csv(PROCESSED_DIR / "profitandloss.csv")
    except Exception as e:
        logger.error(f"Error loading datasets: {e}")
        return

    logger.info(f"Loaded records: CashFlow={len(cf_df)}, P&L={len(pl_df)}")

    # Clean company_id and year
    for df in [cf_df, pl_df]:
        df["company_id"] = df["company_id"].astype(str).str.strip()
        df["year"] = df["year"].astype(str).str.strip()

    # Avoid duplicate records in the base tables
    cf_df = cf_df.drop_duplicates(subset=["company_id", "year"])
    pl_df = pl_df.drop_duplicates(subset=["company_id", "year"])

    # 2. Merge datasets
    logger.info("Merging CashFlow and P&L datasets...")
    merged_df = pd.merge(
        cf_df,
        pl_df[["company_id", "year", "net_profit"]],
        on=["company_id", "year"],
        how="inner"
    )
    logger.info(f"Merged records: {len(merged_df)}")

    # 3. Calculate Pattern Classification
    logger.info("Classifying Capital Allocation Patterns...")
    cfo_signs = []
    cfi_signs = []
    cff_signs = []
    pattern_labels = []

    for _, row in merged_df.iterrows():
        cfo_s, cfi_s, cff_s, label = classify_capital_allocation(
            cfo=row.get("operating_activity"),
            cfi=row.get("investing_activity"),
            cff=row.get("financing_activity"),
            pat=row.get("net_profit")
        )
        cfo_signs.append(cfo_s)
        cfi_signs.append(cfi_s)
        cff_signs.append(cff_s)
        pattern_labels.append(label)

    # 4. Structure output
    output_df = pd.DataFrame(
        {
            "company_id": merged_df["company_id"],
            "year": merged_df["year"],
            "cfo_sign": cfo_signs,
            "cfi_sign": cfi_signs,
            "cff_sign": cff_signs,
            "pattern_label": pattern_labels
        }
    )

    # Sort results
    output_df = output_df.sort_values(by=["company_id", "year"])

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save to CSV
    output_df.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"Capital allocation patterns successfully saved to: {OUTPUT_FILE.resolve()}")
    logger.info(f"Total calculated company-year records: {len(output_df)}")


if __name__ == "__main__":
    main()
