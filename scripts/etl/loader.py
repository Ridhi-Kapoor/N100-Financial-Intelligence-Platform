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

        output_file = processed_folder / f"{file.stem}.csv"

        save_processed(df, output_file)

        print(f"Saved: {output_file}")

    print("\nAll datasets processed successfully!")


if __name__ == "__main__":
    process_all_files()