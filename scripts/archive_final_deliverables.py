"""
Script to aggregate and archive all 23 project deliverables into output/final_deliverables/.
"""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DELIVERABLES_DIR = PROJECT_ROOT / "output" / "final_deliverables"

def archive_deliverables():
    # Create target directory structure
    dirs = {
        "docs": DELIVERABLES_DIR / "documentation",
        "reports": DELIVERABLES_DIR / "reports",
        "excel": DELIVERABLES_DIR / "excel_summaries",
        "db": DELIVERABLES_DIR / "database",
        "processed": DELIVERABLES_DIR / "processed_datasets",
        "logs": DELIVERABLES_DIR / "audit_logs",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # 1. Documentation
    shutil.copy2(PROJECT_ROOT / "docs" / "analyst_guide.pdf", dirs["docs"] / "analyst_guide.pdf")
    shutil.copy2(PROJECT_ROOT / "output" / "perf_notes.md", dirs["docs"] / "perf_notes.md")
    shutil.copy2(PROJECT_ROOT / "README.md", dirs["docs"] / "README.md")

    # 2. PDF Reports & Test Results
    if (PROJECT_ROOT / "reports" / "portfolio" / "portfolio_summary.pdf").exists():
        shutil.copy2(PROJECT_ROOT / "reports" / "portfolio" / "portfolio_summary.pdf", dirs["reports"] / "portfolio_summary.pdf")
    if (PROJECT_ROOT / "reports" / "pytest_report.html").exists():
        shutil.copy2(PROJECT_ROOT / "reports" / "pytest_report.html", dirs["reports"] / "pytest_report.html")

    tearsheet_dest = dirs["reports"] / "tearsheets"
    tearsheet_dest.mkdir(parents=True, exist_ok=True)
    tearsheet_src = PROJECT_ROOT / "reports" / "tearsheets"
    if tearsheet_src.exists():
        for pdf_file in tearsheet_src.glob("*.pdf"):
            shutil.copy2(pdf_file, tearsheet_dest / pdf_file.name)

    # 3. Excel Workbooks & Analytics Reports
    for excel_name in ["valuation_summary.xlsx", "screener_results.xlsx", "peer_comparison.xlsx", "capital_allocation_report.xlsx"]:
        src_f = PROJECT_ROOT / "output" / excel_name
        if src_f.exists():
            shutil.copy2(src_f, dirs["excel"] / excel_name)

    # 4. Database & DDL Schema
    if (PROJECT_ROOT / "data" / "db" / "nifty100.db").exists():
        shutil.copy2(PROJECT_ROOT / "data" / "db" / "nifty100.db", dirs["db"] / "nifty100.db")
    if (PROJECT_ROOT / "sql" / "schema.sql").exists():
        shutil.copy2(PROJECT_ROOT / "sql" / "schema.sql", dirs["db"] / "schema.sql")

    # 5. Processed CSV Datasets
    proc_dir = PROJECT_ROOT / "data" / "processed"
    if proc_dir.exists():
        for csv_f in proc_dir.glob("*.csv"):
            shutil.copy2(csv_f, dirs["processed"] / csv_f.name)

    # 6. Audit & Anomaly Logs
    for log_name in ["ratio_edge_cases.log", "load_audit.csv", "dq_audit_log.csv"]:
        for parent_folder in [PROJECT_ROOT / "data" / "output", PROJECT_ROOT / "output", PROJECT_ROOT / "logs"]:
            candidate = parent_folder / log_name
            if candidate.exists():
                shutil.copy2(candidate, dirs["logs"] / log_name)

    print(f"Successfully archived project deliverables into: {DELIVERABLES_DIR}")

if __name__ == "__main__":
    archive_deliverables()
