# 🔄 Sprint 4 Retrospective & Final Project Closeout

**Project:** Nifty 100 Financial Intelligence Platform  
**Sprint:** Sprint 4 (Dashboard Development, Testing, Optimization & Closure)  
**Date:** July 22, 2026  

---

## 1. Executive Summary

Sprint 4 focused on completing the multi-page Streamlit analytics dashboard, carrying out end-to-end functional testing across all 8 screens, resolving chart sizing and missing data edge cases, validating profile load performance under 3 seconds, updating technical documentation, and finalizing project closure deliverables. 

All 8 dashboard views are fully operational, tested with live database records, and verified for production readiness.

---

## 2. UX & Design Decisions

* **Dark Mode Design System**: Built a cohesive, high-contrast dark theme (`#0b0f19` main background, `#111827` sidebar, `#1e293b` card backgrounds) using Google Font *Plus Jakarta Sans* to deliver a sleek, modern visual aesthetic.
* **Unified Page Navigation**: Standardized multi-page routing via Streamlit's modern `st.navigation` and `st.Page` API, featuring custom icons and descriptive screen titles.
* **Responsive Visualizations**: Configured all Plotly charts (`px.scatter`, `px.pie`, `px.treemap`, `px.bar`, `go.Scatterpolar`, `make_subplots`) with `use_container_width=True` and standardized padding margins (`margin=dict(t=..., b=..., l=..., r=...)`) to prevent overflow.
* **Strategy Presets & Custom Sliders**: Implemented 6 one-click preset buttons (*Quality*, *Value*, *Growth*, *Dividend*, *Debt-Free*, *Turnaround*) alongside 10 custom filter sliders in the Stock Screener for effortless multi-factor screening.
* **Dynamic Status Badging**: Added clear visual indicators such as green PDF link buttons vs. red `🚨 Report Unavailable` badges for document filing links, and yellow `⭐ Benchmark` badges in peer comparison tables.

---

## 3. Data Quality & Edge Cases Encountered

1. **Partial Historical Data (< 10 Years)**:
   - *Observation*: Identified 5 companies (`JIOFIN`, `LICI`, `ATGL`, `ZOMATO`, `ADANIGREEN`) with fewer than 10 years of historical data in SQLite.
   - *Resolution*: Implemented fallback detection in `02_profile.py` and `05_trends.py` to display an explicit informative banner: `ℹ️ Limited historical data available (X years of financial records)` without breaking chart rendering or throwing errors.

2. **Missing & Invalid Metric Values**:
   - *Observation*: Certain companies (e.g. newly listed entities or financial sector firms) have `NaN`, `None`, or missing values for metrics like FCF, P/E ratio, or Debt-to-Equity.
   - *Resolution*: Updated metric display cards and tables across all views to display explicit `"N/A"` placeholders (via `pd.notna()` checks and `.style.format(na_rep="N/A")`), preventing `NoneType` crashes or blank UI elements.

3. **Financial Sector & Debt-Free Rule Overrides**:
   - *Observation*: Applying strict Debt-to-Equity or Interest Coverage Ratio (ICR) filters erroneously excluded financial institutions (banks/NBFCs) and debt-free companies with 0 interest expense.
   - *Resolution*: Enforced rule overrides in `src/screener/engine.py` to waive D/E limits for `Financials` sector companies and treat debt-free companies as having infinite ICR.

4. **Screener Filter Limits**:
   - *Observation*: Setting sliders to extreme minimums or maximums (e.g. P/E max = 150 or P/E max = 0) resulted in either full universe pass or 0 matches.
   - *Resolution*: Added graceful fallback messages (`⚠️ No companies match all your selected filter criteria`) and tips to relax thresholds, ensuring tables and downloads continue to work without exceptions.

---

## 4. Performance Improvements & Optimization Findings

* **Database Query Caching**: Wrapped core database lookup functions in `src/dashboard/utils/db.py` with `@st.cache_data(ttl=600)`.
* **Profile Page Benchmark**: Measured data loading execution times for the Company Profile page across 7 diverse companies:
  - `TCS` (IT): **20.21 ms**
  - `HDFCBANK` (Financials): **19.02 ms**
  - `RELIANCE` (Energy): **16.64 ms**
  - `HINDUNILVR` (FMCG): **16.25 ms**
  - `APOLLOHOSP` (Healthcare): **16.81 ms**
  - `JIOFIN` (Financials - Partial Data): **15.72 ms**
  - `ZOMATO` (Consumer Discretionary - Partial Data): **17.32 ms**
* **Finding**: Profile data loading executes in **15 to 20 milliseconds**, well below the target SLA of 3 seconds (3,000 ms).

---

## 5. Challenges & Resolutions

| Challenge | Root Cause | Resolution |
| :--- | :--- | :--- |
| **Plotly Chart Overflow** | Default Plotly margin settings causing horizontal scrollbars in Streamlit columns. | Applied `use_container_width=True` and updated layout margins to `dict(t=30, b=30, l=30, r=30)` on all figures. |
| **Broken Annual Report PDF Links** | Some historical BSE filing URLs in `documents.csv` return 404 or point to invalid paths. | Created `is_url_available()` helper using `requests.head()` with 2.5s timeout and caching to flag unavailable links gracefully. |
| **Radar Chart Metric Scaling** | Mixing absolute numbers (Sales in ₹ Cr) with percentages (ROE %) distorted radar chart polygons. | Normalized all 8 radar axes to a uniform **0–100 percentile score** in `src/analytics/radar.py`. |

---

## 6. Lessons Learned & Future Enhancements

### Lessons Learned
* **Pre-computing Analytics**: Pre-computing quality scores and radar percentiles during ETL significantly speeds up interactive dashboard rendering.
* **Defensive Frontend Rendering**: Explicitly checking for `empty` DataFrames and `NaN` values before rendering Plotly traces prevents silent UI failures.

### Future Enhancements
1. **Automated PDF Report Ingestion**: Integrate a background worker to extract text and tables directly from BSE Annual Report PDFs using OCR/PyPDF.
2. **Predictive Financial Modeling**: Add machine-learning models (e.g. Altman Z-score, Beneish M-score, DuPont analysis) to predict financial distress or earnings manipulation.
3. **Real-time Price Feed Integration**: Connect to live market data APIs (e.g. NSE API / Yahoo Finance) for intra-day price tracking.

---

## 7. Sprint 4 Task Board Completion Status

- [x] **Task 4.1**: Test all 8 Streamlit dashboard screens across 10+ companies and multiple sectors — **COMPLETED**
- [x] **Task 4.2**: Handle companies with partial historical data (< 10 years) with "Limited historical data available" messages — **COMPLETED**
- [x] **Task 4.3**: Test Screener min/max filter bounds, verify tables and CSV downloads — **COMPLETED**
- [x] **Task 4.4**: Resolve Plotly chart sizing and responsiveness issues — **COMPLETED**
- [x] **Task 4.5**: Handle missing/NaN values gracefully with "N/A" placeholders — **COMPLETED**
- [x] **Task 4.6**: Validate Company Profile load performance under 3 seconds — **COMPLETED**
- [x] **Task 4.7**: Update `README.md` with overview, setup, dependencies, DB setup, launch command, structure, and usage — **COMPLETED**
- [x] **Task 4.8**: Complete Dashboard Documentation for all 8 screens — **COMPLETED**
- [x] **Task 4.9**: Document Sprint 4 Retrospective — **COMPLETED**
- [x] **Task 4.10**: Update Sprint 4 Task Board and verify production readiness — **COMPLETED**
