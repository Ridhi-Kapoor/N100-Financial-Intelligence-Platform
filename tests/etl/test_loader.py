import pandas as pd
import pytest
from scripts.etl.loader import validate_dataframe


# ----------------------------
# validate_dataframe()
# ----------------------------

def test_valid_dataframe():
    df = pd.DataFrame({"A":[1,2]})
    assert validate_dataframe(df) == True


def test_empty_dataframe():
    df = pd.DataFrame()

    with pytest.raises(ValueError):
        validate_dataframe(df)


def test_single_row():
    df = pd.DataFrame({"A":[10]})
    assert validate_dataframe(df)


def test_multiple_columns():
    df = pd.DataFrame({
        "Name":["A","B"],
        "Age":[10,20]
    })

    assert validate_dataframe(df)


def test_missing_values():
    df = pd.DataFrame({
        "A":[1,None]
    })

    assert validate_dataframe(df)


def test_duplicate_rows():
    df = pd.DataFrame({
        "A":[1,1]
    })

    assert validate_dataframe(df)


def test_string_dataframe():
    df = pd.DataFrame({
        "Name":["ABC","XYZ"]
    })

    assert validate_dataframe(df)


def test_numeric_dataframe():
    df = pd.DataFrame({
        "A":[10,20,30]
    })

    assert validate_dataframe(df)

def test_dataframe_three_rows():
    df = pd.DataFrame({"A":[1,2,3]})
    assert validate_dataframe(df)

def test_dataframe_float():
    df = pd.DataFrame({"A":[1.5,2.5]})
    assert validate_dataframe(df)

def test_dataframe_boolean():
    df = pd.DataFrame({"A":[True,False]})
    assert validate_dataframe(df)

def test_dataframe_large():
    df = pd.DataFrame({"A":range(100)})
    assert validate_dataframe(df)

def test_dataframe_duplicate_columns():
    df = pd.DataFrame([[1,2]], columns=["A","A"])
    assert validate_dataframe(df)