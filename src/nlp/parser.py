"""
NLP Text Parser Module for Structured Financial Metrics Extraction.

This module parses unstructured financial text fields from analysis.xlsx using
regular expressions, extracts period and percentage values, logs parsing failures,
and cross-validates parsed values against the existing Ratio Engine outputs.
"""

import logging
import math
import re
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
import pandas as pd

# Define project root and paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = PROJECT_ROOT / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Configure logger
logger = logging.getLogger("nlp_parser")
logger.setLevel(logging.INFO)

if not logger.handlers:
    log_file = LOG_DIR / "nlp_parser.log"
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

# Import Ratio Engine utilities if available
try:
    from src.analytics.cagr import calculate_cagr
    from src.analytics.ratios import calculate_roe
except ImportError:
    logger.warning(
        "Could not import ratio engine modules directly; using internal fallback calculations."
    )
    calculate_cagr = None
    calculate_roe = None

# Standard regex for extracting period (years) and value (%)
# Matches strings like "10 Years: 21%", "5 Years 14%", "1 Year: 16%"
REGEX_PATTERN = re.compile(r"(\d+)\s*Years?:?\s*([\d.]+)%", re.IGNORECASE)

METRIC_COLUMNS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]


def parse_text_field(
    text: Union[str, float, int, None],
) -> Tuple[Optional[int], Optional[float], Optional[str]]:
    """
    Parse a single text field using regular expressions.

    Args:
        text: Raw text string (or missing value).

    Returns:
        Tuple[Optional[int], Optional[float], Optional[str]]:
            - Period in years (int), or None if parsing failed.
            - Metric value as percentage (float), or None if parsing failed.
            - Failure reason (str), or None if successfully parsed.
    """
    if text is None or pd.isna(text):
        return None, None, "Empty or missing text"

    text_str = str(text).strip()
    if not text_str or text_str.lower() in ("nan", "none", "null"):
        return None, None, "Empty or missing text"

    match = REGEX_PATTERN.search(text_str)
    if match:
        try:
            period = int(match.group(1))
            val = float(match.group(2))
            return period, val, None
        except (ValueError, TypeError) as e:
            logger.debug(f"Conversion error for text '{text_str}': {e}")
            return None, None, f"Numeric conversion error: {e}"

    # Determine failure reason if pattern didn't match
    text_upper = text_str.upper()
    if "TTM" in text_upper:
        reason = "TTM format not supported by year pattern"
    elif "LAST YEAR" in text_upper:
        reason = "Last Year format not supported by year pattern"
    elif "-" in text_str:
        reason = "Negative percentage value not matched by regex pattern"
    else:
        reason = "Regex pattern match failed"

    return None, None, reason


def load_analysis_file(file_path: Path) -> pd.DataFrame:
    """
    Load analysis dataset (Excel or CSV), handling potential metadata banner rows.

    Args:
        file_path: Path to analysis.xlsx or analysis.csv.

    Returns:
        pd.DataFrame: Cleaned DataFrame with standard columns.
    """
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"Input analysis file does not exist: {file_path}")

    suffix = file_path.suffix.lower()

    if suffix in (".xlsx", ".xls"):
        # Check first line / header
        df_raw = pd.read_excel(file_path)
        first_cols = [str(c).strip().lower() for c in df_raw.columns]
        if any("company_id" in c or "compounded_sales_growth" in c for c in first_cols):
            df = df_raw
        else:
            # Skip banner header row
            df = pd.read_excel(file_path, header=1)
    elif suffix == ".csv":
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline()
        if "company_id" in first_line or "compounded_sales_growth" in first_line:
            df = pd.read_csv(file_path)
        else:
            df = pd.read_csv(file_path, header=1)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    # Strip column names
    df.columns = [str(c).strip() for c in df.columns]

    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].astype(str).str.strip()

    return df


def load_company_names_map(processed_dir: Path) -> Dict[str, str]:
    """
    Load mapping from company_id to clean company_name from companies.csv.

    Args:
        processed_dir: Path to processed directory.

    Returns:
        Dict[str, str]: Map of company_id -> company_name.
    """
    company_map = {}
    companies_file = processed_dir / "companies.csv"

    if companies_file.exists():
        try:
            with open(companies_file, "r", encoding="utf-8") as f:
                first_line = f.readline()
            if "company_name" in first_line or "id" in first_line:
                df_comp = pd.read_csv(companies_file)
            else:
                df_comp = pd.read_csv(companies_file, header=1)

            df_comp.columns = [str(c).strip() for c in df_comp.columns]

            # Detect ID and name column names
            id_col = (
                "id"
                if "id" in df_comp.columns
                else ("company_id" if "company_id" in df_comp.columns else None)
            )
            name_col = "company_name" if "company_name" in df_comp.columns else None

            if id_col and name_col:
                for _, row in df_comp.iterrows():
                    cid = str(row[id_col]).strip()
                    raw_name = str(row[name_col]) if pd.notna(row[name_col]) else cid
                    # Clean newlines or trailing descriptions
                    clean_name = raw_name.split("\n")[0].strip()
                    company_map[cid] = clean_name
        except Exception as e:
            logger.warning(f"Error loading company names map: {e}")

    return company_map


def parse_analysis_data(
    df: pd.DataFrame, company_names_map: Optional[Dict[str, str]] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Parse text fields in analysis DataFrame into parsed metrics and parse failures.

    Args:
        df: Input analysis DataFrame.
        company_names_map: Mapping of company_id -> company_name.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]:
            - DataFrame of successfully parsed metrics: [Company ID, Metric Type, Period (Years), Value (%)]
            - DataFrame of parse failures: [Company ID, Company Name, Metric Type, Original Text, Failure Reason]
    """
    if company_names_map is None:
        company_names_map = {}

    parsed_records = []
    failure_records = []

    for _, row in df.iterrows():
        cid = str(row.get("company_id", "")).strip()
        cname = company_names_map.get(cid, cid)

        for col in METRIC_COLUMNS:
            if col not in df.columns:
                continue

            raw_text = row.get(col)
            text_str = str(raw_text).strip() if pd.notna(raw_text) else ""

            period, value, failure_reason = parse_text_field(raw_text)

            if failure_reason is None and period is not None and value is not None:
                parsed_records.append(
                    {
                        "Company ID": cid,
                        "Metric Type": col,
                        "Period (Years)": period,
                        "Value (%)": value,
                    }
                )
            else:
                failure_records.append(
                    {
                        "Company ID": cid,
                        "Company Name": cname,
                        "Metric Type": col,
                        "Original Text": text_str,
                        "Failure Reason": failure_reason or "Parsing failed",
                    }
                )

    parsed_df = pd.DataFrame(
        parsed_records,
        columns=["Company ID", "Metric Type", "Period (Years)", "Value (%)"],
    )

    failures_df = pd.DataFrame(
        failure_records,
        columns=[
            "Company ID",
            "Company Name",
            "Metric Type",
            "Original Text",
            "Failure Reason",
        ],
    )

    return parsed_df, failures_df


def _calculate_cagr_internal(
    beg_val: Optional[float], end_val: Optional[float], n: int
) -> Optional[float]:
    """
    Internal helper to calculate CAGR if calculate_cagr standard module is unavailable.
    """
    if calculate_cagr is not None:
        val, _ = calculate_cagr(beg_val, end_val, n)
        return val

    if beg_val is None or end_val is None or n is None or n <= 0:
        return None
    try:
        b = float(beg_val)
        e = float(end_val)
        if b <= 0 or e < 0 or math.isnan(b) or math.isnan(e):
            return None
        return ((e / b) ** (1.0 / n) - 1.0) * 100.0
    except Exception:
        return None


def cross_validate_with_ratio_engine(
    parsed_df: pd.DataFrame,
    processed_dir: Path,
    company_names_map: Dict[str, str],
) -> pd.DataFrame:
    """
    Cross-validate parsed values with values generated by the Ratio Engine.

    Calculates absolute difference and flags records where difference > 5% for Manual Review.

    Args:
        parsed_df: DataFrame of parsed metrics.
        processed_dir: Path to data/processed directory.
        company_names_map: Map of company_id -> company_name.

    Returns:
        pd.DataFrame: Validation report containing:
            [Company ID, Company Name, Metric Type, Parsed Value, Ratio Engine Value, Difference (%), Review Status]
    """
    # Load underlying datasets for Ratio Engine computations
    pl_file = processed_dir / "profitandloss.csv"
    sp_file = processed_dir / "stock_prices.csv"
    comp_file = processed_dir / "companies.csv"

    pl_df = pd.DataFrame()
    if pl_file.exists():
        try:
            with open(pl_file, "r", encoding="utf-8") as f:
                first_line = f.readline()
            header = 0 if "company_id" in first_line or "id" in first_line else 1
            pl_df = pd.read_csv(pl_file, header=header)
            pl_df.columns = [str(c).strip() for c in pl_df.columns]
            if "company_id" in pl_df.columns:
                pl_df["company_id"] = pl_df["company_id"].astype(str).str.strip()
            if "year" in pl_df.columns:
                pl_df["year_int"] = pd.to_numeric(pl_df["year"], errors="coerce")
        except Exception as e:
            logger.warning(f"Error loading P&L for validation: {e}")

    sp_df = pd.DataFrame()
    if sp_file.exists():
        try:
            sp_df = pd.read_csv(sp_file)
            sp_df.columns = [str(c).strip() for c in sp_df.columns]
            if "company_id" in sp_df.columns:
                sp_df["company_id"] = sp_df["company_id"].astype(str).str.strip()
            if "date" in sp_df.columns:
                sp_df["date"] = pd.to_datetime(sp_df["date"], errors="coerce")
        except Exception as e:
            logger.warning(f"Error loading stock prices for validation: {e}")

    comp_df = pd.DataFrame()
    if comp_file.exists():
        try:
            with open(comp_file, "r", encoding="utf-8") as f:
                first_line = f.readline()
            header = 0 if "company_name" in first_line or "id" in first_line else 1
            comp_df = pd.read_csv(comp_file, header=header)
            comp_df.columns = [str(c).strip() for c in comp_df.columns]
            id_col = "id" if "id" in comp_df.columns else "company_id"
            if id_col in comp_df.columns:
                comp_df[id_col] = comp_df[id_col].astype(str).str.strip()
        except Exception as e:
            logger.warning(f"Error loading companies for validation: {e}")

    validation_records = []

    for _, row in parsed_df.iterrows():
        cid = str(row["Company ID"]).strip()
        metric_type = str(row["Metric Type"]).strip()
        period = int(row["Period (Years)"])
        parsed_val = float(row["Value (%)"])
        cname = company_names_map.get(cid, cid)

        re_val: Optional[float] = None

        if metric_type == "compounded_sales_growth" and not pl_df.empty:
            c_pl = (
                pl_df[pl_df["company_id"] == cid]
                .dropna(subset=["year_int"])
                .sort_values("year_int")
            )
            if not c_pl.empty:
                latest_yr = int(c_pl["year_int"].max())
                beg_yr = latest_yr - period
                end_rows = c_pl[c_pl["year_int"] == latest_yr]
                beg_rows = c_pl[c_pl["year_int"] == beg_yr]
                if (
                    not end_rows.empty
                    and not beg_rows.empty
                    and "sales" in c_pl.columns
                ):
                    end_sales = float(end_rows["sales"].values[0])
                    beg_sales = float(beg_rows["sales"].values[0])
                    re_val = _calculate_cagr_internal(beg_sales, end_sales, period)

        elif metric_type == "compounded_profit_growth" and not pl_df.empty:
            c_pl = (
                pl_df[pl_df["company_id"] == cid]
                .dropna(subset=["year_int"])
                .sort_values("year_int")
            )
            if not c_pl.empty:
                latest_yr = int(c_pl["year_int"].max())
                beg_yr = latest_yr - period
                end_rows = c_pl[c_pl["year_int"] == latest_yr]
                beg_rows = c_pl[c_pl["year_int"] == beg_yr]
                if (
                    not end_rows.empty
                    and not beg_rows.empty
                    and "net_profit" in c_pl.columns
                ):
                    end_profit = float(end_rows["net_profit"].values[0])
                    beg_profit = float(beg_rows["net_profit"].values[0])
                    re_val = _calculate_cagr_internal(beg_profit, end_profit, period)

        elif metric_type == "stock_price_cagr" and not sp_df.empty:
            c_sp = (
                sp_df[sp_df["company_id"] == cid]
                .dropna(subset=["date"])
                .sort_values("date")
            )
            if not c_sp.empty and "close_price" in c_sp.columns:
                latest_date = c_sp["date"].max()
                target_beg_date = latest_date - pd.DateOffset(years=period)
                end_price = float(
                    c_sp[c_sp["date"] == latest_date]["close_price"].values[0]
                )
                c_sp_beg = c_sp.iloc[
                    (c_sp["date"] - target_beg_date).abs().argsort()[:1]
                ]
                beg_price = float(c_sp_beg["close_price"].values[0])
                re_val = _calculate_cagr_internal(beg_price, end_price, period)

        elif metric_type == "roe":
            # Check source ROE from companies dataset
            if not comp_df.empty:
                id_col = "id" if "id" in comp_df.columns else "company_id"
                c_comp = comp_df[comp_df[id_col] == cid]
                if not c_comp.empty and "roe_percentage" in c_comp.columns:
                    val = c_comp["roe_percentage"].values[0]
                    if pd.notna(val):
                        try:
                            re_val = float(val)
                        except (ValueError, TypeError):
                            pass

            # Fallback to calculated ROE from P&L
            if re_val is None and not pl_df.empty:
                c_pl = (
                    pl_df[pl_df["company_id"] == cid]
                    .dropna(subset=["year_int"])
                    .sort_values("year_int")
                )
                if not c_pl.empty:
                    last_row = c_pl.iloc[-1]
                    net_profit = last_row.get("net_profit")
                    equity = last_row.get("equity_capital")
                    reserves = last_row.get("reserves")
                    if calculate_roe is not None:
                        re_val = calculate_roe(net_profit, equity, reserves)
                    elif net_profit is not None and equity is not None:
                        try:
                            np_v = float(net_profit)
                            eq_v = float(equity)
                            res_v = (
                                float(reserves)
                                if reserves is not None and pd.notna(reserves)
                                else 0.0
                            )
                            tot_eq = eq_v + res_v
                            if tot_eq > 0:
                                re_val = (np_v / tot_eq) * 100.0
                        except Exception:
                            re_val = None

        # Calculate difference and review status
        if re_val is not None and not math.isnan(re_val):
            re_val_rounded = round(re_val, 2)
            diff_pct = round(abs(parsed_val - re_val_rounded), 2)
            status = "Manual Review" if diff_pct > 5.0 else "Pass"
        else:
            re_val_rounded = None
            diff_pct = None
            status = "Manual Review"

        validation_records.append(
            {
                "Company ID": cid,
                "Company Name": cname,
                "Metric Type": metric_type,
                "Parsed Value": parsed_val,
                "Ratio Engine Value": re_val_rounded,
                "Difference (%)": diff_pct,
                "Review Status": status,
            }
        )

    return pd.DataFrame(
        validation_records,
        columns=[
            "Company ID",
            "Company Name",
            "Metric Type",
            "Parsed Value",
            "Ratio Engine Value",
            "Difference (%)",
            "Review Status",
        ],
    )


def run_nlp_parser(
    input_file: Optional[Path] = None, output_dir: Optional[Path] = None
) -> Dict[str, pd.DataFrame]:
    """
    Run complete NLP parser pipeline:
    1. Load analysis dataset
    2. Parse text fields using regular expressions
    3. Generate analysis_parsed.csv & parse_failures.csv
    4. Cross-validate with Ratio Engine outputs and generate validation report

    Args:
        input_file: Optional path to analysis.xlsx. Defaults to data/raw/analysis.xlsx.
        output_dir: Optional path to output directory. Defaults to project output/.

    Returns:
        Dict[str, pd.DataFrame]: Dictionary containing parsed_df, failures_df, validation_df.
    """
    logger.info("Starting Day 29 NLP Text Parser execution...")

    if input_file is None:
        input_file = RAW_DIR / "analysis.xlsx"

    if output_dir is None:
        output_dir = OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load input file
    logger.info(f"Loading input file from: {input_file}")
    df_analysis = load_analysis_file(input_file)

    # 2. Load company names
    company_map = load_company_names_map(PROCESSED_DIR)

    # 3. Parse metrics and log failures
    logger.info("Parsing financial metric text fields...")
    parsed_df, failures_df = parse_analysis_data(df_analysis, company_map)

    # 4. Cross-validate with Ratio Engine
    logger.info("Cross-validating parsed values with Ratio Engine outputs...")
    validation_df = cross_validate_with_ratio_engine(
        parsed_df, PROCESSED_DIR, company_map
    )

    # 5. Save generated files to output/ directory
    parsed_path = output_dir / "analysis_parsed.csv"
    failures_path = output_dir / "parse_failures.csv"
    validation_path = output_dir / "validation_report.csv"

    parsed_df.to_csv(parsed_path, index=False)
    failures_df.to_csv(failures_path, index=False)
    validation_df.to_csv(validation_path, index=False)

    logger.info(f"Saved parsed metrics ({len(parsed_df)} rows) to: {parsed_path}")
    logger.info(f"Saved parse failures ({len(failures_df)} rows) to: {failures_path}")
    logger.info(
        f"Saved validation report ({len(validation_df)} rows) to: {validation_path}"
    )

    # Display summary
    pass_count = (validation_df["Review Status"] == "Pass").sum()
    review_count = (validation_df["Review Status"] == "Manual Review").sum()

    logger.info("NLP Parsing Complete!")
    logger.info(
        f"Summary: Parsed={len(parsed_df)}, Failures={len(failures_df)}, Pass={pass_count}, Manual Review={review_count}"
    )

    return {
        "parsed_df": parsed_df,
        "failures_df": failures_df,
        "validation_df": validation_df,
    }


if __name__ == "__main__":
    run_nlp_parser()
