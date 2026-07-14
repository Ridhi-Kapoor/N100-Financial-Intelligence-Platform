"""
Unit tests for KPI formulas and financial analytics calculations.

Covers at least 20 test cases across:
- Profitability Ratios
- Leverage Ratios
- Efficiency Ratios
- CAGR Engine
- Cash Flow KPIs
- Capital Allocation logic
"""

import pytest
import pandas as pd
from src.analytics.ratios import (
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    calculate_roe,
    calculate_roce,
    calculate_roa,
    calculate_debt_to_equity,
    get_high_leverage_flag,
    calculate_interest_coverage_ratio,
    get_icr_warning_flag,
    calculate_net_debt,
    calculate_asset_turnover,
)
from src.analytics.cagr import calculate_cagr
from src.analytics.cashflow import (
    calculate_free_cash_flow,
    calculate_cfo_quality_score,
    calculate_capex_intensity,
    calculate_fcf_conversion,
    classify_capital_allocation,
)


# === 1. Profitability Ratios (5 Tests) ===

def test_kpi_net_profit_margin_normal():
    assert calculate_net_profit_margin(120.0, 1000.0) == pytest.approx(12.0)

def test_kpi_net_profit_margin_zero_sales():
    assert calculate_net_profit_margin(120.0, 0.0) is None

def test_kpi_operating_profit_margin_normal():
    assert calculate_operating_profit_margin(200.0, 1000.0) == pytest.approx(20.0)

def test_kpi_roe_normal():
    assert calculate_roe(150.0, 100.0, 400.0) == pytest.approx(30.0)

def test_kpi_roa_normal():
    assert calculate_roa(80.0, 800.0) == pytest.approx(10.0)


# === 2. Leverage Ratios (5 Tests) ===

def test_kpi_debt_to_equity_normal():
    assert calculate_debt_to_equity(300.0, 100.0, 200.0) == pytest.approx(1.0)

def test_kpi_debt_to_equity_zero_borrowings():
    assert calculate_debt_to_equity(0.0, 100.0, 200.0) == 0.0

def test_kpi_high_leverage_flag_non_financial():
    assert get_high_leverage_flag(5.5, "Technology") is True

def test_kpi_high_leverage_flag_financial():
    assert get_high_leverage_flag(5.5, "Financials") is False

def test_kpi_interest_coverage_ratio_zero_interest():
    icr, label = calculate_interest_coverage_ratio(100.0, 20.0, 0.0)
    assert icr is None
    assert label == "Debt Free"


# === 3. Efficiency Ratios (2 Tests) ===

def test_kpi_asset_turnover_normal():
    assert calculate_asset_turnover(1500.0, 1000.0) == pytest.approx(1.5)

def test_kpi_asset_turnover_zero_assets():
    assert calculate_asset_turnover(1500.0, 0.0) is None


# === 4. CAGR Engine (4 Tests) ===

def test_kpi_cagr_normal():
    val, flag = calculate_cagr(100.0, 144.0, 2)
    assert val == pytest.approx(20.0)
    assert flag is None

def test_kpi_cagr_positive_to_negative():
    val, flag = calculate_cagr(100.0, -10.0, 3)
    assert val is None
    assert flag == "DECLINE_TO_LOSS"

def test_kpi_cagr_negative_to_positive():
    val, flag = calculate_cagr(-50.0, 100.0, 3)
    assert val is None
    assert flag == "TURNAROUND"

def test_kpi_cagr_zero_base():
    val, flag = calculate_cagr(0.0, 100.0, 3)
    assert val is None
    assert flag == "ZERO_BASE"


# === 5. Cash Flow KPIs (4 Tests) ===

def test_kpi_free_cash_flow_normal():
    assert calculate_free_cash_flow(400.0, -150.0) == pytest.approx(250.0)

def test_kpi_cfo_quality_score_moderate():
    score, label = calculate_cfo_quality_score([0.8, 0.7, 0.9, 0.6, 1.0])
    assert score == pytest.approx(0.8)
    assert label == "Moderate"

def test_kpi_capex_intensity_moderate():
    intensity, label = calculate_capex_intensity(-50.0, 1000.0)
    assert intensity == pytest.approx(5.0)
    assert label == "Moderate"

def test_kpi_fcf_conversion_normal():
    assert calculate_fcf_conversion(120.0, 200.0) == pytest.approx(60.0)


# === 6. Capital Allocation Logic (3 Tests) ===

def test_kpi_capital_allocation_reinvestor():
    cfo, cfi, cff, label = classify_capital_allocation(100.0, -80.0, -10.0, 150.0)
    assert cfo == "+"
    assert cfi == "-"
    assert cff == "-"
    assert label == "Reinvestor"

def test_kpi_capital_allocation_shareholder_returns():
    cfo, cfi, cff, label = classify_capital_allocation(200.0, -50.0, -50.0, 150.0)
    assert cfo == "+"
    assert cfi == "-"
    assert cff == "-"
    assert label == "Shareholder Returns"

def test_kpi_capital_allocation_liquidating_assets():
    cfo, cfi, cff, label = classify_capital_allocation(100.0, 50.0, -30.0, 150.0)
    assert cfo == "+"
    assert cfi == "+"
    assert cff == "-"
    assert label == "Liquidating Assets"
