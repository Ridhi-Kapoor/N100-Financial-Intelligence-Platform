"""
Module for calculating and validating key financial profitability ratios.

This module provides functions to calculate:
- Net Profit Margin (NPM)
- Operating Profit Margin (OPM)
- Return on Equity (ROE)
- Return on Capital Employed (ROCE)
- Return on Assets (ROA)

It also includes validation logic for OPM mismatches (logging to a dedicated file)
and benchmark calculations for the Financials sector.
"""

import logging
import math
from pathlib import Path
from typing import Optional, Tuple, Union
import pandas as pd

# Define paths for logging
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "opm_validation.log"

# Create logs directory if it does not exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure the logger for OPM validation
opm_logger = logging.getLogger("opm_validation")
opm_logger.setLevel(logging.INFO)

# Set up file handler if not already present
if not opm_logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    opm_logger.addHandler(file_handler)


def calculate_net_profit_margin(
    net_profit: Optional[float], sales: Optional[float]
) -> Optional[float]:
    """
    Calculate the Net Profit Margin.

    Formula:
        Net Profit Margin = (Net Profit / Sales) * 100

    Args:
        net_profit: The net profit of the company (float).
        sales: The sales/revenue of the company (float).

    Returns:
        The Net Profit Margin as a percentage (float), or None if sales is 0
        or inputs are invalid/None.
    """
    if net_profit is None or sales is None:
        return None

    try:
        net_profit_val = float(net_profit)
        sales_val = float(sales)
    except (ValueError, TypeError):
        return None

    # Handle division by zero and invalid numeric inputs (e.g. NaN)
    if sales_val == 0.0 or math.isnan(sales_val) or math.isnan(net_profit_val):
        return None

    return (net_profit_val / sales_val) * 100.0


def calculate_operating_profit_margin(
    operating_profit: Optional[float], sales: Optional[float]
) -> Optional[float]:
    """
    Calculate the Operating Profit Margin (OPM).

    Formula:
        Operating Profit Margin = (Operating Profit / Sales) * 100

    Args:
        operating_profit: The operating profit of the company (float).
        sales: The sales/revenue of the company (float).

    Returns:
        The Operating Profit Margin as a percentage (float), or None if sales is 0
        or inputs are invalid/None.
    """
    if operating_profit is None or sales is None:
        return None

    try:
        op_profit_val = float(operating_profit)
        sales_val = float(sales)
    except (ValueError, TypeError):
        return None

    # Handle division by zero and invalid numeric inputs (e.g. NaN)
    if sales_val == 0.0 or math.isnan(sales_val) or math.isnan(op_profit_val):
        return None

    return (op_profit_val / sales_val) * 100.0


def validate_operating_profit_margin(
    calculated_opm: Optional[float],
    source_opm: Optional[float],
    company_id: Optional[str] = None,
    company_name: Optional[str] = None,
    year: Optional[Union[int, str]] = None,
) -> bool:
    """
    Validate the calculated Operating Profit Margin against a source value.

    If the absolute difference between the calculated OPM and the source OPM
    exceeds 1%, the discrepancy is logged to 'logs/opm_validation.log' and the
    function returns False. Otherwise, returns True.

    Args:
        calculated_opm: The calculated OPM percentage (float).
        source_opm: The source OPM percentage (float) from raw records.
        company_id: Optional unique identifier of the company.
        company_name: Optional name of the company.
        year: Optional year of the record.

    Returns:
        bool: True if the difference is <= 1%, False if it exceeds 1% or inputs are invalid.
    """
    if calculated_opm is None or source_opm is None:
        return False

    try:
        calc_val = float(calculated_opm)
        src_val = float(source_opm)
    except (ValueError, TypeError):
        return False

    if math.isnan(calc_val) or math.isnan(src_val):
        return False

    difference = abs(calc_val - src_val)

    if difference > 1.0:
        # Log mismatch
        log_msg = (
            f"OPM Mismatch - Company ID: {company_id or 'N/A'}, "
            f"Company Name: {company_name or 'N/A'}, Year: {year or 'N/A'}, "
            f"Calculated OPM: {calc_val:.2f}%, Source OPM: {src_val:.2f}%, "
            f"Difference: {difference:.2f}%"
        )
        opm_logger.warning(log_msg)
        return False

    return True


def calculate_roe(
    net_profit: Optional[float],
    equity_capital: Optional[float],
    reserves: Optional[float],
) -> Optional[float]:
    """
    Calculate the Return on Equity (ROE).

    Formula:
        Return on Equity = net_profit / (equity_capital + reserves) * 100

    Args:
        net_profit: Net profit of the company (float).
        equity_capital: Equity capital of the company (float).
        reserves: Reserves of the company (float).

    Returns:
        ROE percentage (float), or None if denominator (equity_capital + reserves) <= 0
        or inputs are invalid/None.
    """
    if net_profit is None or equity_capital is None or reserves is None:
        return None

    try:
        np_val = float(net_profit)
        eq_val = float(equity_capital)
        res_val = float(reserves)
    except (ValueError, TypeError):
        return None

    denominator = eq_val + res_val

    if denominator <= 0.0 or math.isnan(denominator) or math.isnan(np_val):
        return None

    return (np_val / denominator) * 100.0


def calculate_roce(
    ebit: Optional[float],
    equity_capital: Optional[float],
    reserves: Optional[float],
    borrowings: Optional[float],
    broad_sector: Optional[str],
    benchmark_roce: Optional[float] = None,
) -> Union[Optional[float], Tuple[Optional[float], Optional[str]]]:
    """
    Calculate the Return on Capital Employed (ROCE).

    Formula:
        Return on Capital Employed = EBIT / (equity_capital + reserves + borrowings) * 100

    For companies whose broad_sector == "Financials":
        Returns a tuple of (ROCE, benchmark_status).
        If benchmark_roce is provided, benchmark_status is 'Above Benchmark' or 'Below Benchmark'.
        Otherwise, benchmark_status is None.

    For other companies:
        Returns ROCE (float or None).

    Args:
        ebit: Earnings Before Interest and Taxes (float).
        equity_capital: Equity capital of the company (float).
        reserves: Reserves of the company (float).
        borrowings: Borrowings of the company (float).
        broad_sector: Sector of the company (str).
        benchmark_roce: Optional sector benchmark ROCE (float).

    Returns:
        ROCE float/None, or a tuple of (ROCE, benchmark_status) for Financials.
    """
    is_financial = broad_sector == "Financials"

    if ebit is None or equity_capital is None or reserves is None or borrowings is None:
        return (None, None) if is_financial else None

    try:
        ebit_val = float(ebit)
        eq_val = float(equity_capital)
        res_val = float(reserves)
        bor_val = float(borrowings)
    except (ValueError, TypeError):
        return (None, None) if is_financial else None

    denominator = eq_val + res_val + bor_val

    if denominator <= 0.0 or math.isnan(denominator) or math.isnan(ebit_val):
        return (None, None) if is_financial else None

    roce = (ebit_val / denominator) * 100.0

    if is_financial:
        benchmark_status = None
        if benchmark_roce is not None:
            try:
                bench_val = float(benchmark_roce)
                if not math.isnan(bench_val):
                    benchmark_status = (
                        "Above Benchmark" if roce >= bench_val else "Below Benchmark"
                    )
            except (ValueError, TypeError):
                pass
        return roce, benchmark_status

    return roce


def calculate_roa(
    net_profit: Optional[float], total_assets: Optional[float]
) -> Optional[float]:
    """
    Calculate the Return on Assets (ROA).

    Formula:
        Return on Assets = (Net Profit / Total Assets) * 100

    Args:
        net_profit: The net profit of the company (float).
        total_assets: The total assets of the company (float).

    Returns:
        The ROA percentage (float), or None if total_assets is 0 or inputs are invalid/None.
    """
    if net_profit is None or total_assets is None:
        return None

    try:
        np_val = float(net_profit)
        assets_val = float(total_assets)
    except (ValueError, TypeError):
        return None

    if assets_val == 0.0 or math.isnan(assets_val) or math.isnan(np_val):
        return None

    return (np_val / assets_val) * 100.0


def get_financial_sector_roce_benchmark(
    df: pd.DataFrame,
) -> Optional[float]:
    """
    Calculate the average ROCE for companies in the 'Financials' sector.

    Args:
        df: A pandas DataFrame containing at least 'broad_sector' and 'roce' columns.

    Returns:
        The average ROCE of the Financials sector as a float, or None if no data is available.
    """
    if df is None or df.empty:
        return None

    if "broad_sector" not in df.columns or "roce" not in df.columns:
        return None

    # Filter for companies in the 'Financials' sector
    financials_df = df[df["broad_sector"] == "Financials"]
    if financials_df.empty:
        return None

    # Cast ROCE column to numeric and drop NaNs
    roces = pd.to_numeric(financials_df["roce"], errors="coerce").dropna()
    if roces.empty:
        return None

    return float(roces.mean())


# Configure the logger for leverage ratios
leverage_logger = logging.getLogger("leverage_efficiency")
leverage_logger.setLevel(logging.INFO)
LEVERAGE_LOG_FILE = LOG_DIR / "leverage_efficiency.log"
if not leverage_logger.handlers:
    leverage_file_handler = logging.FileHandler(
        LEVERAGE_LOG_FILE, mode="a", encoding="utf-8"
    )
    leverage_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    leverage_file_handler.setFormatter(leverage_formatter)
    leverage_logger.addHandler(leverage_file_handler)


def calculate_debt_to_equity(
    borrowings: Optional[Union[float, int]],
    equity_capital: Optional[Union[float, int]],
    reserves: Optional[Union[float, int]],
) -> Optional[float]:
    """
    Calculate the Debt-to-Equity ratio.

    Formula:
        Debt-to-Equity = borrowings / (equity_capital + reserves)

    Args:
        borrowings: Total borrowings of the company.
        equity_capital: Equity capital of the company.
        reserves: Reserves of the company.

    Returns:
        The Debt-to-Equity ratio as a float, 0.0 if borrowings is 0,
        or None if the denominator is <= 0 or inputs are invalid.
    """
    if borrowings is None or equity_capital is None or reserves is None:
        return None

    try:
        borrowings_val = float(borrowings)
        equity_val = float(equity_capital)
        reserves_val = float(reserves)
    except (ValueError, TypeError) as e:
        leverage_logger.warning(
            f"Invalid input types for Debt-to-Equity calculation: "
            f"borrowings={borrowings}, equity={equity_capital}, reserves={reserves}. Error: {e}"
        )
        return None

    if math.isnan(borrowings_val) or math.isnan(equity_val) or math.isnan(reserves_val):
        return None

    if borrowings_val == 0.0:
        return 0.0

    denominator = equity_val + reserves_val
    if denominator <= 0.0 or math.isnan(denominator):
        leverage_logger.info(
            f"Debt-to-Equity denominator <= 0: {denominator} "
            f"(equity={equity_val}, reserves={reserves_val}). Returning None."
        )
        return None

    return borrowings_val / denominator


def get_high_leverage_flag(
    debt_to_equity: Optional[float],
    broad_sector: Optional[str],
) -> bool:
    """
    Determine if a company has high leverage.

    Rules:
        If Debt-to-Equity > 5 AND broad_sector != "Financials", returns True.
        Otherwise, False.

    Args:
        debt_to_equity: The calculated Debt-to-Equity ratio.
        broad_sector: The broad sector of the company (e.g. "Financials").

    Returns:
        bool: True if high leverage flag is triggered, False otherwise.
    """
    if debt_to_equity is None:
        return False

    try:
        d_e_val = float(debt_to_equity)
    except (ValueError, TypeError):
        return False

    if math.isnan(d_e_val):
        return False

    sector_clean = str(broad_sector).strip() if broad_sector is not None else ""

    if d_e_val > 5.0 and sector_clean != "Financials":
        leverage_logger.warning(
            f"High Leverage Flag triggered: Debt-to-Equity={d_e_val:.2f}, Sector={sector_clean}"
        )
        return True

    return False


def calculate_interest_coverage_ratio(
    operating_profit: Optional[Union[float, int]],
    other_income: Optional[Union[float, int]],
    interest: Optional[Union[float, int]],
) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate the Interest Coverage Ratio (ICR) and return the ratio and label.

    Formula:
        ICR = (operating_profit + other_income) / interest

    Rules:
        If interest == 0, return ICR = None, label = "Debt Free".
        Otherwise, return actual ICR and None.

    Args:
        operating_profit: Operating profit of the company.
        other_income: Other income of the company.
        interest: Interest expense of the company.

    Returns:
        Tuple[Optional[float], Optional[str]]:
            - The Interest Coverage Ratio (float or None).
            - The ICR label (str or None).
    """
    if operating_profit is None or other_income is None or interest is None:
        return None, None

    try:
        op_profit_val = float(operating_profit)
        other_inc_val = float(other_income)
        interest_val = float(interest)
    except (ValueError, TypeError) as e:
        leverage_logger.warning(
            f"Invalid input types for ICR calculation: "
            f"operating_profit={operating_profit}, other_income={other_income}, interest={interest}. Error: {e}"
        )
        return None, None

    if (
        math.isnan(op_profit_val)
        or math.isnan(other_inc_val)
        or math.isnan(interest_val)
    ):
        return None, None

    if interest_val == 0.0:
        return None, "Debt Free"

    icr = (op_profit_val + other_inc_val) / interest_val
    return icr, None


def get_icr_warning_flag(
    icr: Optional[float],
    icr_label: Optional[str],
) -> bool:
    """
    Determine if a company has an Interest Coverage Ratio warning.

    Rules:
        If ICR < 1.5, returns True.
        Otherwise, False.
        Debt Free companies (icr_label == "Debt Free") should not receive warnings.

    Args:
        icr: The calculated Interest Coverage Ratio.
        icr_label: The ICR label (e.g. "Debt Free").

    Returns:
        bool: True if ICR warning flag is triggered, False otherwise.
    """
    if icr_label == "Debt Free":
        return False

    if icr is None:
        return False

    try:
        icr_val = float(icr)
    except (ValueError, TypeError):
        return False

    if math.isnan(icr_val):
        return False

    if icr_val < 1.5:
        leverage_logger.warning(f"ICR Warning triggered: ICR={icr_val:.2f}")
        return True

    return False


def calculate_net_debt(
    borrowings: Optional[Union[float, int]],
    investments: Optional[Union[float, int]],
) -> Optional[float]:
    """
    Calculate Net Debt.

    Formula:
        Net Debt = borrowings - investments

    Args:
        borrowings: Total borrowings of the company.
        investments: Total investments of the company.

    Returns:
        The Net Debt as a float, or None if inputs are invalid.
        Negative Net Debt is allowed.
    """
    if borrowings is None or investments is None:
        return None

    try:
        borrowings_val = float(borrowings)
        investments_val = float(investments)
    except (ValueError, TypeError) as e:
        leverage_logger.warning(
            f"Invalid input types for Net Debt calculation: "
            f"borrowings={borrowings}, investments={investments}. Error: {e}"
        )
        return None

    if math.isnan(borrowings_val) or math.isnan(investments_val):
        return None

    return borrowings_val - investments_val


def calculate_asset_turnover(
    sales: Optional[Union[float, int]],
    total_assets: Optional[Union[float, int]],
) -> Optional[float]:
    """
    Calculate Asset Turnover.

    Formula:
        Asset Turnover = sales / total_assets

    Args:
        sales: Net sales of the company.
        total_assets: Total assets of the company.

    Returns:
        The Asset Turnover as a float, or None if total_assets is 0 or inputs are invalid.
    """
    if sales is None or total_assets is None:
        return None

    try:
        sales_val = float(sales)
        assets_val = float(total_assets)
    except (ValueError, TypeError) as e:
        leverage_logger.warning(
            f"Invalid input types for Asset Turnover calculation: "
            f"sales={sales}, total_assets={total_assets}. Error: {e}"
        )
        return None

    if math.isnan(sales_val) or math.isnan(assets_val):
        return None

    if assets_val == 0.0:
        leverage_logger.info(
            "Asset Turnover calculation: total_assets is 0. Returning None."
        )
        return None

    return sales_val / assets_val
