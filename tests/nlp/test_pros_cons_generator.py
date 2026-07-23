"""
Unit tests for Day 30 NLP Auto Pros & Cons Generator module (src/nlp/pros_cons_generator.py).
"""

import sys
from pathlib import Path
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.nlp.pros_cons_generator import (
    load_dataset,
    evaluate_company_rules,
    generate_pros_cons_report,
)


def test_load_dataset():
    """Test loading financial datasets."""
    datasets = load_dataset(PROJECT_ROOT / "data" / "processed")
    assert "companies" in datasets
    assert "pl" in datasets
    assert "bs" in datasets
    assert "cf" in datasets
    assert "ratios" in datasets
    assert "sectors" in datasets
    assert not datasets["companies"].empty


def test_evaluate_company_rules_sample():
    """Test rule evaluation for a sample company (HDFCBANK)."""
    datasets = load_dataset(PROJECT_ROOT / "data" / "processed")
    insights = evaluate_company_rules("HDFCBANK", datasets)

    assert len(insights) >= 2
    types = {item["type"] for item in insights}
    assert "Pro" in types
    assert "Con" in types

    for item in insights:
        assert 60.0 < item["score"] <= 100.0
        assert item["rule_id"] is not None
        assert len(item["text"]) > 10


def test_validation_at_least_one_pro_and_con():
    """Test that every company evaluates to at least one Pro and one Con."""
    datasets = load_dataset(PROJECT_ROOT / "data" / "processed")
    companies = datasets["companies"]["id"].unique()[:10]

    for cid in companies:
        insights = evaluate_company_rules(cid, datasets)
        pros = [item for item in insights if item["type"] == "Pro"]
        cons = [item for item in insights if item["type"] == "Con"]
        assert len(pros) >= 1, f"Company {cid} missing Pro"
        assert len(cons) >= 1, f"Company {cid} missing Con"


def test_generate_pros_cons_report_end_to_end(tmp_path):
    """Test full pipeline execution saving to temp output directory."""
    df_out = generate_pros_cons_report(
        processed_dir=PROJECT_ROOT / "data" / "processed",
        output_dir=tmp_path,
    )

    assert not df_out.empty
    expected_cols = [
        "Company ID",
        "Type",
        "Rule ID",
        "Generated Text",
        "Confidence Score (%)",
    ]
    assert list(df_out.columns) == expected_cols

    output_csv = tmp_path / "pros_cons_generated.csv"
    assert output_csv.exists()

    df_csv = pd.read_csv(output_csv)
    assert len(df_csv) == len(df_out)
    assert (df_csv["Confidence Score (%)"] > 60.0).all()
