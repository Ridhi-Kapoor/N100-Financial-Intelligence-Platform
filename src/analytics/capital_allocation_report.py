"""
Module for Capital Allocation Data Validation, Distribution Summarization,
Cash Flow Intelligence Integration, and YoY Pattern Change Detection.

This module delivers Day 32 Capital Allocation Report functionality:
1. Data Validation for capital_allocation.csv
2. Distribution Summary table of Capital Allocation Patterns
3. Integration with output/cashflow_intelligence.xlsx
4. Detection and export of YoY pattern changes to output/pattern_changes.csv
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd

# Configure module logger
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("capital_allocation_report")
logger.setLevel(logging.INFO)

if not logger.handlers:
    log_file = LOG_DIR / "capital_allocation_report.log"
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# The 8 official Capital Allocation Patterns
ALL_CAPITAL_ALLOCATION_PATTERNS = [
    "Reinvestor",
    "Shareholder Returns",
    "Liquidating Assets",
    "Distress Signal",
    "Growth Funded by Debt",
    "Cash Accumulator",
    "Pre-Revenue",
    "Mixed",
]


def load_dataset_csv(path: Path) -> pd.DataFrame:
    """
    Load a CSV file, dynamically skipping metadata header rows if present.

    Args:
        path: Absolute or relative Path to CSV file.

    Returns:
        Cleaned pandas DataFrame with stripped column names.
    """
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        first_line = f.readline()

    header = (
        0 if any(k in first_line.lower() for k in ["id", "company_id", "year"]) else 1
    )
    df = pd.read_csv(path, header=header)
    df.columns = [str(col).strip() for col in df.columns]

    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].astype(str).str.strip()
    if "id" in df.columns:
        df["id"] = df["id"].astype(str).str.strip()
    if "year" in df.columns:
        df["year_int"] = pd.to_numeric(df["year"], errors="coerce")

    return df


def validate_capital_allocation_data(
    ca_df: pd.DataFrame,
    companies_df: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, Dict[str, Union[int, List[str]]]]:
    """
    Validate capital allocation dataset for:
    - Missing master companies (from 92 Nifty 100 companies)
    - Missing financial years (global and per-company gap years)
    - Duplicate (company_id, year) records
    - Missing capital allocation labels (NaN, empty, or 'Unknown')

    Args:
        ca_df: DataFrame of capital allocation records.
        companies_df: Master companies DataFrame (optional).

    Returns:
        Tuple[pd.DataFrame, Dict]:
            - Validation summary DataFrame suitable for reporting/exporting.
            - Metrics dictionary containing detailed validation findings.
    """
    logger.info("Starting Capital Allocation Data Validation...")

    ca_clean = ca_df.copy()
    if "company_id" in ca_clean.columns:
        ca_clean["company_id"] = ca_clean["company_id"].astype(str).str.strip()
    if "year" in ca_clean.columns:
        ca_clean["year_int"] = pd.to_numeric(ca_clean["year"], errors="coerce")

    total_records = len(ca_clean)

    # Master companies list (92 companies)
    if companies_df is not None and not companies_df.empty:
        comp_col = "id" if "id" in companies_df.columns else "company_id"
        master_comp_ids = sorted(
            companies_df[comp_col].astype(str).str.strip().unique().tolist()
        )
    else:
        master_comp_ids = sorted(ca_clean["company_id"].unique().tolist())

    ca_clean[ca_clean["company_id"].isin(master_comp_ids)]

    # 1. Missing Companies
    present_comp_ids = set(ca_clean["company_id"].unique())
    missing_comp_ids = [cid for cid in master_comp_ids if cid not in present_comp_ids]

    # 2. Duplicate Records
    dup_mask = ca_clean.duplicated(subset=["company_id", "year_int"], keep=False)
    dup_records_count = int(dup_mask.sum())
    dup_pairs = (
        ca_clean[dup_mask][["company_id", "year_int"]]
        .drop_duplicates()
        .apply(lambda r: f"{r['company_id']}-{r['year_int']}", axis=1)
        .tolist()
    )

    # 3. Missing or Unknown Labels
    if "pattern_label" in ca_clean.columns:
        missing_label_mask = (
            ca_clean["pattern_label"].isna()
            | (ca_clean["pattern_label"].astype(str).str.strip() == "")
            | (ca_clean["pattern_label"].astype(str).str.strip() == "Unknown")
        )
    else:
        missing_label_mask = pd.Series([True] * len(ca_clean), index=ca_clean.index)

    missing_labels_count = int(missing_label_mask.sum())
    missing_label_records = (
        ca_clean[missing_label_mask][["company_id", "year_int"]]
        .apply(lambda r: f"{r['company_id']}-{r['year_int']}", axis=1)
        .tolist()
    )

    # 4. Missing Years Assessment
    all_years = sorted(ca_clean["year_int"].dropna().astype(int).unique().tolist())
    min_year = min(all_years) if all_years else 2011
    max_year = max(all_years) if all_years else 2024
    expected_full_years = set(range(min_year, max_year + 1))

    companies_with_gap_years = {}
    companies_with_missing_full_years = {}

    for cid in master_comp_ids:
        comp_yrs = sorted(
            ca_clean[ca_clean["company_id"] == cid]["year_int"]
            .dropna()
            .astype(int)
            .tolist()
        )
        if comp_yrs:
            comp_yr_set = set(comp_yrs)
            # Gap years within active range
            active_range = set(range(min(comp_yrs), max(comp_yrs) + 1))
            gaps = sorted(list(active_range - comp_yr_set))
            if gaps:
                companies_with_gap_years[cid] = gaps

            # Missing years relative to global max range
            missing_global = sorted(list(expected_full_years - comp_yr_set))
            if missing_global:
                companies_with_missing_full_years[cid] = missing_global

    # Build Summary Table
    summary_rows = [
        {
            "Check Category": "Total Records",
            "Value / Count": total_records,
            "Details": f"Total company-year records in dataset across {len(present_comp_ids)} companies.",
            "Status": "PASSED",
        },
        {
            "Check Category": "Master Companies Coverage",
            "Value / Count": f"{len(master_comp_ids) - len(missing_comp_ids)}/{len(master_comp_ids)}",
            "Details": (
                "All 92 master companies present in dataset."
                if not missing_comp_ids
                else f"Missing {len(missing_comp_ids)} companies: {', '.join(missing_comp_ids[:5])}"
            ),
            "Status": "PASSED" if not missing_comp_ids else "INCONSISTENCY DETECTED",
        },
        {
            "Check Category": "Duplicate (company_id, year) Records",
            "Value / Count": dup_records_count,
            "Details": (
                "No duplicate records found."
                if dup_records_count == 0
                else f"Duplicates found in {len(dup_pairs)} company-year pairs: {', '.join(dup_pairs[:5])}"
            ),
            "Status": "PASSED" if dup_records_count == 0 else "INCONSISTENCY DETECTED",
        },
        {
            "Check Category": "Missing Capital Allocation Labels",
            "Value / Count": missing_labels_count,
            "Details": (
                "All records have valid capital allocation labels."
                if missing_labels_count == 0
                else f"Missing/Unknown labels in {missing_labels_count} records: {', '.join(missing_label_records[:5])}"
            ),
            "Status": "PASSED" if missing_labels_count == 0 else "WARNING",
        },
        {
            "Check Category": "Company Year Range Gaps",
            "Value / Count": len(companies_with_gap_years),
            "Details": (
                "No gap years within company historical ranges."
                if not companies_with_gap_years
                else f"{len(companies_with_gap_years)} companies have missing intermediate years: {list(companies_with_gap_years.keys())[:5]}"
            ),
            "Status": "PASSED" if not companies_with_gap_years else "WARNING",
        },
    ]

    summary_df = pd.DataFrame(summary_rows)

    metrics = {
        "total_records": total_records,
        "master_companies_count": len(master_comp_ids),
        "present_companies_count": len(present_comp_ids),
        "missing_companies": missing_comp_ids,
        "duplicate_records_count": dup_records_count,
        "duplicate_pairs": dup_pairs,
        "missing_labels_count": missing_labels_count,
        "missing_label_records": missing_label_records,
        "companies_with_gap_years": companies_with_gap_years,
        "global_year_range": [min_year, max_year],
    }

    logger.info(
        f"Validation complete: {len(missing_comp_ids)} missing companies, "
        f"{dup_records_count} duplicates, {missing_labels_count} missing labels."
    )
    return summary_df, metrics


def generate_capital_allocation_distribution(
    ca_df: pd.DataFrame,
    year: Optional[int] = None,
    companies_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Generate Capital Allocation Distribution Summary for the latest financial year.

    Calculates the number of companies and percentage of total companies belonging
    to each of the 8 Capital Allocation Patterns.

    Args:
        ca_df: DataFrame containing capital allocation records.
        year: Optional financial year to calculate distribution for. If None, uses latest year per company.
        companies_df: Optional DataFrame of 92 master companies to restrict scope.

    Returns:
        pd.DataFrame with columns:
        - Capital Allocation Pattern
        - Number of Companies
        - Percentage of Total Companies
    """
    logger.info("Calculating Capital Allocation Distribution Summary...")

    df_clean = ca_df.copy()
    if "company_id" in df_clean.columns:
        df_clean["company_id"] = df_clean["company_id"].astype(str).str.strip()
    if "year" in df_clean.columns:
        df_clean["year_int"] = pd.to_numeric(df_clean["year"], errors="coerce")

    # Filter by master companies if provided
    if companies_df is not None and not companies_df.empty:
        comp_col = "id" if "id" in companies_df.columns else "company_id"
        master_ids = set(companies_df[comp_col].astype(str).str.strip().unique())
        df_clean = df_clean[df_clean["company_id"].isin(master_ids)]

    # Filter for target year or take latest record per company
    if year is not None:
        target_df = df_clean[df_clean["year_int"] == year]
    else:
        # Take latest available financial year for each company
        target_df = (
            df_clean.sort_values("year_int").groupby("company_id").last().reset_index()
        )

    total_companies = len(target_df)
    if total_companies == 0:
        logger.warning("No company records found for distribution calculation.")
        return pd.DataFrame(
            {
                "Capital Allocation Pattern": ALL_CAPITAL_ALLOCATION_PATTERNS,
                "Number of Companies": [0] * len(ALL_CAPITAL_ALLOCATION_PATTERNS),
                "Percentage of Total Companies": [0.0]
                * len(ALL_CAPITAL_ALLOCATION_PATTERNS),
            }
        )

    # Count pattern occurrences
    pattern_counts = target_df["pattern_label"].value_counts().to_dict()

    rows = []
    for pattern in ALL_CAPITAL_ALLOCATION_PATTERNS:
        count = int(pattern_counts.get(pattern, 0))
        pct = (
            round((count / total_companies) * 100.0, 2) if total_companies > 0 else 0.0
        )
        rows.append(
            {
                "Capital Allocation Pattern": pattern,
                "Number of Companies": count,
                "Percentage of Total Companies": pct,
            }
        )

    dist_df = pd.DataFrame(rows)
    logger.info(f"Distribution summary calculated across {total_companies} companies.")
    return dist_df


def integrate_with_cashflow_intelligence(
    excel_path: Path,
    ca_df: pd.DataFrame,
    output_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Integrate capital allocation data into cashflow_intelligence.xlsx.

    Adds a new column 'Capital Allocation' containing the latest capital allocation label
    for each company without altering any existing columns or calculations.

    Args:
        excel_path: Path to existing output/cashflow_intelligence.xlsx.
        ca_df: DataFrame of capital allocation records.
        output_path: Target path to save updated Excel file (defaults to excel_path).

    Returns:
        pd.DataFrame: Updated Cash Flow Intelligence DataFrame.
    """
    logger.info(
        f"Integrating Capital Allocation into Cash Flow Intelligence Excel ({excel_path})..."
    )

    if not excel_path.exists():
        raise FileNotFoundError(
            f"Cash Flow Intelligence Excel file not found at: {excel_path}"
        )

    # Read existing Excel file
    intel_df = pd.read_excel(excel_path)

    # Get latest capital allocation pattern for each company
    ca_clean = ca_df.copy()
    if "company_id" in ca_clean.columns:
        ca_clean["company_id"] = ca_clean["company_id"].astype(str).str.strip()
    if "year" in ca_clean.columns:
        ca_clean["year_int"] = pd.to_numeric(ca_clean["year"], errors="coerce")

    latest_ca = (
        ca_clean.sort_values("year_int").groupby("company_id").last().reset_index()
    )
    ca_map = dict(zip(latest_ca["company_id"], latest_ca["pattern_label"]))

    # Map to intel_df using Company ID
    if "Company ID" in intel_df.columns:
        intel_df["Capital Allocation"] = (
            intel_df["Company ID"].astype(str).str.strip().map(ca_map).fillna("Unknown")
        )
    else:
        logger.warning("'Company ID' column missing in cashflow_intelligence.xlsx.")

    save_path = output_path if output_path is not None else excel_path
    save_path.parent.mkdir(parents=True, exist_ok=True)
    intel_df.to_excel(save_path, index=False)
    logger.info(
        f"Successfully saved updated Cash Flow Intelligence file to: {save_path}"
    )

    return intel_df


def detect_pattern_changes(
    ca_df: pd.DataFrame,
    companies_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Detect YoY capital allocation pattern changes between consecutive years for each company.

    Args:
        ca_df: DataFrame containing capital allocation history.
        companies_df: Optional master companies DataFrame for company names.

    Returns:
        pd.DataFrame with columns:
        - Company ID
        - Company Name
        - Previous Year
        - Previous Pattern
        - Current Year
        - Current Pattern
        - Change Description
    """
    logger.info("Detecting Year-over-Year Capital Allocation Pattern changes...")

    ca_clean = ca_df.copy()
    if "company_id" in ca_clean.columns:
        ca_clean["company_id"] = ca_clean["company_id"].astype(str).str.strip()
    if "year" in ca_clean.columns:
        ca_clean["year_int"] = pd.to_numeric(ca_clean["year"], errors="coerce")

    # Filter by master companies if provided
    name_map = {}
    if companies_df is not None and not companies_df.empty:
        comp_id_col = "id" if "id" in companies_df.columns else "company_id"
        comp_name_col = (
            "company_name" if "company_name" in companies_df.columns else comp_id_col
        )
        for _, row in companies_df.iterrows():
            cid = str(row[comp_id_col]).strip()
            raw_name = str(row.get(comp_name_col, cid))
            clean_name = raw_name.split("\n")[0].strip() if pd.notna(raw_name) else cid
            name_map[cid] = clean_name

        ca_clean = ca_clean[ca_clean["company_id"].isin(name_map.keys())]

    ca_clean = ca_clean.sort_values(["company_id", "year_int"]).reset_index(drop=True)

    changes = []
    for cid, group in ca_clean.groupby("company_id"):
        group_sorted = group.sort_values("year_int").reset_index(drop=True)
        cname = name_map.get(cid, cid)

        for i in range(1, len(group_sorted)):
            prev_row = group_sorted.iloc[i - 1]
            curr_row = group_sorted.iloc[i]

            prev_pattern = str(prev_row.get("pattern_label", "")).strip()
            curr_pattern = str(curr_row.get("pattern_label", "")).strip()
            prev_year = (
                int(prev_row["year_int"])
                if pd.notna(prev_row.get("year_int"))
                else None
            )
            curr_year = (
                int(curr_row["year_int"])
                if pd.notna(curr_row.get("year_int"))
                else None
            )

            # Check if pattern changed and both patterns are valid
            if (
                prev_pattern != curr_pattern
                and prev_pattern not in ["", "nan", "None", "Unknown"]
                and curr_pattern not in ["", "nan", "None", "Unknown"]
            ):
                change_desc = f"{prev_pattern} \u2192 {curr_pattern}"
                changes.append(
                    {
                        "Company ID": cid,
                        "Company Name": cname,
                        "Previous Year": prev_year,
                        "Previous Pattern": prev_pattern,
                        "Current Year": curr_year,
                        "Current Pattern": curr_pattern,
                        "Change Description": change_desc,
                    }
                )

    changes_df = pd.DataFrame(
        changes,
        columns=[
            "Company ID",
            "Company Name",
            "Previous Year",
            "Previous Pattern",
            "Current Year",
            "Current Pattern",
            "Change Description",
        ],
    )

    logger.info(
        f"Pattern change detection complete: found {len(changes_df)} YoY pattern transitions."
    )
    return changes_df


def generate_capital_allocation_report(
    project_root: Optional[Path] = None,
) -> Dict[str, Union[pd.DataFrame, Path]]:
    """
    Main orchestration function for Day 32 Capital Allocation Report.

    Loads inputs, executes validation, generates distribution summary, updates cashflow intelligence excel,
    detects YoY pattern changes, and saves all outputs in output/ directory.

    Args:
        project_root: Optional root directory path of project.

    Returns:
        Dict containing generated DataFrames and output file paths.
    """
    logger.info("Executing Day 32 Capital Allocation Report workflow...")

    if project_root is None:
        project_root = PROJECT_ROOT

    data_dir = project_root / "data"
    output_dir = project_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Datasets
    ca_path = output_dir / "capital_allocation.csv"
    if not ca_path.exists():
        ca_path = data_dir / "output" / "capital_allocation.csv"

    companies_path = data_dir / "processed" / "companies.csv"

    ca_df = load_dataset_csv(ca_path)
    companies_df = load_dataset_csv(companies_path) if companies_path.exists() else None

    # Task 1: Data Validation
    val_summary_df, val_metrics = validate_capital_allocation_data(ca_df, companies_df)
    val_csv_path = output_dir / "capital_allocation_validation.csv"
    val_summary_df.to_csv(val_csv_path, index=False)

    # Task 2: Distribution Summary
    dist_df = generate_capital_allocation_distribution(
        ca_df, year=None, companies_df=companies_df
    )
    dist_csv_path = output_dir / "capital_allocation_distribution.csv"
    dist_df.to_csv(dist_csv_path, index=False)

    # Task 3: Cash Flow Intelligence Integration
    intel_excel_path = output_dir / "cashflow_intelligence.xlsx"
    if intel_excel_path.exists():
        intel_df = integrate_with_cashflow_intelligence(intel_excel_path, ca_df)
    else:
        logger.warning(
            f"Cash flow intelligence file not found at {intel_excel_path}, skipping integration step."
        )
        intel_df = pd.DataFrame()

    # Task 4: Detect YoY Pattern Changes
    pattern_changes_df = detect_pattern_changes(ca_df, companies_df)
    changes_csv_path = output_dir / "pattern_changes.csv"
    pattern_changes_df.to_csv(changes_csv_path, index=False)

    logger.info("Capital Allocation Report workflow successfully completed.")

    return {
        "validation_summary": val_summary_df,
        "validation_metrics": val_metrics,
        "distribution_summary": dist_df,
        "cashflow_intelligence": intel_df,
        "pattern_changes": pattern_changes_df,
        "output_paths": {
            "validation_csv": val_csv_path,
            "distribution_csv": dist_csv_path,
            "cashflow_intelligence_excel": intel_excel_path,
            "pattern_changes_csv": changes_csv_path,
        },
    }
