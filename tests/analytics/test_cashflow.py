"""
Unit tests for cash flow analytics calculations.

Covers the following test cases:
1. Free Cash Flow normal positive case
2. Free Cash Flow with negative values
3. CFO Quality Score - High Quality
4. CFO Quality Score - Accrual Risk
5. CFO Quality Score - Insufficient ratios
6. CapEx Intensity - Asset Light
7. CapEx Intensity - Capital Intensive
8. FCF Conversion - Normal calculation
9. FCF Conversion - Zero Operating Profit
10. Capital Allocation Pattern - Reinvestor
11. Capital Allocation Pattern - Shareholder Returns
12. Capital Allocation Pattern - Distress Signal
"""

import pytest
from src.analytics.cashflow import (
    calculate_free_cash_flow,
    calculate_cfo_quality_score,
    calculate_capex_intensity,
    calculate_fcf_conversion,
    classify_capital_allocation,
)


def test_free_cash_flow_normal():
    # Operating = 500, Investing = -200 -> FCF = 300
    assert calculate_free_cash_flow(500.0, -200.0) == pytest.approx(300.0)


def test_free_cash_flow_negative():
    # Operating = -100, Investing = -400 -> FCF = -500
    assert calculate_free_cash_flow(-100.0, -400.0) == pytest.approx(-500.0)
    # Inputs with None
    assert calculate_free_cash_flow(500.0, None) is None


def test_cfo_quality_score_high():
    # Previous 5 years CFO/PAT ratios: 1.2, 1.1, 1.3, 1.0, 1.4 -> average = 1.2 > 1.0 -> High Quality
    score, label = calculate_cfo_quality_score([1.2, 1.1, 1.3, 1.0, 1.4])
    assert score == pytest.approx(1.2)
    assert label == "High Quality"


def test_cfo_quality_score_accrual_risk():
    # Previous 5 years: 0.2, 0.3, 0.4, 0.1, 0.5 -> average = 0.3 < 0.5 -> Accrual Risk
    score, label = calculate_cfo_quality_score([0.2, 0.3, 0.4, 0.1, 0.5])
    assert score == pytest.approx(0.3)
    assert label == "Accrual Risk"


def test_cfo_quality_score_insufficient():
    # Fewer than 5 ratios -> None
    score, label = calculate_cfo_quality_score([1.2, 1.1, 1.3])
    assert score is None
    assert label is None


def test_capex_intensity_asset_light():
    # abs(-20) / 1000 * 100 = 2% < 3% -> Asset Light
    intensity, label = calculate_capex_intensity(-20.0, 1000.0)
    assert intensity == pytest.approx(2.0)
    assert label == "Asset Light"


def test_capex_intensity_capital_intensive():
    # abs(-100) / 1000 * 100 = 10% > 8% -> Capital Intensive
    intensity, label = calculate_capex_intensity(-100.0, 1000.0)
    assert intensity == pytest.approx(10.0)
    assert label == "Capital Intensive"


def test_fcf_conversion_normal():
    # FCF = 150, Operating Profit = 300 -> 50%
    assert calculate_fcf_conversion(150.0, 300.0) == pytest.approx(50.0)


def test_fcf_conversion_zero_profit():
    # Operating Profit = 0 -> None
    assert calculate_fcf_conversion(150.0, 0.0) is None


def test_classify_capital_allocation_reinvestor():
    # CFO >= 0 (+), CFI < 0 (-), CFF < 0 (-) and CFO/PAT <= 1.0 -> Reinvestor
    # CFO = 100, PAT = 150 -> CFO/PAT = 0.67 <= 1.0
    cfo_s, cfi_s, cff_s, label = classify_capital_allocation(100.0, -50.0, -30.0, 150.0)
    assert cfo_s == "+"
    assert cfi_s == "-"
    assert cff_s == "-"
    assert label == "Reinvestor"


def test_classify_capital_allocation_shareholder_returns():
    # CFO >= 0 (+), CFI < 0 (-), CFF < 0 (-) and CFO/PAT > 1.0 -> Shareholder Returns
    # CFO = 200, PAT = 150 -> CFO/PAT = 1.33 > 1.0
    cfo_s, cfi_s, cff_s, label = classify_capital_allocation(200.0, -50.0, -30.0, 150.0)
    assert cfo_s == "+"
    assert cfi_s == "-"
    assert cff_s == "-"
    assert label == "Shareholder Returns"


def test_classify_capital_allocation_distress_signal():
    # CFO < 0 (-), CFI >= 0 (+), CFF >= 0 (+) -> Distress Signal
    cfo_s, cfi_s, cff_s, label = classify_capital_allocation(-100.0, 50.0, 30.0, 150.0)
    assert cfo_s == "-"
    assert cfi_s == "+"
    assert cff_s == "+"
    assert label == "Distress Signal"
