import pandas as pd

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