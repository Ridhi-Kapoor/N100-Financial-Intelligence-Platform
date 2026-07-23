"""
Script to generate a 10+ page Analyst Guide PDF document at docs/analyst_guide.pdf using ReportLab.
"""

import sys
from pathlib import Path
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, KeepTogether
)

OUTPUT_PDF = PROJECT_ROOT / "docs" / "analyst_guide.pdf"
OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)

def build_analyst_guide():
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#1A365D")
    SECONDARY = colors.HexColor("#2B6CB0")
    ACCENT = colors.HexColor("#319795")
    TEXT_DARK = colors.HexColor("#2D3748")
    BG_LIGHT = colors.HexColor("#F7FAFC")
    BORDER_COLOR = colors.HexColor("#E2E8F0")

    # Custom Typography Styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=34,
        textColor=PRIMARY,
        alignment=0,
        spaceAfter=15,
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=14,
        leading=20,
        textColor=SECONDARY,
        spaceAfter=30,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=PRIMARY,
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=SECONDARY,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=TEXT_DARK,
        spaceAfter=8,
    )

    code_style = ParagraphStyle(
        "CodeBlock",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#2C5282"),
        backColor=colors.HexColor("#EDF2F7"),
        borderColor=BORDER_COLOR,
        borderWidth=0.5,
        borderPadding=6,
        spaceAfter=10,
    )

    story = []

    # =========================================================================
    # PAGE 1: COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 40))
    story.append(Paragraph("NIFTY 100 FINANCIAL INTELLIGENCE PLATFORM", title_style))
    story.append(Paragraph("Comprehensive Platform Analyst & Developer Guide", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=3, color=ACCENT, spaceAfter=40))

    cover_meta = [
        [Paragraph("<b>Document Version:</b>", body_style), Paragraph("1.0.0 (Production Release)", body_style)],
        [Paragraph("<b>Author / Team:</b>", body_style), Paragraph("Advanced Financial Intelligence Engineering", body_style)],
        [Paragraph("<b>Date of Issue:</b>", body_style), Paragraph("July 2026", body_style)],
        [Paragraph("<b>Target Audience:</b>", body_style), Paragraph("Equity Research Analysts, Portfolio Managers, Developers", body_style)],
        [Paragraph("<b>Backend API Server:</b>", body_style), Paragraph("FastAPI (v1.0.0) — Port 8000", body_style)],
        [Paragraph("<b>Web Application:</b>", body_style), Paragraph("Streamlit Multi-Page App — Port 8501", body_style)],
        [Paragraph("<b>Database Engine:</b>", body_style), Paragraph("SQLite 3 (Indexed Relational Store)", body_style)],
    ]
    t_cover = Table(cover_meta, colWidths=[160, 344])
    t_cover.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_cover)
    story.append(Spacer(1, 40))
    story.append(Paragraph("<b>Executive Notice:</b> This technical guide provides step-by-step documentation for deploying, navigating, querying, and extending the Nifty 100 Financial Intelligence Platform. It includes REST API references, cURL commands, dashboard navigation workflows, PDF report generation instructions, data quality rule catalogs, and system troubleshooting protocols.", body_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: TABLE OF CONTENTS & PROJECT OVERVIEW
    # =========================================================================
    story.append(Paragraph("1. Project Overview & Architecture", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=12))

    story.append(Paragraph("The <b>Nifty 100 Financial Intelligence Platform</b> is an end-to-end quantitative equity research system designed for analyzing India's top 100 market-cap companies. The platform integrates an automated ETL data pipeline, relational SQLite storage, a multi-factor quantitative stock screener, financial ratio engines, clustering analytics, automated PDF report generation, and a high-performance FastAPI REST server.", body_style))

    story.append(Paragraph("<b>Key Architectural Components:</b>", h2_style))
    overview_table = [
        [Paragraph("<b>Layer</b>", body_style), Paragraph("<b>Technologies Used</b>", body_style), Paragraph("<b>Functionality</b>", body_style)],
        [Paragraph("Data Pipeline (ETL)", body_style), Paragraph("Python, Pandas, Regex", body_style), Paragraph("Normalizes dates/tickers, cleans raw Excel files, injects FK stubs.", body_style)],
        [Paragraph("Relational Database", body_style), Paragraph("SQLite 3, Composite B-Tree Indexes", body_style), Paragraph("Stores 10 financial tables with $O(\\log N)$ query optimization.", body_style)],
        [Paragraph("Analytics Engine", body_style), Paragraph("NumPy, SciPy, Scikit-Learn", body_style), Paragraph("Computes CAGR, CFO Quality Score, K-Means clustering & peer ranks.", body_style)],
        [Paragraph("REST API Server", body_style), Paragraph("FastAPI, Uvicorn, Pydantic", body_style), Paragraph("Exposes 9 modular JSON endpoints with Swagger UI & OpenAPI docs.", body_style)],
        [Paragraph("Web Application", body_style), Paragraph("Streamlit, Plotly", body_style), Paragraph("8 interactive dashboard views with sidebar screening sliders.", body_style)],
        [Paragraph("Reporting Engine", body_style), Paragraph("ReportLab, PyPDF", body_style), Paragraph("Generates 1-page company tearsheets and 3-page portfolio PDFs.", body_style)],
    ]
    t_ov = Table(overview_table, colWidths=[110, 140, 254])
    t_ov.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_ov)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: STREAMLIT DASHBOARD NAVIGATION
    # =========================================================================
    story.append(Paragraph("2. Streamlit Dashboard User Guide", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=12))

    story.append(Paragraph("The Streamlit dashboard provides an intuitive, web-based portal for interacting with Nifty 100 financial data. Launch the dashboard by executing <code>streamlit run main.py</code>.", body_style))

    story.append(Paragraph("<b>Navigating the 8 Dashboard Views:</b>", h2_style))

    views_data = [
        [Paragraph("<b>Page / View</b>", body_style), Paragraph("<b>Key Features & Interactive Capabilities</b>", body_style)],
        [Paragraph("<b>01 Home / Overview</b>", body_style), Paragraph("Market-wide summary KPIs, total market-cap distribution, top gainers/losers, and high-level sector breakdown charts.", body_style)],
        [Paragraph("<b>02 Company Profile</b>", body_style), Paragraph("Deep-dive company search with autocomplete. View 10-year P&L, Balance Sheet, Cash Flow, Valuation history, and peer radar charts.", body_style)],
        [Paragraph("<b>03 Stock Screener</b>", body_style), Paragraph("Interactive 10-slider quantitative screener with preset strategy buttons (Quality Compounders, Value, Growth, Debt-Free).", body_style)],
        [Paragraph("<b>04 Peer Comparison</b>", body_style), Paragraph("Side-by-side metric comparison, peer percentile rankings across 10 financial metrics, and radar chart overlays.", body_style)],
        [Paragraph("<b>05 Financial Trends</b>", body_style), Paragraph("Multi-year trend analysis for Revenue, Net Profit, OPM %, ROE %, and Debt-to-Equity across selected companies.", body_style)],
        [Paragraph("<b>06 Sector Analytics</b>", body_style), Paragraph("Broad sector median KPIs, index weight analysis, sector constituent tables, and cross-sector valuation comparisons.", body_style)],
        [Paragraph("<b>07 Capital Allocation</b>", body_style), Paragraph("Classifies companies into 7 capital allocation patterns (Reinvestor, Shareholder Returns, Distress, Liquidating) based on cash flow signs.", body_style)],
        [Paragraph("<b>08 PDF Reports</b>", body_style), Paragraph("On-demand PDF generation portal. Export 1-page company tearsheets or comprehensive 3-page portfolio summary PDF reports.", body_style)],
    ]
    t_views = Table(views_data, colWidths=[140, 364])
    t_views.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SECONDARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_views)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: QUANTITATIVE STOCK SCREENER DEEP-DIVE
    # =========================================================================
    story.append(Paragraph("3. Quantitative Stock Screener Guide", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=12))

    story.append(Paragraph("The Stock Screener allows analysts to filter Nifty 100 companies using 10 quantitative financial metrics simultaneously. Filtering operates dynamically in real time.", body_style))

    story.append(Paragraph("<b>Available Sidebar Filter Sliders:</b>", h2_style))
    screener_params = [
        [Paragraph("<b>Filter Name</b>", body_style), Paragraph("<b>Metric Field</b>", body_style), Paragraph("<b>Default Range</b>", body_style), Paragraph("<b>Financial Description</b>", body_style)],
        [Paragraph("Return on Equity (ROE)", body_style), Paragraph("<code>return_on_equity_pct</code>", body_style), Paragraph("Min: 0% to 100%", body_style), Paragraph("Measures profitability generated per rupee of equity.", body_style)],
        [Paragraph("Debt to Equity (D/E)", body_style), Paragraph("<code>debt_to_equity</code>", body_style), Paragraph("Max: 0.0 to 10.0", body_style), Paragraph("Measures financial leverage (excl. Financials sector).", body_style)],
        [Paragraph("Free Cash Flow (Cr)", body_style), Paragraph("<code>free_cash_flow_cr</code>", body_style), Paragraph("Min: -5,000 to 50,000", body_style), Paragraph("Operating Cash Flow minus Capital Expenditures.", body_style)],
        [Paragraph("Revenue 5Yr CAGR", body_style), Paragraph("<code>revenue_cagr_5yr</code>", body_style), Paragraph("Min: -50% to 100%", body_style), Paragraph("Compounded annual growth rate of net sales over 5 years.", body_style)],
        [Paragraph("PAT 5Yr CAGR", body_style), Paragraph("<code>pat_cagr_5yr</code>", body_style), Paragraph("Min: -50% to 100%", body_style), Paragraph("Compounded annual growth rate of net profit over 5 years.", body_style)],
        [Paragraph("Price to Earnings (P/E)", body_style), Paragraph("<code>pe_ratio</code>", body_style), Paragraph("Max: 0 to 200", body_style), Paragraph("Valuation ratio comparing stock price to EPS.", body_style)],
    ]
    t_scr = Table(screener_params, colWidths=[120, 110, 94, 180])
    t_scr.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_scr)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Strategy Preset Buttons:</b> Analysts can click one of 6 preset buttons in the sidebar to auto-populate slider configurations: <i>Quality Compounders</i>, <i>Growth Accelerators</i>, <i>Value Picks</i>, <i>Dividend Champions</i>, <i>Debt-Free Blue Chips</i>, and <i>Turnaround Candidates</i>.", body_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: FINANCIAL RATIOS & KPI CALCULATIONS
    # =========================================================================
    story.append(Paragraph("4. Financial Ratios & KPI Methodologies", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=12))

    story.append(Paragraph("All financial indicators follow strict standard corporate finance definitions and edge-case handling rules.", body_style))

    ratios_formulas = [
        [Paragraph("<b>Financial Metric</b>", body_style), Paragraph("<b>Mathematical Formula</b>", body_style), Paragraph("<b>Special Edge Case Handling Rules</b>", body_style)],
        [
            Paragraph("<b>Return on Equity (ROE)</b>", body_style),
            Paragraph("$$\\frac{\\text{Net Profit}}{\\text{Equity Capital} + \\text{Reserves}} \\times 100$$", body_style),
            Paragraph("Returns <code>None</code> if denominator $\\le 0$ (negative/zero equity).", body_style)
        ],
        [
            Paragraph("<b>Debt to Equity (D/E)</b>", body_style),
            Paragraph("$$\\frac{\\text{Borrowings}}{\\text{Equity Capital} + \\text{Reserves}}$$", body_style),
            Paragraph("Returns <code>0.0</code> for debt-free companies. Flags <code>High Leverage</code> if D/E > 5 (excl. Financials).", body_style)
        ],
        [
            Paragraph("<b>Interest Coverage Ratio</b>", body_style),
            Paragraph("$$\\frac{\\text{Operating Profit} + \\text{Other Income}}{\\text{Interest Expense}}$$", body_style),
            Paragraph("Returns <code>None</code> & label <code>'Debt Free'</code> if Interest = 0.", body_style)
        ],
        [
            Paragraph("<b>Compound Growth (CAGR)</b>", body_style),
            Paragraph("$$\\left(\\left(\\frac{\\text{End Value}}{\\text{Beg Value}}\\right)^{\\frac{1}{n}} - 1\\right) \\times 100$$", body_style),
            Paragraph("Returns <code>None</code> with flag: <code>'TURNAROUND'</code> (neg to pos), <code>'DECLINE_TO_LOSS'</code> (pos to neg), or <code>'ZERO_BASE'</code>.", body_style)
        ],
        [
            Paragraph("<b>CFO Quality Score</b>", body_style),
            Paragraph("$$\\text{Average}\\left(\\frac{\\text{CFO}}{\\text{PAT}}\\right) \\text{ over 5 Years}$$", body_style),
            Paragraph("Classifies score: <code>High Quality</code> (> 1.0), <code>Moderate</code> (0.5 to 1.0), <code>Accrual Risk</code> (< 0.5).", body_style)
        ],
    ]
    t_form = Table(ratios_formulas, colWidths=[120, 164, 220])
    t_form.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), SECONDARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_form)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: AUTOMATED PDF TEARSHEETS & REPORTS
    # =========================================================================
    story.append(Paragraph("5. PDF Report & Tearsheet Generation", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=12))

    story.append(Paragraph("The platform includes a ReportLab PDF rendering engine capable of building publication-grade financial tearsheets and portfolio executive summaries.", body_style))

    story.append(Paragraph("<b>1. Single-Company Tearsheets (1-Page PDF):</b>", h2_style))
    story.append(Paragraph("Contains company profile header, key valuation metrics, 5-year financial trend table, peer percentile radar chart, and automated NLP Pros & Cons bullet points.", body_style))
    story.append(Paragraph("<b>Command / API Execution:</b>", body_style))
    story.append(Paragraph("<code>python scripts/generate_tearsheets.py --ticker TCS</code>", code_style))
    story.append(Paragraph("Or via REST API: <code>GET /api/v1/documents/tearsheet/TCS</code>", code_style))

    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>2. Portfolio Summary Report (3-Page PDF):</b>", h2_style))
    story.append(Paragraph("Contains portfolio-wide KPI summary matrix, sector weight pie charts, 5-cluster profiling summary, distress alerts table, and deleveraging trends.", body_style))
    story.append(Paragraph("<b>Command / API Execution:</b>", body_style))
    story.append(Paragraph("<code>python scripts/generate_portfolio_summary.py</code>", code_style))
    story.append(Paragraph("Or via REST API: <code>GET /api/v1/documents/portfolio-summary</code>", code_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: FASTAPI DEVELOPER GUIDE
    # =========================================================================
    story.append(Paragraph("6. REST API Developer Guide", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=12))

    story.append(Paragraph("The REST API is built on FastAPI and Uvicorn. All endpoints return standardized JSON payloads with strict Pydantic schema validation.", body_style))

    story.append(Paragraph("<b>Base Server Configuration:</b>", h2_style))
    story.append(Paragraph("• Base URL: <code>http://127.0.0.1:8000</code><br/>• Common Route Prefix: <code>/api/v1</code><br/>• Interactive Swagger Docs: <code>http://127.0.0.1:8000/docs</code><br/>• ReDoc Specification: <code>http://127.0.0.1:8000/redoc</code>", body_style))

    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Core API Routers & Endpoint Summary:</b>", h2_style))

    api_summary = [
        [Paragraph("<b>Router / Endpoint</b>", body_style), Paragraph("<b>HTTP Method</b>", body_style), Paragraph("<b>Description</b>", body_style)],
        [Paragraph("<code>/api/v1/health</code>", body_style), Paragraph("GET", body_style), Paragraph("System status, uptime, DB connectivity, and 10 table row counts.", body_style)],
        [Paragraph("<code>/companies</code>", body_style), Paragraph("GET", body_style), Paragraph("List all 92 Nifty 100 constituent companies.", body_style)],
        [Paragraph("<code>/companies/{ticker}</code>", body_style), Paragraph("GET", body_style), Paragraph("Detailed profile, financial KPIs, and about text by ticker.", body_style)],
        [Paragraph("<code>/screener</code>", body_style), Paragraph("GET", body_style), Paragraph("Execute quantitative stock screener query across 7 filters.", body_style)],
        [Paragraph("<code>/sectors</code>", body_style), Paragraph("GET", body_style), Paragraph("List broad sectors with median ROE, PE, and Debt-to-Equity.", body_style)],
        [Paragraph("<code>/sectors/{sector}/companies</code>", body_style), Paragraph("GET", body_style), Paragraph("Get all companies and latest KPIs in a specific sector.", body_style)],
        [Paragraph("<code>/peers/{group_name}</code>", body_style), Paragraph("GET", body_style), Paragraph("Get 10 percentile ranks for companies in a peer group.", body_style)],
        [Paragraph("<code>/market-cap/{ticker}</code>", body_style), Paragraph("GET", body_style), Paragraph("Historical market cap, P/E, P/B, and EV/EBITDA time-series.", body_style)],
        [Paragraph("<code>/portfolio/stats</code>", body_style), Paragraph("GET", body_style), Paragraph("Portfolio-wide 10th, 25th, 50th, 75th, 90th percentile KPI stats.", body_style)],
    ]
    t_api = Table(api_summary, colWidths=[150, 70, 284])
    t_api.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_api)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 8: API CURL CODE EXAMPLES
    # =========================================================================
    story.append(Paragraph("7. cURL Code Examples & Request Samples", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=12))

    story.append(Paragraph("<b>1. Health Check Request:</b>", h2_style))
    story.append(Paragraph("curl -X GET \"http://127.0.0.1:8000/api/v1/health\" -H \"accept: application/json\"", code_style))

    story.append(Paragraph("<b>2. Stock Screener Query (Min ROE 15%, Max D/E 1.5):</b>", h2_style))
    story.append(Paragraph("curl -X GET \"http://127.0.0.1:8000/api/v1/screener?min_roe=15&max_de=1.5\" -H \"accept: application/json\"", code_style))

    story.append(Paragraph("<b>3. Fetch Company Profile (TCS):</b>", h2_style))
    story.append(Paragraph("curl -X GET \"http://127.0.0.1:8000/companies/TCS\" -H \"accept: application/json\"", code_style))

    story.append(Paragraph("<b>4. Fetch Sector Companies (Information Technology / IT):</b>", h2_style))
    story.append(Paragraph("curl -X GET \"http://127.0.0.1:8000/sectors/IT/companies\" -H \"accept: application/json\"", code_style))

    story.append(Paragraph("<b>5. Fetch Peer Group Percentile Ranks:</b>", h2_style))
    story.append(Paragraph("curl -X GET \"http://127.0.0.1:8000/api/v1/peers/IT%20Services\" -H \"accept: application/json\"", code_style))

    story.append(Paragraph("<b>6. Download Company PDF Tearsheet:</b>", h2_style))
    story.append(Paragraph("curl -X GET \"http://127.0.0.1:8000/api/v1/documents/tearsheet/INFY\" --output INFY_tearsheet.pdf", code_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 9: DATA QUALITY & VALIDATION RULES
    # =========================================================================
    story.append(Paragraph("8. Data Quality Rules & Audit Framework", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=12))

    story.append(Paragraph("The platform enforces 14 automated Data Quality (DQ) validation rules split across CRITICAL and WARNING severity levels.", body_style))

    dq_rules = [
        [Paragraph("<b>Rule ID</b>", body_style), Paragraph("<b>Severity</b>", body_style), Paragraph("<b>Rule Name & Condition Description</b>", body_style)],
        [Paragraph("<b>DQ-01</b>", body_style), Paragraph("<font color='red'>CRITICAL</font>", body_style), Paragraph("Primary Key cannot be NULL or NaN.", body_style)],
        [Paragraph("<b>DQ-02</b>", body_style), Paragraph("<font color='red'>CRITICAL</font>", body_style), Paragraph("Duplicate Primary Keys across table records.", body_style)],
        [Paragraph("<b>DQ-03</b>", body_style), Paragraph("<font color='red'>CRITICAL</font>", body_style), Paragraph("Foreign Key violation (referencing non-existent company ID).", body_style)],
        [Paragraph("<b>DQ-04</b>", body_style), Paragraph("<font color='red'>CRITICAL</font>", body_style), Paragraph("Missing or empty financial year string.", body_style)],
        [Paragraph("<b>DQ-05</b>", body_style), Paragraph("<font color='red'>CRITICAL</font>", body_style), Paragraph("Missing mandatory schema fields.", body_style)],
        [Paragraph("<b>DQ-06</b>", body_style), Paragraph("<font color='red'>CRITICAL</font>", body_style), Paragraph("Sales / Revenue value is negative.", body_style)],
        [Paragraph("<b>DQ-07</b>", body_style), Paragraph("<font color='red'>CRITICAL</font>", body_style), Paragraph("Invalid ticker string pattern (must be uppercase alphanumeric).", body_style)],
        [Paragraph("<b>DQ-08</b>", body_style), Paragraph("<font color='red'>CRITICAL</font>", body_style), Paragraph("Duplicate (company_id, year) composite record.", body_style)],
        [Paragraph("<b>DQ-09</b>", body_style), Paragraph("<font color='orange'>WARNING</font>", body_style), Paragraph("Operating Profit Margin (OPM) outside range [-100%, +100%].", body_style)],
        [Paragraph("<b>DQ-10</b>", body_style), Paragraph("<font color='orange'>WARNING</font>", body_style), Paragraph("Balance Sheet mismatch (Assets $\\ne$ Liabilities + Equity).", body_style)],
        [Paragraph("<b>DQ-11</b>", body_style), Paragraph("<font color='orange'>WARNING</font>", body_style), Paragraph("Sales is equal to 0.0.", body_style)],
        [Paragraph("<b>DQ-12</b>", body_style), Paragraph("<font color='orange'>WARNING</font>", body_style), Paragraph("Net Profit is negative (loss-making year).", body_style)],
        [Paragraph("<b>DQ-13</b>", body_style), Paragraph("<font color='orange'>WARNING</font>", body_style), Paragraph("Total Assets value is negative.", body_style)],
        [Paragraph("<b>DQ-14</b>", body_style), Paragraph("<font color='orange'>WARNING</font>", body_style), Paragraph("Financial year is in the future (> current year).", body_style)],
    ]
    t_dq = Table(dq_rules, colWidths=[65, 75, 364])
    t_dq.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_dq)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 10: TROUBLESHOOTING & SYSTEM ADMINISTRATION
    # =========================================================================
    story.append(Paragraph("9. Troubleshooting & Operations Guide", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=12))

    story.append(Paragraph("<b>1. Port Conflicts (Port 8000 or 8501 in Use):</b>", h2_style))
    story.append(Paragraph("If port 8000 or 8501 is already bound by another process on Windows:<br/><code>netstat -ano | findstr :8000</code><br/><code>taskkill /PID &lt;PID&gt; /F</code>", code_style))

    story.append(Paragraph("<b>2. Database Lock or Schema Errors:</b>", h2_style))
    story.append(Paragraph("If SQLite database throws <code>OperationalError: database is locked</code>, re-run the automated database loader script:<br/><code>python scripts/etl/load_to_sqlite.py</code>", code_style))

    story.append(Paragraph("<b>3. Regenerating All Project Output Files:</b>", h2_style))
    story.append(Paragraph("To re-run the full analytics engine, screener presets, and report generation pipeline:<br/><code>python scripts/run_presets_demo.py</code><br/><code>python scripts/data_quality_audit.py</code>", code_style))

    story.append(Paragraph("<b>4. Running Automated Pytest Suite:</b>", h2_style))
    story.append(Paragraph("To run all 290+ unit, integration, and API tests with HTML coverage report:<br/><code>pytest tests/ --html=reports/pytest_report.html -v</code>", code_style))

    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=15))
    story.append(Paragraph("<b>End of Analyst Guide — Nifty 100 Financial Intelligence Platform</b>", ParagraphStyle("Footer", parent=body_style, fontName="Helvetica-Bold", alignment=1, textColor=PRIMARY)))

    doc.build(story)
    
    # Verify page count
    reader = PdfReader(OUTPUT_PDF)
    num_pages = len(reader.pages)
    print(f"Generated docs/analyst_guide.pdf successfully. Total Pages: {num_pages}")
    return num_pages

if __name__ == "__main__":
    build_analyst_guide()
