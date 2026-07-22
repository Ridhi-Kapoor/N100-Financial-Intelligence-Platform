# 📊 Nifty 100 Dashboard Documentation

This document provides detailed screen descriptions, layouts, interactive controls, and key functionalities for all **8 Streamlit dashboard screens** in the Nifty 100 Financial Intelligence & Analytics Platform.

---

## Screen 1: Executive Overview (`01_home.py`)

### Purpose
Serves as the central command center for executive oversight, providing high-level financial health summaries, sector distribution metrics, and top-quality company rankings for any selected financial year (FY2019 – FY2024).

### Key Features & Layout
1. **Financial Year Control**: Sidebar select box allowing instant recalculation of metrics across FY2019–FY2024.
2. **Top Metric Cards Row**: 6 dynamic KPI cards displaying:
   - **Average ROE (%)**: Mean Return on Equity across all active constituents.
   - **Median P/E (x)**: Central valuation multiple for the universe.
   - **Median Debt-to-Equity**: Overall financial leverage benchmark.
   - **Total Companies**: Total company universe count (100 constituents).
   - **Median 5Y Revenue CAGR (%)**: Compound annual top-line growth rate.
   - **Debt-Free Companies Count**: Number of companies maintaining $D/E \le 0.05$.
3. **Sector Distribution Donut Chart (Plotly)**: Interactive donut chart rendering company distribution across all 11 broad sectors with percentages and hover breakdown.
4. **Top 5 Quality Compounders Table**: Sortable table ranking top companies by Composite Quality Score, displaying Ticker, Name, Sector, Quality Score, ROE %, and Debt/Equity.
5. **Platform Module Quick Links**: Navigation grid summarizing downstream analytics modules.

---

## Screen 2: Company Profile & Deep-Dive (`02_profile.py`)

### Purpose
Provides comprehensive individual company analysis, multi-year performance visualization, fundamental pros & cons evaluation, and full financial statements.

### Key Features & Layout
1. **Search & Autocomplete Bar**: Search by company name or NSE ticker symbol (e.g. `TCS`, `HDFCBANK`, `JIOFIN`), or type a custom query.
2. **Company Header Banner**: Displays company title, ticker, sector, sub-sector, and business summary.
3. **6 KPI Highlight Cards**: Instant view of ROE, ROCE, Net Profit Margin %, Debt-to-Equity, 5-Year Revenue CAGR, and Latest Free Cash Flow (₹ Cr).
4. **Limited Data Banner**: Displays an informative banner (`ℹ️ Limited historical data available`) if a company has fewer than 10 years of historical data (e.g. `JIOFIN`, `LICI`, `ATGL`, `ZOMATO`, `ADANIGREEN`).
5. **Multi-Year Financial Charts**:
   - **10-Year Revenue & Net Profit Bar Chart**: Grouped bar chart comparing sales vs. PAT over time.
   - **10-Year ROE & ROCE Dual-Axis Line Chart**: Dual-axis chart highlighting return trajectories.
6. **Automated Pros & Cons Breakdown**: Dynamic fundamental evaluation highlighting low leverage, high ROE/ROCE track records, positive FCF generation, or high P/E valuation warnings.
7. **Full Financial Statement Tabs**: Interactive DataFrames for:
   - **Profit & Loss Table** (Sales, OPM %, Net Profit, EPS)
   - **Balance Sheet Table** (Equity, Reserves, Borrowings, Total Assets)
   - **Cash Flow Table** (CFO, CFI, CFF, Net Cash Flow)
   - **Ratios & Valuation Table** (ROE %, Debt/Equity, FCF, Market Cap, P/E, P/B, EV/EBITDA, Dividend Yield %)

---

## Screen 3: Quantitative Stock Screener (`03_screener.py`)

### Purpose
Enables quantitative stock filtering based on multi-factor fundamental metrics, strategy presets, and custom slider thresholds.

### Key Features & Layout
1. **6 Strategy Presets**: One-click sidebar buttons to instantly configure filters:
   - **Quality**: High ROE ($\ge 15\%$), low leverage ($D/E \le 0.5$), positive FCF.
   - **Value**: Low P/E ($\le 35x$), low P/B ($\le 5x$), dividend yield ($\ge 1.0\%$).
   - **Growth**: High 5-year Revenue & PAT CAGR ($\ge 12\%$).
   - **Dividend**: High dividend yield ($\ge 2.0\%$), low leverage.
   - **Debt-Free**: Near-zero leverage ($D/E \le 0.05$).
   - **Turnaround**: Moderate ROE recovery, improving margins and leverage.
2. **10 Interactive Sliders**: Sidebar controls for ROE min, D/E max, FCF min, Revenue CAGR min, PAT CAGR min, OPM min, P/E max, P/B max, Dividend Yield min, and ICR min. Supports extreme min/max values without crashing.
3. **Summary Metric Bar**: Live counter showing matching company count, average filtered ROE %, median P/E ratio, and average quality score.
4. **Risk vs. Return Scatter Plot (Plotly)**: Interactive scatter matrix plotting Debt-to-Equity (X-axis) against ROE % (Y-axis), with bubble size representing Composite Quality Score and color indicating sector.
5. **Filtered Results Table**: Comprehensive sortable table with custom column formatting.
6. **CSV Export Button**: Download currently filtered results as `nifty100_screener_results.csv`.

---

## Screen 4: Peer Comparison & Benchmarking (`04_peers.py`)

### Purpose
Facilitates side-by-side relative performance comparison of companies against industry peer group averages and designated sector benchmarks.

### Key Features & Layout
1. **Peer Group & Company Selectors**: Select one of 11 industry peer groups (e.g. *Private Banks*, *IT Services*, *Pharmaceuticals*, *FMCG*) and choose a target constituent.
2. **Benchmark Highlight Cards**: Side-by-side comparison of target company vs. peer group average across ROE %, Composite Quality Score, Debt-to-Equity, and FCF (₹ Cr).
3. **8-Axis Plotly Radar Chart (Scatterpolar)**: Visual comparison of 8 normalized score axes (0–100 scale):
   - ROE Score, ROCE Score, NPM Score, Debt-to-Equity Score, FCF Score, PAT CAGR 5Y Score, Revenue CAGR 5Y Score, and Composite Quality Score.
   - Traces overlay Target Company (filled blue), Peer Group Average (dashed red), and Benchmark Company (dotted green).
4. **Side-by-Side KPI Comparison Table**: Complete peer table highlighting the benchmark company row with distinct color fill.
5. **CSV Download Button**: Export peer group metrics as CSV.

---

## Screen 5: Multi-Year Financial Trend Analysis (`05_trends.py`)

### Purpose
Provides multi-metric historical trajectory overlays to evaluate long-term financial trends and Year-over-Year (YoY) growth rates.

### Key Features & Layout
1. **Company Autocomplete Search**: Quick selection of any constituent company.
2. **Multi-Metric Overlay Selector**: Choose 1 to 3 metrics simultaneously (e.g., Revenue, Net Profit, ROE %, OPM %, Market Cap, P/E Ratio).
3. **Dual Y-Axes Trajectory Chart (Plotly)**:
   - Primary Y-axis for absolute currency metrics (₹ Cr).
   - Secondary Y-axis for ratios, percentages, and multiples (%, x).
   - **YoY Growth Annotations**: Displays percentage change badges directly above each data point (e.g., `+14.2%`).
4. **Historical Breakdown Data Table**: Full numerical table displaying historical values with `N/A` handling for missing records.
5. **Limited Data Banner**: Displays info alert when data window is less than 10 years.

---

## Screen 6: Sector & Sub-Sector Analytics (`06_sectors.py`)

### Purpose
Visualizes broad sector and sub-sector market distributions, top-line vs. profitability relationships, and sector median KPI benchmarks.

### Key Features & Layout
1. **Broad Sector Filter**: Select a specific broad sector or view "All Sectors".
2. **Revenue vs. ROE % Bubble Map (Plotly)**:
   - **X-axis**: Revenue (Sales - ₹ Cr).
   - **Y-axis**: Return on Equity (ROE %).
   - **Bubble Size**: Market Capitalization (₹ Cr).
   - **Bubble Color**: Sub-sector mapping.
3. **Sector Median KPI Bar Chart**: Comparative bar chart displaying sector medians for ROE %, ROCE %, OPM %, P/E, 5Y Revenue CAGR %, or Debt-to-Equity, with the selected sector highlighted.
4. **Detailed Sector Company Table**: Expandable view listing all constituents in the selected sector.

---

## Screen 7: Capital Allocation Map (`07_capital.py`)

### Purpose
Categorizes Nifty 100 companies into cash flow capital allocation patterns based on Operating (CFO), Investing (CFI), and Financing (CFF) cash flow dynamics.

### Key Features & Layout
1. **8 Capital Allocation Patterns**:
   - **Shareholder Returns**: $CFO (+), CFI (-), CFF (-)$
   - **Reinvestor**: High Capex Reinvestment $CFO (+), CFI (-)$
   - **Growth Funded by Debt**: $CFO (+/--), CFI (-), CFF (+)$
   - **Liquidating Assets**: $CFO (-), CFI (+)$
   - **Distress Signal**: $CFO (-), CFF (-)$
   - **Pre-Revenue / Cash Accumulator / Mixed**
2. **Capital Allocation Treemap (Plotly)**: Treemap where rectangle size represents Market Capitalization and color represents allocation pattern.
3. **Pattern Count Summary Cards**: High-level counts for Shareholder Returns, Reinvestors, Debt-Funded Growth, and Distress signals.
4. **Filterable Allocation Table**: Interactive table filtering constituents by selected capital allocation pattern.

---

## Screen 8: Annual Reports & Data Export Portal (`08_reports.py`)

### Purpose
Central hub for accessing BSE annual report filings, generating company factsheets, downloading raw datasets, and monitoring database audit health.

### Key Features & Layout
1. **BSE Annual Reports Tab**: Search company to view filing years and PDF links. Incorporates HTTP head checking to display a red `🚨 Report Unavailable` badge if missing/404 or a green `📄 Open Report (PDF)` button if active.
2. **Company Factsheet Generator Tab**: One-click generation of markdown executive factsheets combining company profile, valuation metrics, and P&L summaries.
3. **Data Export Center Tab**: Direct CSV download buttons for `Financial Ratios`, `Companies Directory`, and `Sector Mapping`.
4. **Database Audit & Health Status Tab**: Displays active connection status and table-by-table record counts across all 9 relational tables.
