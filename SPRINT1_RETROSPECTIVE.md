# Sprint 1 Retrospective - Nifty 100 Data Foundation

## 1. Sprint Goal
The goal of Sprint 1 was to establish the foundation of the Nifty 100 Financial Intelligence Platform by building a robust, automated ETL (Extract, Transform, Load) pipeline to process raw Excel data, validate it against strict data quality rules, and load it into a structured SQLite relational database.

---

## 2. What Was Completed
* **ETL Pipeline Preprocessing**: Designed `loader.py` to automatically scan raw Excel files in `data/raw`, validate sheets, and convert them to processed CSVs.
* **Data Normalization Engine**: Built `normaliser.py` containing modular logic for standardizing ticker symbols and cleaning year fields (e.g., resolving decimal years, fiscal year shorthand, and different month prefixes).
* **Robust Quality Validator**: Created `validator.py` containing 16+ granular, parameterized data quality checks (e.g., primary key constraints, foreign key referential integrity, range checks, and financial balance verification).
* **SQLite Relational Database Loader**: Written `load_to_sqlite.py` to initialize tables, load normalized CSV records in transaction blocks, dynamically resolve missing profiles via stub records, verify row counts, check for foreign key constraints, and output execution audit logs.
* **Data Quality Audits**: Generated comprehensive python and SQL scripts to sample companies, check year-wise data coverage, report low data coverage, and detect missing, duplicate, invalid, or negative values.
* **Unit Testing Suite**: Structured and wrote 66 robust unit tests covering loader, normalizer, validator, and SQLite database loading operations.

---

## 3. Challenges Faced
1. **Ticker Typo Mismatch**: The ticker `AGTL` was referenced in the raw cashflow sheet instead of `ATGL` (Adani Total Gas Ltd). This caused the loader to create an unnecessary duplicate stub profile (`AGTL (Stub)`), separating cash flow data from other statements.
2. **Fractional and Shorthand Years**: Raw sheets contained mixed-type year values like `'2024.5'` (decimal float representations), `'Mar-13'` (month suffix format), and `'TTM'` (rolling periods). Setting integer years in columns containing string/object types caused Pandas `LossySetitemError` and `TypeError` when editing in-place.
3. **Database Integrity Constraints**: The database year column was marked as `NOT NULL`. Converting rolling labels like `'TTM'` to `None` caused SQL insertion violations.
4. **Missing Parent Entity Profiles**: Raw financial files contained data for 100 companies, but the parent `companies.xlsx` file only listed 92. This caused foreign key constraint violations upon inserting records.

---

## 4. How They Were Resolved
1. **Typo Mapping**: Added ticker translation mapping in `normaliser.py` (`AGTL` $\rightarrow$ `ATGL`) so that it is processed as the correct company symbol.
2. **Pandas Type Casting**: Cast pandas DataFrame columns to the generic `object` dtype (`df = df.astype(object)`) before running normalization loops. This bypassed strict pandas Numpy/Arrow series constraint checks.
3. **TTM Preservation**: Updated `normalize_year` to recognize and preserve `'TTM'` as a valid string and return `None` only for genuine garbage entries (e.g., `'ABC'`), which kept SQLite `NOT NULL` constraints intact.
4. **Referential Integrity Stubs**: Integrated automatic stub record injection inside `load_to_sqlite.py`. If a company ID is referenced in financial tables but missing in `companies.csv`, the script dynamically inserts a basic company stub record first, satisfying the foreign key constraint.

---

## 5. Lessons Learned
* **Pre-ETL Normalization is Critical**: Standardizing identifiers (tickers) and dimensions (years) at the earliest preprocessing stage avoids complex parsing issues and data corruption down the line.
* **Mixed-Type Fields in Pandas**: In-place edits of pandas columns can easily trigger strict dtype conversion issues; casting dataframes to `object` is a robust way to clean fields of mixed types safely.
* **Relational Constraint Safety**: SQLite's `PRAGMA foreign_keys = ON;` and `PRAGMA foreign_key_check;` are essential tools to verify database referential integrity programmatically.

---

## 6. Improvements for Sprint 2
* **Deduplication Engine**: Create an automated check/loader modification to cleanly deduplicate exact duplicate rows from raw spreadsheets during the extraction phase rather than relying solely on detection.
* **Incremental Loading Support**: Support upserting (`INSERT OR REPLACE`) or delta-loads instead of dropping tables and doing full rebuilds on every run.
* **Automated Audit Pipeline**: Integrate `data_quality_audit.py` directly into the ETL run phase so that database reloading fails early if critical data validation errors or duplicates exceed acceptable thresholds.

---

## 7. Sprint Outcome
* **Database Loaded**: `data/db/nifty100.db` contains clean, relational data across 10 linked tables.
* **Integrity Maintained**: Row counts match expected CSV sources, and foreign key integrity is verified.
* **Unit Tests**: All 66 test cases in the test suite pass with 100% success.
* **Status**: **Successful Completion of Sprint 1.**
