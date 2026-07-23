"""
Module for calculating Compound Annual Growth Rate (CAGR) and classification flags.

This module provides functions to calculate CAGR for financial metrics (Revenue, PAT, EPS)
over 3, 5, and 10 year periods. It handles various financial edge cases such as
zero beginning values, turnarounds, decline to loss, and insufficient data.
"""

import logging
import math
from pathlib import Path
from typing import Optional, Tuple, Union
import pandas as pd

# Configure the logger for CAGR validation
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

cagr_logger = logging.getLogger("cagr_analytics")
cagr_logger.setLevel(logging.INFO)

if not cagr_logger.handlers:
    cagr_file = LOG_DIR / "cagr_analytics.log"
    file_handler = logging.FileHandler(cagr_file, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    cagr_logger.addHandler(file_handler)


def calculate_cagr(
    beginning_value: Optional[Union[float, int]],
    ending_value: Optional[Union[float, int]],
    n: int,
) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate the Compound Annual Growth Rate (CAGR) and return the value and classification flag.

    Formula:
        CAGR = ((Ending Value / Beginning Value)^(1/n) - 1) * 100

    Edge Cases:
        - Positive -> Positive: Return CAGR normally. Flag is None.
        - Positive -> Negative: Return None. Flag = 'DECLINE_TO_LOSS'.
        - Negative -> Positive: Return None. Flag = 'TURNAROUND'.
        - Negative -> Negative: Return None. Flag = 'BOTH_NEGATIVE'.
        - Beginning Value = 0: Return None. Flag = 'ZERO_BASE'.
        - Insufficient years of data: Return None. Flag = 'INSUFFICIENT'.

    Args:
        beginning_value: The starting value of the metric (float/int).
        ending_value: The ending value of the metric (float/int).
        n: The number of years/periods (int).

    Returns:
        Tuple[Optional[float], Optional[str]]:
            - CAGR value as a percentage (float), or None if it cannot be calculated.
            - Classification flag (str), or None if calculation was normal.
    """
    if beginning_value is None or ending_value is None or n is None:
        return None, "INSUFFICIENT"

    try:
        beg_val = float(beginning_value)
        end_val = float(ending_value)
        n_val = int(n)
    except (ValueError, TypeError) as e:
        cagr_logger.warning(
            f"CAGR calculation failed: Invalid input types (beg={beginning_value}, end={ending_value}, n={n}). Error: {e}"
        )
        return None, "INSUFFICIENT"

    if math.isnan(beg_val) or math.isnan(end_val):
        return None, "INSUFFICIENT"

    if n_val <= 0:
        cagr_logger.warning(
            f"CAGR calculation failed: Number of years n={n_val} must be greater than 0."
        )
        return None, "INSUFFICIENT"

    if beg_val == 0.0:
        return None, "ZERO_BASE"

    if beg_val > 0.0:
        if end_val < 0.0:
            return None, "DECLINE_TO_LOSS"
        else:
            try:
                cagr = ((end_val / beg_val) ** (1.0 / n_val) - 1.0) * 100.0
                return cagr, None
            except Exception as e:
                cagr_logger.error(f"Unexpected error in CAGR calculation: {e}")
                return None, "INSUFFICIENT"
    else:  # beg_val < 0.0
        if end_val >= 0.0:
            return None, "TURNAROUND"
        else:
            return None, "BOTH_NEGATIVE"


def compute_dataframe_cagr(
    df: pd.DataFrame,
    metric_col: str,
    n_years: int,
    output_val_col: str,
    output_flag_col: str,
) -> Tuple[list, list]:
    """
    Compute CAGR values and flags for a specific metric column in a DataFrame over n_years.

    Args:
        df: Input DataFrame containing 'company_id', 'year', and metric_col.
        metric_col: The column name of the metric to compute CAGR for.
        n_years: The number of years for the CAGR period.
        output_val_col: The column name of the output CAGR value.
        output_flag_col: The column name of the output classification flag.

    Returns:
        Tuple[list, list]:
            - List of calculated CAGR values.
            - List of classification flags.
    """
    # Create lookup map: (company_id, year) -> metric_value
    lookup = {}
    for _, row in df.iterrows():
        try:
            cid = str(row["company_id"]).strip()
            yr = int(float(row["year"]))
            val = float(row[metric_col]) if pd.notna(row[metric_col]) else None
            if val is not None and not math.isnan(val):
                lookup[(cid, yr)] = val
        except (ValueError, TypeError):
            continue

    cagr_values = []
    cagr_flags = []

    for _, row in df.iterrows():
        try:
            cid = str(row["company_id"]).strip()
            if pd.isna(row["year"]):
                cagr_values.append(None)
                cagr_flags.append("INSUFFICIENT")
                continue
            yr_end = int(float(row["year"]))
            end_val = lookup.get((cid, yr_end))
            yr_beg = yr_end - n_years
            beg_val = lookup.get((cid, yr_beg))

            if beg_val is None or end_val is None:
                cagr_values.append(None)
                cagr_flags.append("INSUFFICIENT")
            else:
                val, flag = calculate_cagr(beg_val, end_val, n_years)
                cagr_values.append(val)
                cagr_flags.append(flag)
        except Exception as e:
            cagr_logger.debug(f"Exception during DataFrame CAGR row lookup: {e}")
            cagr_values.append(None)
            cagr_flags.append("INSUFFICIENT")

    return cagr_values, cagr_flags
