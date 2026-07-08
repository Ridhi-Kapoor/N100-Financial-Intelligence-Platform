# Sprint 1 Deliverables Checklist

This checklist summarizes the deliverables completed and verified during Sprint 1.

## Database & Artifact Output
* [✓] **nifty100.db** - Structured SQLite database loaded with clean relational data (located at [nifty100.db](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/data/db/nifty100.db))
* [✓] **load_audit.csv** - Detailed load summary logs tracking SQLite loading success (located at [load_audit.csv](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/data/output/load_audit.csv))
* [✓] **validation_failures.csv** - Validation results tracking data quality failures (located at [validation_failures.csv](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/data/output/validation_failures.csv))

## ETL Pipeline Python Modules
* [✓] **loader.py** - Scan, extract, and preprocess raw Excel sheets into CSVs (located at [loader.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/scripts/etl/loader.py))
* [✓] **normaliser.py** - Standardize tickers, clean formatting inconsistencies, and parse mixed year types (located at [normaliser.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/scripts/etl/normaliser.py))
* [✓] **validator.py** - High-coverage quality checker validation module (located at [validator.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/scripts/etl/validator.py))
* [✓] **load_to_sqlite.py** - Database compiler that builds schemas, checks constraints, injects stubs, and loads datasets (located at [load_to_sqlite.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/scripts/etl/load_to_sqlite.py))

## SQL Scripts & Configuration
* [✓] **schema.sql** - SQL schema script defining tables, data types, and primary/foreign key relationships (located at [schema.sql](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/sql/schema.sql))
* [✓] **exploratory_queries.sql** - Contains 10 exploratory queries including row count, sampling, and aggregations (located at [exploratory_queries.sql](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/notebooks/exploratory_queries.sql))
* [✓] **data_quality_audit.sql** - Audit queries to verify data quality and detect issues (located at [data_quality_audit.sql](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/sql/data_quality_audit.sql))

## Tests & Verification
* [✓] **66 Unit Tests** - Robust pytest suite covering normalizer, validator, loader, and SQLite database loading operations (located in [tests/etl/](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/tests/etl))
* [✓] **data_quality_audit.py** - Python script to run quality audits against the database (located at [data_quality_audit.py](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/scripts/data_quality_audit.py))

## Documentation
* [✓] **SPRINT1_RETROSPECTIVE.md** - Summary of Sprint 1 goals, blockers, solutions, and goals for Sprint 2 (located at [SPRINT1_RETROSPECTIVE.md](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/SPRINT1_RETROSPECTIVE.md))
* [✓] **PROJECT_SUMMARY.md** - Technical summary of the project architecture, design, and next steps (located at [PROJECT_SUMMARY.md](file:///C:/Users/Ridhi%20Kapoor/Desktop/Projects/Nifty100_Data_Foundation/PROJECT_SUMMARY.md))
