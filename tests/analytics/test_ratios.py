"""
Unit tests for the financial ratios module.

Covers the following test cases:
1. Net Profit Margin normal calculation
2. Net Profit Margin when sales = 0
3. Operating Profit Margin calculation
4. OPM mismatch (>1%) logging and return value
5. ROE normal case
6. ROE with negative/zero denominator
7. ROCE calculation including Financials sector
8. ROA when total_assets = 0
9. Sector benchmark calculation for Financials
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from src.analytics.ratios import (
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    validate_operating_profit_margin,
    calculate_roe,
    calculate_roce,
    calculate_roa,
    get_financial_sector_roce_benchmark,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_FILE = PROJECT_ROOT / "logs" / "opm_validation.log"


def test_net_profit_margin_normal():
    # NPM = (net_profit / sales) * 100
    # Normal case: profit 150, sales 1000 -> 15%
    result = calculate_net_profit_margin(150.0, 1000.0)
    assert result == pytest.approx(15.0)

    # Negative profit case: profit -50, sales 500 -> -10%
    result_neg = calculate_net_profit_margin(-50.0, 500.0)
    assert result_neg == pytest.approx(-10.0)


def test_net_profit_margin_sales_zero():
    # Sales = 0
    assert calculate_net_profit_margin(150.0, 0.0) is None
    # Sales = None
    assert calculate_net_profit_margin(150.0, None) is None
    # Net profit = None
    assert calculate_net_profit_margin(None, 1000.0) is None
    # NaN check
    assert calculate_net_profit_margin(150.0, float("nan")) is None


def test_operating_profit_margin_normal():
    # OPM = (operating_profit / sales) * 100
    # Normal case: operating profit 250, sales 1000 -> 25%
    result = calculate_operating_profit_margin(250.0, 1000.0)
    assert result == pytest.approx(25.0)


def test_opm_mismatch():
    # Read current size of log file if it exists
    initial_size = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0

    # Case 1: Difference is within 1% (e.g. 0.8% difference) -> Should return True and NOT log
    assert (
        validate_operating_profit_margin(
            calculated_opm=24.8,
            source_opm=24.0,
            company_id="COMP1",
            company_name="Company One",
            year=2024,
        )
        is True
    )

    # Check that no log was written (size did not change)
    current_size = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0
    assert current_size == initial_size

    # Case 2: Difference is greater than 1% (e.g. 1.5% difference) -> Should return False and log
    assert (
        validate_operating_profit_margin(
            calculated_opm=25.5,
            source_opm=24.0,
            company_id="COMP2",
            company_name="Company Two",
            year=2024,
        )
        is False
    )

    # Check that mismatch log was appended (size increased)
    new_size = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0
    assert new_size > current_size

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log_content = f.read()
    assert "COMP2" in log_content
    assert "Company Two" in log_content
    assert "2024" in log_content
    assert "25.5" in log_content
    assert "24.0" in log_content
    assert "1.5" in log_content


def test_roe_normal():
    # ROE = net_profit / (equity_capital + reserves) * 100
    # Normal case: profit 120, equity 100, reserves 300 -> 120 / 400 * 100 = 30%
    result = calculate_roe(120.0, 100.0, 300.0)
    assert result == pytest.approx(30.0)


def test_roe_invalid_denominator():
    # Denominator (equity + reserves) <= 0
    # Zero denominator
    assert calculate_roe(100.0, 0.0, 0.0) is None
    # Negative denominator
    assert calculate_roe(100.0, 50.0, -100.0) is None
    # None inputs
    assert calculate_roe(None, 100.0, 300.0) is None
    assert calculate_roe(120.0, None, 300.0) is None


def test_roce_calculation_including_financials():
    # ROCE = EBIT / (equity_capital + reserves + borrowings) * 100
    # Normal sector (e.g. Industrials)
    # EBIT 200, equity 100, reserves 300, borrowings 100 -> 200 / 500 * 100 = 40%
    result_ind = calculate_roce(200.0, 100.0, 300.0, 100.0, "Industrials")
    assert result_ind == pytest.approx(40.0)

    # Financials sector - should return tuple (roce, benchmark_status)
    # Case A: No benchmark provided -> status is None
    result_fin_no_bench = calculate_roce(200.0, 100.0, 300.0, 100.0, "Financials")
    assert isinstance(result_fin_no_bench, tuple)
    assert result_fin_no_bench[0] == pytest.approx(40.0)
    assert result_fin_no_bench[1] is None

    # Case B: Benchmark is 35.0% -> ROCE (40%) >= Benchmark -> Above Benchmark
    result_fin_above = calculate_roce(
        200.0, 100.0, 300.0, 100.0, "Financials", benchmark_roce=35.0
    )
    assert result_fin_above == (pytest.approx(40.0), "Above Benchmark")

    # Case C: Benchmark is 45.0% -> ROCE (40%) < Benchmark -> Below Benchmark
    result_fin_below = calculate_roce(
        200.0, 100.0, 300.0, 100.0, "Financials", benchmark_roce=45.0
    )
    assert result_fin_below == (pytest.approx(40.0), "Below Benchmark")


def test_roa_assets_zero():
    # Normal case: profit 50, assets 1000 -> 5%
    assert calculate_roa(50.0, 1000.0) == pytest.approx(5.0)

    # Total assets = 0
    assert calculate_roa(50.0, 0.0) is None
    # None inputs
    assert calculate_roa(None, 1000.0) is None
    assert calculate_roa(50.0, None) is None


def test_get_financial_sector_roce_benchmark():
    # Create mock dataframe containing sector and roce column
    df = pd.DataFrame(
        {
            "broad_sector": [
                "Financials",
                "Financials",
                "Industrials",
                "Financials",
                "Healthcare",
            ],
            "roce": [15.0, 25.0, 40.0, np.nan, 20.0],
        }
    )

    # Expected average ROCE for Financials is (15 + 25) / 2 = 20.0
    bench = get_financial_sector_roce_benchmark(df)
    assert bench == pytest.approx(20.0)

    # Empty df or invalid structure
    assert get_financial_sector_roce_benchmark(pd.DataFrame()) is None
    assert get_financial_sector_roce_benchmark(None) is None
