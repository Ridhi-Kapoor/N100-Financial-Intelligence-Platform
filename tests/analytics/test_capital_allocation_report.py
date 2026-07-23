"""
Unit and integration tests for Capital Allocation Report module.
"""

from pathlib import Path
import tempfile
import pandas as pd
import pytest

from src.analytics.capital_allocation_report import (
    ALL_CAPITAL_ALLOCATION_PATTERNS,
    detect_pattern_changes,
    generate_capital_allocation_distribution,
    generate_capital_allocation_report,
    integrate_with_cashflow_intelligence,
    validate_capital_allocation_data,
)


@pytest.fixture
def mock_ca_df():
    return pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "year": 2022,
                "cfo_sign": "+",
                "cfi_sign": "-",
                "cff_sign": "-",
                "pattern_label": "Reinvestor",
            },
            {
                "company_id": "ABC",
                "year": 2023,
                "cfo_sign": "+",
                "cfi_sign": "-",
                "cff_sign": "-",
                "pattern_label": "Shareholder Returns",
            },
            {
                "company_id": "ABC",
                "year": 2024,
                "cfo_sign": "+",
                "cfi_sign": "-",
                "cff_sign": "-",
                "pattern_label": "Shareholder Returns",
            },
            {
                "company_id": "XYZ",
                "year": 2023,
                "cfo_sign": "-",
                "cfi_sign": "+",
                "cff_sign": "+",
                "pattern_label": "Distress Signal",
            },
            {
                "company_id": "XYZ",
                "year": 2024,
                "cfo_sign": "-",
                "cfi_sign": "-",
                "cff_sign": "+",
                "pattern_label": "Growth Funded by Debt",
            },
        ]
    )


@pytest.fixture
def mock_companies_df():
    return pd.DataFrame(
        [
            {"id": "ABC", "company_name": "ABC Corp Ltd"},
            {"id": "XYZ", "company_name": "XYZ Holdings Ltd"},
            {"id": "NOP", "company_name": "NOP Enterprise Ltd"},
        ]
    )


def test_validate_capital_allocation_data(mock_ca_df, mock_companies_df):
    summary_df, metrics = validate_capital_allocation_data(
        mock_ca_df, mock_companies_df
    )

    assert not summary_df.empty
    assert metrics["total_records"] == 5
    assert metrics["master_companies_count"] == 3
    assert metrics["missing_companies"] == ["NOP"]
    assert metrics["duplicate_records_count"] == 0
    assert metrics["missing_labels_count"] == 0


def test_validate_capital_allocation_with_anomalies():
    dirty_ca = pd.DataFrame(
        [
            {"company_id": "ABC", "year": 2023, "pattern_label": "Reinvestor"},
            {
                "company_id": "ABC",
                "year": 2023,
                "pattern_label": "Reinvestor",
            },  # duplicate
            {
                "company_id": "ABC",
                "year": 2024,
                "pattern_label": "Unknown",
            },  # missing label
        ]
    )
    summary_df, metrics = validate_capital_allocation_data(dirty_ca)

    assert metrics["duplicate_records_count"] == 2
    assert metrics["missing_labels_count"] == 1


def test_generate_capital_allocation_distribution(mock_ca_df):
    dist_df = generate_capital_allocation_distribution(mock_ca_df)

    assert len(dist_df) == 8
    assert (
        list(dist_df["Capital Allocation Pattern"]) == ALL_CAPITAL_ALLOCATION_PATTERNS
    )
    assert (
        dist_df["Number of Companies"].sum() == 2
    )  # ABC and XYZ in latest year (2024)

    abc_row = dist_df[dist_df["Capital Allocation Pattern"] == "Shareholder Returns"]
    assert abc_row["Number of Companies"].values[0] == 1
    assert abc_row["Percentage of Total Companies"].values[0] == 50.0


def test_integrate_with_cashflow_intelligence(mock_ca_df):
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        excel_file = tmp_path / "cashflow_intelligence.xlsx"

        # Create dummy existing cashflow_intelligence.xlsx
        existing_df = pd.DataFrame(
            [
                {"Company ID": "ABC", "Sector": "Tech", "Distress Flag": "No"},
                {"Company ID": "XYZ", "Sector": "Energy", "Distress Flag": "Yes"},
            ]
        )
        existing_df.to_excel(excel_file, index=False)

        updated_df = integrate_with_cashflow_intelligence(excel_file, mock_ca_df)

        assert "Capital Allocation" in updated_df.columns
        assert (
            updated_df[updated_df["Company ID"] == "ABC"]["Capital Allocation"].values[
                0
            ]
            == "Shareholder Returns"
        )
        assert (
            updated_df[updated_df["Company ID"] == "XYZ"]["Capital Allocation"].values[
                0
            ]
            == "Growth Funded by Debt"
        )
        assert excel_file.exists()


def test_detect_pattern_changes(mock_ca_df, mock_companies_df):
    changes_df = detect_pattern_changes(mock_ca_df, mock_companies_df)

    assert len(changes_df) == 2

    abc_change = changes_df[changes_df["Company ID"] == "ABC"].iloc[0]
    assert abc_change["Previous Year"] == 2022
    assert abc_change["Previous Pattern"] == "Reinvestor"
    assert abc_change["Current Year"] == 2023
    assert abc_change["Current Pattern"] == "Shareholder Returns"
    assert "Reinvestor" in abc_change["Change Description"]
    assert "Shareholder Returns" in abc_change["Change Description"]

    xyz_change = changes_df[changes_df["Company ID"] == "XYZ"].iloc[0]
    assert xyz_change["Previous Pattern"] == "Distress Signal"
    assert xyz_change["Current Pattern"] == "Growth Funded by Debt"


def test_generate_capital_allocation_report_e2e(tmp_path):
    # Setup mock data directory structure
    data_dir = tmp_path / "data"
    processed_dir = data_dir / "processed"
    output_dir = tmp_path / "output"

    processed_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    companies_csv = processed_dir / "companies.csv"
    pd.DataFrame(
        [
            {"id": "ABC", "company_name": "ABC Corp"},
            {"id": "XYZ", "company_name": "XYZ Corp"},
        ]
    ).to_csv(companies_csv, index=False)

    ca_csv = output_dir / "capital_allocation.csv"
    pd.DataFrame(
        [
            {"company_id": "ABC", "year": 2023, "pattern_label": "Reinvestor"},
            {"company_id": "ABC", "year": 2024, "pattern_label": "Shareholder Returns"},
            {"company_id": "XYZ", "year": 2023, "pattern_label": "Distress Signal"},
            {"company_id": "XYZ", "year": 2024, "pattern_label": "Distress Signal"},
        ]
    ).to_csv(ca_csv, index=False)

    intel_excel = output_dir / "cashflow_intelligence.xlsx"
    pd.DataFrame([{"Company ID": "ABC"}, {"Company ID": "XYZ"}]).to_excel(
        intel_excel, index=False
    )

    results = generate_capital_allocation_report(tmp_path)

    assert (output_dir / "capital_allocation_validation.csv").exists()
    assert (output_dir / "capital_allocation_distribution.csv").exists()
    assert (output_dir / "pattern_changes.csv").exists()
    assert (output_dir / "cashflow_intelligence.xlsx").exists()

    assert len(results["pattern_changes"]) == 1
