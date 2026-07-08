import re

def normalize_year(value):
    """
    Convert values like FY20, FY2020, 2020-21, Mar-13, Mar 2013 into 2020.
    Preserves TTM as a valid financial year label.
    """
    if value is None or str(value).strip() == "":
        return None

    value_str = str(value).strip().upper()

    # Match 4-digit years like 2020, Mar 2020, FY2020, etc.
    match = re.search(r'(20\d{2})', value_str)
    if match:
        return int(match.group(1))

    # Match FY20 or similar 2-digit financial years
    match = re.search(r'FY(\d{2})', value_str)
    if match:
        return 2000 + int(match.group(1))

    # Match formats like Mar-13 or 13-Mar
    match = re.search(r'-(\d{2})$', value_str)
    if match:
        return 2000 + int(match.group(1))
    
    match = re.search(r'^(\d{2})-', value_str)
    if match:
        return 2000 + int(match.group(1))

    # Preserve TTM
    if value_str == "TTM":
        return "TTM"

    return None


def normalize_ticker(ticker):
    """
    Convert ticker symbols to standard format, resolving known typos.
    """
    if ticker is None:
        return None

    ticker = ticker.strip().upper()

    if ticker.endswith(".NS"):
        ticker = ticker[:-3]

    # Map known ticker typos/inconsistencies
    if ticker == "AGTL":
        ticker = "ATGL"

    return ticker