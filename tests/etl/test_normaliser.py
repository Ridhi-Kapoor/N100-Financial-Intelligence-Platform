import pytest
from scripts.etl.normaliser import normalize_year, normalize_ticker


# ----------------------------
# normalize_year()
# ----------------------------

def test_year_fy18():
    assert normalize_year("FY18") == 2018

def test_year_fy19():
    assert normalize_year("FY19") == 2019

def test_year_2022():
    assert normalize_year("2022") == 2022

def test_year_2023():
    assert normalize_year("2023") == 2023

def test_ticker_lower_ns():
    assert normalize_ticker("tcs.ns") == "TCS"

def test_ticker_digits():
    assert normalize_ticker("abc123") == "ABC123"

def test_ticker_newline():
    assert normalize_ticker("INFY\n") == "INFY"

def test_ticker_tab():
    assert normalize_ticker("\tTCS") == "TCS"

def test_year_fy20():
    assert normalize_year("FY20") == 2020


def test_year_fy2020():
    assert normalize_year("FY2020") == 2020


def test_year_range():
    assert normalize_year("2020-21") == 2020


def test_year_integer():
    assert normalize_year(2021) == 2021


def test_year_none():
    assert normalize_year(None) is None


def test_year_empty():
    assert normalize_year("") is None


def test_year_invalid():
    assert normalize_year("ABC") is None


def test_year_spaces():
    assert normalize_year(" FY22 ") == 2022


# ----------------------------
# normalize_ticker()
# ----------------------------

def test_ticker_lowercase():
    assert normalize_ticker("tcs") == "TCS"


def test_ticker_uppercase():
    assert normalize_ticker("INFY") == "INFY"


def test_ticker_ns():
    assert normalize_ticker("RELIANCE.NS") == "RELIANCE"


def test_ticker_spaces():
    assert normalize_ticker("  hdfcbank ") == "HDFCBANK"


def test_ticker_none():
    assert normalize_ticker(None) is None


def test_ticker_empty():
    assert normalize_ticker("") == ""


def test_ticker_special():
    assert normalize_ticker("SBIN.NS") == "SBIN"


def test_ticker_mixed():
    assert normalize_ticker("TcS") == "TCS"