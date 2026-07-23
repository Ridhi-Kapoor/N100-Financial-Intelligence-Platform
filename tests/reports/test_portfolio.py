"""
Unit and integration tests for Portfolio Summary PDF Generator (Day 35).
"""

import pypdf

from src.reports.portfolio import (
    calculate_kpi_trend,
    fetch_portfolio_companies_data,
    generate_portfolio_summary_pdf,
)


def test_calculate_kpi_trend():
    # Improved (+5%)
    pct_str, arrow, label = calculate_kpi_trend(105.0, 100.0)
    assert pct_str == "+5.0%"
    assert label == "Improved"
    assert "▲" in arrow

    # Stable (+1%)
    pct_str, arrow, label = calculate_kpi_trend(101.0, 100.0)
    assert pct_str == "+1.0%"
    assert label == "Stable"
    assert "►" in arrow

    # Declined (-5%)
    pct_str, arrow, label = calculate_kpi_trend(95.0, 100.0)
    assert pct_str == "-5.0%"
    assert label == "Declined"
    assert "▼" in arrow

    # Lower is better (Debt-to-equity reduced by 10%)
    pct_str, arrow, label = calculate_kpi_trend(0.9, 1.0, lower_is_better=True)
    assert label == "Improved"
    assert "▲" in arrow


def test_fetch_portfolio_companies_data():
    comp_data = fetch_portfolio_companies_data()

    assert len(comp_data) > 0
    # Verify sorted alphabetically by ticker
    tickers = [c["ticker"] for c in comp_data]
    assert tickers == sorted(tickers)

    first_comp = comp_data[0]
    assert "ticker" in first_comp
    assert "company_name" in first_comp
    assert "kpis" in first_comp
    assert "capital_allocation_label" in first_comp


def test_generate_portfolio_summary_pdf_e2e(tmp_path):
    output_pdf = tmp_path / "portfolio_summary.pdf"
    res_path = generate_portfolio_summary_pdf(output_path=output_pdf)

    assert res_path.exists()
    assert res_path.stat().st_size > 100000

    reader = pypdf.PdfReader(res_path)
    # Verify 1 page per company for all master companies
    assert len(reader.pages) == 100
