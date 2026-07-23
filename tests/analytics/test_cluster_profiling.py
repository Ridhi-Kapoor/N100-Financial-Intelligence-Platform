"""
Unit and integration tests for Cluster Profiling and Portfolio Statistics module (Day 37).
"""

import numpy as np
import pandas as pd

from src.analytics.cluster_profiling import (
    TEN_KEY_KPIS,
    detect_sector_outliers,
    generate_cluster_profiles,
    generate_correlation_matrix_heatmap,
    generate_portfolio_statistics,
    load_10_kpis_dataset,
    run_cluster_profiling_pipeline,
)


def test_load_10_kpis_dataset():
    df = load_10_kpis_dataset()

    assert not df.empty
    assert len(df) == 100
    for kpi in TEN_KEY_KPIS:
        assert kpi in df.columns
        assert df[kpi].isna().sum() == 0


def test_generate_cluster_profiles(tmp_path):
    # Setup mock output directory with cluster_labels.csv
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    labels_csv = output_dir / "cluster_labels.csv"
    pd.DataFrame(
        [
            {
                "Company ID": "ABB",
                "Cluster ID": 0,
                "Cluster Name": "Value Plays",
                "Distance from Cluster Centroid": 0.5,
            },
            {
                "Company ID": "ADANIENT",
                "Cluster ID": 1,
                "Cluster Name": "High Growth",
                "Distance from Cluster Centroid": 1.2,
            },
        ]
    ).to_csv(labels_csv, index=False)

    profiles_df, updated_labels = generate_cluster_profiles(output_dir=output_dir)

    assert (output_dir / "cluster_profiles.csv").exists()
    assert not profiles_df.empty
    assert "Cluster ID" in profiles_df.columns
    assert "Number of Companies" in profiles_df.columns
    assert "return_on_equity_pct_mean" in profiles_df.columns
    assert "return_on_equity_pct_median" in profiles_df.columns


def test_generate_correlation_matrix_heatmap(tmp_path):
    df_kpis = load_10_kpis_dataset()
    reports_dir = tmp_path / "reports"

    corr_df, heatmap_path = generate_correlation_matrix_heatmap(
        df_kpis, reports_dir=reports_dir
    )

    assert heatmap_path.exists()
    assert corr_df.shape == (10, 10)
    assert corr_df.isna().sum().sum() == 0
    # Diagonal of correlation matrix should be 1.0
    assert np.allclose(np.diag(corr_df.values), 1.0)


def test_detect_sector_outliers(tmp_path):
    df_kpis = load_10_kpis_dataset()

    # Artificially inject an extreme outlier in one row
    df_kpis.loc[0, "return_on_equity_pct"] = 10000.0

    outliers_df = detect_sector_outliers(df_kpis, output_dir=tmp_path, z_threshold=3.0)

    assert (tmp_path / "outlier_report.csv").exists()
    assert not outliers_df.empty
    assert "Company ID" in outliers_df.columns
    assert "Broad Sector" in outliers_df.columns
    assert "Z-score" in outliers_df.columns
    assert "Outlier Flag" in outliers_df.columns
    assert any(outliers_df["Z-score"] > 3.0)


def test_generate_portfolio_statistics(tmp_path):
    df_kpis = load_10_kpis_dataset()

    stats_df = generate_portfolio_statistics(df_kpis, output_dir=tmp_path)

    assert (tmp_path / "portfolio_stats.csv").exists()
    assert len(stats_df) == 10
    assert list(stats_df.columns) == [
        "KPI Name",
        "P10",
        "P25",
        "P50 (Median)",
        "P75",
        "P90",
        "Mean",
        "Standard Deviation",
    ]
    # P10 <= P25 <= P50 <= P75 <= P90
    for _, row in stats_df.iterrows():
        assert (
            row["P10"] <= row["P25"] <= row["P50 (Median)"] <= row["P75"] <= row["P90"]
        )


def test_run_cluster_profiling_pipeline_e2e(tmp_path):
    results = run_cluster_profiling_pipeline()

    paths = results["output_paths"]

    assert paths["cluster_profiles_csv"].exists()
    assert paths["cluster_labels_csv"].exists()
    assert paths["outlier_report_csv"].exists()
    assert paths["portfolio_stats_csv"].exists()
    assert paths["correlation_heatmap_png"].exists()
