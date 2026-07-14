# Sprint 2 Retrospective - Nifty 100 Financial Intelligence Platform

## 1. Sprint Goal
The goal of Sprint 2 was to implement a robust, high-performance financial analytics and calculation engine that processes raw/normalized financial records, computes key performance indicators (KPIs) covering profitability, leverage, efficiency, growth (CAGR), and cash flows, cross-checks computed values against raw source data, logs mismatches (edge cases), and stores them in a structured SQLite database (`financial_ratios`).

---

## 2. Work Completed
* **Leverage & Efficiency Module**: Extended `src/analytics/ratios.py` to calculate Debt-to-Equity, Interest Coverage Ratio (ICR), Net Debt, Asset Turnover, and warning flags.
* **CAGR Growth Engine**: Created `src/analytics/cagr.py` containing growth calculations over 3-year, 5-year, and 10-year windows for Revenue, PAT, and EPS. Includes 6 custom edge-case handlers.
* **Cash Flow Analytics Module**: Created `src/analytics/cashflow.py` and [src/analytics/cashflow_kpis.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/src/analytics/cashflow_kpis.py) to calculate Free Cash Flow (FCF), trailing 5-year CFO Quality Score, CapEx Intensity, FCF Conversion, and classify companies into 8 capital allocation patterns.
* **Ratio Calculation Engine Runner**: Created `src/analytics/run_ratio_engine.py` to load processed datasets, perform de-duplication, execute all analytics calculations, detect and log anomalies (difference > 5%), and populate the `financial_ratios` table in `nifty100.db`.
* **Testing Suite**: Created `tests/analytics/test_leverage_ratios.py`, `tests/analytics/test_cagr.py`, `tests/analytics/test_cashflow.py`, `tests/analytics/test_ratio_engine_anomalies.py`, and `tests/kpi/test_kpi_formulas.py` for a total of **135 passing unit tests**.
* **Database Verification & Screener Scripts**:
  * [scripts/verify_database.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/scripts/verify_database.py): Diagnostics script tracking row count (1,184), missing values, and duplicate records.
  * [scripts/run_screener.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/scripts/run_screener.py): Screener script verifying filters (ROE > 15%, Debt-to-Equity < 1.0, excluding Financials).
  * [scripts/demo_financial_ratios.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/scripts/demo_financial_ratios.py): Polished demo report summarizing KPIs vertically for 5 target companies.

---

## 3. Formula Decisions
* **Debt-to-Equity**: $\frac{\text{Borrowings}}{\text{Equity Capital} + \text{Reserves}}$. Handled division by zero and negative equity capital.
* **Interest Coverage Ratio (ICR)**: $\frac{\text{Operating Profit} + \text{Other Income}}{\text{Interest Expense}}$. If Interest is 0, the company is flagged as `"Debt Free"` (ratio set to `None`).
* **Net Debt**: $\text{Borrowings} - \text{Investments}$. Permitted negative net debt values.
* **Asset Turnover**: $\frac{\text{Sales}}{\text{Total Assets}}$. Suppressed calculation if Total Assets is 0.
* **Free Cash Flow**: $\text{Operating Activity (CFO)} + \text{Investing Activity (CFI)}$. CFI is negative for capital expenditures, so FCF represents net surplus.
* **CFO Quality Score**: Trailing 5-year average of $\frac{\text{CFO}}{\text{PAT}}$. Requires a full 5-year sequence; otherwise returns `None`.
* **CAGR**: $\left(\left(\frac{\text{Ending Value}}{\text{Beginning Value}}\right)^{\frac{1}{n}} - 1\right) \times 100$.

---

## 4. Edge Cases Implemented
* **Leverage Suppression for Financials**: Suppressed the High Leverage warning (Debt-to-Equity > 5) for Financial sector companies like PNB, PFC, REC, ICICI, Axis Bank, and Bank of Baroda because high leverage is structurally normal.
* **CAGR Growth Sign Handling**:
  * `Positive -> Positive`: Normal CAGR.
  * `Positive -> Negative`: Returns `None`, Flag = `"DECLINE_TO_LOSS"`.
  * `Negative -> Positive`: Returns `None`, Flag = `"TURNAROUND"`.
  * `Negative -> Negative`: Returns `None`, Flag = `"BOTH_NEGATIVE"`.
  * `Beginning Value = 0`: Returns `None`, Flag = `"ZERO_BASE"`.
  * `Insufficient years of data`: Returns `None`, Flag = `"INSUFFICIENT"`.
* **CFO Quality Score Boundary Conditions**: Returns `None` if PAT is 0 or if there are fewer than 5 trailing years of data.
* **FCF Conversion**: Returns `None` if Operating Profit is 0.

---

## 5. Challenges Faced & Solutions
1. **Quoting and Escaping in PowerShell**: Executing SQLite raw queries with Python via the command line resulted in string escaping errors. 
   * *Solution*: Wrote clear standalone python scripts (`verify_database.py`, `run_screener.py`, `demo_financial_ratios.py`) which bypass PowerShell's parsing issues.
2. **Duplicate Records in Raw Datasets**: The processed `financial_ratios.csv` file contained duplicate company-year records with zero-filled cash flow values (e.g. ABB 2014 had two rows).
   * *Solution*: Collapsed duplicate company-year records during screener queries using `GROUP BY` to ensure unique results (returning exactly 48 unique companies instead of 56 duplicate rows).
3. **Data Type Mismatches during Merging**: Some files had `year` as an integer while others had it as a string containing `"TTM"`.
   * *Solution*: Cast `year` and `company_id` columns to stripped strings across all datasets before executing joins.

---

## 6. Lessons Learned
* **Index Preservation in Merges**: Using dictionary-based lookup maps for CAGR and trailing averages is far more robust and faster than executing complex multi-stage pandas joins, especially when handling gaps in data.
* **Early Data Auditing**: The data quality discrepancies (duplicates) highlight the importance of having data quality audits run during the ETL stage before data is written to the database.

---

## 7. Future Improvements
* **Dynamic Table Rebuilding**: Create database triggers to automatically calculate/update the `financial_ratios` table whenever a new record is added to the P&L, Balance Sheet, or Cash Flow tables.
* **Automated Data Quality Cleanups**: Extend the ETL pipeline to automatically de-duplicate company-year stubs before writing them to processed CSV files.
