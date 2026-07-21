"""
Unit tests for src/analytics/radar.py module.
"""

from pathlib import Path
import pandas as pd
import pytest

from src.analytics.radar import (
    load_radar_data,
    generate_company_radar_chart,
    generate_all_radar_charts,
    RADAR_METRIC_LABELS,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "radar_charts"


def test_load_radar_data():
    """Verify loading and scaling radar data."""
    df = load_radar_data(db_path=DB_PATH)
    assert not df.empty
    assert len(df) == 100

    score_cols = [
        "ROE_score",
        "ROCE_score",
        "Net_Profit_Margin_score",
        "Debt_to_Equity_score",
        "FCF_Score",
        "PAT_CAGR_5Y_score",
        "Revenue_CAGR_5Y_score",
        "Composite_Quality_Score",
    ]

    for col in score_cols:
        assert col in df.columns
        assert df[col].min() >= 0.0
        assert df[col].max() <= 100.0


def test_generate_single_peer_radar_chart(tmp_path):
    """Verify radar chart generation for a company with a peer group."""
    df = load_radar_data(db_path=DB_PATH)
    score_cols = [
        "ROE_score",
        "ROCE_score",
        "Net_Profit_Margin_score",
        "Debt_to_Equity_score",
        "FCF_Score",
        "PAT_CAGR_5Y_score",
        "Revenue_CAGR_5Y_score",
        "Composite_Quality_Score",
    ]

    peer_averages = {}
    for pg, grp in df.groupby("peer_group_name"):
        if pd.notna(pg):
            peer_averages[str(pg).strip()] = grp[score_cols].mean()

    nifty_average = df[score_cols].mean()

    hdfc = df[df["id"] == "HDFCBANK"].iloc[0]
    out_file = generate_company_radar_chart(
        company_row=hdfc,
        peer_averages=peer_averages,
        nifty_average=nifty_average,
        output_dir=tmp_path,
    )

    assert out_file.exists()
    assert out_file.name == "HDFCBANK_radar.png"
    assert out_file.stat().st_size > 0


def test_generate_standalone_radar_chart(tmp_path):
    """Verify radar chart generation for a company without a peer group (standalone)."""
    df = load_radar_data(db_path=DB_PATH)
    score_cols = [
        "ROE_score",
        "ROCE_score",
        "Net_Profit_Margin_score",
        "Debt_to_Equity_score",
        "FCF_Score",
        "PAT_CAGR_5Y_score",
        "Revenue_CAGR_5Y_score",
        "Composite_Quality_Score",
    ]

    peer_averages = {}
    for pg, grp in df.groupby("peer_group_name"):
        if pd.notna(pg):
            peer_averages[str(pg).strip()] = grp[score_cols].mean()

    nifty_average = df[score_cols].mean()

    zomato = df[df["id"] == "ZOMATO"].iloc[0]
    out_file = generate_company_radar_chart(
        company_row=zomato,
        peer_averages=peer_averages,
        nifty_average=nifty_average,
        output_dir=tmp_path,
    )

    assert out_file.exists()
    assert out_file.name == "ZOMATO_radar.png"
    assert out_file.stat().st_size > 0


def test_generate_all_radar_charts():
    """Verify generating radar charts for all companies."""
    generated = generate_all_radar_charts(db_path=DB_PATH, output_dir=OUTPUT_DIR)
    assert len(generated) == 100
    for p in generated:
        assert p.exists()
        assert p.stat().st_size > 0
