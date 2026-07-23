"""
Module for calculating cash flow analytics and classification.

This module provides functions to calculate:
- Free Cash Flow (FCF)
- CFO Quality Score and classification
- CapEx Intensity and classification
- FCF Conversion
- Capital Allocation Pattern Classifier based on cash flow signs
"""

import logging
import math
from pathlib import Path
from typing import Optional, Tuple, Union

# Configure the logger for cash flow analytics
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

cf_logger = logging.getLogger("cashflow_analytics")
cf_logger.setLevel(logging.INFO)

if not cf_logger.handlers:
    cf_file = LOG_DIR / "cashflow_analytics.log"
    file_handler = logging.FileHandler(cf_file, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    cf_logger.addHandler(file_handler)


def calculate_free_cash_flow(
    operating_activity: Optional[Union[float, int]],
    investing_activity: Optional[Union[float, int]],
) -> Optional[float]:
    """
    Calculate Free Cash Flow (FCF).

    Formula:
        FCF = Operating Activity + Investing Activity

    Args:
        operating_activity: Cash Flow from Operating Activities.
        investing_activity: Cash Flow from Investing Activities.

    Returns:
        The Free Cash Flow as a float, or None if inputs are invalid.
    """
    if operating_activity is None or investing_activity is None:
        return None

    try:
        op_val = float(operating_activity)
        inv_val = float(investing_activity)
    except (ValueError, TypeError) as e:
        cf_logger.warning(
            f"FCF calculation failed: Invalid input types (op={operating_activity}, inv={investing_activity}). Error: {e}"
        )
        return None

    if math.isnan(op_val) or math.isnan(inv_val):
        return None

    return op_val + inv_val


def calculate_cfo_quality_score(
    cfo_pat_ratios: list[Optional[float]],
) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate the CFO Quality Score.

    CFO Quality Score = Average(CFO / PAT) over previous 5 years.

    Classification:
        - > 1.0: High Quality
        - 0.5 to 1.0: Moderate
        - < 0.5: Accrual Risk

    Args:
        cfo_pat_ratios: List of CFO/PAT ratio values (expected to be up to 5 values).

    Returns:
        Tuple[Optional[float], Optional[str]]:
            - The average CFO/PAT score (float or None).
            - The classification label (str or None).
    """
    valid_ratios = [r for r in cfo_pat_ratios if r is not None and not math.isnan(r)]
    if len(valid_ratios) < 5:
        cf_logger.info(
            f"Insufficient ratios for CFO Quality Score: only {len(valid_ratios)} valid ratios provided."
        )
        return None, None

    avg_score = sum(valid_ratios) / 5.0

    if avg_score > 1.0:
        label = "High Quality"
    elif 0.5 <= avg_score <= 1.0:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return avg_score, label


def calculate_capex_intensity(
    investing_activity: Optional[Union[float, int]],
    sales: Optional[Union[float, int]],
) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate CapEx Intensity and classify it.

    Formula:
        CapEx Intensity = abs(Investing Activity) / Sales * 100

    Classification:
        - < 3%: Asset Light
        - 3% to 8%: Moderate
        - > 8%: Capital Intensive

    Args:
        investing_activity: Cash Flow from Investing Activities.
        sales: Net sales/revenue.

    Returns:
        Tuple[Optional[float], Optional[str]]:
            - CapEx Intensity percentage (float or None).
            - Classification label (str or None).
    """
    if investing_activity is None or sales is None:
        return None, None

    try:
        inv_val = float(investing_activity)
        sales_val = float(sales)
    except (ValueError, TypeError) as e:
        cf_logger.warning(
            f"CapEx Intensity calculation failed: Invalid input types (inv={investing_activity}, sales={sales}). Error: {e}"
        )
        return None, None

    if math.isnan(inv_val) or math.isnan(sales_val):
        return None, None

    if sales_val == 0.0:
        cf_logger.warning("CapEx Intensity calculation failed: Sales is 0.")
        return None, None

    intensity = (abs(inv_val) / sales_val) * 100.0

    if intensity < 3.0:
        label = "Asset Light"
    elif 3.0 <= intensity <= 8.0:
        label = "Moderate"
    else:
        label = "Capital Intensive"

    return intensity, label


def calculate_fcf_conversion(
    fcf: Optional[Union[float, int]],
    operating_profit: Optional[Union[float, int]],
) -> Optional[float]:
    """
    Calculate Free Cash Flow (FCF) Conversion.

    Formula:
        FCF Conversion = FCF / Operating Profit * 100

    Args:
        fcf: Free Cash Flow value.
        operating_profit: Operating profit.

    Returns:
        FCF Conversion percentage (float), or None if Operating Profit = 0 or inputs are invalid.
    """
    if fcf is None or operating_profit is None:
        return None

    try:
        fcf_val = float(fcf)
        op_val = float(operating_profit)
    except (ValueError, TypeError) as e:
        cf_logger.warning(
            f"FCF Conversion calculation failed: Invalid input types (fcf={fcf}, op={operating_profit}). Error: {e}"
        )
        return None

    if math.isnan(fcf_val) or math.isnan(op_val):
        return None

    if op_val == 0.0:
        cf_logger.warning("FCF Conversion calculation failed: Operating Profit is 0.")
        return None

    return (fcf_val / op_val) * 100.0


def classify_capital_allocation(
    cfo: Optional[Union[float, int]],
    cfi: Optional[Union[float, int]],
    cff: Optional[Union[float, int]],
    pat: Optional[Union[float, int]],
) -> Tuple[str, str, str, str]:
    """
    Classify the Capital Allocation Pattern using signs of CFO, CFI, and CFF.

    Signs (+ if >= 0, - if < 0) map to patterns:
        - (+,-,-) and CFO/PAT <= 1.0 -> Reinvestor
        - (+,-,-) and CFO/PAT > 1.0 -> Shareholder Returns
        - (+,+,-) -> Liquidating Assets
        - (-,+,+) -> Distress Signal
        - (-,-,+) -> Growth Funded by Debt
        - (+,+,+) -> Cash Accumulator
        - (-,-,-) -> Pre-Revenue
        - (+,-,+) -> Mixed
        - Any other -> Mixed

    Args:
        cfo: Cash Flow from Operating Activities.
        cfi: Cash Flow from Investing Activities.
        cff: Cash Flow from Financing Activities.
        pat: Profit After Tax (Net Profit).

    Returns:
        Tuple[str, str, str, str]:
            - cfo_sign ('+' or '-')
            - cfi_sign ('+' or '-')
            - cff_sign ('+' or '-')
            - pattern_label (str)
    """
    if cfo is None or cfi is None or cff is None:
        return "N/A", "N/A", "N/A", "Unknown"

    try:
        cfo_val = float(cfo)
        cfi_val = float(cfi)
        cff_val = float(cff)
    except (ValueError, TypeError) as e:
        cf_logger.warning(
            f"Capital Allocation classification failed: Invalid input types. Error: {e}"
        )
        return "N/A", "N/A", "N/A", "Unknown"

    if math.isnan(cfo_val) or math.isnan(cfi_val) or math.isnan(cff_val):
        return "N/A", "N/A", "N/A", "Unknown"

    cfo_sign = "+" if cfo_val >= 0.0 else "-"
    cfi_sign = "+" if cfi_val >= 0.0 else "-"
    cff_sign = "+" if cff_val >= 0.0 else "-"

    pattern = (cfo_sign, cfi_sign, cff_sign)

    if pattern == ("+", "-", "-"):
        is_high_cfo_pat = False
        if pat is not None:
            try:
                pat_val = float(pat)
                if pat_val != 0.0 and not math.isnan(pat_val):
                    if (cfo_val / pat_val) > 1.0:
                        is_high_cfo_pat = True
            except (ValueError, TypeError):
                pass

        if is_high_cfo_pat:
            label = "Shareholder Returns"
        else:
            label = "Reinvestor"

    elif pattern == ("+", "+", "-"):
        label = "Liquidating Assets"
    elif pattern == ("-", "+", "+"):
        label = "Distress Signal"
    elif pattern == ("-", "-", "+"):
        label = "Growth Funded by Debt"
    elif pattern == ("+", "+", "+"):
        label = "Cash Accumulator"
    elif pattern == ("-", "-", "-"):
        label = "Pre-Revenue"
    elif pattern == ("+", "-", "+"):
        label = "Mixed"
    else:
        label = "Mixed"

    return cfo_sign, cfi_sign, cff_sign, label
