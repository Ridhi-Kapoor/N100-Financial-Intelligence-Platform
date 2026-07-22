# ⚡ Nifty 100 Financial Intelligence & Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/Plotly-5.20+-orange.svg)](https://plotly.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-green.svg)](https://www.sqlite.org/)

A multi-page financial intelligence and quantitative analytics dashboard built with **Streamlit** and **Plotly**. The platform processes, normalizes, and visualizes multi-year financial statements (Profit & Loss, Balance Sheets, Cash Flows), financial ratios, sector benchmarks, capital allocation patterns, and market valuation metrics for Nifty 100 constituents.

---

## 🚀 Key Features

* **Executive Overview (Screen 1)**: Key market-wide KPIs (Average ROE, Median P/E, Median D/E, 5Y Revenue CAGR, Debt-Free company count), 11-sector breakdown donut chart, and top 5 quality compounder rankings.
* **Company Profile & Deep-Dive (Screen 2)**: Individual ticker lookup with autocomplete search, financial overview cards, 10-year Revenue & Net Profit bar charts, dual-axis ROE vs. ROCE trend lines, automated Pros & Cons fundamental analysis, and full financial statements. Handles partial historical data (< 10 years) gracefully.
* **Quantitative Stock Screener (Screen 3)**: Interactive multi-factor screening engine with 10 sidebar filter sliders, 6 strategy presets (*Quality*, *Value*, *Growth*, *Dividend*, *Debt-Free*, *Turnaround*), Risk vs. Return scatter plot, detailed tabular results, and one-click CSV export.
* **Peer Comparison & Benchmarking (Screen 4)**: Selection across 11 industry peer groups, target company selection, 8-axis Plotly Scatterpolar radar chart comparing target company vs. peer average vs. benchmark, and side-by-side KPI comparison table with benchmark highlighting.
* **Multi-Year Financial Trends (Screen 5)**: Multi-metric overlay trends (up to 3 metrics simultaneously) over a 10-year window with dual Y-axes support, Year-over-Year (YoY) percentage growth labels, and exportable history tables.
* **Sector & Sub-Sector Analytics (Screen 6)**: Revenue vs. ROE bubble map sized by market capitalization and colored by sub-sector, alongside interactive bar charts comparing median sector KPIs.
* **Capital Allocation Map (Screen 7)**: Plotly treemap categorizing companies into the 8 cash flow capital allocation patterns (e.g., *Shareholder Returns*, *Reinvestor*, *Growth Funded by Debt*, *Distress Signal*) based on CFO, CFI, and CFF dynamics.
* **Annual Reports & Export Portal (Screen 8)**: Company search for BSE annual report PDF links with status validation badges, executive tear-sheet factsheet generator, raw CSV export center, and database health audit log.

---

## 🛠️ Technology Stack

* **Frontend & Dashboard Engine**: Streamlit (`st.navigation`, `st.Page`, custom CSS design tokens)
* **Data Visualization**: Plotly Express & Plotly Graph Objects (`Scatterpolar`, `Treemap`, `Bar`, `Scatter`, `Pie`, `Subplots`)
* **Data Processing & Analytics**: Pandas, NumPy, PyYAML
* **Database**: SQLite 3 (`nifty100.db`)
* **Testing & Verification**: PyTest

---

## ⚙️ Installation & Setup

### 1. Prerequisites
Ensure Python **3.10+** is installed on your system.

### 2. Clone Repository & Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/Ridhi-Kapoor/N100-Financial-Intelligence-Platform.git
cd N100-Financial-Intelligence-Platform

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🗄️ Database Setup

The platform uses a relational SQLite database located at `data/db/nifty100.db`.

If you need to rebuild the database from raw Excel datasets:
```bash
# Run full ETL pipeline
python scripts/etl/loader.py
python scripts/etl/normaliser.py
python scripts/etl/validator.py
python scripts/etl/load_to_sqlite.py
```

To verify database health:
```bash
python scripts/data_quality_audit.py
```

---

## 🖥️ Dashboard Launch Command

To start the Streamlit multi-page web application locally, execute:

```bash
streamlit run src/dashboard/app.py
```

The application will launch automatically in your web browser at `http://localhost:8501`.

---

## 📁 Project Structure

```
Nifty100_Data_Foundation/
├── data/
│   ├── raw/                  # Source Excel spreadsheets
│   ├── processed/            # Cleaned and normalized CSVs
│   ├── db/                   # SQLite database (nifty100.db)
│   └── output/               # Audit reports and validation logs
├── src/
│   ├── analytics/            # Financial CAGR, leverage, peer & radar engines
│   ├── dashboard/            # Streamlit multi-page application
│   │   ├── app.py            # Main entrypoint & page navigation
│   │   ├── utils/            # DB query helpers & caching layer (db.py)
│   │   └── views/            # 8 Streamlit view pages
│   │       ├── 01_home.py    # Executive Overview
│   │       ├── 02_profile.py # Company Profile
│   │       ├── 03_screener.py# Stock Screener
│   │       ├── 04_peers.py   # Peer Comparison
│   │       ├── 05_trends.py  # Financial Trends
│   │       ├── 06_sectors.py # Sector Analysis
│   │       ├── 07_capital.py # Capital Structure
│   │       └── 08_reports.py # Reports & Export
│   └── screener/             # Multi-factor screening engine & presets
├── tests/                    # Pytest test suite (173 unit & integration tests)
├── screener_config.yaml      # Screener filter configuration parameters
├── requirements.txt          # Python package dependencies
├── README.md                 # Project documentation
├── DASHBOARD_DOCUMENTATION.md# Detailed screen-by-screen documentation
└── SPRINT4_RETROSPECTIVE.md  # Sprint 4 retrospective report
```

---

## 📖 Dashboard Usage Instructions

1. **Executive Overview**: Select the Financial Year (2019-2024) from the left sidebar to inspect high-level KPIs, sector company distribution, and quality leader rankings.
2. **Company Profile**: Use the top search bar to find any Nifty 100 constituent by name or ticker (e.g. `TCS`, `HDFCBANK`, `JIOFIN`). Toggle tabs to view full Profit & Loss, Balance Sheet, and Cash Flow statements.
3. **Stock Screener**: Select strategy presets (*Quality*, *Value*, *Growth*, etc.) or adjust slider thresholds. Results update live. Click **Download CSV** to export screened results.
4. **Peer Comparison**: Choose an industry peer group (e.g., *Private Banks*, *IT Services*) and a target company to view 8-axis radar overlays against peer averages and benchmarks.
5. **Financial Trends**: Select up to 3 metrics to plot historical trajectories. View YoY percentage change badges directly on data points.
6. **Sector Analysis**: Select broad sectors to view Revenue vs. ROE bubble distributions and median KPI bar charts.
7. **Capital Allocation**: Inspect the treemap to analyze cash flow allocation strategies (*Shareholder Returns*, *Reinvestor*, etc.).
8. **Reports & Export**: Download annual report PDFs, generate markdown factsheets, or export financial tables to CSV.

---

## 🧪 Testing & Verification

Run the full automated pytest suite:
```bash
python -m pytest
```
All **173 unit and integration tests** verify financial formulas, ETL transformations, screening engine logic, and radar scoring models.
