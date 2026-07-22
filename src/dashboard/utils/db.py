"""
Database Utility Module for Nifty 100 Analytics Dashboard.

Provides cached access (@st.cache_data(ttl=600)) to nifty100.db.
All functions return Pandas DataFrames and gracefully handle database errors.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Union
import pandas as pd
import streamlit as st

logger = logging.getLogger("dashboard_db")


def get_db_path() -> Path:
    """Resolve the path to nifty100.db database file."""
    current_dir = Path(__file__).resolve().parent
    candidates = [
        current_dir.parents[2] / "data" / "db" / "nifty100.db",
        current_dir.parents[1] / "data" / "db" / "nifty100.db",
        Path.cwd() / "data" / "db" / "nifty100.db",
        Path("data/db/nifty100.db").resolve()
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path.cwd() / "data" / "db" / "nifty100.db"


def run_query(query: str, params: tuple = ()) -> pd.DataFrame:
    """Execute SQL query safely and return DataFrame."""
    db_path = get_db_path()
    if not db_path.exists():
        logger.error(f"Database file not found at {db_path}")
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        logger.error(f"Error executing database query: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    """
    Fetch all companies with optional sector mapping.
    Returns Pandas DataFrame with company info.
    """
    query = """
    SELECT c.*, s.broad_sector, s.sub_sector, s.index_weight_pct, s.market_cap_category
    FROM companies c
    LEFT JOIN sectors s ON c.id = s.company_id
    ORDER BY c.company_name ASC
    """
    df = run_query(query)
    if df.empty:
        df = run_query("SELECT * FROM companies ORDER BY company_name ASC")
    return df


@st.cache_data(ttl=600)
def get_ratios(ticker: Optional[str] = None, year: Optional[Union[str, int]] = None) -> pd.DataFrame:
    """
    Fetch financial ratios for a given ticker or all companies, optionally filtered by year.
    Returns Pandas DataFrame.
    """
    query = "SELECT * FROM financial_ratios WHERE 1=1"
    params = []
    if ticker:
        query += " AND (company_id = ? OR company_id = ?)"
        params.extend([str(ticker).upper(), str(ticker)])
    if year is not None and str(year).strip() != "":
        query += " AND year = ?"
        params.append(str(year))
    query += " ORDER BY year ASC"
    return run_query(query, tuple(params))


@st.cache_data(ttl=600)
def get_pl(ticker: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch Profit & Loss statement for a ticker or all companies.
    Returns Pandas DataFrame.
    """
    if ticker:
        query = "SELECT * FROM profitandloss WHERE company_id = ? OR company_id = ? ORDER BY year ASC"
        return run_query(query, (str(ticker).upper(), str(ticker)))
    else:
        return run_query("SELECT * FROM profitandloss ORDER BY company_id, year ASC")


@st.cache_data(ttl=600)
def get_bs(ticker: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch Balance Sheet statement for a ticker or all companies.
    Returns Pandas DataFrame.
    """
    if ticker:
        query = "SELECT * FROM balancesheet WHERE company_id = ? OR company_id = ? ORDER BY year ASC"
        return run_query(query, (str(ticker).upper(), str(ticker)))
    else:
        return run_query("SELECT * FROM balancesheet ORDER BY company_id, year ASC")


@st.cache_data(ttl=600)
def get_cf(ticker: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch Cash Flow statement for a ticker or all companies.
    Returns Pandas DataFrame.
    """
    if ticker:
        query = "SELECT * FROM cashflow WHERE company_id = ? OR company_id = ? ORDER BY year ASC"
        return run_query(query, (str(ticker).upper(), str(ticker)))
    else:
        return run_query("SELECT * FROM cashflow ORDER BY company_id, year ASC")


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    """
    Fetch sector information for all companies.
    Returns Pandas DataFrame.
    """
    query = """
    SELECT s.*, c.company_name
    FROM sectors s
    LEFT JOIN companies c ON s.company_id = c.id
    ORDER BY s.broad_sector, c.company_name ASC
    """
    df = run_query(query)
    if df.empty:
        df = run_query("SELECT * FROM sectors")
    return df


@st.cache_data(ttl=600)
def get_peers(group_name: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch peer groups information. If group_name is specified, filters by group_name.
    Returns Pandas DataFrame.
    """
    if group_name and str(group_name).strip() != "":
        query = """
        SELECT pg.*, c.company_name, s.broad_sector
        FROM peer_groups pg
        LEFT JOIN companies c ON pg.company_id = c.id
        LEFT JOIN sectors s ON pg.company_id = s.company_id
        WHERE pg.peer_group_name = ?
        """
        df = run_query(query, (group_name,))
        if df.empty:
            df = run_query("SELECT * FROM peer_groups WHERE peer_group_name = ?", (group_name,))
        return df
    else:
        query = """
        SELECT pg.*, c.company_name, s.broad_sector
        FROM peer_groups pg
        LEFT JOIN companies c ON pg.company_id = c.id
        LEFT JOIN sectors s ON pg.company_id = s.company_id
        """
        df = run_query(query)
        if df.empty:
            df = run_query("SELECT * FROM peer_groups")
        return df


@st.cache_data(ttl=600)
def get_valuation(ticker: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch valuation metrics (market cap, P/E, P/B, EV/EBITDA, dividend yield) for a ticker or all companies.
    Returns Pandas DataFrame.
    """
    if ticker:
        query = "SELECT * FROM market_cap WHERE company_id = ? OR company_id = ? ORDER BY year ASC"
        return run_query(query, (str(ticker).upper(), str(ticker)))
    else:
        return run_query("SELECT * FROM market_cap ORDER BY company_id, year ASC")
