"""
Data Quality Validator for ETL Pipeline.

This module provides the DataValidator class and reusable validation functions
to check data quality rules (critical and warning levels) for financial
datasets in the ETL pipeline.
"""

import datetime
from enum import Enum
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
import pandas as pd


class Severity(str, Enum):
    """Severity levels for data quality validation failures."""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"


@dataclass
class ValidationFailure:
    """Represents a single data quality validation failure."""
    rule_id: str
    severity: str
    table_name: str
    row_number: int
    column_name: str
    failed_value: str
    error_message: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation failure to a dictionary for exporting."""
        return {
            "Rule ID": self.rule_id,
            "Severity": self.severity,
            "Table Name": self.table_name,
            "Row Number": self.row_number,
            "Column Name": self.column_name,
            "Failed Value": self.failed_value,
            "Error Message": self.error_message
        }


# -------------------------------------------------------------------------
# Reusable Validation Functions
# -------------------------------------------------------------------------

def check_pk_not_null(
    df: pd.DataFrame, 
    pk_cols: Union[str, List[str]], 
    table_name: str
) -> List[ValidationFailure]:
    """
    DQ-01: Primary Key cannot be NULL.
    
    Checks if any primary key column(s) contain null or NaN values.
    """
    failures = []
    if isinstance(pk_cols, str):
        pk_cols = [pk_cols]

    for col in pk_cols:
        if col not in df.columns:
            continue
        null_mask = df[col].isna()
        for idx, row in df[null_mask].iterrows():
            # Using 1-indexed row number matching the sheet row number
            row_num = int(idx) + 1
            failures.append(ValidationFailure(
                rule_id="DQ-01",
                severity=Severity.CRITICAL.value,
                table_name=table_name,
                row_number=row_num,
                column_name=col,
                failed_value=str(row[col]),
                error_message=f"Primary key column '{col}' cannot be NULL."
            ))
    return failures


def check_duplicate_pks(
    df: pd.DataFrame, 
    pk_cols: Union[str, List[str]], 
    table_name: str
) -> List[ValidationFailure]:
    """
    DQ-02: Duplicate Primary Keys.
    
    Checks if there are duplicate values across primary key columns.
    """
    failures = []
    if isinstance(pk_cols, str):
        pk_cols = [pk_cols]

    # Verify that all PK columns exist
    pk_cols = [c for c in pk_cols if c in df.columns]
    if not pk_cols:
        return failures

    # Find duplicate indices (keep=False flags all duplicates)
    dup_mask = df.duplicated(subset=pk_cols, keep=False)
    for idx, row in df[dup_mask].iterrows():
        val_dict = {col: row[col] for col in pk_cols}
        val_str = str(val_dict) if len(pk_cols) > 1 else str(row[pk_cols[0]])
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-02",
            severity=Severity.CRITICAL.value,
            table_name=table_name,
            row_number=row_num,
            column_name=", ".join(pk_cols),
            failed_value=val_str,
            error_message=f"Duplicate primary key detected: {val_str}."
        ))
    return failures


def check_foreign_key_violations(
    df: pd.DataFrame,
    fk_col: str,
    parent_keys: Set[Any],
    parent_table_name: str,
    table_name: str
) -> List[ValidationFailure]:
    """
    DQ-03: Foreign Key violations.
    
    Checks if foreign key values exist in the parent table's keys.
    """
    failures = []
    if fk_col not in df.columns:
        return failures

    # Only validate non-null values
    valid_fk_mask = df[fk_col].notna()
    invalid_mask = ~df[fk_col].isin(parent_keys) & valid_fk_mask

    for idx, row in df[invalid_mask].iterrows():
        val = row[fk_col]
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-03",
            severity=Severity.CRITICAL.value,
            table_name=table_name,
            row_number=row_num,
            column_name=fk_col,
            failed_value=str(val),
            error_message=(
                f"Foreign key violation: '{val}' does not exist in parent "
                f"table '{parent_table_name}'."
            )
        ))
    return failures


def check_missing_financial_year(
    df: pd.DataFrame, 
    year_col: str, 
    table_name: str
) -> List[ValidationFailure]:
    """
    DQ-04: Missing financial year.
    
    Checks if the financial year column has NULL, empty, or whitespace values.
    """
    failures = []
    if year_col not in df.columns:
        return failures

    # Check for NaN or empty strings after stripping
    null_mask = df[year_col].isna() | (df[year_col].astype(str).str.strip() == "")
    for idx, row in df[null_mask].iterrows():
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-04",
            severity=Severity.CRITICAL.value,
            table_name=table_name,
            row_number=row_num,
            column_name=year_col,
            failed_value=str(row[year_col]),
            error_message="Financial year is missing or empty."
        ))
    return failures


def check_missing_mandatory_fields(
    df: pd.DataFrame, 
    mandatory_cols: List[str], 
    table_name: str
) -> List[ValidationFailure]:
    """
    DQ-05: Missing mandatory fields.
    
    Checks if any mandatory columns have NULL or empty values.
    """
    failures = []
    for col in mandatory_cols:
        if col not in df.columns:
            # Column-level schema error
            failures.append(ValidationFailure(
                rule_id="DQ-05",
                severity=Severity.CRITICAL.value,
                table_name=table_name,
                row_number=0,
                column_name=col,
                failed_value="N/A",
                error_message=f"Mandatory column '{col}' is missing from the table schema."
            ))
            continue

        null_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
        for idx, row in df[null_mask].iterrows():
            row_num = int(idx) + 1
            failures.append(ValidationFailure(
                rule_id="DQ-05",
                severity=Severity.CRITICAL.value,
                table_name=table_name,
                row_number=row_num,
                column_name=col,
                failed_value=str(row[col]),
                error_message=f"Mandatory field '{col}' is missing or empty."
            ))
    return failures


def check_negative_sales(
    df: pd.DataFrame, 
    sales_col: str, 
    table_name: str
) -> List[ValidationFailure]:
    """
    DQ-06: Negative sales.
    
    Checks if the sales/revenue column contains negative values.
    """
    failures = []
    if sales_col not in df.columns:
        return failures

    numeric_sales = pd.to_numeric(df[sales_col], errors='coerce')
    neg_mask = (numeric_sales < 0) & numeric_sales.notna()

    for idx, row in df[neg_mask].iterrows():
        val = row[sales_col]
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-06",
            severity=Severity.CRITICAL.value,
            table_name=table_name,
            row_number=row_num,
            column_name=sales_col,
            failed_value=str(val),
            error_message=f"Sales cannot be negative (found value: {val})."
        ))
    return failures


def check_invalid_ticker(
    df: pd.DataFrame, 
    ticker_col: str, 
    table_name: str,
    pattern: str = r"^[A-Z0-9]{1,12}$"
) -> List[ValidationFailure]:
    """
    DQ-07: Invalid ticker/company code.
    
    Checks if ticker contains non-standard characters, space, or doesn't match
    the expected uppercase alphanumeric pattern.
    """
    failures = []
    if ticker_col not in df.columns:
        return failures

    regex = re.compile(pattern)
    for idx, row in df.iterrows():
        val = row[ticker_col]
        val_str = str(val).strip() if pd.notna(val) else ""
        if not val_str or not regex.match(val_str):
            row_num = int(idx) + 1
            failures.append(ValidationFailure(
                rule_id="DQ-07",
                severity=Severity.CRITICAL.value,
                table_name=table_name,
                row_number=row_num,
                column_name=ticker_col,
                failed_value=str(val),
                error_message=(
                    f"Ticker '{val}' is invalid. Must match pattern '{pattern}'."
                )
            ))
    return failures


def check_duplicate_company_year(
    df: pd.DataFrame, 
    company_col: str, 
    year_col: str, 
    table_name: str
) -> List[ValidationFailure]:
    """
    DQ-08: Duplicate Company-Year records.
    
    Checks if there are duplicate entries for the same company and year.
    """
    failures = []
    if company_col not in df.columns or year_col not in df.columns:
        return failures

    # Only look at rows with non-null company and year values
    valid_df = df[df[company_col].notna() & df[year_col].notna()]
    dup_mask = valid_df.duplicated(subset=[company_col, year_col], keep=False)

    for idx, row in valid_df[dup_mask].iterrows():
        comp_val = row[company_col]
        year_val = row[year_col]
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-08",
            severity=Severity.CRITICAL.value,
            table_name=table_name,
            row_number=row_num,
            column_name=f"{company_col}, {year_col}",
            failed_value=f"({comp_val}, {year_val})",
            error_message=(
                f"Duplicate record for Company: '{comp_val}' and "
                f"Financial Year: '{year_val}'."
            )
        ))
    return failures


def check_opm_out_of_range(
    df: pd.DataFrame,
    table_name: str,
    opm_col: Optional[str] = None,
    operating_profit_col: Optional[str] = None,
    sales_col: Optional[str] = None,
    min_val: float = -1.0,
    max_val: float = 1.0
) -> List[ValidationFailure]:
    """
    DQ-09: Operating Profit Margin outside expected range.
    
    Checks if OPM (precalculated or computed as Operating Profit / Sales)
    is within the expected bounds (default is -100% to +100%, i.e., -1.0 to 1.0).
    """
    failures = []
    
    # Calculate or get OPM values
    if opm_col and opm_col in df.columns:
        opm_series = pd.to_numeric(df[opm_col], errors='coerce')
        source_col = opm_col
    elif (operating_profit_col and operating_profit_col in df.columns 
          and sales_col and sales_col in df.columns):
        op = pd.to_numeric(df[operating_profit_col], errors='coerce')
        sales = pd.to_numeric(df[sales_col], errors='coerce')
        # Avoid division by zero by replacing zero with NaN
        opm_series = op / sales.replace(0, pd.NA)
        source_col = f"{operating_profit_col}/{sales_col}"
    else:
        # None of the combinations exist
        return failures

    out_of_range = ((opm_series < min_val) | (opm_series > max_val)) & opm_series.notna()

    for idx, row in df[out_of_range].iterrows():
        val = row[opm_col] if (opm_col and opm_col in df.columns) else opm_series[idx]
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-09",
            severity=Severity.WARNING.value,
            table_name=table_name,
            row_number=row_num,
            column_name=source_col,
            failed_value=f"{val:.4f}" if isinstance(val, (int, float)) else str(val),
            error_message=(
                f"Operating Profit Margin is outside the expected "
                f"range [{min_val}, {max_val}]."
            )
        ))
    return failures


def check_balance_sheet_mismatch(
    df: pd.DataFrame,
    assets_col: str,
    liabilities_col: str,
    equity_col: str,
    table_name: str,
    tolerance: float = 1.0
) -> List[ValidationFailure]:
    """
    DQ-10: Balance Sheet mismatch.
    
    Checks if Assets != Liabilities + Equity within a given tolerance.
    """
    failures = []
    cols = [assets_col, liabilities_col, equity_col]
    if not all(col in df.columns for col in cols):
        return failures

    # Fill NaN values with 0 for numerical comparisons
    assets = pd.to_numeric(df[assets_col], errors='coerce').fillna(0)
    liabilities = pd.to_numeric(df[liabilities_col], errors='coerce').fillna(0)
    equity = pd.to_numeric(df[equity_col], errors='coerce').fillna(0)

    # Check rows with mismatch
    diff = (assets - (liabilities + equity)).abs()
    mismatch_mask = diff > tolerance

    # Ensure at least one field was originally present to avoid flagging empty rows
    any_present = df[assets_col].notna() | df[liabilities_col].notna() | df[equity_col].notna()
    mismatch_mask = mismatch_mask & any_present

    for idx, row in df[mismatch_mask].iterrows():
        a_val = row[assets_col]
        l_val = row[liabilities_col]
        e_val = row[equity_col]
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-10",
            severity=Severity.WARNING.value,
            table_name=table_name,
            row_number=row_num,
            column_name=f"{assets_col}, {liabilities_col}, {equity_col}",
            failed_value=f"Assets: {a_val}, Liab: {l_val}, Equity: {e_val}",
            error_message=(
                f"Balance sheet mismatch: Assets ({a_val}) != Liabilities "
                f"({l_val}) + Equity ({e_val}) (diff: {diff[idx]:.2f})."
            )
        ))
    return failures


def check_zero_sales(
    df: pd.DataFrame, 
    sales_col: str, 
    table_name: str
) -> List[ValidationFailure]:
    """
    DQ-11: Sales equal to zero.
    
    Checks if sales/revenue is equal to zero (raises warning).
    """
    failures = []
    if sales_col not in df.columns:
        return failures

    numeric_sales = pd.to_numeric(df[sales_col], errors='coerce')
    zero_mask = (numeric_sales == 0) & numeric_sales.notna()

    for idx, row in df[zero_mask].iterrows():
        val = row[sales_col]
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-11",
            severity=Severity.WARNING.value,
            table_name=table_name,
            row_number=row_num,
            column_name=sales_col,
            failed_value=str(val),
            error_message="Sales is equal to zero."
        ))
    return failures


def check_negative_net_profit(
    df: pd.DataFrame, 
    net_profit_col: str, 
    table_name: str
) -> List[ValidationFailure]:
    """
    DQ-12: Negative Net Profit.
    
    Checks if net profit is negative (raises warning).
    """
    failures = []
    if net_profit_col not in df.columns:
        return failures

    numeric_np = pd.to_numeric(df[net_profit_col], errors='coerce')
    neg_mask = (numeric_np < 0) & numeric_np.notna()

    for idx, row in df[neg_mask].iterrows():
        val = row[net_profit_col]
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-12",
            severity=Severity.WARNING.value,
            table_name=table_name,
            row_number=row_num,
            column_name=net_profit_col,
            failed_value=str(val),
            error_message=f"Net Profit is negative (found value: {val})."
        ))
    return failures


def check_negative_assets(
    df: pd.DataFrame, 
    assets_col: str, 
    table_name: str
) -> List[ValidationFailure]:
    """
    DQ-13: Negative Total Assets.
    
    Checks if total assets are negative (raises warning).
    """
    failures = []
    if assets_col not in df.columns:
        return failures

    numeric_assets = pd.to_numeric(df[assets_col], errors='coerce')
    neg_mask = (numeric_assets < 0) & numeric_assets.notna()

    for idx, row in df[neg_mask].iterrows():
        val = row[assets_col]
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-13",
            severity=Severity.WARNING.value,
            table_name=table_name,
            row_number=row_num,
            column_name=assets_col,
            failed_value=str(val),
            error_message=f"Total Assets are negative (found value: {val})."
        ))
    return failures


def check_future_financial_year(
    df: pd.DataFrame,
    year_col: str,
    table_name: str,
    current_year: Optional[int] = None
) -> List[ValidationFailure]:
    """
    DQ-14: Future financial year.
    
    Checks if the financial year is greater than the current calendar year.
    """
    failures = []
    if year_col not in df.columns:
        return failures

    if current_year is None:
        current_year = datetime.datetime.now().year

    numeric_year = pd.to_numeric(df[year_col], errors='coerce')
    future_mask = (numeric_year > current_year) & numeric_year.notna()

    for idx, row in df[future_mask].iterrows():
        val = row[year_col]
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-14",
            severity=Severity.WARNING.value,
            table_name=table_name,
            row_number=row_num,
            column_name=year_col,
            failed_value=str(val),
            error_message=(
                f"Financial year '{val}' is in the future. "
                f"Current year is {current_year}."
            )
        ))
    return failures


def check_missing_sector(
    df: pd.DataFrame, 
    sector_col: str, 
    table_name: str
) -> List[ValidationFailure]:
    """
    DQ-15: Missing Broad Sector.
    
    Checks if Broad Sector is missing/empty.
    """
    failures = []
    if sector_col not in df.columns:
        return failures

    null_mask = df[sector_col].isna() | (df[sector_col].astype(str).str.strip() == "")
    for idx, row in df[null_mask].iterrows():
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-15",
            severity=Severity.WARNING.value,
            table_name=table_name,
            row_number=row_num,
            column_name=sector_col,
            failed_value=str(row[sector_col]),
            error_message="Broad Sector is missing or empty."
        ))
    return failures


def check_missing_industry(
    df: pd.DataFrame, 
    industry_col: str, 
    table_name: str
) -> List[ValidationFailure]:
    """
    DQ-16: Missing Industry.
    
    Checks if Industry is missing/empty.
    """
    failures = []
    if industry_col not in df.columns:
        return failures

    null_mask = df[industry_col].isna() | (df[industry_col].astype(str).str.strip() == "")
    for idx, row in df[null_mask].iterrows():
        row_num = int(idx) + 1
        failures.append(ValidationFailure(
            rule_id="DQ-16",
            severity=Severity.WARNING.value,
            table_name=table_name,
            row_number=row_num,
            column_name=industry_col,
            failed_value=str(row[industry_col]),
            error_message="Industry is missing or empty."
        ))
    return failures


# -------------------------------------------------------------------------
# DataValidator Class
# -------------------------------------------------------------------------

class DataValidator:
    """
    Main validator class that accumulates data quality failures and exports them.
    """

    def __init__(self) -> None:
        """Initialize the validator with an empty list of failures."""
        self.failures: List[ValidationFailure] = []

    def clear(self) -> None:
        """Clear all accumulated validation failures."""
        self.failures.clear()

    def add_failures(self, failures: List[ValidationFailure]) -> None:
        """Add a list of validation failures to the accumulator."""
        self.failures.extend(failures)

    def get_failures(self) -> List[ValidationFailure]:
        """Return the list of validation failures."""
        return self.failures

    def get_failures_df(self) -> pd.DataFrame:
        """
        Convert accumulated validation failures into a pandas DataFrame.
        
        Returns:
            pd.DataFrame: Contains all failures with correct column names.
        """
        cols = [
            "Rule ID", "Severity", "Table Name", 
            "Row Number", "Column Name", "Failed Value", "Error Message"
        ]
        if not self.failures:
            return pd.DataFrame(columns=cols)

        data = [f.to_dict() for f in self.failures]
        return pd.DataFrame(data)[cols]

    def export_failures(self, output_path: Union[str, Path]) -> None:
        """
        Save all validation failures to a CSV file.
        
        Args:
            output_path: Path where the CSV should be exported.
        """
        path = Path(output_path)
        # Create output directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        df = self.get_failures_df()
        df.to_csv(path, index=False)

    def validate_dataset(
        self,
        df: pd.DataFrame,
        table_name: str,
        pk_cols: Union[str, List[str]],
        year_col: str,
        mandatory_cols: List[str],
        fk_col: Optional[str] = None,
        parent_keys: Optional[Set[Any]] = None,
        parent_table_name: Optional[str] = None,
        sales_col: Optional[str] = None,
        opm_col: Optional[str] = None,
        operating_profit_col: Optional[str] = None,
        assets_col: Optional[str] = None,
        liabilities_col: Optional[str] = None,
        equity_col: Optional[str] = None,
        net_profit_col: Optional[str] = None,
        sector_col: Optional[str] = None,
        industry_col: Optional[str] = None,
        current_year: Optional[int] = None
    ) -> List[ValidationFailure]:
        """
        Validates a dataframe against all standard rules DQ-01 to DQ-16.
        
        Accumulates and returns any failures found.
        """
        failures: List[ValidationFailure] = []

        if df.empty:
            failures.append(ValidationFailure(
                rule_id="DQ-05",  # Use DQ-05 for general schema / mandatory check
                severity=Severity.CRITICAL.value,
                table_name=table_name,
                row_number=0,
                column_name="DataFrame",
                failed_value="Empty DataFrame",
                error_message="The input DataFrame is empty."
            ))
            self.add_failures(failures)
            return failures

        # Critical Rules
        # DQ-01: PK Null
        failures.extend(check_pk_not_null(df, pk_cols, table_name))

        # DQ-02: Duplicate PKs
        failures.extend(check_duplicate_pks(df, pk_cols, table_name))

        # DQ-03: FK Violations
        if fk_col and parent_keys is not None:
            failures.extend(check_foreign_key_violations(
                df, fk_col, parent_keys, parent_table_name or "parent", table_name
            ))

        # DQ-04: Missing year
        failures.extend(check_missing_financial_year(df, year_col, table_name))

        # DQ-05: Missing mandatory
        failures.extend(check_missing_mandatory_fields(df, mandatory_cols, table_name))

        # DQ-06: Negative sales
        if sales_col:
            failures.extend(check_negative_sales(df, sales_col, table_name))

        # DQ-07: Invalid ticker
        ticker_col = pk_cols if isinstance(pk_cols, str) else pk_cols[0]
        failures.extend(check_invalid_ticker(df, ticker_col, table_name))

        # DQ-08: Duplicate Company-Year
        failures.extend(check_duplicate_company_year(df, ticker_col, year_col, table_name))

        # Warning Rules
        # DQ-09: OPM out of range
        failures.extend(check_opm_out_of_range(
            df=df,
            table_name=table_name,
            opm_col=opm_col,
            operating_profit_col=operating_profit_col,
            sales_col=sales_col
        ))

        # DQ-10: Balance Sheet mismatch
        if assets_col and liabilities_col and equity_col:
            failures.extend(check_balance_sheet_mismatch(
                df, assets_col, liabilities_col, equity_col, table_name
            ))

        # DQ-11: Sales equal to zero
        if sales_col:
            failures.extend(check_zero_sales(df, sales_col, table_name))

        # DQ-12: Negative net profit
        if net_profit_col:
            failures.extend(check_negative_net_profit(df, net_profit_col, table_name))

        # DQ-13: Negative total assets
        if assets_col:
            failures.extend(check_negative_assets(df, assets_col, table_name))

        # DQ-14: Future financial year
        failures.extend(check_future_financial_year(df, year_col, table_name, current_year))

        # DQ-15: Missing Sector
        if sector_col:
            failures.extend(check_missing_sector(df, sector_col, table_name))

        # DQ-16: Missing Industry
        if industry_col:
            failures.extend(check_missing_industry(df, industry_col, table_name))

        self.add_failures(failures)
        return failures

if __name__ == "__main__":
    from pathlib import Path
    import pandas as pd

    # Input file (change this to your processed dataset)
    input_file = Path("data/processed/companies.csv")

    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        exit()

    # Load dataset
    df = pd.read_csv(input_file)

    validator = DataValidator()

    # Run validation
    validator.validate_dataset(
        df=df,
        table_name="companies",
        pk_cols="ticker",               # Change if your PK is different
        year_col="year",
        mandatory_cols=["ticker", "year"],
        sales_col="sales",
        opm_col="opm_percentage",
        assets_col="total_assets",
        liabilities_col="total_liabilities",
        equity_col="equity",
        net_profit_col="net_profit",
        sector_col="broad_sector",
        industry_col="industry"
    )

    # Export results
    output_file = Path("data/output/validation_failures.csv")
    validator.export_failures(output_file)

    print("=" * 50)
    print("Validation Completed")
    print(f"Total Failures: {len(validator.get_failures())}")
    print(f"Report saved to: {output_file}")
    print("=" * 50)

