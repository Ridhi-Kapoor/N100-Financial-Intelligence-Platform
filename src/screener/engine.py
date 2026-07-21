"""
Screener Engine Module.

This module provides functions to load financial data from the Nifty100 database,
parse screening criteria from a YAML configuration file, apply those criteria
across 15 key financial metrics with industry-specific overrides, and return the
results sorted by their composite quality score.
"""

import logging
import math
from pathlib import Path
from typing import Dict, Any, Optional, Union
import sqlite3
import pandas as pd
import yaml

# Set up logging
logger = logging.getLogger("screener_engine")
logger.setLevel(logging.INFO)

# Map human-readable filter names and database column aliases to actual DataFrame column names
METRIC_MAPPING: Dict[str, str] = {
    # ROE
    "roe": "return_on_equity_pct",
    "roe (min)": "return_on_equity_pct",
    "return_on_equity_pct": "return_on_equity_pct",
    "return_on_equity": "return_on_equity_pct",
    
    # Debt-to-Equity
    "debt-to-equity": "debt_to_equity",
    "debt_to_equity": "debt_to_equity",
    "debt-to-equity (max)": "debt_to_equity",
    
    # Free Cash Flow
    "free cash flow": "free_cash_flow_cr",
    "free_cash_flow": "free_cash_flow_cr",
    "free_cash_flow_cr": "free_cash_flow_cr",
    "free cash flow (min)": "free_cash_flow_cr",
    
    # Revenue CAGR 5Y
    "revenue cagr 5y": "revenue_cagr_5yr",
    "revenue_cagr_5yr": "revenue_cagr_5yr",
    "revenue cagr 5y (min)": "revenue_cagr_5yr",
    
    # PAT CAGR 5Y
    "pat cagr 5y": "pat_cagr_5yr",
    "pat_cagr_5yr": "pat_cagr_5yr",
    "pat cagr 5y (min)": "pat_cagr_5yr",
    
    # Operating Profit Margin
    "operating profit margin": "operating_profit_margin_pct",
    "operating_profit_margin_pct": "operating_profit_margin_pct",
    "operating profit margin (min)": "operating_profit_margin_pct",
    "opm": "operating_profit_margin_pct",
    
    # P/E
    "p/e": "pe_ratio",
    "pe": "pe_ratio",
    "pe_ratio": "pe_ratio",
    "p/e (max)": "pe_ratio",
    
    # P/B
    "p/b": "pb_ratio",
    "pb": "pb_ratio",
    "pb_ratio": "pb_ratio",
    "p/b (max)": "pb_ratio",
    
    # Dividend Yield
    "dividend yield": "dividend_yield_pct",
    "dividend_yield": "dividend_yield_pct",
    "dividend_yield_pct": "dividend_yield_pct",
    "dividend yield (min)": "dividend_yield_pct",
    
    # Interest Coverage Ratio
    "interest coverage ratio": "interest_coverage",
    "interest_coverage": "interest_coverage",
    "interest coverage ratio (min)": "interest_coverage",
    "icr": "interest_coverage",
    
    # Market Cap
    "market cap": "market_cap_crore",
    "market_cap_crore": "market_cap_crore",
    "market cap (min)": "market_cap_crore",
    
    # Net Profit
    "net profit": "net_profit",
    "net_profit": "net_profit",
    "net profit (min)": "net_profit",
    
    # EPS CAGR
    "eps cagr": "eps_cagr_5yr",
    "eps_cagr_5yr": "eps_cagr_5yr",
    "eps cagr (min)": "eps_cagr_5yr",
    
    # Asset Turnover
    "asset turnover": "asset_turnover",
    "asset_turnover": "asset_turnover",
    "asset turnover (min)": "asset_turnover",
    
    # Sales
    "sales": "sales",
    "sales (min)": "sales"
}


def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load screen filter thresholds from a YAML configuration file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        A dictionary containing the configuration keys.
    """
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Configuration file not found at {path.resolve()}. Returning empty dictionary.")
        return {}
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config or {}
    except Exception as e:
        logger.error(f"Failed to parse YAML configuration at {path.resolve()}: {e}")
        raise ValueError(f"Error parsing YAML config: {e}") from e


def is_financial_sector(row: Any) -> bool:
    """
    Check if the company-year record belongs to the Financials sector.

    Args:
        row: A pandas Series or dictionary-like object representing a row of financial data.

    Returns:
        bool: True if sector is 'Financials' (case-insensitive), False otherwise.
    """
    sector = row.get("broad_sector") or row.get("sector")
    if sector is not None and pd.notna(sector):
        return str(sector).strip().lower() == "financials"
    return False


def is_debt_free(row: Any) -> bool:
    """
    Determine if a company-year record is debt-free.

    A company is considered debt-free if:
    1. Its interest expense is explicitly 0.0
    2. Its Debt-to-Equity ratio is explicitly 0.0
    3. Its total debt is explicitly 0.0
    4. Its borrowings are explicitly 0.0

    Args:
        row: A pandas Series or dictionary-like object representing a row of financial data.

    Returns:
        bool: True if the company is debt-free based on available indicators, False otherwise.
    """
    # 1. Check interest expense
    interest = row.get("interest")
    if interest is not None and pd.notna(interest) and float(interest) == 0.0:
        return True
        
    # 2. Check Debt-to-Equity
    de = row.get("debt_to_equity")
    if de is not None and pd.notna(de) and float(de) == 0.0:
        return True
        
    # 3. Check total debt in Crores
    total_debt = row.get("total_debt_cr")
    if total_debt is not None and pd.notna(total_debt) and float(total_debt) == 0.0:
        return True
        
    # 4. Check borrowings
    borrowings = row.get("borrowings")
    if borrowings is not None and pd.notna(borrowings) and float(borrowings) == 0.0:
        return True
        
    return False


def add_composite_quality_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure the 'composite_quality_score' column exists in the DataFrame.
    If it is not present, compute it dynamically as the 5-year average of CFO / PAT.

    Args:
        df: Input DataFrame.

    Returns:
        DataFrame containing the 'composite_quality_score' column.
    """
    df = df.copy()
    if "composite_quality_score" in df.columns:
        df["composite_quality_score"] = pd.to_numeric(df["composite_quality_score"], errors="coerce")
        return df
        
    logger.info("Column 'composite_quality_score' not found. Calculating dynamically...")
    
    # Locate CFO and PAT columns
    cfo_col = None
    for col in ["cash_from_operations_cr", "operating_activity", "cfo"]:
        if col in df.columns:
            cfo_col = col
            break
            
    pat_col = None
    for col in ["net_profit", "net_profit_pl", "pat"]:
        if col in df.columns:
            pat_col = col
            break
            
    if not cfo_col or not pat_col:
        logger.warning(
            f"Unable to calculate composite_quality_score. "
            f"Missing CFO column (found: {cfo_col}) or PAT column (found: {pat_col}). "
            f"Setting composite_quality_score to NaN."
        )
        df["composite_quality_score"] = pd.NA
        return df

    # Map variables to (company_id, year) for fast historical lookup
    cfo_map = {}
    pat_map = {}
    for _, row in df.iterrows():
        comp_id = str(row["company_id"]).strip()
        try:
            yr = int(float(row["year"]))
        except (ValueError, TypeError):
            continue
        
        cfo_val = row[cfo_col]
        pat_val = row[pat_col]
        
        if pd.notna(cfo_val):
            cfo_map[(comp_id, yr)] = float(cfo_val)
        if pd.notna(pat_val):
            pat_map[(comp_id, yr)] = float(pat_val)
            
    scores = []
    for _, row in df.iterrows():
        comp_id = str(row["company_id"]).strip()
        try:
            yr = int(float(row["year"]))
        except (ValueError, TypeError):
            scores.append(None)
            continue
            
        ratios = []
        for y_t in range(yr - 4, yr + 1):
            cfo_t = cfo_map.get((comp_id, y_t))
            pat_t = pat_map.get((comp_id, y_t))
            
            if (
                cfo_t is not None 
                and pat_t is not None 
                and pat_t != 0.0 
                and not math.isnan(cfo_t) 
                and not math.isnan(pat_t)
            ):
                ratios.append(cfo_t / pat_t)
            else:
                ratios.append(None)
                
        # Must have exactly 5 years of valid ratios to compute average
        valid_ratios = [r for r in ratios if r is not None]
        if len(valid_ratios) < 5:
            scores.append(None)
        else:
            scores.append(sum(valid_ratios) / 5.0)
            
    df["composite_quality_score"] = scores
    df["composite_quality_score"] = pd.to_numeric(df["composite_quality_score"], errors="coerce")
    return df


def load_screener_data(db_path: Union[str, Path], year: Optional[Union[str, int]] = None) -> pd.DataFrame:
    """
    Query the SQLite database and construct the base DataFrame with all 15 metrics.

    Args:
        db_path: Path to the nifty100.db SQLite database.
        year: Optional year string or integer (e.g. 2024 or '2024'). If None, loads all years.

    Returns:
        A pandas DataFrame ready for screening.
    """
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"SQLite Database not found at: {path.resolve()}")
        
    conn = sqlite3.connect(path)
    try:
        # Load tables
        df_ratios = pd.read_sql_query("SELECT * FROM financial_ratios", conn)
        df_companies = pd.read_sql_query("SELECT id, company_name, roce_percentage FROM companies", conn)
        df_sectors = pd.read_sql_query("SELECT company_id, broad_sector FROM sectors", conn)
        df_market_cap = pd.read_sql_query("SELECT company_id, year, market_cap_crore, pe_ratio, pb_ratio, dividend_yield_pct FROM market_cap", conn)
        df_pl = pd.read_sql_query("SELECT company_id, year, sales, net_profit FROM profitandloss", conn)
        
        # Clean and standardise join keys
        for df_tmp in [df_ratios, df_sectors, df_market_cap, df_pl]:
            df_tmp["company_id"] = df_tmp["company_id"].astype(str).str.strip()
            
        for df_tmp in [df_ratios, df_market_cap, df_pl]:
            df_tmp["year"] = df_tmp["year"].astype(str).str.strip()
            
        df_companies["id"] = df_companies["id"].astype(str).str.strip()
        
        # Merge tables
        merged = pd.merge(df_ratios, df_companies, left_on="company_id", right_on="id", how="left")
        merged.drop(columns=["id_y"], errors="ignore", inplace=True)
        if "id_x" in merged.columns:
            merged.rename(columns={"id_x": "id"}, inplace=True)
            
        merged = pd.merge(merged, df_sectors, on="company_id", how="left")
        merged = pd.merge(merged, df_market_cap, on=["company_id", "year"], how="left")
        merged = pd.merge(merged, df_pl, on=["company_id", "year"], how="left", suffixes=("", "_pl"))
        
        # Ensure we have the raw variables for is_debt_free detection
        # Since 'interest' and 'borrowings' might be needed, load them as well from PL and BS
        df_bs = pd.read_sql_query("SELECT company_id, year, borrowings FROM balancesheet", conn)
        df_bs["company_id"] = df_bs["company_id"].astype(str).str.strip()
        df_bs["year"] = df_bs["year"].astype(str).str.strip()
        
        merged = pd.merge(merged, df_bs, on=["company_id", "year"], how="left")
        
        df_pl_interest = pd.read_sql_query("SELECT company_id, year, interest FROM profitandloss", conn)
        df_pl_interest["company_id"] = df_pl_interest["company_id"].astype(str).str.strip()
        df_pl_interest["year"] = df_pl_interest["year"].astype(str).str.strip()
        
        merged = pd.merge(merged, df_pl_interest, on=["company_id", "year"], how="left", suffixes=("", "_pl_interest"))
        
        # Resolve year filtering
        if year is not None:
            year_str = str(year).strip()
            merged = merged[merged["year"] == year_str].copy()
            
        # Deduplicate to prevent multiple rows for the same company-year
        merged = merged.drop_duplicates(subset=["company_id", "year"]).copy()
            
        return merged
        
    finally:
        conn.close()


def apply_screener_filters(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Apply filter thresholds loaded from the configuration file to the financial ratios DataFrame.

    Args:
        df: Input DataFrame containing financial ratios and metadata.
        config: Configuration dictionary (typically containing a 'filters' block).

    Returns:
        Filtered DataFrame sorted in descending order of composite_quality_score.
    """
    if df is None or df.empty:
        logger.info("Input DataFrame is empty or None. Returning empty DataFrame.")
        return pd.DataFrame()
        
    df_filtered = df.copy()
    
    # 1. Add composite_quality_score if not exists
    df_filtered = add_composite_quality_score(df_filtered)
    
    # 2. Extract filters
    filters = config.get("filters", {})
    if not filters:
        logger.info("No active filters found in config. Returning sorted base DataFrame.")
        return df_filtered.sort_values(
            by="composite_quality_score", ascending=False, na_position="last"
        ).reset_index(drop=True)
        
    # 3. Apply filters row-by-row to accommodate complex logic overrides
    keep_indices = []
    
    for idx, row in df_filtered.iterrows():
        keep_row = True
        
        # Precompute overrides for the company-year row
        is_fin = is_financial_sector(row)
        is_df = is_debt_free(row)
        
        for filter_name, thresholds in filters.items():
            if not thresholds:
                continue
                
            # Resolve filter name to actual database column name
            col_name = METRIC_MAPPING.get(str(filter_name).lower().strip())
            if not col_name:
                logger.warning(f"Filtering skipped: Metric name '{filter_name}' is not recognized.")
                continue
                
            if col_name not in df_filtered.columns:
                logger.warning(f"Filtering skipped: Column '{col_name}' corresponding to '{filter_name}' is missing.")
                continue
                
            val = row[col_name]
            
            # Check minimum filter threshold
            if "min" in thresholds:
                min_val = thresholds["min"]
                if min_val is not None:
                    # Exception: Treat "Debt Free" companies as having infinite ICR
                    if col_name == "interest_coverage" and is_df:
                        pass
                    else:
                        if val is None or pd.isna(val) or float(val) < float(min_val):
                            keep_row = False
                            break
                            
            # Check maximum filter threshold
            if "max" in thresholds:
                max_val = thresholds["max"]
                if max_val is not None:
                    # Exception: Skip Financial sector companies when applying the Debt-to-Equity filter
                    if col_name == "debt_to_equity" and is_fin:
                        pass
                    else:
                        if val is None or pd.isna(val) or float(val) > float(max_val):
                            keep_row = False
                            break
                            
        if keep_row:
            keep_indices.append(idx)
            
    df_result = df_filtered.loc[keep_indices].copy()
    
    # 4. Sort descending by composite_quality_score
    df_result = df_result.sort_values(
        by="composite_quality_score", ascending=False, na_position="last"
    ).reset_index(drop=True)
    
    return df_result
