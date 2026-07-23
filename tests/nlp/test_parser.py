"""
Tests for src/nlp/parser.py (Day 29 NLP Text Parser).
"""

import sys
from pathlib import Path
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.nlp.parser import (
    parse_text_field,
    load_analysis_file,
    parse_analysis_data,
    cross_validate_with_ratio_engine,
    run_nlp_parser,
)


def test_parse_text_field_valid():
    """Test parsing valid metric strings."""
    period, val, failure = parse_text_field("10 Years: 21%")
    assert period == 10
    assert val == 21.0
    assert failure is None

    period, val, failure = parse_text_field("5 Years       24%")
    assert period == 5
    assert val == 24.0
    assert failure is None

    period, val, failure = parse_text_field("1 Year:       16%")
    assert period == 1
    assert val == 16.0
    assert failure is None

    period, val, failure = parse_text_field("3 Years: 12.5%")
    assert period == 3
    assert val == 12.5
    assert failure is None


def test_parse_text_field_failures():
    """Test parsing invalid / unsupported text fields."""
    # Empty / None
    period, val, failure = parse_text_field(None)
    assert period is None and val is None
    assert failure == "Empty or missing text"

    period, val, failure = parse_text_field("nan")
    assert period is None and val is None
    assert failure == "Empty or missing text"

    # TTM
    period, val, failure = parse_text_field("TTM: 43%")
    assert period is None and val is None
    assert "TTM format not supported" in failure

    # Last Year
    period, val, failure = parse_text_field("Last Year: 12%")
    assert period is None and val is None
    assert "Last Year format not supported" in failure

    # Negative value
    period, val, failure = parse_text_field("1 Year: -2%")
    assert period is None and val is None
    assert "Negative percentage value not matched" in failure


def test_load_analysis_file_real():
    """Test loading data/raw/analysis.xlsx."""
    file_path = PROJECT_ROOT / "data" / "raw" / "analysis.xlsx"
    if file_path.exists():
        df = load_analysis_file(file_path)
        assert not df.empty
        assert "company_id" in df.columns
        assert "compounded_sales_growth" in df.columns


def test_parse_analysis_data_workflow():
    """Test parsing dataframe into parsed and failure records."""
    dummy_data = pd.DataFrame(
        [
            {
                "company_id": "TESTCO",
                "compounded_sales_growth": "10 Years: 20%",
                "compounded_profit_growth": "TTM: 15%",
                "stock_price_cagr": "5 Years: 10%",
                "roe": "Last Year: 18%",
            }
        ]
    )

    comp_map = {"TESTCO": "Test Company Ltd"}
    parsed_df, failures_df = parse_analysis_data(dummy_data, comp_map)

    assert len(parsed_df) == 2
    assert set(parsed_df["Metric Type"]) == {
        "compounded_sales_growth",
        "stock_price_cagr",
    }

    assert len(failures_df) == 2
    assert set(failures_df["Metric Type"]) == {"compounded_profit_growth", "roe"}
    assert failures_df["Company Name"].iloc[0] == "Test Company Ltd"


def test_cross_validate_with_ratio_engine():
    """Test cross-validation status assignment."""
    parsed_df = pd.DataFrame(
        [
            {
                "Company ID": "HDFCBANK",
                "Metric Type": "compounded_sales_growth",
                "Period (Years)": 10,
                "Value (%)": 21.0,
            }
        ]
    )
    comp_map = {"HDFCBANK": "HDFC Bank Ltd"}
    val_df = cross_validate_with_ratio_engine(
        parsed_df, PROJECT_ROOT / "data" / "processed", comp_map
    )

    assert not val_df.empty
    assert "Review Status" in val_df.columns
    assert val_df["Review Status"].iloc[0] in ("Pass", "Manual Review")


def test_run_nlp_parser_end_to_end(tmp_path):
    """Test full pipeline execution saving to temp output directory."""
    raw_file = PROJECT_ROOT / "data" / "raw" / "analysis.xlsx"
    if raw_file.exists():
        res = run_nlp_parser(input_file=raw_file, output_dir=tmp_path)

        assert "parsed_df" in res
        assert "failures_df" in res
        assert "validation_df" in res

        assert (tmp_path / "analysis_parsed.csv").exists()
        assert (tmp_path / "parse_failures.csv").exists()
        assert (tmp_path / "validation_report.csv").exists()

        parsed_file_df = pd.read_csv(tmp_path / "analysis_parsed.csv")
        assert len(parsed_file_df) == len(res["parsed_df"])
