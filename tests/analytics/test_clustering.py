"""
Unit and integration tests for K-Means Financial Clustering module (Day 36).
"""

import numpy as np
import pandas as pd
import pytest

from src.analytics.clustering import (
    CLUSTERING_FEATURES,
    derive_cluster_names,
    load_and_prepare_clustering_data,
    perform_kmeans_clustering,
    plot_elbow_curve,
    run_clustering_pipeline,
    scale_features,
)


@pytest.fixture
def mock_financial_df():
    # 10 synthetic companies with 5 features
    data = [
        {
            "id": "COMP1",
            "broad_sector": "Technology",
            "return_on_equity_pct": 35.0,
            "debt_to_equity": 0.1,
            "revenue_cagr_5yr": 15.0,
            "fcf_cagr_5yr": 20.0,
            "operating_profit_margin_pct": 28.0,
        },
        {
            "id": "COMP2",
            "broad_sector": "Technology",
            "return_on_equity_pct": 30.0,
            "debt_to_equity": 0.2,
            "revenue_cagr_5yr": 18.0,
            "fcf_cagr_5yr": 22.0,
            "operating_profit_margin_pct": 25.0,
        },
        {
            "id": "COMP3",
            "broad_sector": "Energy",
            "return_on_equity_pct": 10.0,
            "debt_to_equity": 1.8,
            "revenue_cagr_5yr": 5.0,
            "fcf_cagr_5yr": 4.0,
            "operating_profit_margin_pct": 12.0,
        },
        {
            "id": "COMP4",
            "broad_sector": "Energy",
            "return_on_equity_pct": 8.0,
            "debt_to_equity": 2.2,
            "revenue_cagr_5yr": 3.0,
            "fcf_cagr_5yr": 2.0,
            "operating_profit_margin_pct": 10.0,
        },
        {
            "id": "COMP5",
            "broad_sector": "Healthcare",
            "return_on_equity_pct": 20.0,
            "debt_to_equity": 0.3,
            "revenue_cagr_5yr": 12.0,
            "fcf_cagr_5yr": 14.0,
            "operating_profit_margin_pct": 22.0,
        },
        {
            "id": "COMP6",
            "broad_sector": "Healthcare",
            "return_on_equity_pct": 22.0,
            "debt_to_equity": 0.4,
            "revenue_cagr_5yr": 11.0,
            "fcf_cagr_5yr": 13.0,
            "operating_profit_margin_pct": 24.0,
        },
        {
            "id": "COMP7",
            "broad_sector": "Financials",
            "return_on_equity_pct": 15.0,
            "debt_to_equity": 6.5,
            "revenue_cagr_5yr": 8.0,
            "fcf_cagr_5yr": 9.0,
            "operating_profit_margin_pct": 35.0,
        },
        {
            "id": "COMP8",
            "broad_sector": "Financials",
            "return_on_equity_pct": 16.0,
            "debt_to_equity": 7.0,
            "revenue_cagr_5yr": 9.0,
            "fcf_cagr_5yr": 10.0,
            "operating_profit_margin_pct": 38.0,
        },
        {
            "id": "COMP9",
            "broad_sector": "Consumer",
            "return_on_equity_pct": -2.0,
            "debt_to_equity": 1.2,
            "revenue_cagr_5yr": -1.0,
            "fcf_cagr_5yr": -5.0,
            "operating_profit_margin_pct": 4.0,
        },
        {
            "id": "COMP10",
            "broad_sector": "Consumer",
            "return_on_equity_pct": 1.0,
            "debt_to_equity": 1.5,
            "revenue_cagr_5yr": 0.5,
            "fcf_cagr_5yr": -2.0,
            "operating_profit_margin_pct": 5.0,
        },
    ]
    return pd.DataFrame(data)


def test_load_and_prepare_clustering_data():
    df = load_and_prepare_clustering_data()

    assert not df.empty
    assert len(df) == 100
    for col in CLUSTERING_FEATURES:
        assert col in df.columns
        assert df[col].isna().sum() == 0


def test_scale_features(mock_financial_df):
    X_scaled, scaler = scale_features(mock_financial_df, CLUSTERING_FEATURES)

    assert X_scaled.shape == (10, 5)
    assert np.allclose(X_scaled.mean(axis=0), 0.0, atol=1e-6)
    assert np.allclose(X_scaled.std(axis=0), 1.0, atol=1e-6)


def test_perform_kmeans_clustering(mock_financial_df):
    X_scaled, _ = scale_features(mock_financial_df, CLUSTERING_FEATURES)
    labels, distances, model = perform_kmeans_clustering(
        X_scaled, n_clusters=5, random_state=42, n_init=10
    )

    assert len(labels) == 10
    assert set(labels).issubset({0, 1, 2, 3, 4})
    assert len(distances) == 10
    assert np.all(distances >= 0.0)


def test_derive_cluster_names(mock_financial_df):
    X_scaled, _ = scale_features(mock_financial_df, CLUSTERING_FEATURES)
    labels, _, _ = perform_kmeans_clustering(
        X_scaled, n_clusters=5, random_state=42, n_init=10
    )

    names_map = derive_cluster_names(mock_financial_df, labels, CLUSTERING_FEATURES)

    assert len(names_map) == 5
    for cid in range(5):
        assert cid in names_map
        assert isinstance(names_map[cid], str)
        assert len(names_map[cid]) > 0


def test_plot_elbow_curve(mock_financial_df, tmp_path):
    X_scaled, _ = scale_features(mock_financial_df, CLUSTERING_FEATURES)
    plot_path = tmp_path / "elbow_plot.png"

    inertias = plot_elbow_curve(X_scaled, k_min=2, k_max=10, output_path=plot_path)

    assert plot_path.exists()
    assert len(inertias) == 9
    assert 5 in inertias
    # Verify decreasing inertia as k increases
    assert inertias[2] > inertias[10]


def test_run_clustering_pipeline_e2e(tmp_path):
    results = run_clustering_pipeline()

    df_out = results["cluster_labels_df"]
    csv_path = results["output_csv"]
    elbow_path = results["elbow_plot"]

    assert csv_path.exists()
    assert elbow_path.exists()
    assert len(df_out) == 100

    assert list(df_out.columns) == [
        "Company ID",
        "Cluster ID",
        "Cluster Name",
        "Distance from Cluster Centroid",
    ]
    assert df_out["Cluster ID"].nunique() == 5
    assert df_out.isna().sum().sum() == 0
