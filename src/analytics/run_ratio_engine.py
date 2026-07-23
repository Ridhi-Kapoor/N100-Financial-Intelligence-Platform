"""
Ratio Engine Runner.

This script reads all processed financial datasets from 'data/processed/',
merges them, executes all previously implemented analytics calculations (Profitability,
Leverage, CAGR, and Cash Flow), and populates/updates the SQLite table
'financial_ratios' in 'data/db/nifty100.db'.

It also performs cross-checking of calculated ROCE and ROE against raw source ratios
from 'companies.csv', logs anomalies (difference > 5%) to 'data/output/ratio_edge_cases.log',
and categorizes each anomaly.
"""

import logging
import math
import sqlite3
from pathlib import Path
from typing import Optional
import pandas as pd

from src.analytics.ratios import (
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    calculate_roe,
    calculate_debt_to_equity,
    calculate_interest_coverage_ratio,
    calculate_asset_turnover,
    calculate_roce,
)
from src.analytics.cagr import calculate_cagr
from src.analytics.cashflow import (
    calculate_free_cash_flow,
    calculate_cfo_quality_score,
)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_FILE = PROJECT_ROOT / "data" / "db" / "nifty100.db"
ANOMALY_LOG_FILE = PROJECT_ROOT / "data" / "output" / "ratio_edge_cases.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("run_ratio_engine")


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

    # Cast critical key columns
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].astype(str).str.strip()
    if "year" in df.columns:
        df["year"] = df["year"].astype(str).str.strip()

    return df


def recreate_database_table(conn: sqlite3.Connection) -> None:
    """
    Drop and recreate the financial_ratios table in Nifty100 database.
    """
    cursor = conn.cursor()

    logger.info("Dropping existing financial_ratios table if it exists...")
    cursor.execute("DROP TABLE IF EXISTS financial_ratios;")

    logger.info("Creating financial_ratios table with updated schema...")
    cursor.execute("""
    CREATE TABLE financial_ratios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        year TEXT NOT NULL,
        net_profit_margin_pct REAL,
        operating_profit_margin_pct REAL,
        return_on_equity_pct REAL,
        debt_to_equity REAL,
        interest_coverage REAL,
        asset_turnover REAL,
        free_cash_flow_cr REAL,
        capex_cr REAL,
        earnings_per_share REAL,
        book_value_per_share REAL,
        dividend_payout_ratio_pct REAL,
        total_debt_cr REAL,
        cash_from_operations_cr REAL,
        revenue_cagr_5yr REAL,
        pat_cagr_5yr REAL,
        eps_cagr_5yr REAL,
        composite_quality_score REAL,
        FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
    );
    """)
    conn.commit()


def categorize_anomaly(
    metric_type: str, year: str, computed: Optional[float], source: Optional[float]
) -> str:
    """
    Categorize ratio anomaly into Version Difference, Data Source Issue, or Formula Discrepancy.

    Args:
        metric_type: 'ROCE' or 'ROE'.
        year: The year of the financial record.
        computed: The computed value of the metric.
        source: The source value of the metric.

    Returns:
        The categorization label (str).
    """
    yr_str = str(year).strip()

    # If the record is historical, it is classified as a Version Difference
    # since companies.csv only contains the latest/TTM ratio.
    if yr_str not in ["TTM", "2024"]:
        return "Version Difference"

    # If computed or source is missing, or is zero/nan, it is a Data Source Issue
    if computed is None or source is None or computed == 0.0 or source == 0.0:
        return "Data Source Issue"

    # Otherwise, it represents a Formula Discrepancy
    return "Formula Discrepancy"


def main() -> None:
    """Execute ratio engine calculation and update SQLite financial_ratios table."""
    logger.info("Starting Nifty100 Ratio Engine...")

    # 1. Load processed CSV files
    logger.info("Loading processed CSV files...")
    try:
        pl_df = load_processed_csv(PROCESSED_DIR / "profitandloss.csv")
        bs_df = load_processed_csv(PROCESSED_DIR / "balancesheet.csv")
        cf_df = load_processed_csv(PROCESSED_DIR / "cashflow.csv")
        fr_df = load_processed_csv(PROCESSED_DIR / "financial_ratios.csv")
        sectors_df = load_processed_csv(PROCESSED_DIR / "sectors.csv")
        companies_df = load_processed_csv(PROCESSED_DIR / "companies.csv")
    except Exception as e:
        logger.error(f"Error loading processed datasets: {e}")
        return

    # De-duplicate base tables to ensure clean joins
    pl_unique = pl_df.drop_duplicates(subset=["company_id", "year"])
    bs_unique = bs_df.drop_duplicates(subset=["company_id", "year"])
    cf_unique = cf_df.drop_duplicates(subset=["company_id", "year"])
    sectors_unique = sectors_df.drop_duplicates(subset=["company_id"])
    companies_unique = companies_df.drop_duplicates(subset=["id"])

    logger.info(
        f"Unique records: P&L={len(pl_unique)}, BS={len(bs_unique)}, CF={len(cf_unique)}"
    )

    # 2. Merge datasets to align records
    logger.info("Merging financial statements...")

    # We use fr_df as the base table to preserve the exact set of company-years loaded in raw database
    # and retrieve pre-calculated fields like book_value_per_share.
    base_columns = [
        "company_id",
        "year",
        "book_value_per_share",
        "earnings_per_share",
        "dividend_payout_ratio_pct",
        "total_debt_cr",
        "cash_from_operations_cr",
    ]
    # Filter columns that are in fr_df
    available_cols = [c for c in base_columns if c in fr_df.columns]
    merged = fr_df[available_cols].copy()

    # Left-join with other tables to fill variables needed for ratios
    merged = pd.merge(merged, pl_unique, on=["company_id", "year"], how="left")
    merged = pd.merge(
        merged,
        bs_unique,
        on=["company_id", "year"],
        how="left",
        suffixes=("_pl", "_bs"),
    )
    merged = pd.merge(merged, cf_unique, on=["company_id", "year"], how="left")
    merged = pd.merge(
        merged,
        sectors_unique[["company_id", "broad_sector"]],
        on="company_id",
        how="left",
    )

    # Join with companies to get company_name, roce_percentage and roe_percentage
    merged = pd.merge(
        merged,
        companies_unique[["id", "company_name", "roce_percentage", "roe_percentage"]],
        left_on="company_id",
        right_on="id",
        how="left",
    )

    logger.info(f"Total merged records to process: {len(merged)}")

    # 3. Build lookup maps for CAGRs and rolling Quality Score
    sales_map = {}
    net_profit_map = {}
    eps_map = {}
    cfo_map = {}
    pat_map = {}

    for _, row in pl_unique.iterrows():
        cid = str(row["company_id"]).strip()
        try:
            yr = int(float(row["year"]))
        except (ValueError, TypeError):
            continue
        if pd.notna(row.get("sales")):
            sales_map[(cid, yr)] = float(row["sales"])
        if pd.notna(row.get("net_profit")):
            net_profit_map[(cid, yr)] = float(row["net_profit"])
            pat_map[(cid, yr)] = float(row["net_profit"])
        if pd.notna(row.get("eps")):
            eps_map[(cid, yr)] = float(row["eps"])

    for _, row in cf_unique.iterrows():
        cid = str(row["company_id"]).strip()
        try:
            yr = int(float(row["year"]))
        except (ValueError, TypeError):
            continue
        if pd.notna(row.get("operating_activity")):
            cfo_map[(cid, yr)] = float(row["operating_activity"])

    # 4. Perform calculations row-by-row & Cross-check
    logger.info("Executing calculations for all rows and cross-checking anomalies...")
    insert_data = []

    # Anomaly tracking structures
    roce_anomalies = []
    roe_anomalies = []
    category_counts = {
        "Version Difference": 0,
        "Data Source Issue": 0,
        "Formula Discrepancy": 0,
    }

    # Ensure output folder for anomalies exists
    ANOMALY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Open anomalies log file to write headers
    with open(ANOMALY_LOG_FILE, "w", encoding="utf-8") as anomaly_f:
        anomaly_f.write("--- RATIO ANOMALY DETECTION LOG ---\n")
        anomaly_f.write(
            "company_id | company_name | year | ratio_type | computed_value | source_value | absolute_difference | category\n"
        )
        anomaly_f.write("-" * 120 + "\n")

    for _, row in merged.iterrows():
        company_id = str(row["company_id"]).strip()
        company_name = (
            str(row.get("company_name")).strip()
            if pd.notna(row.get("company_name"))
            else "Unknown"
        )
        year = str(row["year"]).strip()
        broad_sector = (
            str(row.get("broad_sector")).strip()
            if pd.notna(row.get("broad_sector"))
            else ""
        )

        try:
            yr_int = int(float(year))
        except (ValueError, TypeError):
            yr_int = None

        # Profitability Ratios
        npm = calculate_net_profit_margin(row.get("net_profit"), row.get("sales"))
        opm = calculate_operating_profit_margin(
            row.get("operating_profit"), row.get("sales")
        )
        roe = calculate_roe(
            row.get("net_profit"), row.get("equity_capital"), row.get("reserves")
        )

        # Leverage Ratios (D/E checks suppress high leverage flag for Financials sector)
        d_e = calculate_debt_to_equity(
            row.get("borrowings"), row.get("equity_capital"), row.get("reserves")
        )
        icr_val, _ = calculate_interest_coverage_ratio(
            row.get("operating_profit"), row.get("other_income"), row.get("interest")
        )
        asset_turnover = calculate_asset_turnover(
            row.get("sales"), row.get("total_assets")
        )

        # Cash Flow KPIs
        fcf = calculate_free_cash_flow(
            row.get("operating_activity"), row.get("investing_activity")
        )
        capex = (
            abs(float(row["investing_activity"]))
            if pd.notna(row.get("investing_activity"))
            else None
        )

        # 5-year CAGRs
        rev_cagr = None
        pat_cagr = None
        eps_cagr = None
        if yr_int is not None:
            beg_year = yr_int - 5
            # Revenue CAGR
            s_end = sales_map.get((company_id, yr_int))
            s_beg = sales_map.get((company_id, beg_year))
            rev_cagr, _ = calculate_cagr(s_beg, s_end, 5)

            # PAT CAGR
            p_end = net_profit_map.get((company_id, yr_int))
            p_beg = net_profit_map.get((company_id, beg_year))
            pat_cagr, _ = calculate_cagr(p_beg, p_end, 5)

            # EPS CAGR
            e_end = eps_map.get((company_id, yr_int))
            e_beg = eps_map.get((company_id, beg_year))
            eps_cagr, _ = calculate_cagr(e_beg, e_end, 5)

        # Composite Quality Score (CFO / PAT average over previous 5 years)
        comp_quality_score = None
        if yr_int is not None:
            ratios_list = []
            for y_t in range(yr_int - 4, yr_int + 1):
                cfo_t = cfo_map.get((company_id, y_t))
                pat_t = pat_map.get((company_id, y_t))
                if (
                    cfo_t is not None
                    and pat_t is not None
                    and pat_t != 0.0
                    and not math.isnan(cfo_t)
                    and not math.isnan(pat_t)
                ):
                    ratios_list.append(cfo_t / pat_t)
                else:
                    ratios_list.append(None)
            comp_quality_score, _ = calculate_cfo_quality_score(ratios_list)

        # Retrieve precalculated values
        eps = (
            float(row["earnings_per_share"])
            if pd.notna(row.get("earnings_per_share"))
            else None
        )
        bvps = (
            float(row["book_value_per_share"])
            if pd.notna(row.get("book_value_per_share"))
            else None
        )
        div_payout = (
            float(row["dividend_payout_ratio_pct"])
            if pd.notna(row.get("dividend_payout_ratio_pct"))
            else None
        )
        total_debt = (
            float(row["total_debt_cr"]) if pd.notna(row.get("total_debt_cr")) else None
        )
        cfo = (
            float(row["cash_from_operations_cr"])
            if pd.notna(row.get("cash_from_operations_cr"))
            else None
        )

        # --- CROSS-CHECKS ---
        # 1. ROCE Cross-Check
        # Compute ROCE using core function
        pbt = (
            float(row["profit_before_tax"])
            if pd.notna(row.get("profit_before_tax"))
            else 0.0
        )
        interest_exp = float(row["interest"]) if pd.notna(row.get("interest")) else 0.0
        ebit = pbt + interest_exp

        roce_calc_res = calculate_roce(
            ebit=ebit,
            equity_capital=row.get("equity_capital"),
            reserves=row.get("reserves"),
            borrowings=row.get("borrowings"),
            broad_sector=broad_sector,
        )

        computed_roce = (
            roce_calc_res[0] if isinstance(roce_calc_res, tuple) else roce_calc_res
        )
        source_roce = (
            float(row["roce_percentage"])
            if pd.notna(row.get("roce_percentage"))
            else None
        )

        if computed_roce is not None and source_roce is not None:
            roce_diff = abs(computed_roce - source_roce)
            if roce_diff > 5.0:
                cat = categorize_anomaly("ROCE", year, computed_roce, source_roce)
                category_counts[cat] += 1
                roce_anomalies.append(
                    {
                        "company_id": company_id,
                        "company_name": company_name,
                        "year": year,
                        "computed": computed_roce,
                        "source": source_roce,
                        "diff": roce_diff,
                        "category": cat,
                    }
                )
                with open(ANOMALY_LOG_FILE, "a", encoding="utf-8") as anomaly_f:
                    anomaly_f.write(
                        f"{company_id} | {company_name} | {year} | ROCE | {computed_roce:.2f}% | {source_roce:.2f}% | {roce_diff:.2f}% | {cat}\n"
                    )

        # 2. ROE Cross-Check
        computed_roe = roe
        source_roe = (
            float(row["roe_percentage"])
            if pd.notna(row.get("roe_percentage"))
            else None
        )

        if computed_roe is not None and source_roe is not None:
            roe_diff = abs(computed_roe - source_roe)
            if roe_diff > 5.0:
                cat = categorize_anomaly("ROE", year, computed_roe, source_roe)
                category_counts[cat] += 1
                roe_anomalies.append(
                    {
                        "company_id": company_id,
                        "company_name": company_name,
                        "year": year,
                        "computed": computed_roe,
                        "source": source_roe,
                        "diff": roe_diff,
                        "category": cat,
                    }
                )
                with open(ANOMALY_LOG_FILE, "a", encoding="utf-8") as anomaly_f:
                    anomaly_f.write(
                        f"{company_id} | {company_name} | {year} | ROE | {computed_roe:.2f}% | {source_roe:.2f}% | {roe_diff:.2f}% | {cat}\n"
                    )

        # Clean NaN values to None for SQL INSERT
        values = [
            company_id,
            year,
            npm if (npm is not None and not math.isnan(npm)) else None,
            opm if (opm is not None and not math.isnan(opm)) else None,
            roe if (roe is not None and not math.isnan(roe)) else None,
            d_e if (d_e is not None and not math.isnan(d_e)) else None,
            icr_val if (icr_val is not None and not math.isnan(icr_val)) else None,
            (
                asset_turnover
                if (asset_turnover is not None and not math.isnan(asset_turnover))
                else None
            ),
            fcf if (fcf is not None and not math.isnan(fcf)) else None,
            capex if (capex is not None and not math.isnan(capex)) else None,
            eps if (eps is not None and not math.isnan(eps)) else None,
            bvps if (bvps is not None and not math.isnan(bvps)) else None,
            (
                div_payout
                if (div_payout is not None and not math.isnan(div_payout))
                else None
            ),
            (
                total_debt
                if (total_debt is not None and not math.isnan(total_debt))
                else None
            ),
            cfo if (cfo is not None and not math.isnan(cfo)) else None,
            rev_cagr if (rev_cagr is not None and not math.isnan(rev_cagr)) else None,
            pat_cagr if (pat_cagr is not None and not math.isnan(pat_cagr)) else None,
            eps_cagr if (eps_cagr is not None and not math.isnan(eps_cagr)) else None,
            (
                comp_quality_score
                if (
                    comp_quality_score is not None
                    and not math.isnan(comp_quality_score)
                )
                else None
            ),
        ]
        insert_data.append(values)

    # 5. Populate SQLite table
    logger.info(f"Connecting to database at {DB_FILE}...")
    try:
        conn = sqlite3.connect(DB_FILE)
        recreate_database_table(conn)

        cursor = conn.cursor()
        logger.info(f"Inserting {len(insert_data)} rows into financial_ratios...")

        cursor.executemany(
            """
        INSERT INTO financial_ratios (
            company_id,
            year,
            net_profit_margin_pct,
            operating_profit_margin_pct,
            return_on_equity_pct,
            debt_to_equity,
            interest_coverage,
            asset_turnover,
            free_cash_flow_cr,
            capex_cr,
            earnings_per_share,
            book_value_per_share,
            dividend_payout_ratio_pct,
            total_debt_cr,
            cash_from_operations_cr,
            revenue_cagr_5yr,
            pat_cagr_5yr,
            eps_cagr_5yr,
            composite_quality_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            insert_data,
        )

        conn.commit()

        # Verify row count
        cursor.execute("SELECT COUNT(*) FROM financial_ratios;")
        count = cursor.fetchone()[0]
        logger.info(f"Verification complete. Total rows in table: {count}")

    except Exception as e:
        logger.exception(f"Database operation failed: {e}")
    finally:
        if "conn" in locals():
            conn.close()

    # 6. Generate and append Summary Report to the log file and console
    total_anomalies = len(roce_anomalies) + len(roe_anomalies)

    summary_report = f"""
==================================================
              RATIO ANOMALY REPORT
==================================================
Total Anomalies Identified : {total_anomalies}
  - ROCE Mismatches (> 5%) : {len(roce_anomalies)}
  - ROE Mismatches (> 5%)  : {len(roe_anomalies)}

Category Breakdown:
  - Version Difference     : {category_counts["Version Difference"]}
  - Data Source Issue      : {category_counts["Data Source Issue"]}
  - Formula Discrepancy    : {category_counts["Formula Discrepancy"]}
==================================================
"""
    print(summary_report)

    with open(ANOMALY_LOG_FILE, "a", encoding="utf-8") as anomaly_f:
        anomaly_f.write(summary_report)

    logger.info(
        f"Anomaly detection details and summary saved to: {ANOMALY_LOG_FILE.resolve()}"
    )


if __name__ == "__main__":
    main()
