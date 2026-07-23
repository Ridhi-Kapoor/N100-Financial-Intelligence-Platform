"""
Unit tests for Day 31 Cash Flow Intelligence module (src/analytics/cashflow_kpis.py).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.cashflow_kpis import (
    detect_distress_signal,
    detect_deleveraging,
    generate_cashflow_intelligence_report,
)


def test_detect_distress_signal():
    """Test distress signal detection (CFO < 0 and CFF > 0)."""
    assert detect_distress_signal(-100.0, 50.0) is True
    assert detect_distress_signal(100.0, 50.0) is False
    assert detect_distress_signal(-100.0, -50.0) is False
    assert detect_distress_signal(None, 50.0) is False


def test_detect_deleveraging():
    """Test deleveraging detection (CFF < 0 and borrowings decreasing YoY)."""
    assert detect_deleveraging(-50.0, 800.0, 1000.0) is True
    assert detect_deleveraging(50.0, 800.0, 1000.0) is False
    assert detect_deleveraging(-50.0, 1200.0, 1000.0) is False
    assert detect_deleveraging(-50.0, None, 1000.0) is False


def test_generate_cashflow_intelligence_report_end_to_end(tmp_path):
    """Test end-to-end execution of cashflow intelligence report generation."""
    intel_df, distress_df = generate_cashflow_intelligence_report(
        processed_dir=PROJECT_ROOT / "data" / "processed",
        output_dir=tmp_path,
    )

    assert not intel_df.empty
    expected_intel_cols = [
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
    ]
    assert list(intel_df.columns) == expected_intel_cols

    assert (tmp_path / "cashflow_intelligence.xlsx").exists()
    assert (tmp_path / "distress_alerts.csv").exists()

    expected_distress_cols = [
        "Company ID",
        "Company Name",
        "Sector",
        "Latest Operating Cash Flow (CFO)",
        "Latest Cash Flow from Financing (CFF)",
        "Latest Net Profit",
        "Distress Reason",
    ]
    assert list(distress_df.columns) == expected_distress_cols
