"""
Unit tests for normalize_year() function in ETL pipeline.
Covers 20 test cases including all supported date formats, edge cases,
invalid inputs, boundary values, and whitespace handling.
"""

from scripts.etl.normaliser import normalize_year


def test_normalize_year_yyyy():
    """Verify standard YYYY string format."""
    assert normalize_year("2023") == 2023


def test_normalize_year_yyyy_mm_dash():
    """Verify YYYY-MM dash separator format."""
    assert normalize_year("2021-03") == 2021


def test_normalize_year_yyyy_mm_slash():
    """Verify YYYY/MM slash separator format."""
    assert normalize_year("2022/05") == 2022


def test_normalize_year_dd_mm_yyyy():
    """Verify DD-MM-YYYY full date format."""
    assert normalize_year("31-03-2020") == 2020


def test_normalize_year_mm_yyyy():
    """Verify MM/YYYY month-year format."""
    assert normalize_year("03/2021") == 2021


def test_normalize_year_integer():
    """Verify integer year values."""
    assert normalize_year(2022) == 2022


def test_normalize_year_string():
    """Verify numeric string year values."""
    assert normalize_year("2020") == 2020


def test_normalize_year_leading_trailing_whitespace():
    """Verify strings with leading/trailing whitespace."""
    assert normalize_year("  2021  ") == 2021


def test_normalize_year_null():
    """Verify None/Null input handling."""
    assert normalize_year(None) is None


def test_normalize_year_empty_string():
    """Verify empty string input."""
    assert normalize_year("") is None


def test_normalize_year_whitespace_only():
    """Verify whitespace-only string input."""
    assert normalize_year("   ") is None


def test_normalize_year_invalid_date_format():
    """Verify invalid date string format."""
    assert normalize_year("INVALID_DATE") is None


def test_normalize_year_future_year():
    """Verify future year handling."""
    assert normalize_year("2050") == 2050


def test_normalize_year_very_old_year():
    """Verify old/historical year handling (19xx)."""
    assert normalize_year("1995") == 1995


def test_normalize_year_non_numeric():
    """Verify arbitrary non-numeric text input."""
    assert normalize_year("ABCXYZ") is None


def test_normalize_year_mixed_separators():
    """Verify dates with mixed separators."""
    assert normalize_year("2021/03-15") == 2021


def test_normalize_year_fy_prefix_two_digit():
    """Verify FY prefix with 2-digit year (e.g. FY20)."""
    assert normalize_year("FY20") == 2020


def test_normalize_year_fy_prefix_four_digit():
    """Verify FY prefix with 4-digit year (e.g. FY2020)."""
    assert normalize_year("FY2020") == 2020


def test_normalize_year_ttm_preservation():
    """Verify TTM string preservation."""
    assert normalize_year("TTM") == "TTM"


def test_normalize_year_boundary_values():
    """Verify boundary years (2000 and 2099)."""
    assert normalize_year("2000") == 2000
    assert normalize_year("2099") == 2099
