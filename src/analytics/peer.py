"""
Peer Group Percentile Analytics Module.

This module loads peer group data from 'data/raw/peer_groups.xlsx' (or database table 'peer_groups'),
calculates percentile ranks for 10 financial metrics within each of the 11 peer groups across years,
handles inverse percentile ranking for Debt-to-Equity (lower values receive higher percentile scores),
populates the 'peer_percentiles' SQLite table, and provides safe lookup utilities for unassigned companies.
"""

import logging
import math
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd

from src.analytics.ratios import calculate_roce

# Define project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_EXCEL_PATH = PROJECT_ROOT / "data" / "raw" / "peer_groups.xlsx"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "db" / "nifty100.db"

# Configure logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("peer_analytics")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_DIR / "peer_analytics.log", mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Metric definitions: (DB Column Name / Expression Name, Is Ascending / Higher is Better)
METRIC_DEFINITIONS: Dict[str, Tuple[str, bool]] = {
    "ROE": ("return_on_equity_pct", True),
    "ROCE": ("roce", True),
    "Net Profit Margin": ("net_profit_margin_pct", True),
    "Debt-to-Equity": ("debt_to_equity", False),  # Inverse ranking: lower value -> higher percentile rank
    "Free Cash Flow": ("free_cash_flow_cr", True),
    "PAT CAGR 5Y": ("pat_cagr_5yr", True),
    "Revenue CAGR 5Y": ("revenue_cagr_5yr", True),
    "EPS CAGR 5Y": ("eps_cagr_5yr", True),
    "Interest Coverage Ratio": ("interest_coverage", True),
    "Asset Turnover": ("asset_turnover", True),
}


def load_peer_groups(excel_path: Optional[Union[str, Path]] = None, db_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """
    Load peer group assignments from Excel or SQLite database.

    Args:
        excel_path: Path to peer_groups.xlsx.
        db_path: Path to nifty100.db database.

    Returns:
        pd.DataFrame containing 'company_id', 'peer_group_name', and 'is_benchmark'.
    """
    path_xl = Path(excel_path) if excel_path else DEFAULT_EXCEL_PATH
    path_db = Path(db_path) if db_path else DEFAULT_DB_PATH

    if path_xl.exists():
        logger.info(f"Loading peer groups from Excel file: {path_xl}")
        df = pd.read_excel(path_xl)
        df["company_id"] = df["company_id"].astype(str).str.strip()
        df["peer_group_name"] = df["peer_group_name"].astype(str).str.strip()
        return df

    if path_db.exists():
        logger.info(f"Loading peer groups from database table: {path_db}")
        conn = sqlite3.connect(path_db)
        try:
            df = pd.read_sql("SELECT company_id, peer_group_name, is_benchmark FROM peer_groups", conn)
            df["company_id"] = df["company_id"].astype(str).str.strip()
            df["peer_group_name"] = df["peer_group_name"].astype(str).str.strip()
            return df
        finally:
            conn.close()

    raise FileNotFoundError(f"Peer group source not found at '{path_xl}' or '{path_db}'.")


def get_company_peer_group(
    company_id: str,
    peer_groups_df: Optional[pd.DataFrame] = None,
    excel_path: Optional[Union[str, Path]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> str:
    """
    Retrieve the peer group name for a given company ID.

    If the company is not assigned to any peer group, returns "No peer group assigned".

    Args:
        company_id: Ticker / company identifier (e.g. 'HDFCBANK', 'ZOMATO').
        peer_groups_df: Optional preloaded peer groups DataFrame.
        excel_path: Path to peer_groups.xlsx.
        db_path: Path to SQLite DB.

    Returns:
        str: The peer group name, or "No peer group assigned".
    """
    cid_clean = str(company_id).strip()

    if peer_groups_df is None:
        try:
            peer_groups_df = load_peer_groups(excel_path=excel_path, db_path=db_path)
        except Exception as e:
            logger.warning(f"Failed to load peer groups: {e}")
            return "No peer group assigned"

    match = peer_groups_df[peer_groups_df["company_id"].astype(str).str.strip() == cid_clean]
    if match.empty:
        return "No peer group assigned"

    return str(match.iloc[0]["peer_group_name"]).strip()


def compute_roce_series(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Calculate ROCE for all company-year records from profitandloss, balancesheet, and sectors tables.

    Args:
        conn: Open SQLite connection.

    Returns:
        pd.DataFrame with columns: 'company_id', 'year', 'roce'.
    """
    pl_df = pd.read_sql("SELECT company_id, year, profit_before_tax, interest FROM profitandloss", conn)
    bs_df = pd.read_sql("SELECT company_id, year, equity_capital, reserves, borrowings FROM balancesheet", conn)
    sec_df = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)

    # De-duplicate inputs
    pl_df = pl_df.drop_duplicates(subset=["company_id", "year"])
    bs_df = bs_df.drop_duplicates(subset=["company_id", "year"])
    sec_df = sec_df.drop_duplicates(subset=["company_id"])

    merged = pd.merge(pl_df, bs_df, on=["company_id", "year"], how="outer")
    merged = pd.merge(merged, sec_df, on="company_id", how="left")

    roce_list = []
    for _, row in merged.iterrows():
        try:
            pbt = float(row["profit_before_tax"]) if pd.notna(row.get("profit_before_tax")) else 0.0
            interest_exp = float(row["interest"]) if pd.notna(row.get("interest")) else 0.0
            ebit = pbt + interest_exp
            roce_res = calculate_roce(
                ebit=ebit,
                equity_capital=row.get("equity_capital"),
                reserves=row.get("reserves"),
                borrowings=row.get("borrowings"),
                broad_sector=row.get("broad_sector"),
            )
            roce_val = roce_res[0] if isinstance(roce_res, tuple) else roce_res
            if roce_val is not None and not math.isnan(roce_val):
                roce_list.append(roce_val)
            else:
                roce_list.append(None)
        except Exception:
            roce_list.append(None)

    merged["roce"] = roce_list
    return merged[["company_id", "year", "roce"]].drop_duplicates(subset=["company_id", "year"])


def compute_peer_percentiles(
    db_path: Optional[Union[str, Path]] = None,
    excel_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """
    Compute percentile ranks within each peer group across years for all 10 financial metrics.

    Args:
        db_path: Path to SQLite database.
        excel_path: Path to peer_groups.xlsx file.

    Returns:
        pd.DataFrame: Calculated percentiles containing company_id, peer_group_name, metric, value, percentile_rank, year.
    """
    path_db = Path(db_path) if db_path else DEFAULT_DB_PATH
    peer_groups_df = load_peer_groups(excel_path=excel_path, db_path=db_path)

    conn = sqlite3.connect(path_db)
    try:
        # Load financial ratios table
        fr_df = pd.read_sql("""
            SELECT company_id, year, net_profit_margin_pct, return_on_equity_pct,
                   debt_to_equity, interest_coverage, asset_turnover, free_cash_flow_cr,
                   revenue_cagr_5yr, pat_cagr_5yr, eps_cagr_5yr
            FROM financial_ratios
        """, conn)

        fr_df["company_id"] = fr_df["company_id"].astype(str).str.strip()
        fr_df["year"] = fr_df["year"].astype(str).str.strip()
        fr_df = fr_df.drop_duplicates(subset=["company_id", "year"])

        # Compute ROCE
        roce_df = compute_roce_series(conn)
        roce_df["company_id"] = roce_df["company_id"].astype(str).str.strip()
        roce_df["year"] = roce_df["year"].astype(str).str.strip()

        # Merge financial ratios with ROCE
        financials = pd.merge(fr_df, roce_df, on=["company_id", "year"], how="left")

        # Merge with peer groups (inner join filters to companies in peer groups)
        merged = pd.merge(
            financials,
            peer_groups_df[["company_id", "peer_group_name"]],
            on="company_id",
            how="inner",
        )

        records = []
        for (peer_group, year), group_df in merged.groupby(["peer_group_name", "year"]):
            for metric_name, (col_name, higher_is_better) in METRIC_DEFINITIONS.items():
                if col_name in group_df.columns:
                    series = group_df[col_name].astype(float)
                    # Use pandas rank(pct=True)
                    # higher_is_better=True => ascending=True (higher value gets higher percentile rank)
                    # higher_is_better=False => ascending=False (lower value gets higher percentile rank)
                    ranks = series.rank(pct=True, ascending=higher_is_better, method="average", na_option="keep") * 100.0

                    for cid, raw_val, pct_rank in zip(group_df["company_id"], series, ranks):
                        val_out = float(raw_val) if pd.notna(raw_val) else None
                        rank_out = float(pct_rank) if pd.notna(pct_rank) else None

                        records.append({
                            "company_id": str(cid).strip(),
                            "peer_group_name": str(peer_group).strip(),
                            "metric": metric_name,
                            "value": val_out,
                            "percentile_rank": rank_out,
                            "year": str(year).strip(),
                        })

        df_result = pd.DataFrame(records)
        return df_result
    finally:
        conn.close()


def populate_peer_percentiles_table(
    db_path: Optional[Union[str, Path]] = None,
    excel_path: Optional[Union[str, Path]] = None,
) -> int:
    """
    Populate the 'peer_percentiles' table in the SQLite database with calculated ranks.

    Args:
        db_path: Path to SQLite database.
        excel_path: Path to peer_groups.xlsx.

    Returns:
        int: Number of rows inserted into peer_percentiles.
    """
    path_db = Path(db_path) if db_path else DEFAULT_DB_PATH
    logger.info("Computing peer percentiles...")
    df_percentiles = compute_peer_percentiles(db_path=path_db, excel_path=excel_path)

    logger.info(f"Connecting to database at {path_db} to populate peer_percentiles...")
    conn = sqlite3.connect(path_db)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys = ON;")
        logger.info("Recreating peer_percentiles table...")
        cursor.execute("DROP TABLE IF EXISTS peer_percentiles;")
        cursor.execute("""
            CREATE TABLE peer_percentiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id TEXT NOT NULL,
                peer_group_name TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL,
                percentile_rank REAL,
                year TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
            );
        """)

        insert_tuples = [
            (
                row["company_id"],
                row["peer_group_name"],
                row["metric"],
                row["value"],
                row["percentile_rank"],
                row["year"],
            )
            for _, row in df_percentiles.iterrows()
        ]

        logger.info(f"Inserting {len(insert_tuples)} records into peer_percentiles...")
        cursor.executemany("""
            INSERT INTO peer_percentiles (
                company_id, peer_group_name, metric, value, percentile_rank, year
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, insert_tuples)

        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM peer_percentiles;")
        inserted_count = cursor.fetchone()[0]
        logger.info(f"Verification complete. Total rows in peer_percentiles table: {inserted_count}")
        return inserted_count
    except Exception as e:
        conn.rollback()
        logger.exception(f"Failed to populate peer_percentiles table: {e}")
        raise e
    finally:
        conn.close()


def get_peer_percentiles_for_company(
    company_id: str,
    year: Optional[Union[str, int]] = None,
    db_path: Optional[Union[str, Path]] = None,
    excel_path: Optional[Union[str, Path]] = None,
) -> Union[str, pd.DataFrame]:
    """
    Get peer percentiles for a specific company and optional year.

    If the company is not assigned to any peer group, returns "No peer group assigned".

    Args:
        company_id: Ticker symbol (e.g. 'HDFCBANK', 'ZOMATO').
        year: Optional year string or integer.
        db_path: Path to SQLite database.
        excel_path: Path to peer_groups.xlsx.

    Returns:
        Union[str, pd.DataFrame]: "No peer group assigned" if unassigned,
        otherwise a DataFrame containing peer percentiles.
    """
    cid_clean = str(company_id).strip()
    peer_group = get_company_peer_group(cid_clean, excel_path=excel_path, db_path=db_path)

    if peer_group == "No peer group assigned":
        return "No peer group assigned"

    path_db = Path(db_path) if db_path else DEFAULT_DB_PATH

    conn = sqlite3.connect(path_db)
    try:
        query = "SELECT company_id, peer_group_name, metric, value, percentile_rank, year FROM peer_percentiles WHERE company_id = ?"
        params = [cid_clean]

        if year is not None:
            query += " AND year = ?"
            params.append(str(year).strip())

        df = pd.read_sql(query, conn, params=params)
        if df.empty:
            # Table might not be populated yet, compute dynamically
            df_all = compute_peer_percentiles(db_path=path_db, excel_path=excel_path)
            df = df_all[df_all["company_id"] == cid_clean]
            if year is not None:
                df = df[df["year"] == str(year).strip()]

        return df
    finally:
        conn.close()


def main() -> None:
    """Main execution block."""
    logger.info("Executing Peer Analytics Pipeline...")
    row_count = populate_peer_percentiles_table()
    logger.info(f"Peer percentiles pipeline finished successfully. Total records populated: {row_count}")


if __name__ == "__main__":
    main()
