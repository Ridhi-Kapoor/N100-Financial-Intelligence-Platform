"""
Unit tests for CAGR calculations.

Covers the following test cases:
1. Normal CAGR (Positive -> Positive)
2. Positive -> Negative (decline to loss)
3. Negative -> Positive (turnaround)
4. Both Negative (negative -> negative)
5. Zero Base (beginning value is 0)
6. Insufficient Data (missing values, n <= 0, etc.)
7. Revenue CAGR (using dataframe function)
8. PAT CAGR (using dataframe function)
9. EPS CAGR (using dataframe function)
10. Invalid input (non-numeric, NaN, etc.)
"""

import pandas as pd
import pytest

from src.analytics.cagr import calculate_cagr, compute_dataframe_cagr


def test_normal_cagr():
    # beg = 100, end = 133.1, n = 3 -> (1.331 ** (1/3) - 1) * 100 = 10%
    val, flag = calculate_cagr(100.0, 133.1, 3)
    assert val == pytest.approx(10.0)
    assert flag is None

    # beg = 100, end = 200, n = 1 -> 100%
    val_1, flag_1 = calculate_cagr(100.0, 200.0, 1)
    assert val_1 == pytest.approx(100.0)
    assert flag_1 is None


def test_positive_to_negative():
    # beg = 100, end = -50, n = 3 -> None, DECLINE_TO_LOSS
    val, flag = calculate_cagr(100.0, -50.0, 3)
    assert val is None
    assert flag == "DECLINE_TO_LOSS"


def test_negative_to_positive():
    # beg = -100, end = 50, n = 3 -> None, TURNAROUND
    val, flag = calculate_cagr(-100.0, 50.0, 3)
    assert val is None
    assert flag == "TURNAROUND"


def test_both_negative():
    # beg = -100, end = -50, n = 3 -> None, BOTH_NEGATIVE
    val, flag = calculate_cagr(-100.0, -50.0, 3)
    assert val is None
    assert flag == "BOTH_NEGATIVE"


def test_zero_base():
    # beg = 0, end = 100, n = 3 -> None, ZERO_BASE
    val, flag = calculate_cagr(0.0, 100.0, 3)
    assert val is None
    assert flag == "ZERO_BASE"


def test_insufficient_data():
    # n <= 0
    val_1, flag_1 = calculate_cagr(100.0, 150.0, 0)
    assert val_1 is None
    assert flag_1 == "INSUFFICIENT"

    # None inputs
    val_2, flag_2 = calculate_cagr(None, 150.0, 3)
    assert val_2 is None
    assert flag_2 == "INSUFFICIENT"

    val_3, flag_3 = calculate_cagr(100.0, None, 3)
    assert val_3 is None
    assert flag_3 == "INSUFFICIENT"


def test_invalid_input():
    # non-numeric string
    val, flag = calculate_cagr("abc", 150.0, 3)
    assert val is None
    assert flag == "INSUFFICIENT"

    # NaN inputs
    val_nan, flag_nan = calculate_cagr(float("nan"), 150.0, 3)
    assert val_nan is None
    assert flag_nan == "INSUFFICIENT"


def test_dataframe_revenue_cagr():
    df = pd.DataFrame(
        {
            "company_id": ["C1", "C1", "C1", "C1"],
            "year": [2017, 2018, 2019, 2020],
            "sales": [100.0, 110.0, 120.0, 133.1],
        }
    )
    vals, flags = compute_dataframe_cagr(
        df, "sales", 3, "revenue_cagr_3yr", "revenue_cagr_3yr_flag"
    )

    # 2020 should have 3yr CAGR from 2017: (133.1 / 100.0) ** (1/3) - 1 = 10%
    assert vals[3] == pytest.approx(10.0)
    assert flags[3] is None

    # 2017, 2018, 2019 should have INSUFFICIENT flag because there's no year-3 data
    assert vals[0] is None
    assert flags[0] == "INSUFFICIENT"
    assert flags[1] == "INSUFFICIENT"


def test_dataframe_pat_cagr():
    df = pd.DataFrame(
        {
            "company_id": ["C1", "C1", "C1", "C1"],
            "year": [2017, 2018, 2019, 2020],
            "net_profit": [100.0, 120.0, 80.0, -10.0],
        }
    )
    vals, flags = compute_dataframe_cagr(
        df, "net_profit", 3, "pat_cagr_3yr", "pat_cagr_3yr_flag"
    )

    # 2020 is Positive -> Negative -> None, DECLINE_TO_LOSS
    assert vals[3] is None
    assert flags[3] == "DECLINE_TO_LOSS"


def test_dataframe_eps_cagr():
    df = pd.DataFrame(
        {
            "company_id": ["C1", "C1", "C1", "C1"],
            "year": [2017, 2018, 2019, 2020],
            "eps": [-2.0, -1.0, 1.0, 5.0],
        }
    )
    vals, flags = compute_dataframe_cagr(
        df, "eps", 3, "eps_cagr_3yr", "eps_cagr_3yr_flag"
    )

    # 2020 is Negative -> Positive -> None, TURNAROUND
    assert vals[3] is None
    assert flags[3] == "TURNAROUND"
