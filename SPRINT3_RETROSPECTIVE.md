# Sprint 3 Retrospective - Nifty 100 Financial Intelligence Platform

## 1. Sprint Objectives
The objective of Sprint 3 was to deliver advanced peer analytics, stock screening engines with 6 predefined presets, high-resolution radar (polar) performance chart visualizations for all Nifty 100 constituents, and multi-worksheet formatted Excel deliverables.

Key objectives included:
* Implementing peer group percentile rank calculations with inverse ranking for Debt-to-Equity and populating the `peer_percentiles` SQLite table.
* Building a 0–100 composite quality scoring system and stock screener presets (Quality Compounder, Value Pick, Growth Accelerator, Dividend Champion, Debt-Free Blue Chip, Turnaround Watch).
* Generating 8-axis radar charts for all 100 companies overlaid with Peer Group or Nifty 100 Market Averages.
* Exporting multi-sheet formatted Excel reports (`output/peer_comparison.xlsx` and `output/screener_output.xlsx`) with 3-tier conditional formatting, benchmark highlights, and peer median summary rows.
* Verifying 100% test passing across all 14 Data Quality (DQ) rule unit tests and validating peer ranking and preset logic.

---

## 2. Work Completed & Deliverables

### 2.1 Peer Group Percentile Analytics Engine
* **Module**: [src/analytics/peer.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/src/analytics/peer.py)
* **Table**: `peer_percentiles` in [nifty100.db](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/data/db/nifty100.db)
* Computed percentile ranks within each of the 11 peer groups across all years for 10 financial metrics: ROE, ROCE, Net Profit Margin, Debt-to-Equity (inverse ranking), Free Cash Flow, PAT CAGR 5Y, Revenue CAGR 5Y, EPS CAGR 5Y, Interest Coverage Ratio, and Asset Turnover.
* Handled unassigned companies gracefully by returning `"No peer group assigned"` without raising errors.
* Populated **6,460 records** into `peer_percentiles` table.

### 2.2 Stock Screener Engine & Presets
* **Modules**: [src/screener/engine.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/src/screener/engine.py), [src/screener/presets.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/src/screener/presets.py), [src/screener/excel_export.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/src/screener/excel_export.py)
* Built a 0–100 sector-relative composite quality score.
* Implemented 6 screener presets and exported results to [output/screener_output.xlsx](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/output/screener_output.xlsx).

### 2.3 Financial Radar Chart Visualizations
* **Module**: [src/analytics/radar.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/src/analytics/radar.py)
* **Directory**: [reports/radar_charts/](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/reports/radar_charts)
* Generated 100 high-resolution radar (polar) PNG charts (`<company_id>_radar.png`) featuring 8 radial metrics.
* Plotted filled polygons for company performance and overlaid dashed reference outlines (Peer Group Average for peer-assigned companies, Nifty 100 Market Average for standalone companies).

### 2.4 Multi-Sheet Peer Comparison Excel Report
* **Module**: [src/analytics/peer_report.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/src/analytics/peer_report.py)
* **Output File**: [output/peer_comparison.xlsx](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/output/peer_comparison.xlsx)
* Generated 11 worksheets (one for each peer group) with 42 columns (20 KPIs + 20 Percentile Ranks).
* Applied cell-level conditional formatting (Green $\ge 75^{\text{th}}$, Yellow $25^{\text{th}}–75^{\text{th}}$, Red $\le 25^{\text{th}}$ percentile), Gold/Amber benchmark row highlights (`#FFE699`), and a `PEER MEDIAN` summary row at the bottom (`#D9E1F2`).

### 2.5 Test Suite Execution
* **Total Passing Tests**: **166 passed** in 47.56s across `tests/analytics/`, `tests/etl/`, `tests/kpi/`, and `tests/screener/`.

---

## 3. Manual Verification & Key Insights

### 3.1 Data Quality (DQ) Rule Unit Tests
* Executed [tests/etl/test_validator.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/tests/etl/test_validator.py).
* All 14 Data Quality rule unit tests passed with **0 failures**.

### 3.2 Quality Compounder Screener Preset Verification
Checked the top 5 companies in the **Quality Compounder** screener preset to verify that `ROE > 15%` and `Debt-to-Equity < 1.0`:

| Rank | Company Ticker | Company Name | ROE (%) | Debt-to-Equity | Composite Quality Score | Verification Status |
|:---:|---|---|:---:|:---:|:---:|:---:|
| 1 | `ASIANPAINT` | Asian Paints Ltd | 29.68% | 0.13 | 84.05 | ✅ Satisfied (`ROE > 15%`, `D/E < 1`) |
| 2 | `IRCTC` | Indian Railway Catering & Tourism Corp | 34.40% | 0.02 | 82.58 | ✅ Satisfied (`ROE > 15%`, `D/E < 1`) |
| 3 | `COALINDIA` | Coal India Ltd | 45.17% | 0.08 | 76.84 | ✅ Satisfied (`ROE > 15%`, `D/E < 1`) |
| 4 | `NESTLEIND` | Nestle India Ltd | 117.75% | 0.10 | 75.05 | ✅ Satisfied (`ROE > 15%`, `D/E < 1`) |
| 5 | `INDIGO` | InterGlobe Aviation Ltd | 892.57% | 0.02 | 73.50 | ✅ Satisfied (`ROE > 15%`, `D/E < 1`) |

### 3.3 Peer Ranking & IT Services ROE Verification
Checked the `IT Services` peer group to verify that the company with the highest raw ROE also receives the highest ROE percentile rank:

| Company Ticker | Company Name | Raw ROE (%) | ROE Percentile Rank | Rank Status |
|---|---|:---:|:---:|:---:|
| 🥇 `TCS` | Tata Consultancy Services Ltd | **50.94%** | **100.0%** | 🟢 Highest ROE & Top Rank |
| `INFY` | Infosys Ltd | 29.79% | 80.0% | 🟢 2nd |
| `HCLTECH` | HCL Technologies Ltd | 23.01% | 60.0% | 🟡 3rd |
| `LTIM` | LTIMindtree Ltd | 22.90% | 40.0% | 🔴 4th |
| `TECHM` | Tech Mahindra Ltd | 8.99% | 20.0% | 🔴 5th |

*Confirmation*: `TCS` holds the highest raw ROE (50.94%) and the highest percentile rank (100.0%).

---

## 4. Challenges Faced & Solutions

1. **Matplotlib GUI Backend Conflict in Headless Testing Environment**:
   * *Challenge*: Running `pytest` on radar chart generation failed with `_tkinter.TclError: invalid command name "tcl_findLibrary"` because Matplotlib defaulted to an interactive Tkinter GUI backend.
   * *Solution*: Enforced headless image rendering by setting `matplotlib.use('Agg')` prior to importing `matplotlib.pyplot`.

2. **Inverse Percentile Ranking for Debt-to-Equity & Valuation Ratios**:
   * *Challenge*: Default pandas ranking (`ascending=True`) assigns higher ranks to larger numbers, which incorrectly penalizes companies with low debt.
   * *Solution*: Passed `ascending=False` for Debt-to-Equity and P/E ratio ranking so that lower debt and lower valuation ratios map to higher percentile ranks (up to 100%).

3. **Safe Unassigned Company Handling**:
   * *Challenge*: 44 Nifty 100 companies do not belong to any of the 11 peer groups. Queries attempting to join non-existent peer groups could raise exceptions.
   * *Solution*: Implemented explicit checks returning `"No peer group assigned"` and benchmarked standalone companies against the Nifty 100 Market Average.

---

## 5. Lessons Learned
* **Headless Chart Generation**: Explicitly declaring `matplotlib.use('Agg')` in analytics scripts ensures background batch processing and unit testing without GUI dependencies.
* **Persistent Cell-Level OpenPyXL Formatting**: Setting explicit fill and font properties cell-by-cell in openpyxl guarantees rendering consistency across Excel, LibreOffice, and Google Sheets without relying on external conditional formatting engines.

---

## 6. Recommendations & Next Steps
* **Interactive Web Dashboard**: Integrate the generated radar PNGs and peer comparison tables into a Streamlit or Next.js web dashboard.
* **Automated Scheduled Refreshes**: Schedule daily or quarterly batch refreshes of `peer_percentiles`, radar charts, and Excel reports using cron schedules.
