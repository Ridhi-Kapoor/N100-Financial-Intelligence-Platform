"""
Unit tests for financial ratio calculations and KPI metrics.

Covers 20 unit tests across ROE, Debt-to-Equity, Interest Coverage Ratio (ICR),
CAGR, Operating Profit Margin (OPM), CFO Quality Score, and edge case behaviors.
"""

import pytest
from src.analytics.ratios import (
    calculate_roe,
    calculate_debt_to_equity,
    get_high_leverage_flag,
    calculate_interest_coverage_ratio,
    calculate_operating_profit_margin,
    validate_operating_profit_margin,
    calculate_net_profit_margin,
    calculate_roa,
)
from src.analytics.cagr import calculate_cagr
from src.analytics.cashflow import calculate_cfo_quality_score

# -------------------------------------------------------------------------
# 1. Return on Equity (ROE) Tests
# -------------------------------------------------------------------------


def test_roe_positive_equity():
    """ROE calculation with positive net profit and positive equity."""
    # Net profit = 150, Equity = 100 + 400 = 500 -> ROE = 30.0%
    assert calculate_roe(150.0, 100.0, 400.0) == pytest.approx(30.0)


def test_roe_zero_equity():
    """ROE calculation with zero total equity (should return None)."""
    assert calculate_roe(100.0, 0.0, 0.0) is None


def test_roe_negative_equity():
    """ROE calculation with negative equity (should return None)."""
    assert calculate_roe(100.0, -200.0, 50.0) is None


# -------------------------------------------------------------------------
# 2. Debt-to-Equity Tests
# -------------------------------------------------------------------------


def test_debt_to_equity_debt_free():
    """Debt-to-Equity for a debt-free company (borrowings = 0, returns 0.0)."""
    assert calculate_debt_to_equity(0.0, 100.0, 400.0) == 0.0


def test_debt_to_equity_high_leverage():
    """Debt-to-Equity calculation under high debt load."""
    # Borrowings = 600, Equity = 50 + 50 = 100 -> D/E = 6.0
    assert calculate_debt_to_equity(600.0, 50.0, 50.0) == pytest.approx(6.0)


def test_high_leverage_flag_non_financial():
    """High leverage flag triggers when D/E > 5 for non-financial companies."""
    assert get_high_leverage_flag(5.5, "Technology") is True
    assert get_high_leverage_flag(5.5, "Financials") is False


# -------------------------------------------------------------------------
# 3. Interest Coverage Ratio (ICR) Tests
# -------------------------------------------------------------------------


def test_icr_normal_calculation():
    """Interest Coverage Ratio normal calculation."""
    # OP = 100, Other Income = 20, Interest = 30 -> ICR = 120 / 30 = 4.0
    icr, label = calculate_interest_coverage_ratio(100.0, 20.0, 30.0)
    assert icr == pytest.approx(4.0)
    assert label is None


def test_icr_zero_interest():
    """ICR calculation when interest expense is zero (returns None, 'Debt Free')."""
    icr, label = calculate_interest_coverage_ratio(100.0, 20.0, 0.0)
    assert icr is None
    assert label == "Debt Free"


# -------------------------------------------------------------------------
# 4. Compound Annual Growth Rate (CAGR) Tests
# -------------------------------------------------------------------------


def test_cagr_normal_calculation():
    """Normal CAGR calculation with positive beginning and ending values."""
    val, flag = calculate_cagr(100.0, 144.0, 2)
    assert val == pytest.approx(20.0)
    assert flag is None


def test_cagr_turnaround_case():
    """CAGR turnaround case from negative to positive value."""
    val, flag = calculate_cagr(-50.0, 100.0, 3)
    assert val is None
    assert flag == "TURNAROUND"


def test_cagr_decline_to_loss_case():
    """CAGR decline to loss case from positive to negative value."""
    val, flag = calculate_cagr(100.0, -20.0, 3)
    assert val is None
    assert flag == "DECLINE_TO_LOSS"


def test_cagr_negative_to_positive_transition():
    """CAGR negative-to-positive transition handling."""
    val, flag = calculate_cagr(-100.0, 50.0, 5)
    assert val is None
    assert flag == "TURNAROUND"


def test_cagr_invalid_period_handling():
    """CAGR handling of invalid/zero/negative period n."""
    val, flag = calculate_cagr(100.0, 200.0, 0)
    assert val is None
    assert flag == "INSUFFICIENT"


# -------------------------------------------------------------------------
# 5. Operating Profit Margin (OPM) Tests
# -------------------------------------------------------------------------


def test_opm_correct_calculation():
    """Operating Profit Margin correct calculation."""
    # Operating profit = 250, Sales = 1000 -> OPM = 25.0%
    assert calculate_operating_profit_margin(250.0, 1000.0) == pytest.approx(25.0)


def test_opm_cross_check_divergence_flag():
    """OPM validation flags discrepancy when difference exceeds 1.0%."""
    # calc_opm = 25.0, source_opm = 20.0 -> diff = 5.0% -> returns False
    assert validate_operating_profit_margin(25.0, 20.0, "TCS", "Tata", 2021) is False
    # calc_opm = 25.0, source_opm = 25.4 -> diff = 0.4% -> returns True
    assert validate_operating_profit_margin(25.0, 25.4, "TCS", "Tata", 2021) is True


# -------------------------------------------------------------------------
# 6. CFO Quality Score Tests
# -------------------------------------------------------------------------


def test_cfo_quality_score_strong():
    """CFO Quality Score for strong cash flow (> 1.0 -> 'High Quality')."""
    score, label = calculate_cfo_quality_score([1.2, 1.5, 1.1, 1.3, 1.4])
    assert score == pytest.approx(1.3)
    assert label == "High Quality"


def test_cfo_quality_score_weak():
    """CFO Quality Score for weak cash flow (< 0.5 -> 'Accrual Risk')."""
    score, label = calculate_cfo_quality_score([0.2, 0.3, 0.4, 0.1, 0.3])
    assert score == pytest.approx(0.26)
    assert label == "Accrual Risk"


def test_cfo_quality_score_zero_cfo():
    """CFO Quality Score when CFO is zero over period."""
    score, label = calculate_cfo_quality_score([0.0, 0.0, 0.0, 0.0, 0.0])
    assert score == 0.0
    assert label == "Accrual Risk"


def test_cfo_quality_score_negative_cfo():
    """CFO Quality Score when CFO is negative."""
    score, label = calculate_cfo_quality_score([-0.5, -0.2, -0.1, -0.4, -0.3])
    assert score == pytest.approx(-0.3)
    assert label == "Accrual Risk"


# -------------------------------------------------------------------------
# 7. Additional Profitability & Edge Case Tests
# -------------------------------------------------------------------------


def test_net_profit_margin_and_roa():
    """Verify NPM and ROA ratio calculation edge cases."""
    assert calculate_net_profit_margin(120.0, 1000.0) == pytest.approx(12.0)
    assert calculate_net_profit_margin(120.0, 0.0) is None
    assert calculate_roa(80.0, 800.0) == pytest.approx(10.0)
    assert calculate_roa(80.0, 0.0) is None
