"""
Day 31 Cash Flow Intelligence Module.

This module evaluates cash flow quality, capital allocation efficiency, financial
distress indicators, and deleveraging trends for all companies using cash flow datasets.

Functions provided:
- Free Cash Flow (FCF) calculation
- CFO Quality Score & classification
- CapEx Intensity & classification
- FCF Conversion calculation
- Capital Allocation Pattern classification
- Financial Distress Signal detection
- Deleveraging detection
- Report generation for cashflow_intelligence.xlsx and distress_alerts.csv
"""

import logging
import math
from pathlib import Path
from typing import Optional, Tuple, Union
import pandas as pd

# Configure logger
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = PROJECT_ROOT / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

cf_logger = logging.getLogger("cashflow_kpis")
cf_logger.setLevel(logging.INFO)

if not cf_logger.handlers:
    cf_file = LOG_DIR / "cashflow_kpis.log"
    file_handler = logging.FileHandler(cf_file, mode="a", encoding="utf-8")
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    cf_logger.addHandler(file_handler)
    cf_logger.addHandler(stream_handler)

# Import CAGR calculation if available
try:
    from src.analytics.cagr import calculate_cagr
except ImportError:

    def calculate_cagr(beg_val, end_val, n):
        """Calculate fallback Compound Annual Growth Rate."""
        if beg_val is None or end_val is None or n is None or n <= 0:
            return None, "INSUFFICIENT"
        try:
            b, e = float(beg_val), float(end_val)
            if b <= 0 or e < 0 or math.isnan(b) or math.isnan(e):
                return None, "INSUFFICIENT"
            return ((e / b) ** (1.0 / n) - 1.0) * 100.0, None
        except Exception:
            return None, "INSUFFICIENT"


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


def detect_distress_signal(cfo: Optional[float], cff: Optional[float]) -> bool:
    """
    Detect distress signal for latest year (CFO < 0 and CFF > 0).

    Args:
        cfo: Operating Cash Flow.
        cff: Cash Flow from Financing.

    Returns:
        bool: True if distress signal detected, else False.
    """
    if cfo is None or cff is None:
        return False
    try:
        return float(cfo) < 0 and float(cff) > 0
    except (ValueError, TypeError):
        return False


def detect_deleveraging(
    cff: Optional[float],
    latest_borrowings: Optional[float],
    prev_borrowings: Optional[float],
) -> bool:
    """
    Detect deleveraging signal for latest year (CFF < 0 and Borrowings YoY decreasing).

    Args:
        cff: Cash Flow from Financing.
        latest_borrowings: Borrowings in latest year.
        prev_borrowings: Borrowings in previous year.

    Returns:
        bool: True if deleveraging detected, else False.
    """
    if cff is None or latest_borrowings is None or prev_borrowings is None:
        return False
    try:
        cff_v = float(cff)
        curr_b = float(latest_borrowings)
        prev_b = float(prev_borrowings)
        return cff_v < 0 and curr_b < prev_b
    except (ValueError, TypeError):
        return False


def generate_cashflow_intelligence_report(
    processed_dir: Optional[Path] = None, output_dir: Optional[Path] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate Cash Flow Intelligence outputs:
    1. output/cashflow_intelligence.xlsx
    2. output/distress_alerts.csv

    Args:
        processed_dir: Path to data/processed folder.
        output_dir: Path to output folder.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]:
            - Cashflow Intelligence DataFrame
            - Distress Alerts DataFrame
    """
    cf_logger.info("Starting Day 31 Cash Flow Intelligence Report generation...")

    if processed_dir is None:
        processed_dir = PROCESSED_DIR

    if output_dir is None:
        output_dir = OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    def _read_csv_safe(name: str) -> pd.DataFrame:
        path = processed_dir / f"{name}.csv"
        if not path.exists():
            cf_logger.warning(f"File not found: {path}")
            return pd.DataFrame()
        try:
            with open(path, "r", encoding="utf-8") as f:
                first_line = f.readline()
            header = (
                0
                if any(k in first_line.lower() for k in ["id", "company_id", "year"])
                else 1
            )
            df = pd.read_csv(path, header=header)
            df.columns = [str(c).strip() for c in df.columns]
            if "company_id" in df.columns:
                df["company_id"] = df["company_id"].astype(str).str.strip()
            if "id" in df.columns:
                df["id"] = df["id"].astype(str).str.strip()
            if "year" in df.columns:
                df["year_int"] = pd.to_numeric(df["year"], errors="coerce")
            return df
        except Exception as e:
            cf_logger.error(f"Error reading {path}: {e}")
            return pd.DataFrame()

    companies_df = _read_csv_safe("companies")
    pl_df = _read_csv_safe("profitandloss")
    bs_df = _read_csv_safe("balancesheet")
    cf_df = _read_csv_safe("cashflow")
    sectors_df = _read_csv_safe("sectors")

    if companies_df.empty:
        cf_logger.error("No companies found in dataset.")
        return pd.DataFrame(), pd.DataFrame()

    sector_map = (
        dict(zip(sectors_df["company_id"], sectors_df["broad_sector"]))
        if not sectors_df.empty and "broad_sector" in sectors_df.columns
        else {}
    )
    name_map = (
        dict(zip(companies_df["id"], companies_df["company_name"]))
        if not companies_df.empty and "company_name" in companies_df.columns
        else {}
    )

    company_ids = companies_df["id"].unique().tolist()
    cf_logger.info(
        f"Loaded {len(company_ids)} companies for Cash Flow Intelligence processing."
    )

    intel_rows = []
    distress_rows = []

    for cid in company_ids:
        raw_name = name_map.get(cid, cid)
        cname = str(raw_name).split("\n")[0].strip() if pd.notna(raw_name) else cid
        sector = sector_map.get(cid, "N/A")

        c_pl = (
            pl_df[pl_df["company_id"] == cid]
            .dropna(subset=["year_int"])
            .sort_values("year_int")
            if not pl_df.empty
            else pd.DataFrame()
        )
        c_bs = (
            bs_df[bs_df["company_id"] == cid]
            .dropna(subset=["year_int"])
            .sort_values("year_int")
            if not bs_df.empty
            else pd.DataFrame()
        )
        c_cf = (
            cf_df[cf_df["company_id"] == cid]
            .dropna(subset=["year_int"])
            .sort_values("year_int")
            if not cf_df.empty
            else pd.DataFrame()
        )

        if c_cf.empty or c_pl.empty:
            continue

        latest_yr = int(c_cf["year_int"].max())
        prev_yr = latest_yr - 1
        yr_5_ago = latest_yr - 5

        # 1. CFO Quality Score (5-year average CFO / PAT ratio)
        cfo_pat_ratios = []
        recent_yrs = sorted(c_cf["year_int"].unique())[-5:]
        for y in recent_yrs:
            cf_row = c_cf[c_cf["year_int"] == y]
            pl_row = c_pl[c_pl["year_int"] == y]
            if not cf_row.empty and not pl_row.empty:
                cfo = (
                    cf_row["operating_activity"].values[0]
                    if "operating_activity" in cf_row.columns
                    else None
                )
                pat = (
                    pl_row["net_profit"].values[0]
                    if "net_profit" in pl_row.columns
                    else None
                )
                if pd.notna(cfo) and pd.notna(pat) and float(pat) != 0.0:
                    cfo_pat_ratios.append(float(cfo) / float(pat))

        cfo_score, cfo_label = calculate_cfo_quality_score(cfo_pat_ratios)

        # 2. CapEx Intensity
        latest_cf = c_cf[c_cf["year_int"] == latest_yr]
        latest_pl = c_pl[c_pl["year_int"] == latest_yr]
        latest_bs = c_bs[c_bs["year_int"] == latest_yr]
        prev_bs = c_bs[c_bs["year_int"] == prev_yr]

        latest_cfo = (
            float(latest_cf["operating_activity"].values[0])
            if not latest_cf.empty
            and "operating_activity" in latest_cf.columns
            and pd.notna(latest_cf["operating_activity"].values[0])
            else 0.0
        )
        latest_cfi = (
            float(latest_cf["investing_activity"].values[0])
            if not latest_cf.empty
            and "investing_activity" in latest_cf.columns
            and pd.notna(latest_cf["investing_activity"].values[0])
            else 0.0
        )
        latest_cff = (
            float(latest_cf["financing_activity"].values[0])
            if not latest_cf.empty
            and "financing_activity" in latest_cf.columns
            and pd.notna(latest_cf["financing_activity"].values[0])
            else 0.0
        )
        latest_sales = (
            float(latest_pl["sales"].values[0])
            if not latest_pl.empty
            and "sales" in latest_pl.columns
            and pd.notna(latest_pl["sales"].values[0])
            else 0.0
        )
        latest_pat = (
            float(latest_pl["net_profit"].values[0])
            if not latest_pl.empty
            and "net_profit" in latest_pl.columns
            and pd.notna(latest_pl["net_profit"].values[0])
            else 0.0
        )
        latest_op = (
            float(latest_pl["operating_profit"].values[0])
            if not latest_pl.empty
            and "operating_profit" in latest_pl.columns
            and pd.notna(latest_pl["operating_profit"].values[0])
            else 0.0
        )

        capex_intensity, capex_label = calculate_capex_intensity(
            latest_cfi, latest_sales
        )

        # 3. FCF CAGR & FCF Conversion
        latest_fcf = calculate_free_cash_flow(latest_cfo, latest_cfi)
        fcf_conversion = calculate_fcf_conversion(latest_fcf, latest_op)

        fcf_5yr_ago = None
        cf_5yr = c_cf[c_cf["year_int"] == yr_5_ago]
        if not cf_5yr.empty:
            cfo_5yr = (
                cf_5yr["operating_activity"].values[0]
                if "operating_activity" in cf_5yr.columns
                else None
            )
            cfi_5yr = (
                cf_5yr["investing_activity"].values[0]
                if "investing_activity" in cf_5yr.columns
                else None
            )
            fcf_5yr_ago = calculate_free_cash_flow(cfo_5yr, cfi_5yr)

        fcf_cagr, _ = (
            calculate_cagr(fcf_5yr_ago, latest_fcf, 5)
            if (fcf_5yr_ago is not None and latest_fcf is not None)
            else (None, None)
        )

        # 4. Distress Signal Detection
        is_distress = detect_distress_signal(latest_cfo, latest_cff)
        distress_flag = "Yes" if is_distress else "No"

        # 5. Deleveraging Detection
        latest_debt = (
            float(latest_bs["borrowings"].values[0])
            if not latest_bs.empty
            and "borrowings" in latest_bs.columns
            and pd.notna(latest_bs["borrowings"].values[0])
            else None
        )
        prev_debt = (
            float(prev_bs["borrowings"].values[0])
            if not prev_bs.empty
            and "borrowings" in prev_bs.columns
            and pd.notna(prev_bs["borrowings"].values[0])
            else None
        )
        is_deleveraging = detect_deleveraging(latest_cff, latest_debt, prev_debt)
        deleveraging_flag = "Yes" if is_deleveraging else "No"

        # 6. Capital Allocation Label
        _, _, _, alloc_label = classify_capital_allocation(
            latest_cfo, latest_cfi, latest_cff, latest_pat
        )

        intel_rows.append(
            {
                "Company ID": cid,
                "Sector": sector,
                "CFO Quality Score": (
                    round(cfo_score, 2) if cfo_score is not None else None
                ),
                "CFO Quality Label": cfo_label if cfo_label is not None else "N/A",
                "CapEx Intensity (%)": (
                    round(capex_intensity, 2) if capex_intensity is not None else None
                ),
                "CapEx Label": capex_label if capex_label is not None else "N/A",
                "FCF CAGR (5-Year)": (
                    round(fcf_cagr, 2) if fcf_cagr is not None else None
                ),
                "FCF Conversion (%)": (
                    round(fcf_conversion, 2) if fcf_conversion is not None else None
                ),
                "Distress Flag": distress_flag,
                "Deleveraging Flag": deleveraging_flag,
                "Capital Allocation Label": alloc_label,
            }
        )

        if is_distress:
            distress_rows.append(
                {
                    "Company ID": cid,
                    "Company Name": cname,
                    "Sector": sector,
                    "Latest Operating Cash Flow (CFO)": latest_cfo,
                    "Latest Cash Flow from Financing (CFF)": latest_cff,
                    "Latest Net Profit": latest_pat,
                    "Distress Reason": "Operating Cash Flow is negative (CFO < 0) while Financing Cash Flow is positive (CFF > 0), indicating operations are dependent on external debt/equity financing.",
                }
            )

    intel_df = pd.DataFrame(
        intel_rows,
        columns=[
            "Company ID",
            "Sector",
            "CFO Quality Score",
            "CFO Quality Label",
            "CapEx Intensity (%)",
            "CapEx Label",
            "FCF CAGR (5-Year)",
            "FCF Conversion (%)",
            "Distress Flag",
            "Deleveraging Flag",
            "Capital Allocation Label",
        ],
    )

    distress_df = pd.DataFrame(
        distress_rows,
        columns=[
            "Company ID",
            "Company Name",
            "Sector",
            "Latest Operating Cash Flow (CFO)",
            "Latest Cash Flow from Financing (CFF)",
            "Latest Net Profit",
            "Distress Reason",
        ],
    )

    # Save to Excel and CSV
    intel_excel_path = output_dir / "cashflow_intelligence.xlsx"
    distress_csv_path = output_dir / "distress_alerts.csv"

    intel_df.to_excel(intel_excel_path, index=False)
    distress_df.to_csv(distress_csv_path, index=False)

    cf_logger.info(
        f"Saved Cash Flow Intelligence matrix ({len(intel_df)} rows) to: {intel_excel_path}"
    )
    cf_logger.info(
        f"Saved Distress Alerts report ({len(distress_df)} rows) to: {distress_csv_path}"
    )

    return intel_df, distress_df


if __name__ == "__main__":
    generate_cashflow_intelligence_report()
