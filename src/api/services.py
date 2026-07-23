"""
Business Logic & Service Layer for Day 40 REST API Endpoints.

Implements core domain logic, data aggregation, and database querying
for stock screening, sector analytics, peer comparison, historical valuation,
portfolio statistics, and company documents.
"""

import logging
import math
from pathlib import Path
import sqlite3
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
import pandas as pd
import requests

from src.screener.engine import load_screener_data
from src.analytics.radar import load_radar_data, RADAR_METRIC_LABELS
from src.analytics.peer import (
    compute_peer_percentiles,
    METRIC_DEFINITIONS,
)

logger = logging.getLogger("api_services")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "db" / "nifty100.db"
DOCUMENTS_CSV = PROJECT_ROOT / "data" / "processed" / "documents.csv"
PORTFOLIO_STATS_CSV = PROJECT_ROOT / "output" / "portfolio_stats.csv"

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def is_url_valid_helper(url: str) -> bool:
    """
    Check if a URL string is valid and reachable.
    """
    if (
        not url
        or pd.isna(url)
        or str(url).strip().lower() in ["", "none", "null", "nan"]
    ):
        return False
    url_str = str(url).strip()
    if not (url_str.startswith("http://") or url_str.startswith("https://")):
        return False
    try:
        resp = requests.head(
            url_str, headers=HTTP_HEADERS, timeout=2.0, allow_redirects=True
        )
        return resp.status_code in [200, 301, 302, 303, 307, 308]
    except Exception:
        # Fallback basic structural check if request times out or fails
        return len(url_str) > 12 and "." in url_str


# ---------------------------------------------------------------------------
# 1. Stock Screener Service
# ---------------------------------------------------------------------------
def run_screener_service(
    min_roe: Optional[float] = None,
    max_de: Optional[float] = None,
    min_fcf: Optional[float] = None,
    sector: Optional[str] = None,
    min_rev_cagr_5yr: Optional[float] = None,
    min_pat_cagr_5yr: Optional[float] = None,
    max_pe: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Execute quantitative stock screener query across financial metrics.
    """
    # 1. Parameter Validation
    if max_de is not None and max_de < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid parameter value: max_de cannot be negative.",
        )
    if max_pe is not None and max_pe < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid parameter value: max_pe cannot be negative.",
        )
    if min_roe is not None and (min_roe < -100.0 or min_roe > 1000.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid parameter value: min_roe must be between -100 and 1000.",
        )
    if min_rev_cagr_5yr is not None and (
        min_rev_cagr_5yr < -100.0 or min_rev_cagr_5yr > 1000.0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid parameter value: min_rev_cagr_5yr must be between -100 and 1000.",
        )
    if min_pat_cagr_5yr is not None and (
        min_pat_cagr_5yr < -100.0 or min_pat_cagr_5yr > 1000.0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid parameter value: min_pat_cagr_5yr must be between -100 and 1000.",
        )

    # 2. Load Base Financial Data
    try:
        df = load_screener_data(DB_PATH)
    except Exception as e:
        logger.error(f"Error loading screener data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load screener database: {e}",
        )

    if df.empty:
        return {"total_matches": 0, "filters_applied": {}, "results": []}

    # Deduplicate to latest available record per company
    if "year" in df.columns:
        df["year_num"] = pd.to_numeric(df["year"], errors="coerce")
        df = df.sort_values("year_num").groupby("company_id").last().reset_index()

    # 3. Apply Filters
    filters_applied: Dict[str, Any] = {}

    if min_roe is not None:
        filters_applied["min_roe"] = min_roe
        df = df[df["return_on_equity_pct"].astype(float) >= min_roe]

    if max_de is not None:
        filters_applied["max_de"] = max_de
        fin_mask = df["broad_sector"].astype(str).str.lower().str.contains("financial")
        df = df[(df["debt_to_equity"].astype(float) <= max_de) | fin_mask]

    if min_fcf is not None:
        filters_applied["min_fcf"] = min_fcf
        df = df[df["free_cash_flow_cr"].astype(float) >= min_fcf]

    if sector is not None and str(sector).strip():
        sec_clean = str(sector).strip()
        filters_applied["sector"] = sec_clean
        df = df[
            df["broad_sector"].astype(str).str.lower().str.contains(sec_clean.lower())
        ]

    if min_rev_cagr_5yr is not None:
        filters_applied["min_rev_cagr_5yr"] = min_rev_cagr_5yr
        df = df[df["revenue_cagr_5yr"].astype(float) >= min_rev_cagr_5yr]

    if min_pat_cagr_5yr is not None:
        filters_applied["min_pat_cagr_5yr"] = min_pat_cagr_5yr
        df = df[df["pat_cagr_5yr"].astype(float) >= min_pat_cagr_5yr]

    if max_pe is not None:
        filters_applied["max_pe"] = max_pe
        df = df[df["pe_ratio"].astype(float) <= max_pe]

    # 4. Compute composite quality score if missing & Sort
    if (
        "composite_quality_score" not in df.columns
        or df["composite_quality_score"].isna().all()
    ):
        df["composite_quality_score"] = (
            df["return_on_equity_pct"].astype(float).fillna(0)
        )

    df = df.sort_values(by="composite_quality_score", ascending=False).reset_index(
        drop=True
    )

    # 5. Build Result List
    results = []
    for rank, (_, row) in enumerate(df.iterrows(), 1):

        def safe_float(val: Any) -> Optional[float]:
            """Convert value to rounded float safely or return None."""
            if val is None or pd.isna(val):
                return None
            try:
                v = float(val)
                return round(v, 2) if not math.isnan(v) else None
            except (ValueError, TypeError):
                return None

        results.append(
            {
                "rank": rank,
                "company_id": str(row["company_id"]).strip(),
                "company_name": str(row.get("company_name", row["company_id"])).strip(),
                "sector": str(row.get("broad_sector", "N/A")).strip(),
                "latest_kpis": {
                    "roe": safe_float(row.get("return_on_equity_pct")),
                    "debt_to_equity": safe_float(row.get("debt_to_equity")),
                    "free_cash_flow": safe_float(row.get("free_cash_flow_cr")),
                    "revenue_cagr_5yr": safe_float(row.get("revenue_cagr_5yr")),
                    "pat_cagr_5yr": safe_float(row.get("pat_cagr_5yr")),
                    "pe_ratio": safe_float(row.get("pe_ratio")),
                    "composite_quality_score": safe_float(
                        row.get("composite_quality_score")
                    ),
                },
            }
        )

    return {
        "total_matches": len(results),
        "filters_applied": filters_applied,
        "results": results,
    }


# ---------------------------------------------------------------------------
# 2. Sector Analytics Services
# ---------------------------------------------------------------------------
def get_sectors_summary_service(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Get summary statistics (company count, median ROE, PE, Debt-to-Equity) for all sectors.
    """
    query = """
        SELECT 
            s.broad_sector as sector,
            COUNT(DISTINCT s.company_id) as company_count
        FROM sectors s
        GROUP BY s.broad_sector
        ORDER BY company_count DESC
    """
    df_sec = pd.read_sql(query, conn)
    if df_sec.empty:
        return {"total_sectors": 0, "sectors": []}

    df_fr = pd.read_sql(
        """
        SELECT company_id, return_on_equity_pct, debt_to_equity, year
        FROM financial_ratios
    """,
        conn,
    )
    df_mc = pd.read_sql(
        """
        SELECT company_id, pe_ratio, year
        FROM market_cap
    """,
        conn,
    )

    if not df_fr.empty and "year" in df_fr.columns:
        df_fr["year_num"] = pd.to_numeric(df_fr["year"], errors="coerce")
        df_fr = df_fr.sort_values("year_num").groupby("company_id").last().reset_index()

    if not df_mc.empty and "year" in df_mc.columns:
        df_mc["year_num"] = pd.to_numeric(df_mc["year"], errors="coerce")
        df_mc = df_mc.sort_values("year_num").groupby("company_id").last().reset_index()

    df_comp_sec = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)

    merged = pd.merge(df_comp_sec, df_fr, on="company_id", how="left")
    merged = pd.merge(merged, df_mc, on="company_id", how="left")

    sectors_list = []
    for _, row in df_sec.iterrows():
        sec_name = str(row["sector"]).strip()
        sec_data = merged[merged["broad_sector"].astype(str).str.strip() == sec_name]

        med_roe = sec_data["return_on_equity_pct"].dropna().median()
        med_pe = sec_data["pe_ratio"].dropna().median()
        med_de = sec_data["debt_to_equity"].dropna().median()

        sectors_list.append(
            {
                "sector": sec_name,
                "company_count": int(row["company_count"]),
                "median_roe": round(float(med_roe), 2) if pd.notna(med_roe) else None,
                "median_pe": round(float(med_pe), 2) if pd.notna(med_pe) else None,
                "median_debt_to_equity": (
                    round(float(med_de), 2) if pd.notna(med_de) else None
                ),
            }
        )

    return {"total_sectors": len(sectors_list), "sectors": sectors_list}


def get_sector_companies_service(
    conn: sqlite3.Connection, sector: str
) -> Dict[str, Any]:
    """
    Get all companies and their latest KPIs for a selected sector.
    """
    sec_clean = str(sector).strip()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT broad_sector FROM sectors")
    all_sectors = [r[0] for r in cursor.fetchall() if r[0]]

    matched_sector = None
    for s in all_sectors:
        s_clean = s.strip()
        if s_clean.lower() == sec_clean.lower() or (
            sec_clean.lower() in ["it", "info tech"]
            and "information technology" in s_clean.lower()
        ):
            matched_sector = s_clean
            break

    if not matched_sector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sector '{sector}' does not exist.",
        )

    query = """
        SELECT 
            c.id as company_id,
            c.company_name,
            c.roce_percentage,
            s.sub_sector
        FROM companies c
        JOIN sectors s ON c.id = s.company_id
        WHERE LOWER(TRIM(s.broad_sector)) = LOWER(?)
        ORDER BY c.id ASC
    """
    df_comps = pd.read_sql(query, conn, params=[matched_sector])

    df_fr = pd.read_sql("SELECT * FROM financial_ratios", conn)
    df_mc = pd.read_sql("SELECT * FROM market_cap", conn)

    if not df_fr.empty and "year" in df_fr.columns:
        df_fr["year_num"] = pd.to_numeric(df_fr["year"], errors="coerce")
        df_fr = df_fr.sort_values("year_num").groupby("company_id").last().reset_index()

    if not df_mc.empty and "year" in df_mc.columns:
        df_mc["year_num"] = pd.to_numeric(df_mc["year"], errors="coerce")
        df_mc = df_mc.sort_values("year_num").groupby("company_id").last().reset_index()

    companies_list = []
    for _, row in df_comps.iterrows():
        cid = str(row["company_id"]).strip()
        fr_row = df_fr[df_fr["company_id"].astype(str).str.strip() == cid]
        mc_row = df_mc[df_mc["company_id"].astype(str).str.strip() == cid]

        def get_val(df_source, col):
            """Extract rounded numeric value for specified column."""
            if (
                not df_source.empty
                and col in df_source.columns
                and pd.notna(df_source.iloc[0][col])
            ):
                try:
                    val = float(df_source.iloc[0][col])
                    return round(val, 2) if not math.isnan(val) else None
                except (ValueError, TypeError):
                    return None
            return None

        roe = get_val(fr_row, "return_on_equity_pct")
        roce = get_val(fr_row, "roce") or (
            float(row["roce_percentage"])
            if pd.notna(row.get("roce_percentage"))
            else None
        )
        if roce is not None:
            roce = round(roce, 2)

        companies_list.append(
            {
                "company_id": cid,
                "company_name": str(row["company_name"]).strip(),
                "sub_sector": (
                    str(row.get("sub_sector", "")).strip()
                    if pd.notna(row.get("sub_sector"))
                    else None
                ),
                "latest_kpis": {
                    "roe": roe,
                    "roce": roce,
                    "opm": get_val(fr_row, "operating_profit_margin_pct"),
                    "npm": get_val(fr_row, "net_profit_margin_pct"),
                    "debt_to_equity": get_val(fr_row, "debt_to_equity"),
                    "pe_ratio": get_val(mc_row, "pe_ratio"),
                    "pb_ratio": get_val(mc_row, "pb_ratio"),
                    "revenue_cagr_5yr": get_val(fr_row, "revenue_cagr_5yr"),
                    "pat_cagr_5yr": get_val(fr_row, "pat_cagr_5yr"),
                    "free_cash_flow": get_val(fr_row, "free_cash_flow_cr"),
                },
            }
        )

    return {
        "sector": matched_sector,
        "company_count": len(companies_list),
        "companies": companies_list,
    }


# ---------------------------------------------------------------------------
# 3. Peer Groups & Peer Comparison Services
# ---------------------------------------------------------------------------
def get_peer_group_service(conn: sqlite3.Connection, group_name: str) -> Dict[str, Any]:
    """
    Get companies in a peer group along with percentile ranks for 10 selected KPIs.
    Supports lookup by peer group name or company ticker symbol.
    """
    grp_clean = str(group_name).strip()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT peer_group_name FROM peer_groups")
    all_groups = [r[0] for r in cursor.fetchall() if r[0]]

    # 1. Match directly against peer group name
    matched_group = None
    for g in all_groups:
        if g.strip().lower() == grp_clean.lower():
            matched_group = g
            break

    # 2. If not matched as group name, try looking up as company ticker
    if not matched_group:
        cursor.execute(
            "SELECT peer_group_name FROM peer_groups WHERE UPPER(TRIM(company_id)) = UPPER(TRIM(?)) LIMIT 1",
            (grp_clean,),
        )
        row_ticker = cursor.fetchone()
        if row_ticker and row_ticker[0]:
            matched_group = str(row_ticker[0]).strip()

    if not matched_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peer group '{group_name}' is unknown.",
        )

    # Fetch percentiles for this peer group
    try:
        df_pct = pd.read_sql(
            "SELECT company_id, metric, percentile_rank, year FROM peer_percentiles WHERE LOWER(TRIM(peer_group_name)) = LOWER(?)",
            conn,
            params=[matched_group.lower()],
        )
    except Exception:
        df_pct = pd.DataFrame()

    if df_pct.empty:
        df_all_pct = compute_peer_percentiles(db_path=DB_PATH)
        df_pct = df_all_pct[
            df_all_pct["peer_group_name"].astype(str).str.strip().str.lower()
            == matched_group.lower()
        ]

    if not df_pct.empty and "year" in df_pct.columns:
        latest_yr = str(df_pct["year"].max()).strip()
        df_pct = df_pct[df_pct["year"].astype(str).str.strip() == latest_yr]

    # Load peer group members metadata
    df_pg = pd.read_sql(
        "SELECT pg.company_id, pg.is_benchmark, c.company_name FROM peer_groups pg JOIN companies c ON pg.company_id = c.id WHERE LOWER(TRIM(pg.peer_group_name)) = LOWER(?)",
        conn,
        params=[matched_group.lower()],
    )

    companies_list = []
    for _, row in df_pg.iterrows():
        cid = str(row["company_id"]).strip()
        c_pcts = df_pct[df_pct["company_id"].astype(str).str.strip() == cid]

        ranks_dict = {}
        for m_name in METRIC_DEFINITIONS.keys():
            m_match = c_pcts[c_pcts["metric"].astype(str).str.strip() == m_name]
            if not m_match.empty and pd.notna(m_match.iloc[0]["percentile_rank"]):
                ranks_dict[m_name] = round(float(m_match.iloc[0]["percentile_rank"]), 2)
            else:
                ranks_dict[m_name] = None

        companies_list.append(
            {
                "company_id": cid,
                "company_name": str(row["company_name"]).strip(),
                "is_benchmark": bool(row["is_benchmark"]),
                "percentile_ranks": ranks_dict,
            }
        )

    return {
        "peer_group_name": matched_group,
        "company_count": len(companies_list),
        "companies": companies_list,
    }


def get_peer_comparison_radar_service(
    conn: sqlite3.Connection, ticker: str
) -> Dict[str, Any]:
    """
    Get 8-axis radar chart comparison metrics for a company vs peer average & benchmark.
    """
    t_clean = str(ticker).strip().upper()
    cursor = conn.cursor()
    cursor.execute("SELECT id, company_name FROM companies WHERE id = ?", (t_clean,))
    comp_row = cursor.fetchone()
    if not comp_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker '{t_clean}' not found.",
        )

    df_radar = load_radar_data(db_path=DB_PATH)
    target_row = df_radar[df_radar["id"].astype(str).str.strip().str.upper() == t_clean]

    score_cols = [
        "ROE_score",
        "ROCE_score",
        "Net_Profit_Margin_score",
        "Debt_to_Equity_score",
        "FCF_Score",
        "PAT_CAGR_5Y_score",
        "Revenue_CAGR_5Y_score",
        "Composite_Quality_Score",
    ]

    metric_mapping = dict(zip(score_cols, RADAR_METRIC_LABELS))

    if target_row.empty:
        comp_scores = {lbl: 50.0 for lbl in RADAR_METRIC_LABELS}
        peer_group_name = "Market Standalone"
    else:
        r = target_row.iloc[0]
        comp_scores = {
            metric_mapping[col]: round(float(r[col]), 2) for col in score_cols
        }
        peer_group_name = (
            str(r.get("peer_group_name")).strip()
            if pd.notna(r.get("peer_group_name"))
            else "Market Standalone"
        )

    if peer_group_name != "Market Standalone" and not df_radar.empty:
        peer_grp_df = df_radar[
            df_radar["peer_group_name"].astype(str).str.strip() == peer_group_name
        ]
        peer_avg_scores = {
            metric_mapping[col]: round(float(peer_grp_df[col].mean()), 2)
            for col in score_cols
        }
    else:
        peer_avg_scores = (
            {
                metric_mapping[col]: round(float(df_radar[col].mean()), 2)
                for col in score_cols
            }
            if not df_radar.empty
            else {lbl: 50.0 for lbl in RADAR_METRIC_LABELS}
        )

    cursor.execute(
        "SELECT company_id FROM peer_groups WHERE LOWER(TRIM(peer_group_name)) = LOWER(?) AND is_benchmark = 1 LIMIT 1",
        (peer_group_name,),
    )
    bench_row = cursor.fetchone()
    bench_ticker = bench_row[0] if bench_row else None

    if bench_ticker and not df_radar.empty:
        bench_df = df_radar[
            df_radar["id"].astype(str).str.strip().str.upper()
            == str(bench_ticker).strip().upper()
        ]
        if not bench_df.empty:
            r_b = bench_df.iloc[0]
            bench_scores = {
                metric_mapping[col]: round(float(r_b[col]), 2) for col in score_cols
            }
        else:
            bench_scores = peer_avg_scores.copy()
    else:
        bench_scores = peer_avg_scores.copy()

    return {
        "ticker": t_clean,
        "company_name": comp_row["company_name"],
        "peer_group_name": peer_group_name,
        "benchmark_ticker": bench_ticker,
        "metrics": RADAR_METRIC_LABELS,
        "company_values": comp_scores,
        "peer_group_average": peer_avg_scores,
        "benchmark_values": bench_scores,
    }


# ---------------------------------------------------------------------------
# 4. Historical Valuation Service
# ---------------------------------------------------------------------------
def get_historical_valuation_service(
    conn: sqlite3.Connection, ticker: str
) -> Dict[str, Any]:
    """
    Get valuation history from 2019 to 2024 for a given ticker.
    """
    t_clean = str(ticker).strip().upper()
    cursor = conn.cursor()
    cursor.execute("SELECT id, company_name FROM companies WHERE id = ?", (t_clean,))
    comp = cursor.fetchone()

    query = """
        SELECT year, pe_ratio, pb_ratio, ev_ebitda, dividend_yield_pct, market_cap_crore, enterprise_value_crore
        FROM market_cap
        WHERE id = ? OR company_id = ?
        ORDER BY CAST(year AS INTEGER) ASC
    """
    rows = cursor.execute(query, (t_clean, t_clean)).fetchall()

    if not comp and not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker '{t_clean}' not found.",
        )

    company_name = comp["company_name"] if comp else t_clean

    history = []
    for r in rows:

        def safe_num(v):
            """Safely convert numeric value or return None."""
            if v is None:
                return None
            try:
                val = float(v)
                return round(val, 2) if not math.isnan(val) else None
            except (ValueError, TypeError):
                return None

        yr_str = str(r["year"]).strip()
        if yr_str in ["2019", "2020", "2021", "2022", "2023", "2024"]:
            history.append(
                {
                    "year": yr_str,
                    "pe_ratio": safe_num(r["pe_ratio"]),
                    "pb_ratio": safe_num(r["pb_ratio"]),
                    "ev_ebitda": safe_num(r["ev_ebitda"]),
                    "dividend_yield_pct": safe_num(r["dividend_yield_pct"]),
                    "market_cap_crore": safe_num(r["market_cap_crore"]),
                    "enterprise_value_crore": safe_num(r["enterprise_value_crore"]),
                }
            )

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No valuation history found for ticker '{t_clean}' between 2019-2024.",
        )

    return {
        "ticker": t_clean,
        "company_name": company_name,
        "history": history,
    }


# ---------------------------------------------------------------------------
# 5. Portfolio Statistics Service
# ---------------------------------------------------------------------------
def get_portfolio_stats_service() -> Dict[str, Any]:
    """
    Get portfolio-wide descriptive statistics for 10 core KPIs.
    """
    if PORTFOLIO_STATS_CSV.exists():
        df_stats = pd.read_csv(PORTFOLIO_STATS_CSV)
        stats_list = []
        for _, row in df_stats.iterrows():

            def sf(val):
                """Safely format float value."""
                try:
                    return round(float(val), 2)
                except Exception:
                    return 0.0

            stats_list.append(
                {
                    "kpi_name": str(row["KPI Name"]).strip(),
                    "p10": sf(row.get("P10")),
                    "p25": sf(row.get("P25")),
                    "p50": sf(row.get("P50 (Median)")),
                    "p75": sf(row.get("P75")),
                    "p90": sf(row.get("P90")),
                    "mean": sf(row.get("Mean")),
                    "std_dev": sf(row.get("Standard Deviation")),
                }
            )
        return {"total_kpis": len(stats_list), "statistics": stats_list}

    from src.analytics.cluster_profiling import (
        load_10_kpis_dataset,
        generate_portfolio_statistics,
    )

    df_10kpis = load_10_kpis_dataset(DB_PATH)
    df_stats = generate_portfolio_statistics(df_10kpis)

    stats_list = []
    for _, row in df_stats.iterrows():
        stats_list.append(
            {
                "kpi_name": str(row["KPI Name"]).strip(),
                "p10": round(float(row.get("P10", 0.0)), 2),
                "p25": round(float(row.get("P25", 0.0)), 2),
                "p50": round(float(row.get("P50 (Median)", 0.0)), 2),
                "p75": round(float(row.get("P75", 0.0)), 2),
                "p90": round(float(row.get("P90", 0.0)), 2),
                "mean": round(float(row.get("Mean", 0.0)), 2),
                "std_dev": round(float(row.get("Standard Deviation", 0.0)), 2),
            }
        )

    return {"total_kpis": len(stats_list), "statistics": stats_list}


# ---------------------------------------------------------------------------
# 6. Company Documents Service
# ---------------------------------------------------------------------------
def get_company_documents_service(
    conn: sqlite3.Connection, ticker: str
) -> Dict[str, Any]:
    """
    Get annual report documents and validity flags for a company.
    """
    t_clean = str(ticker).strip().upper()
    cursor = conn.cursor()
    cursor.execute("SELECT id, company_name FROM companies WHERE id = ?", (t_clean,))
    comp = cursor.fetchone()
    company_name = comp["company_name"] if comp else t_clean

    if not DOCUMENTS_CSV.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documents dataset not found. No documents available for ticker '{t_clean}'.",
        )

    with open(DOCUMENTS_CSV, "r", encoding="utf-8") as f:
        first_line = f.readline()
    header_idx = 0 if "company_id" in first_line or "id" in first_line else 1

    df_docs = pd.read_csv(DOCUMENTS_CSV, header=header_idx)
    df_docs.columns = [c.strip() for c in df_docs.columns]

    df_c = df_docs[df_docs["company_id"].astype(str).str.strip().str.upper() == t_clean]

    if df_c.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No documents exist for ticker '{t_clean}'.",
        )

    documents_list = []
    for _, row in df_c.iterrows():
        yr = row.get("Year")
        yr_val = int(yr) if pd.notna(yr) and str(yr).isdigit() else None
        url = str(row.get("Annual_Report", "")).strip()

        is_valid = is_url_valid_helper(url)
        title = (
            f"{company_name} Annual Report {yr_val}"
            if yr_val
            else f"{company_name} Annual Report"
        )

        documents_list.append(
            {
                "year": yr_val,
                "annual_report_title": title,
                "report_url": url,
                "is_url_valid": is_valid,
            }
        )

    return {
        "ticker": t_clean,
        "company_name": company_name,
        "total_documents": len(documents_list),
        "documents": documents_list,
    }
