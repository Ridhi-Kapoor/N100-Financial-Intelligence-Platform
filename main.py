"""
Main execution script for Nifty100 Data Foundation ETL Pipeline validation.
"""

from pathlib import Path
import pandas as pd
from scripts.etl.validator import DataValidator

def run_validation_demo():
    print("Initializing Data Validation Demo...")
    
    # 1. Create a sample dirty DataFrame representing raw data
    data = {
        "ticker": ["TCS", "TCS", None, "INFY", "RELIANCE", "invalid_ticker_123"],
        "year": [2022, 2022, 2023, 2024, 2028, 2023],  # Duplicate company-year (TCS 2022), future year (2028)
        "sales": [5000.0, 5000.0, 4000.0, -100.0, 8000.0, 0.0],  # Negative sales for INFY, Zero sales for invalid_ticker_123
        "opm": [0.25, 0.25, 0.22, 0.15, 1.25, 0.05],  # OPM out of range for RELIANCE (1.25 > 1.0)
        "total_assets": [10000, 10000, 8000, 9000, 12000, -500],  # Negative assets for invalid_ticker_123
        "total_liabilities": [4000, 4000, 3000, 5000, 6000, 200],
        "total_equity": [5000, 5000, 5000, 4000, 6000, 300],  # Balance sheet mismatch for TCS (4000 + 5000 != 10000)
        "net_profit": [1000, 1000, 800, -200, 1500, -100],  # Negative profit for INFY & invalid_ticker_123
        "sector": ["Technology", "Technology", "Technology", None, "Energy", "Energy"],  # Missing sector for INFY
        "industry": ["IT Services", "IT Services", "IT Services", "IT Services", "Oil & Gas", ""]  # Empty industry for invalid_ticker_123
    }
    df = pd.DataFrame(data)
    
    # Set of valid parent tickers for FK validation
    valid_tickers = {"TCS", "INFY", "RELIANCE"}
    
    # 2. Instantiate the validator
    validator = DataValidator()
    
    # 3. Run validation
    print("Validating dataset...")
    failures = validator.validate_dataset(
        df=df,
        table_name="company_financials",
        pk_cols="ticker",
        year_col="year",
        mandatory_cols=["ticker", "year", "sales"],
        fk_col="ticker",
        parent_keys=valid_tickers,
        parent_table_name="approved_companies",
        sales_col="sales",
        opm_col="opm",
        assets_col="total_assets",
        liabilities_col="total_liabilities",
        equity_col="total_equity",
        net_profit_col="net_profit",
        sector_col="sector",
        industry_col="industry",
        current_year=2026
    )
    
    print(f"Validation complete. Found {len(failures)} failures.")
    
    # 4. Export failures
    output_path = Path("data/output/validation_failures.csv")
    validator.export_failures(output_path)
    print(f"Validation failures exported to: {output_path.resolve()}")
    
    # 5. Display the failures
    failures_df = validator.get_failures_df()
    print("\nSummary of failures:")
    print(failures_df[["Rule ID", "Severity", "Row Number", "Column Name", "Error Message"]].to_string())

if __name__ == "__main__":
    run_validation_demo()
