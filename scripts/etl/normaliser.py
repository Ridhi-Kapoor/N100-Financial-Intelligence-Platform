import re

def normalize_year(value):
    """
    Convert values like FY20, FY2020, 2020-21 into 2020.
    """
    if value is None:
        return None

    value = str(value).strip().upper()

    match = re.search(r'(20\d{2})', value)
    if match:
        return int(match.group(1))

    match = re.search(r'FY(\d{2})', value)
    if match:
        return 2000 + int(match.group(1))

    return None


def normalize_ticker(ticker):
    """
    Convert ticker symbols to standard format.
    """
    if ticker is None:
        return None

    ticker = ticker.strip().upper()

    if ticker.endswith(".NS"):
        ticker = ticker[:-3]

    return ticker