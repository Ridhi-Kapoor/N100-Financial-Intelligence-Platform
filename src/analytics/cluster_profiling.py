"""
Module for Cluster Profiling, Correlation Matrix Heatmap, Outlier Detection,
and Portfolio Descriptive Statistics (Day 37).

Features:
1. Profile K-Means clusters (Mean & Median of 5 clustering features) -> output/cluster_profiles.csv
2. Update output/cluster_labels.csv with business-friendly descriptive cluster names.
3. Compute 10-KPI Pearson Correlation Matrix & Seaborn Heatmap -> reports/correlation_heatmap.png
4. Sector-based Z-score Outlier Detection (|Z| > 3) -> output/outlier_report.csv
5. Portfolio-wide Percentile Statistics (P10, P25, P50, P75, P90, Mean, Std) -> output/portfolio_stats.csv
"""

import logging
from pathlib import Path
import sqlite3
from typing import Dict, Optional, Tuple, Union

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.analytics.clustering import (
    CLUSTERING_FEATURES,
    load_and_prepare_clustering_data,
)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Configure logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("cluster_profiling")
logger.setLevel(logging.INFO)

if not logger.handlers:
    log_file = LOG_DIR / "cluster_profiling.log"
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

TEN_KEY_KPIS = [
    "return_on_equity_pct",
    "roce_percentage",
    "operating_profit_margin_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "fcf_cagr_5yr",
    "asset_turnover",
    "interest_coverage",
]

KPI_DISPLAY_NAMES = {
    "return_on_equity_pct": "ROE (%)",
    "roce_percentage": "ROCE (%)",
    "operating_profit_margin_pct": "OPM (%)",
    "net_profit_margin_pct": "NPM (%)",
    "debt_to_equity": "Debt / Equity",
    "revenue_cagr_5yr": "Rev CAGR 5Y (%)",
    "pat_cagr_5yr": "PAT CAGR 5Y (%)",
    "fcf_cagr_5yr": "FCF CAGR 5Y (%)",
    "asset_turnover": "Asset Turnover",
    "interest_coverage": "Interest Coverage",
}


def load_10_kpis_dataset(
    db_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load company metadata, sector info, and 10 key financial KPIs for the latest financial year.
    Imputes missing values using sector medians (with global median fallback).

    Args:
        db_path: Path to nifty100.db SQLite database.
        output_dir: Path to output directory.

    Returns:
        pd.DataFrame containing clean, imputed 10 KPI dataset across all companies.
    """
    if db_path is None:
        db_path = DB_PATH
    if output_dir is None:
        output_dir = OUTPUT_DIR

    conn = sqlite3.connect(db_path)

    try:
        # Load companies
        comp_df = pd.read_sql(
            "SELECT id, company_name, roce_percentage FROM companies", conn
        )
        comp_df["id"] = comp_df["id"].astype(str).str.strip()

        # Load sectors
        sec_df = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
        sec_df["company_id"] = sec_df["company_id"].astype(str).str.strip()

        # Load financial ratios (latest year)
        fr_df = pd.read_sql("SELECT * FROM financial_ratios", conn)
        fr_df["company_id"] = fr_df["company_id"].astype(str).str.strip()

        if not fr_df.empty and "year" in fr_df.columns:
            fr_clean = fr_df[fr_df["year"].astype(str).str.isdigit()].copy()
            fr_clean["year_num"] = fr_clean["year"].astype(int)
            latest_fr = (
                fr_clean.sort_values("year_num")
                .groupby("company_id")
                .last()
                .reset_index()
            )
        else:
            latest_fr = pd.DataFrame(columns=["company_id"] + TEN_KEY_KPIS)

        # Merge
        merged = comp_df.merge(sec_df, left_on="id", right_on="company_id", how="left")
        merged = merged.merge(
            latest_fr,
            left_on="id",
            right_on="company_id",
            how="left",
            suffixes=("", "_fr"),
        )

        # Fallback ROCE from companies table
        merged["roce_percentage"] = pd.to_numeric(
            merged["roce_percentage"], errors="coerce"
        )

        # Load Cash Flow Intelligence for FCF CAGR 5Y
        cf_intel_path = output_dir / "cashflow_intelligence.xlsx"
        if cf_intel_path.exists():
            try:
                cf_intel = pd.read_excel(cf_intel_path)
                cf_intel["Company ID"] = cf_intel["Company ID"].astype(str).str.strip()
                merged = merged.merge(
                    cf_intel[["Company ID", "FCF CAGR (5-Year)"]],
                    left_on="id",
                    right_on="Company ID",
                    how="left",
                )
                merged.rename(
                    columns={"FCF CAGR (5-Year)": "fcf_cagr_5yr"}, inplace=True
                )
            except Exception as e:
                logger.warning(f"Error reading cashflow_intelligence.xlsx: {e}")
                merged["fcf_cagr_5yr"] = np.nan
        else:
            merged["fcf_cagr_5yr"] = np.nan

        merged["broad_sector"] = merged["broad_sector"].fillna("Financials & Services")

        # Impute missing values with sector median (and global median fallback)
        for kpi in TEN_KEY_KPIS:
            merged[kpi] = pd.to_numeric(merged[kpi], errors="coerce")
            merged[kpi] = merged.groupby("broad_sector")[kpi].transform(
                lambda x: x.fillna(x.median())
            )
            global_med = merged[kpi].median()
            if pd.isna(global_med):
                global_med = 0.0
            merged[kpi] = merged[kpi].fillna(global_med)

        logger.info(
            f"Loaded and imputed dataset for 10 KPIs across {len(merged)} companies."
        )
        return merged

    finally:
        conn.close()


def generate_cluster_profiles(
    output_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate cluster statistical profile table (Mean & Median of 5 features per cluster)
    and update cluster_labels.csv with descriptive cluster names.

    Args:
        output_dir: Output directory path.
        db_path: SQLite database path.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]:
            - Cluster profiles summary DataFrame.
            - Updated cluster labels DataFrame.
    """
    logger.info("Generating Cluster Statistical Profiles...")

    if output_dir is None:
        output_dir = OUTPUT_DIR

    labels_csv_path = output_dir / "cluster_labels.csv"
    if not labels_csv_path.exists():
        raise FileNotFoundError(f"Cluster labels CSV not found at: {labels_csv_path}")

    cluster_labels_df = pd.read_csv(labels_csv_path)
    cluster_labels_df["Company ID"] = (
        cluster_labels_df["Company ID"].astype(str).str.strip()
    )

    # Load prepared feature data
    prep_df = load_and_prepare_clustering_data(
        db_path, output_dir.parent / "data" if output_dir.parent else None
    )

    # Merge features with cluster_labels
    merged = cluster_labels_df.merge(
        prep_df, left_on="Company ID", right_on="id", how="left"
    )

    profile_rows = []
    unique_clusters = sorted(merged["Cluster ID"].unique().tolist())

    for cid in unique_clusters:
        c_group = merged[merged["Cluster ID"] == cid]
        count = len(c_group)
        c_name = (
            c_group["Cluster Name"].iloc[0]
            if not c_group.empty and "Cluster Name" in c_group.columns
            else f"Cluster {cid}"
        )

        row = {
            "Cluster ID": cid,
            "Cluster Name": c_name,
            "Number of Companies": count,
        }

        for feat in CLUSTERING_FEATURES:
            vals = c_group[feat].values
            row[f"{feat}_mean"] = round(float(np.mean(vals)), 4) if count > 0 else 0.0
            row[f"{feat}_median"] = (
                round(float(np.median(vals)), 4) if count > 0 else 0.0
            )

        profile_rows.append(row)

    profiles_df = pd.DataFrame(profile_rows)

    # Save output/cluster_profiles.csv
    profiles_csv_path = output_dir / "cluster_profiles.csv"
    profiles_df.to_csv(profiles_csv_path, index=False)
    logger.info(
        f"Saved cluster profiles ({len(profiles_df)} rows) to: {profiles_csv_path.resolve()}"
    )

    # Save updated output/cluster_labels.csv
    cluster_labels_df.to_csv(labels_csv_path, index=False)
    logger.info(f"Updated cluster labels saved to: {labels_csv_path.resolve()}")

    return profiles_df, cluster_labels_df


def generate_correlation_matrix_heatmap(
    df_10kpis: pd.DataFrame,
    reports_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, Path]:
    """
    Compute 10-KPI Pearson Correlation Matrix and generate a Seaborn heatmap image.

    Args:
        df_10kpis: DataFrame containing 10 KPI columns across companies.
        reports_dir: Reports output directory path.

    Returns:
        Tuple[pd.DataFrame, Path]:
            - Pearson Correlation Matrix DataFrame.
            - Path to saved correlation_heatmap.png.
    """
    logger.info("Computing Pearson Correlation Matrix & Heatmap...")

    if reports_dir is None:
        reports_dir = REPORTS_DIR

    reports_dir.mkdir(parents=True, exist_ok=True)

    # Calculate Pearson correlation matrix
    corr_df = df_10kpis[TEN_KEY_KPIS].corr(method="pearson")

    # Rename axis labels for clean visual rendering
    corr_renamed = corr_df.rename(index=KPI_DISPLAY_NAMES, columns=KPI_DISPLAY_NAMES)

    # Plot Seaborn Heatmap
    plt.figure(figsize=(9.5, 7.5), dpi=200)
    sns.set_theme(style="white")

    sns.heatmap(
        corr_renamed,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        vmin=-1.0,
        vmax=1.0,
        linewidths=0.5,
        cbar_kws={"shrink": 0.8, "label": "Pearson Correlation Coefficient"},
        annot_kws={"size": 8, "weight": "bold"},
    )

    plt.title(
        "Pearson Correlation Heatmap of Key Financial KPIs",
        fontsize=11,
        fontweight="bold",
        color="#0F172A",
        pad=10,
    )
    plt.xticks(rotation=45, ha="right", fontsize=8.5)
    plt.yticks(rotation=0, fontsize=8.5)
    plt.tight_layout()

    heatmap_path = reports_dir / "correlation_heatmap.png"
    plt.savefig(heatmap_path, format="png", dpi=200, bbox_inches="tight")
    plt.close()

    logger.info(f"Saved correlation heatmap plot to: {heatmap_path.resolve()}")
    return corr_df, heatmap_path


def detect_sector_outliers(
    df_10kpis: pd.DataFrame,
    output_dir: Optional[Path] = None,
    z_threshold: float = 3.0,
) -> pd.DataFrame:
    """
    Calculate sector-based Z-scores for every selected KPI and flag companies where |Z| > 3.

    Args:
        df_10kpis: DataFrame containing company metadata, broad_sector, and 10 KPI columns.
        output_dir: Output directory path.
        z_threshold: Z-score cutoff threshold (default 3.0).

    Returns:
        pd.DataFrame containing detected outlier records.
    """
    logger.info("Performing Sector-based Z-score Outlier Detection (|Z| > 3)...")

    if output_dir is None:
        output_dir = OUTPUT_DIR

    outliers = []

    for sector, group in df_10kpis.groupby("broad_sector"):
        for kpi in TEN_KEY_KPIS:
            vals = group[kpi].values
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0

            for _, row in group.iterrows():
                v = float(row[kpi])
                if std_val > 1e-9:
                    z = (v - mean_val) / std_val
                else:
                    z = 0.0

                if abs(z) > z_threshold:
                    kpi_display = KPI_DISPLAY_NAMES.get(kpi, kpi)
                    outliers.append(
                        {
                            "Company ID": str(row["id"]).strip(),
                            "Company Name": str(
                                row.get("company_name", row["id"])
                            ).strip(),
                            "Broad Sector": sector,
                            "KPI Name": kpi_display,
                            "KPI Value": round(v, 4),
                            "Sector Mean": round(mean_val, 4),
                            "Sector Standard Deviation": round(std_val, 4),
                            "Z-score": round(z, 4),
                            "Outlier Flag": (
                                "High Outlier" if z > z_threshold else "Low Outlier"
                            ),
                        }
                    )

    outliers_df = pd.DataFrame(
        outliers,
        columns=[
            "Company ID",
            "Company Name",
            "Broad Sector",
            "KPI Name",
            "KPI Value",
            "Sector Mean",
            "Sector Standard Deviation",
            "Z-score",
            "Outlier Flag",
        ],
    )

    outlier_csv_path = output_dir / "outlier_report.csv"
    outliers_df.to_csv(outlier_csv_path, index=False)
    logger.info(
        f"Saved outlier report ({len(outliers_df)} records) to: {outlier_csv_path.resolve()}"
    )

    return outliers_df


def generate_portfolio_statistics(
    df_10kpis: pd.DataFrame,
    output_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Generate portfolio-wide descriptive statistics (P10, P25, P50, P75, P90, Mean, Std)
    for all 10 selected KPIs.

    Args:
        df_10kpis: DataFrame containing 10 KPI columns across all companies.
        output_dir: Output directory path.

    Returns:
        pd.DataFrame containing portfolio descriptive statistics.
    """
    logger.info("Calculating Portfolio-wide Descriptive Statistics...")

    if output_dir is None:
        output_dir = OUTPUT_DIR

    stats_rows = []

    for kpi in TEN_KEY_KPIS:
        vals = df_10kpis[kpi].dropna().values
        kpi_display = KPI_DISPLAY_NAMES.get(kpi, kpi)

        if len(vals) > 0:
            stats_rows.append(
                {
                    "KPI Name": kpi_display,
                    "P10": round(float(np.percentile(vals, 10)), 4),
                    "P25": round(float(np.percentile(vals, 25)), 4),
                    "P50 (Median)": round(float(np.percentile(vals, 50)), 4),
                    "P75": round(float(np.percentile(vals, 75)), 4),
                    "P90": round(float(np.percentile(vals, 90)), 4),
                    "Mean": round(float(np.mean(vals)), 4),
                    "Standard Deviation": round(float(np.std(vals, ddof=1)), 4),
                }
            )
        else:
            stats_rows.append(
                {
                    "KPI Name": kpi_display,
                    "P10": 0.0,
                    "P25": 0.0,
                    "P50 (Median)": 0.0,
                    "P75": 0.0,
                    "P90": 0.0,
                    "Mean": 0.0,
                    "Standard Deviation": 0.0,
                }
            )

    stats_df = pd.DataFrame(
        stats_rows,
        columns=[
            "KPI Name",
            "P10",
            "P25",
            "P50 (Median)",
            "P75",
            "P90",
            "Mean",
            "Standard Deviation",
        ],
    )

    stats_csv_path = output_dir / "portfolio_stats.csv"
    stats_df.to_csv(stats_csv_path, index=False)
    logger.info(
        f"Saved portfolio statistics ({len(stats_df)} KPIs) to: {stats_csv_path.resolve()}"
    )

    return stats_df


def run_cluster_profiling_pipeline(
    project_root: Optional[Path] = None,
) -> Dict[str, Union[pd.DataFrame, Path]]:
    """
    Main orchestration function for Day 37 Cluster Profiling & Portfolio Statistics workflow.

    Args:
        project_root: Root directory path of project.

    Returns:
        Dict containing generated DataFrames and output file paths.
    """
    logger.info("Executing Day 37 Cluster Profiling & Portfolio Statistics pipeline...")

    if project_root is None:
        project_root = PROJECT_ROOT

    db_path = project_root / "data" / "db" / "nifty100.db"
    output_dir = project_root / "output"
    reports_dir = project_root / "reports"

    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 1. Cluster Profiling & Name Assignment
    profiles_df, labels_df = generate_cluster_profiles(output_dir, db_path)

    # 2. Load 10 KPIs dataset
    df_10kpis = load_10_kpis_dataset(db_path, output_dir)

    # 3. Pearson Correlation Matrix & Heatmap Plot
    corr_df, heatmap_path = generate_correlation_matrix_heatmap(df_10kpis, reports_dir)

    # 4. Outlier Detection (|Z| > 3)
    outliers_df = detect_sector_outliers(df_10kpis, output_dir, z_threshold=3.0)

    # 5. Portfolio Statistics
    stats_df = generate_portfolio_statistics(df_10kpis, output_dir)

    logger.info("Day 37 Cluster Profiling pipeline successfully completed.")

    return {
        "cluster_profiles": profiles_df,
        "cluster_labels": labels_df,
        "correlation_matrix": corr_df,
        "outlier_report": outliers_df,
        "portfolio_stats": stats_df,
        "output_paths": {
            "cluster_profiles_csv": output_dir / "cluster_profiles.csv",
            "cluster_labels_csv": output_dir / "cluster_labels.csv",
            "outlier_report_csv": output_dir / "outlier_report.csv",
            "portfolio_stats_csv": output_dir / "portfolio_stats.csv",
            "correlation_heatmap_png": reports_dir / "correlation_heatmap.png",
        },
    }


if __name__ == "__main__":
    run_cluster_profiling_pipeline()
