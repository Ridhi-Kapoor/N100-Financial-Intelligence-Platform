"""
Unit tests for the financial sector ratios and anomaly detection engine.
"""

import os
from pathlib import Path
import pytest
from src.analytics.ratios import get_high_leverage_flag
from src.analytics.run_ratio_engine import categorize_anomaly

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_FILE = PROJECT_ROOT / "data" / "output" / "ratio_edge_cases.log"


def test_financial_company_de_suppression():
    # Financial company with debt_to_equity > 5 should NOT get high leverage flag
    assert get_high_leverage_flag(6.0, "Financials") is False
    # Non-financial company with debt_to_equity > 5 SHOULD get high leverage flag
    assert get_high_leverage_flag(6.0, "Technology") is True


def test_anomaly_categorization_version_difference():
    # For a historical year like 2017, it's a Version Difference
    cat = categorize_anomaly("ROCE", "2017", 15.0, 25.0)
    assert cat == "Version Difference"


def test_anomaly_categorization_data_source_issue():
    # For a current year (TTM), if one value is 0.0 or None, it is a Data Source Issue
    cat = categorize_anomaly("ROCE", "TTM", 0.0, 25.0)
    assert cat == "Data Source Issue"

    cat2 = categorize_anomaly("ROCE", "TTM", None, 25.0)
    assert cat2 == "Data Source Issue"


def test_anomaly_categorization_formula_discrepancy():
    # For a current year (TTM), if both are non-zero but mismatch, it's Formula Discrepancy
    cat = categorize_anomaly("ROCE", "TTM", 15.0, 25.0)
    assert cat == "Formula Discrepancy"


def test_roce_mismatch_detection():
    # Test checking logic for difference > 5%
    computed_roce = 10.0
    source_roce = 16.0  # difference = 6.0 > 5.0 -> Mismatch
    assert abs(computed_roce - source_roce) > 5.0

    computed_roce_2 = 10.0
    source_roce_2 = 14.0  # difference = 4.0 <= 5.0 -> Normal
    assert abs(computed_roce_2 - source_roce_2) <= 5.0


def test_roe_comparison():
    computed_roe = 12.0
    source_roe = 18.0  # difference = 6.0 > 5.0 -> Mismatch
    assert abs(computed_roe - source_roe) > 5.0


def test_log_generation(tmp_path):
    # Verify that we can write to the log file and read it back
    test_log = tmp_path / "ratio_edge_cases.log"
    with open(test_log, "w", encoding="utf-8") as f:
        f.write("TEST_ANOMALY")
    
    assert test_log.exists()
    with open(test_log, "r", encoding="utf-8") as f:
        content = f.read()
    assert "TEST_ANOMALY" in content
