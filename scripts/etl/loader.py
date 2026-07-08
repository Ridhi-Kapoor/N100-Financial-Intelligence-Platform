import pandas as pd
from pathlib import Path


def load_excel(file_path, sheet_name=0):
    """Load an Excel file and return a DataFrame."""
    return pd.read_excel(file_path, sheet_name=sheet_name)


def validate_dataframe(df):
    """Basic validation for loaded data."""
    if df.empty:
        raise ValueError("Loaded DataFrame is empty.")
    return True


def save_processed(df, output_path):
    """Save cleaned DataFrame."""
    df.to_csv(output_path, index=False)


def normalize_dataframe(df, file_name):
    """Normalize ticker and year columns in-place in the DataFrame."""
    # Import normaliser functions
    from scripts.etl.normaliser import normalize_ticker, normalize_year
    
    if df.empty:
        return df

    # Convert the entire DataFrame to object dtype to prevent strict type constraints
    df = df.astype(object)

    # Detect header row index. If the first cell of the first column is "id"
    # there is no title row. Otherwise, row 0 is headers and data starts from row 1.
    first_col = df.columns[0]
    if str(first_col).strip().lower() == 'id':
        actual_headers = [str(col).strip() for col in df.columns]
        header_row_idx = None
        start_data_idx = 0
    else:
        actual_headers = [str(x).strip() for x in df.iloc[0]]
        header_row_idx = 0
        start_data_idx = 1

    # Check for ticker column
    ticker_col_idx = None
    if file_name == 'companies.xlsx':
        if 'id' in actual_headers:
            ticker_col_idx = actual_headers.index('id')
    else:
        if 'company_id' in actual_headers:
            ticker_col_idx = actual_headers.index('company_id')

    # Check for year column
    year_col_idx = None
    if 'year' in actual_headers:
        year_col_idx = actual_headers.index('year')

    # Apply normalization to the rows
    for r_idx in range(start_data_idx, len(df)):
        if ticker_col_idx is not None:
            raw_ticker = df.iloc[r_idx, ticker_col_idx]
            if pd.notna(raw_ticker):
                df.iloc[r_idx, ticker_col_idx] = str(normalize_ticker(str(raw_ticker)))

        if year_col_idx is not None:
            raw_year = df.iloc[r_idx, year_col_idx]
            if pd.notna(raw_year):
                norm_yr = normalize_year(raw_year)
                # Keep original string if normalization returns None but input was non-empty (like TTM)
                if norm_yr is not None:
                    df.iloc[r_idx, year_col_idx] = str(norm_yr)

    # Special cleaning for market_cap where year must be integer
    if file_name == 'market_cap.xlsx' and year_col_idx is not None:
        for r_idx in range(start_data_idx, len(df)):
            val = df.iloc[r_idx, year_col_idx]
            if pd.notna(val):
                try:
                    df.iloc[r_idx, year_col_idx] = int(float(val))
                except (ValueError, TypeError):
                    pass

    return df


def process_all_files():
    raw_folder = Path("data/raw")
    processed_folder = Path("data/processed")

    processed_folder.mkdir(parents=True, exist_ok=True)

    excel_files = list(raw_folder.glob("*.xlsx"))

    if not excel_files:
        print("No Excel files found in data/raw/")
        return

    for file in excel_files:
        print(f"Processing {file.name}...")

        df = load_excel(file)

        validate_dataframe(df)

        # Normalize the DataFrame in-place before saving
        df = normalize_dataframe(df, file.name)

        output_file = processed_folder / f"{file.stem}.csv"

        save_processed(df, output_file)

        print(f"Saved: {output_file}")

    print("\nAll datasets processed successfully!")


if __name__ == "__main__":
    process_all_files()