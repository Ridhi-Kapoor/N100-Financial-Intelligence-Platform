"""
Unit tests for the financial leverage and efficiency ratios.

Covers the following test cases:
1. Debt-to-Equity normal calculation
2. Borrowings = 0 returns 0
3. Denominator <=0 returns None
4. High leverage flag (>5)
5. Financial company does NOT receive high leverage flag
6. Interest =0 returns None
7. ICR label = Debt Free
8. Asset Turnover with total_assets = 0 returns None
"""

import pytest
from src.analytics.ratios import (
    calculate_debt_to_equity,
    get_high_leverage_flag,
    calculate_interest_coverage_ratio,
    calculate_asset_turnover,
)


def test_debt_to_equity_normal():
    # Debt-to-Equity = borrowings / (equity_capital + reserves)
    # borrowings = 200, equity_capital = 50, reserves = 150
    # denominator = 200 -> D/E = 1.0
    result = calculate_debt_to_equity(200.0, 50.0, 150.0)
    assert result == pytest.approx(1.0)

    # borrowings = 150, equity_capital = 100, reserves = 200
    # denominator = 300 -> D/E = 0.5
    result_2 = calculate_debt_to_equity(150.0, 100.0, 200.0)
    assert result_2 == pytest.approx(0.5)


def test_debt_to_equity_borrowings_zero():
    # Borrowings = 0 returns 0
    assert calculate_debt_to_equity(0.0, 100.0, 200.0) == 0.0
    assert calculate_debt_to_equity(0, 100.0, 200.0) == 0.0


def test_debt_to_equity_denominator_invalid():
    # Denominator <= 0 returns None
    # equity_capital + reserves = 0
    assert calculate_debt_to_equity(100.0, 0.0, 0.0) is None
    # equity_capital + reserves < 0
    assert calculate_debt_to_equity(100.0, -50.0, 20.0) is None
    # None inputs
    assert calculate_debt_to_equity(None, 100.0, 200.0) is None
    assert calculate_debt_to_equity(100.0, None, 200.0) is None


def test_high_leverage_flag_greater_than_five():
    # Debt-to-Equity > 5, broad_sector != "Financials" -> True
    assert get_high_leverage_flag(5.1, "Technology") is True
    # Debt-to-Equity = 5.0 -> False
    assert get_high_leverage_flag(5.0, "Technology") is False
    # Debt-to-Equity < 5.0 -> False
    assert get_high_leverage_flag(4.9, "Technology") is False


def test_high_leverage_flag_financial_company():
    # Financial company should never receive the flag
    assert get_high_leverage_flag(6.0, "Financials") is False
    assert get_high_leverage_flag(10.5, "Financials ") is False  # with trailing space


def test_interest_zero_returns_none():
    # If interest == 0, return ICR = None
    icr, label = calculate_interest_coverage_ratio(100.0, 50.0, 0.0)
    assert icr is None


def test_icr_label_debt_free():
    # If interest == 0, store icr_label = "Debt Free"
    icr, label = calculate_interest_coverage_ratio(100.0, 50.0, 0.0)
    assert label == "Debt Free"


def test_asset_turnover_assets_zero():
    # Asset Turnover = sales / total_assets
    # total_assets = 0 returns None
    assert calculate_asset_turnover(100.0, 0.0) is None
    # normal calculation
    assert calculate_asset_turnover(500.0, 1000.0) == pytest.approx(0.5)
