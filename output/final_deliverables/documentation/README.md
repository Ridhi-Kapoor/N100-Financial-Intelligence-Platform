# ⚡ Nifty 100 Financial Intelligence & Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/Plotly-5.20+-orange.svg)](https://plotly.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-green.svg)](https://www.sqlite.org/)
[![ReportLab](https://img.shields.io/badge/ReportLab-4.0+-purple.svg)](https://www.reportlab.com/)
[![pytest](https://img.shields.io/badge/pytest-9.0+-yellow.svg)](https://docs.pytest.org/)

An enterprise-grade quantitative equity research platform and financial intelligence web application built with **FastAPI**, **Streamlit**, and **SQLite**. The system normalizes, analyzes, screens, and visualizes multi-year financial statements (Profit & Loss, Balance Sheets, Cash Flows), key performance indicators (KPIs), sector benchmarks, capital allocation patterns, and valuation metrics across all Nifty 100 constituents.

---

## 📌 Project Overview

The **Nifty 100 Financial Intelligence Platform** processes raw financial data for India's top 100 companies, converting raw financial statements into actionable corporate finance insights, quantitative stock screener results, automated PDF tearsheets, and high-performance REST API services.

### Core Value Proposition
- **Automated Data Quality Audit**: 14 automated DQ rules detecting missing keys, schema mismatches, and negative asset anomalies.
- **Quantitative Screener Engine**: 10 interactive sliders and 6 strategy preset algorithms (*Quality Compounders*, *Value Picks*, *Growth Accelerators*, *Dividend Champions*, *Debt-Free Blue Chips*, *Turnaround Watch*).
- **Multi-Factor Scoring & Clustering**: 0-100 sector-relative quality scores and 5-cluster K-Means segmentation.
- **REST API & PDF Engine**: 9 FastAPI JSON endpoints and publication-grade PDF report rendering via ReportLab.

---

## ✨ Features

- **Executive Market Overview (Screen 01)**: Market-wide KPIs (Average ROE, Median P/E, Median D/E, 5Y Revenue CAGR, Debt-Free count), 11-sector weight distribution, and top quality compounder rankings.
- **Company Profile & Deep-Dive (Screen 02)**: Search with autocomplete. 10-year P&L, Balance Sheet, Cash Flow, Valuation trends, dual-axis ROE vs ROCE charts, and automated NLP Pros & Cons.
- **Quantitative Stock Screener (Screen 03)**: Multi-factor screening with 10 sliders, strategy presets, Risk vs Return scatter plots, and one-click Excel/CSV exports.
- **Peer Group Comparison (Screen 04)**: 11 peer group selections, 8-axis Plotly Scatterpolar radar charts, and side-by-side KPI comparison with benchmark highlighting.
- **Financial Trends & CAGR Analysis (Screen 05)**: 10-year multi-metric overlay trends with dual Y-axes, YoY growth indicators, and compounding rate calculations.
- **Sector Analytics & Bubble Maps (Screen 06)**: Revenue vs ROE bubble map sized by market capitalization, sub-sector breakdowns, and sector median comparisons.
- **Capital Allocation Map (Screen 07)**: Plotly treemap categorizing cash flow patterns into 7 capital allocation styles (*Reinvestor*, *Shareholder Returns*, *Growth Funded by Debt*, *Distress Signal*).
- **Annual Reports & Export Portal (Screen 08)**: BSE annual report PDF links, status validation, executive tearsheets, raw data export, and audit logs.
- **FastAPI Server**: Modular REST API with Swagger UI (`/docs`) and ReDoc (`/redoc`) documentation.
- **Automated PDF Engine**: On-demand 1-page company tearsheets and 3-page portfolio summary PDF reports.

---

## 📁 Folder Structure

```
Nifty100_Data_Foundation/
├── data/
│   ├── raw/                      # Raw financial spreadsheets
│   ├── processed/                # Normalized CSV files
│   ├── db/                       # SQLite database (nifty100.db)
│   └── output/                   # Anomaly logs and audit exports
├── docs/                         # Documentation & Analyst Guide (analyst_guide.pdf)
├── pages/                        # Streamlit navigation pages
├── output/                       # Generated Excel summaries, PDF reports, and perf notes
│   └── final_deliverables/       # Archive directory for project deliverables
├── reports/                      # PDF tearsheets and portfolio reports
├── scripts/                      # ETL, analytics, audit, and generation scripts
│   └── etl/                      # ETL pipeline scripts (loader, normaliser, validator, sqlite)
├── sql/                          # Database schema DDL & indexing definitions
├── src/
│   ├── analytics/                # KPI ratio formulas, CAGR, clustering, cashflow engine
│   ├── api/                      # FastAPI application, routers, schemas, and services
│   ├── dashboard/                # Streamlit app views and database utility helpers
│   ├── nlp/                      # NLP parser and automated Pros & Cons rule generator
│   ├── reports/                  # ReportLab PDF report builders (tearsheets & portfolio)
│   └── screener/                 # Stock screener engine, presets, and Excel export
└── tests/                        # Comprehensive PyTest test suite (290+ tests)
    ├── analytics/                # Analytics & ratio tests
    ├── api/                      # FastAPI endpoint & load tests
    ├── dq/                       # Data Quality rule tests (DQ-01 to DQ-14)
    ├── etl/                      # ETL normalization & loader tests
    ├── kpi/                      # KPI calculation tests
    ├── nlp/                      # NLP & Pros/Cons generator tests
    ├── reports/                  # PDF report generation tests
    └── screener/                 # Screener engine & preset tests
```

---

## ⚙️ Prerequisites

- **Python**: Version **3.10** or higher (Python 3.12 recommended).
- **SQLite**: Version **3.35+** (included in standard Python distribution).
- **Operating System**: Windows, macOS, or Linux.

---

## 🛠️ Installation

```bash
# 1. Clone the repository
git clone https://github.com/Ridhi-Kapoor/N100-Financial-Intelligence-Platform.git
cd N100-Financial-Intelligence-Platform

# 2. Create and activate a virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# 3. Install required dependencies
pip install -r requirements.txt
```

---

## 🔄 ETL Pipeline Execution

To re-run the full ETL pipeline and reload data into SQLite:

```bash
# 1. Process raw files and normalize datasets
python scripts/etl/loader.py
python scripts/etl/normaliser.py
python scripts/etl/validator.py

# 2. Load cleaned data into SQLite database with indexes
python scripts/etl/load_to_sqlite.py

# 3. Execute ratio engine calculations
python src/analytics/run_ratio_engine.py

# 4. Run data quality audit
python scripts/data_quality_audit.py
```

---

## 🖥️ Running the Streamlit Dashboard

To launch the multi-page Streamlit web dashboard:

```bash
streamlit run src/dashboard/app.py
```

The application will open automatically in your browser at `http://127.0.0.1:8501`.

---

## ⚡ Running the FastAPI Server

To launch the FastAPI REST API server with Uvicorn:

```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

The server will start at `http://127.0.0.1:8000`.

---

## 🧪 Running the Test Suite

Execute all 290+ unit, integration, performance, and API tests with HTML coverage report generation:

```bash
pytest tests/ --html=reports/pytest_report.html -v
```

View the generated HTML test report at [reports/pytest_report.html](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/reports/pytest_report.html).

---

## 📖 API Documentation & Endpoints

Once the FastAPI server is running, explore interactive docs at:
- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | System status, DB health check, and 10 table row counts |
| `GET` | `/companies` | List all 92 Nifty 100 constituent companies |
| `GET` | `/companies/{ticker}` | Profile metadata, financial KPIs, and about details |
| `GET` | `/screener` | Multi-factor quantitative stock screener query |
| `GET` | `/sectors` | Broad sectors listing with median ROE, P/E, and D/E |
| `GET` | `/sectors/{sector}/companies` | Sector companies listing with latest KPIs |
| `GET` | `/peers/{group_name}` | Peer group percentile ranks across 10 financial metrics |
| `GET` | `/market-cap/{ticker}` | Historical market cap and valuation ratio time-series |
| `GET` | `/portfolio/stats` | Portfolio-wide KPI percentiles (10th, 25th, 50th, 75th, 90th) |

---

## 🧰 Technologies Used

- **Core**: Python 3.12, FastAPI, Uvicorn, Streamlit, Pydantic
- **Data & Analytics**: Pandas, NumPy, SciPy, Scikit-Learn, SQLite 3
- **Visualization**: Plotly Express, Plotly Graph Objects, Matplotlib
- **Document Generation**: ReportLab, PyPDF
- **Testing & Tooling**: pytest, pytest-html, Black, Ruff, requests

---

## 🔮 Future Improvements

1. **Real-Time Price Feeds**: Integrate live WebSockets for real-time stock price streaming from NSE/BSE.
2. **Advanced Machine Learning**: Implement Transformer-based sentiment analysis on earnings transcript PDFs.
3. **Multi-Asset Portfolio Optimizer**: Add Mean-Variance Markowitz portfolio optimization module.
4. **Cloud Deployment**: Containerize with Docker and deploy to AWS / GCP Kubernetes engine.
