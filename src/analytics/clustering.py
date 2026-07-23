"""
Module for K-Means Financial Clustering and Profile Analysis.

This module delivers Day 36 Financial Clustering functionality:
1. Data loading and feature extraction (ROE, D/E, Revenue CAGR 5Y, FCF CAGR 5Y, OPM %).
2. Sector-median missing value imputation and validation.
3. Feature standardization using StandardScaler.
4. K-Means clustering (k = 5, random_state = 42).
5. Inertia calculation and Elbow curve plot generation (reports/elbow_plot.png).
6. Centroid Euclidean distance calculation and dynamic cluster profile naming.
7. Export to output/cluster_labels.csv.
"""

import logging
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Tuple, Union

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "db" / "nifty100.db"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Configure logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("financial_clustering")
logger.setLevel(logging.INFO)

if not logger.handlers:
    log_file = LOG_DIR / "financial_clustering.log"
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

CLUSTERING_FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]


def load_and_prepare_clustering_data(
    db_path: Optional[Path] = None,
    data_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load financial features and sector information, and handle missing values
    by imputing sector medians (with global median fallback).

    Args:
        db_path: Path to nifty100.db SQLite database.
        data_dir: Path to data/ directory.

    Returns:
        pd.DataFrame containing company metadata and clean, imputed feature columns.
    """
    logger.info("Loading dataset for K-Means Financial Clustering...")

    if db_path is None:
        db_path = DB_PATH
    if data_dir is None:
        data_dir = DATA_DIR

    conn = sqlite3.connect(db_path)

    try:
        # Load companies
        comp_df = pd.read_sql("SELECT id, company_name FROM companies", conn)
        comp_df["id"] = comp_df["id"].astype(str).str.strip()

        # Load sectors
        sec_df = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
        sec_df["company_id"] = sec_df["company_id"].astype(str).str.strip()

        # Load financial ratios (latest available year per company)
        ratios_df = pd.read_sql("SELECT * FROM financial_ratios", conn)
        ratios_df["company_id"] = ratios_df["company_id"].astype(str).str.strip()

        if not ratios_df.empty and "year" in ratios_df.columns:
            ratios_clean = ratios_df[ratios_df["year"].astype(str).str.isdigit()].copy()
            ratios_clean["year_num"] = ratios_clean["year"].astype(int)
            latest_ratios = (
                ratios_clean.sort_values("year_num")
                .groupby("company_id")
                .last()
                .reset_index()
            )
        else:
            latest_ratios = pd.DataFrame(columns=["company_id"] + CLUSTERING_FEATURES)

        # Load Cash Flow Intelligence for FCF CAGR 5Y if present
        cf_intel_path = OUTPUT_DIR / "cashflow_intelligence.xlsx"
        if not cf_intel_path.exists():
            cf_intel_path = data_dir / "output" / "cashflow_intelligence.xlsx"

        if cf_intel_path.exists():
            try:
                cf_intel = pd.read_excel(cf_intel_path)
                cf_intel["Company ID"] = cf_intel["Company ID"].astype(str).str.strip()
            except Exception as e:
                logger.warning(f"Error reading cashflow_intelligence.xlsx: {e}")
                cf_intel = pd.DataFrame()
        else:
            cf_intel = pd.DataFrame()

        # Merge Datasets
        merged = comp_df.merge(sec_df, left_on="id", right_on="company_id", how="left")
        merged = merged.merge(
            latest_ratios[
                [
                    "company_id",
                    "return_on_equity_pct",
                    "debt_to_equity",
                    "revenue_cagr_5yr",
                    "operating_profit_margin_pct",
                ]
            ],
            on="company_id",
            how="left",
        )

        if not cf_intel.empty and "FCF CAGR (5-Year)" in cf_intel.columns:
            merged = merged.merge(
                cf_intel[["Company ID", "FCF CAGR (5-Year)"]],
                left_on="id",
                right_on="Company ID",
                how="left",
            )
            merged.rename(columns={"FCF CAGR (5-Year)": "fcf_cagr_5yr"}, inplace=True)
        else:
            merged["fcf_cagr_5yr"] = np.nan

        # Fill broad_sector if missing
        merged["broad_sector"] = merged["broad_sector"].fillna("Financials & Services")

        # Impute missing values with sector median (and fallback to global median)
        for col in CLUSTERING_FEATURES:
            merged[col] = pd.to_numeric(merged[col], errors="coerce")
            merged[col] = merged.groupby("broad_sector")[col].transform(
                lambda x: x.fillna(x.median())
            )
            global_med = merged[col].median()
            if pd.isna(global_med):
                global_med = 0.0
            merged[col] = merged[col].fillna(global_med)

        # Validate zero missing values
        null_count = merged[CLUSTERING_FEATURES].isna().sum().sum()
        if null_count > 0:
            raise ValueError(
                f"Imputation check failed: {null_count} missing values remain after imputation."
            )

        logger.info(
            f"Successfully loaded and prepared dataset with {len(merged)} company records."
        )
        return merged

    finally:
        conn.close()


def scale_features(
    df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
) -> Tuple[np.ndarray, StandardScaler]:
    """
    Standardize features using StandardScaler so that Mean = 0 and Std = 1.

    Args:
        df: Input DataFrame containing feature columns.
        feature_cols: List of feature names.

    Returns:
        Tuple[np.ndarray, StandardScaler]:
            - Scaled feature matrix.
            - Fitted StandardScaler instance.
    """
    if feature_cols is None:
        feature_cols = CLUSTERING_FEATURES

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df[feature_cols])
    logger.info("Features standardized with StandardScaler (Mean = 0, Std = 1).")
    return X_scaled, scaler


def perform_kmeans_clustering(
    X_scaled: np.ndarray,
    n_clusters: int = 5,
    random_state: int = 42,
    n_init: int = 10,
) -> Tuple[np.ndarray, np.ndarray, KMeans]:
    """
    Perform K-Means clustering and calculate Euclidean distance from each sample to its assigned centroid.

    Args:
        X_scaled: Standardized feature matrix.
        n_clusters: Number of clusters (default 5).
        random_state: Random seed (default 42).
        n_init: Number of initializations (default 10).

    Returns:
        Tuple[np.ndarray, np.ndarray, KMeans]:
            - Cluster labels array (0 to n_clusters-1).
            - Centroid Euclidean distances array.
            - Fitted KMeans model instance.
    """
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=n_init)
    labels = kmeans.fit_predict(X_scaled)
    centroids = kmeans.cluster_centers_

    distances = np.zeros(len(X_scaled))
    for i in range(len(X_scaled)):
        c_id = labels[i]
        distances[i] = np.linalg.norm(X_scaled[i] - centroids[c_id])

    logger.info(
        f"K-Means clustering complete (n_clusters={n_clusters}, random_state={random_state})."
    )
    return labels, distances, kmeans


def derive_cluster_names(
    df: pd.DataFrame,
    cluster_labels: np.ndarray,
    feature_cols: Optional[List[str]] = None,
) -> Dict[int, str]:
    """
    Derive meaningful descriptive names for each cluster based on its average financial profile.

    Characteristics evaluated:
    - Quality Compounders: High ROE & High OPM with Low/Moderate Leverage.
    - High Growth: High Revenue CAGR & High FCF CAGR.
    - Capital Intensive: High Debt-to-Equity.
    - Value Plays / Stable Yield: Moderate ROE & Low Debt-to-Equity.
    - Turnaround Candidates: Low ROE & Low/Negative CAGR.

    Args:
        df: Input DataFrame with raw feature columns.
        cluster_labels: Cluster assignment array.
        feature_cols: List of feature names.

    Returns:
        Dict[int, str]: Mapping from cluster ID (0 to 4) to descriptive Cluster Name.
    """
    if feature_cols is None:
        feature_cols = CLUSTERING_FEATURES

    df_calc = df.copy()
    df_calc["cluster_id"] = cluster_labels

    cluster_means = df_calc.groupby("cluster_id")[feature_cols].mean()

    # Overall population medians for comparison
    pop_medians = df_calc[feature_cols].median()

    cluster_names = {}
    assigned_names = set()

    for cid in range(len(cluster_means)):
        row = cluster_means.loc[cid]

        roe = row["return_on_equity_pct"]
        de = row["debt_to_equity"]
        rev_cagr = row["revenue_cagr_5yr"]
        fcf_cagr = row["fcf_cagr_5yr"]
        opm = row["operating_profit_margin_pct"]

        # Score relative attributes
        if (
            roe > pop_medians["return_on_equity_pct"] * 1.5
            and opm > pop_medians["operating_profit_margin_pct"]
            and de <= pop_medians["debt_to_equity"] * 2.0
        ):
            name_candidate = "Quality Compounders"
        elif (
            rev_cagr > pop_medians["revenue_cagr_5yr"] * 1.2
            or fcf_cagr > pop_medians["fcf_cagr_5yr"] * 1.2
        ):
            name_candidate = "High Growth"
        elif de > pop_medians["debt_to_equity"] * 2.0:
            name_candidate = "Capital Intensive"
        elif roe < pop_medians["return_on_equity_pct"] * 0.75 or rev_cagr < 0:
            name_candidate = "Turnaround Candidates"
        else:
            name_candidate = "Value Plays"

        # Resolve duplicate candidate names across clusters by adding descriptive suffix if needed
        if name_candidate in assigned_names:
            if de > pop_medians["debt_to_equity"]:
                name_candidate = f"{name_candidate} (Leveraged)"
            elif roe > pop_medians["return_on_equity_pct"]:
                name_candidate = f"{name_candidate} (High ROE)"
            else:
                name_candidate = f"{name_candidate} (Stable)"

        assigned_names.add(name_candidate)
        cluster_names[cid] = name_candidate

    logger.info(f"Derived cluster names: {cluster_names}")
    return cluster_names


def plot_elbow_curve(
    X_scaled: np.ndarray,
    k_min: int = 2,
    k_max: int = 10,
    output_path: Optional[Path] = None,
) -> Dict[int, float]:
    """
    Calculate inertia for k=k_min through k=k_max and save the elbow curve plot.

    Args:
        X_scaled: Standardized feature matrix.
        k_min: Minimum k (default 2).
        k_max: Maximum k (default 10).
        output_path: Target path to save PNG plot. Defaults to reports/elbow_plot.png.

    Returns:
        Dict[int, float]: Mapping from k value to inertia.
    """
    logger.info(f"Evaluating Elbow Method for k={k_min} to k={k_max}...")

    if output_path is None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / "elbow_plot.png"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    inertias = {}
    k_range = list(range(k_min, k_max + 1))

    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias[k] = float(km.inertia_)

    # Generate Matplotlib Elbow Plot
    plt.figure(figsize=(7, 4.2), dpi=200)
    plt.plot(
        k_range,
        list(inertias.values()),
        marker="o",
        color="#2563EB",
        linewidth=2,
        markersize=6,
    )
    plt.axvline(
        x=5, color="#DC2626", linestyle="--", linewidth=1.5, label="Selected k = 5"
    )

    plt.title(
        "Elbow Method for Optimal K-Means Clusters",
        fontsize=11,
        fontweight="bold",
        color="#0F172A",
        pad=8,
    )
    plt.xlabel("Number of Clusters (k)", fontsize=9, fontweight="bold", color="#334155")
    plt.ylabel(
        "Inertia (Sum of Squared Distances)",
        fontsize=9,
        fontweight="bold",
        color="#334155",
    )
    plt.xticks(k_range)
    plt.grid(True, linestyle="--", alpha=0.35)
    plt.legend(loc="upper right", fontsize=8.5)
    plt.tight_layout()

    plt.savefig(output_path, format="png", dpi=200, bbox_inches="tight")
    plt.close()
    logger.info(f"Elbow plot saved successfully to: {output_path.resolve()}")

    return inertias


def run_clustering_pipeline(
    project_root: Optional[Path] = None,
) -> Dict[str, Union[pd.DataFrame, Path, Dict]]:
    """
    Main orchestration function for Day 36 K-Means Financial Clustering.

    Prepares dataset, scales features, fits K-Means (k=5), generates elbow plot,
    computes centroid distances, derives dynamic cluster names, and exports results.

    Args:
        project_root: Root directory of project.

    Returns:
        Dict containing result DataFrame, output paths, and inertias.
    """
    logger.info("Starting K-Means Financial Clustering pipeline...")

    if project_root is None:
        project_root = PROJECT_ROOT

    data_dir = project_root / "data"
    output_dir = project_root / "output"
    reports_dir = project_root / "reports"

    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load and Impute Data
    df = load_and_prepare_clustering_data(
        project_root / "data" / "db" / "nifty100.db", data_dir
    )

    # 2. Scale Features
    X_scaled, scaler = scale_features(df, CLUSTERING_FEATURES)

    # 3. K-Means Clustering (k=5)
    cluster_labels, distances, kmeans_model = perform_kmeans_clustering(
        X_scaled, n_clusters=5, random_state=42, n_init=10
    )

    # 4. Dynamic Cluster Naming
    cluster_names_map = derive_cluster_names(df, cluster_labels, CLUSTERING_FEATURES)

    # 5. Build Output DataFrame
    output_df = pd.DataFrame(
        {
            "Company ID": df["id"],
            "Cluster ID": cluster_labels,
            "Cluster Name": [cluster_names_map[cid] for cid in cluster_labels],
            "Distance from Cluster Centroid": np.round(distances, 4),
        }
    )

    # Export to output/cluster_labels.csv
    csv_path = output_dir / "cluster_labels.csv"
    output_df.to_csv(csv_path, index=False)
    logger.info(
        f"Saved cluster labels ({len(output_df)} rows) to: {csv_path.resolve()}"
    )

    # 6. Elbow Plot
    elbow_plot_path = reports_dir / "elbow_plot.png"
    inertias = plot_elbow_curve(
        X_scaled, k_min=2, k_max=10, output_path=elbow_plot_path
    )

    logger.info("K-Means Financial Clustering pipeline completed successfully.")

    return {
        "cluster_labels_df": output_df,
        "cluster_names": cluster_names_map,
        "inertias": inertias,
        "output_csv": csv_path,
        "elbow_plot": elbow_plot_path,
    }


if __name__ == "__main__":
    run_clustering_pipeline()
