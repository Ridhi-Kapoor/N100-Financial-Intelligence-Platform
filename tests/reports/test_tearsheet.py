"""
Unit and integration tests for Company Tearsheet PDF Generator (Day 33).
"""

import pypdf

from src.reports.tearsheet import (
    fetch_tearsheet_data,
    generate_all_tearsheets,
    generate_tearsheet_pdf,
)


def test_fetch_tearsheet_data():
    data = fetch_tearsheet_data("TCS")

    assert data["ticker"] == "TCS"
    assert "Tata Consultancy Services" in data["company_name"]
    assert "Information Technology" in data["sector"]
    assert len(data["pl_years"]) > 0
    assert len(data["bs_years"]) > 0
    assert "capital_allocation_label" in data


def test_generate_tearsheet_pdf_single(tmp_path):
    output_pdf = tmp_path / "TCS_tearsheet.pdf"
    res_path = generate_tearsheet_pdf("TCS", output_path=output_pdf)

    assert res_path.exists()
    assert res_path.stat().st_size > 50000

    reader = pypdf.PdfReader(res_path)
    assert len(reader.pages) == 2


def test_generate_all_tearsheets_batch(tmp_path):
    tickers = ["TCS", "HDFCBANK", "RELIANCE"]
    results = generate_all_tearsheets(tickers=tickers, output_dir=tmp_path)

    assert len(results) == 3
    for ticker, pdf_path in results.items():
        assert pdf_path.exists()
        reader = pypdf.PdfReader(pdf_path)
        assert len(reader.pages) == 2


def test_missing_company_graceful_handling(tmp_path):
    output_pdf = tmp_path / "UNKNOWN_COMPANY_tearsheet.pdf"
    res_path = generate_tearsheet_pdf("UNKNOWN_COMPANY", output_path=output_pdf)

    assert res_path.exists()
    reader = pypdf.PdfReader(res_path)
    assert len(reader.pages) == 2
