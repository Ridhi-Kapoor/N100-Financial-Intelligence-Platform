"""
Professional 2-Page Company Tearsheet PDF Generator using ReportLab.

This module generates investment research-style tearsheets for Nifty 100 constituents:
- Page 1: Executive Overview (Navy Header, 6 KPI Cards, 10Y Revenue & Net Profit Bar Charts, 10Y ROE vs ROCE Dual-Axis Line Chart).
- Page 2: Financial Intelligence (Balance Sheet Composition, Cash Flow Waterfall, Capital Allocation Badge, Pros & Cons NLP Insights).

Output path: output/<TICKER>_tearsheet.pdf
"""

import io
import logging
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"
PROS_CONS_PATH = OUTPUT_DIR / "pros_cons_generated.csv"
CAPITAL_ALLOC_PATH = OUTPUT_DIR / "capital_allocation.csv"

# Configure logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("tearsheet_generator")
logger.setLevel(logging.INFO)

if not logger.handlers:
    log_file = LOG_DIR / "tearsheet_generator.log"
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


# ==============================================================================
# DATA EXTRACTION HELPERS
# ==============================================================================


def fetch_tearsheet_data(ticker: str, db_path: Optional[Path] = None) -> Dict:
    """
    Fetch comprehensive financial metrics, time series, Pros/Cons, and Capital Allocation data
    for a given company ticker.

    Args:
        ticker: NSE Ticker symbol (e.g. 'TCS', 'HDFCBANK').
        db_path: Path to nifty100.db SQLite database.

    Returns:
        Dict containing raw and formatted data attributes.
    """
    if db_path is None:
        db_path = DB_PATH

    clean_ticker = str(ticker).strip().upper()
    conn = sqlite3.connect(db_path)

    try:
        # 1. Company Metadata
        comp_df = pd.read_sql(
            "SELECT * FROM companies WHERE id=?", conn, params=[clean_ticker]
        )
        if comp_df.empty:
            logger.warning(f"Company {clean_ticker} not found in companies table.")
            comp_row = pd.Series({"id": clean_ticker, "company_name": clean_ticker})
        else:
            comp_row = comp_df.iloc[0]

        # 2. Sector & Sub-sector
        sec_df = pd.read_sql(
            "SELECT * FROM sectors WHERE company_id=?", conn, params=[clean_ticker]
        )
        sector = (
            str(sec_df["broad_sector"].values[0]).strip()
            if not sec_df.empty
            and "broad_sector" in sec_df.columns
            and pd.notna(sec_df["broad_sector"].values[0])
            else "N/A"
        )
        sub_sector = (
            str(sec_df["sub_sector"].values[0]).strip()
            if not sec_df.empty
            and "sub_sector" in sec_df.columns
            and pd.notna(sec_df["sub_sector"].values[0])
            else "N/A"
        )

        # 3. Market Cap & Valuation
        mcap_df = pd.read_sql(
            "SELECT * FROM market_cap WHERE company_id=?", conn, params=[clean_ticker]
        )
        latest_mcap_row = mcap_df.iloc[-1] if not mcap_df.empty else pd.Series()
        mcap_val = (
            latest_mcap_row.get("market_cap_crore")
            if not latest_mcap_row.empty
            else None
        )
        pe_val = latest_mcap_row.get("pe_ratio") if not latest_mcap_row.empty else None

        # 4. Financial Ratios
        ratios_df = pd.read_sql(
            "SELECT * FROM financial_ratios WHERE company_id=?",
            conn,
            params=[clean_ticker],
        )
        latest_ratio = ratios_df.iloc[-1] if not ratios_df.empty else pd.Series()

        # ROE
        roe_val = (
            latest_ratio.get("return_on_equity_pct") if not latest_ratio.empty else None
        )
        if (roe_val is None or pd.isna(roe_val)) and "roe_percentage" in comp_row:
            raw_roe = comp_row.get("roe_percentage")
            if pd.notna(raw_roe):
                roe_val = (
                    float(raw_roe) * 100.0 if float(raw_roe) <= 1.0 else float(raw_roe)
                )

        # ROCE
        roce_val = comp_row.get("roce_percentage")
        if pd.isna(roce_val) and not latest_ratio.empty:
            roce_val = latest_ratio.get("roce_percentage")

        de_val = latest_ratio.get("debt_to_equity") if not latest_ratio.empty else None
        cagr_val = (
            latest_ratio.get("revenue_cagr_5yr") if not latest_ratio.empty else None
        )

        # 5. Profit & Loss 10-Year Series
        pl_df = pd.read_sql(
            "SELECT * FROM profitandloss WHERE company_id=?",
            conn,
            params=[clean_ticker],
        )
        if not pl_df.empty and "year" in pl_df.columns:
            pl_clean = pl_df[pl_df["year"].astype(str).str.isdigit()].copy()
            pl_clean["year_num"] = pl_clean["year"].astype(int)
            pl_10y = pl_clean.sort_values("year_num").tail(10)
        else:
            pl_10y = pd.DataFrame()

        # 6. Balance Sheet 10-Year Series
        bs_df = pd.read_sql(
            "SELECT * FROM balancesheet WHERE company_id=?", conn, params=[clean_ticker]
        )
        if not bs_df.empty and "year" in bs_df.columns:
            bs_clean = bs_df[bs_df["year"].astype(str).str.isdigit()].copy()
            bs_clean["year_num"] = bs_clean["year"].astype(int)
            bs_10y = bs_clean.sort_values("year_num").tail(10)
        else:
            bs_10y = pd.DataFrame()

        # 7. Cash Flow 10-Year Series
        cf_df = pd.read_sql(
            "SELECT * FROM cashflow WHERE company_id=?", conn, params=[clean_ticker]
        )
        if not cf_df.empty and "year" in cf_df.columns:
            cf_clean = cf_df[cf_df["year"].astype(str).str.isdigit()].copy()
            cf_clean["year_num"] = cf_clean["year"].astype(int)
            cf_10y = cf_clean.sort_values("year_num").tail(10)
        else:
            cf_10y = pd.DataFrame()

        # Build ROE & ROCE Series for Line Chart
        pl_years = pl_10y["year"].tolist() if not pl_10y.empty else []
        sales_list = (
            pl_10y["sales"].tolist()
            if not pl_10y.empty and "sales" in pl_10y.columns
            else []
        )
        net_profit_list = (
            pl_10y["net_profit"].tolist()
            if not pl_10y.empty and "net_profit" in pl_10y.columns
            else []
        )

        # Merge ROE from ratios_df over years if available
        roe_series = []
        roce_series = []

        for _, r in pl_10y.iterrows():
            y_num = r["year_num"]
            r_row = (
                ratios_df[pd.to_numeric(ratios_df["year"], errors="coerce") == y_num]
                if not ratios_df.empty
                else pd.DataFrame()
            )
            bs_row = (
                bs_10y[bs_10y["year_num"] == y_num]
                if not bs_10y.empty
                else pd.DataFrame()
            )

            # ROE
            r_roe = (
                r_row["return_on_equity_pct"].values[0]
                if not r_row.empty
                and "return_on_equity_pct" in r_row.columns
                and pd.notna(r_row["return_on_equity_pct"].values[0])
                else roe_val
            )
            roe_series.append(
                float(r_roe) if r_roe is not None and pd.notna(r_roe) else np.nan
            )

            # ROCE = EBIT / Capital Employed * 100
            pbt = (
                float(r.get("profit_before_tax", r.get("net_profit", 0)))
                if pd.notna(r.get("profit_before_tax", r.get("net_profit", 0)))
                else 0.0
            )
            interest = (
                float(r.get("interest", 0)) if pd.notna(r.get("interest", 0)) else 0.0
            )
            ebit = pbt + interest

            if not bs_row.empty:
                eq_cap = (
                    float(bs_row.get("equity_capital", pd.Series([0])).values[0])
                    if pd.notna(bs_row.get("equity_capital", pd.Series([0])).values[0])
                    else 0.0
                )
                res = (
                    float(bs_row.get("reserves", pd.Series([0])).values[0])
                    if pd.notna(bs_row.get("reserves", pd.Series([0])).values[0])
                    else 0.0
                )
                bor = (
                    float(bs_row.get("borrowings", pd.Series([0])).values[0])
                    if pd.notna(bs_row.get("borrowings", pd.Series([0])).values[0])
                    else 0.0
                )
                cap_emp = eq_cap + res + bor
                calc_roce = (ebit / cap_emp * 100.0) if cap_emp > 0 else roce_val
            else:
                calc_roce = roce_val

            roce_series.append(
                float(calc_roce)
                if calc_roce is not None and pd.notna(calc_roce)
                else np.nan
            )

        # Balance Sheet Composition Lists
        bs_years = bs_10y["year"].tolist() if not bs_10y.empty else []
        eq_list = []
        bor_list = []
        oth_list = []

        if not bs_10y.empty:
            for _, bsr in bs_10y.iterrows():
                eq_c = (
                    float(bsr.get("equity_capital", 0))
                    if pd.notna(bsr.get("equity_capital", 0))
                    else 0.0
                )
                res_c = (
                    float(bsr.get("reserves", 0))
                    if pd.notna(bsr.get("reserves", 0))
                    else 0.0
                )
                eq_list.append(eq_c + res_c)
                bor_list.append(
                    float(bsr.get("borrowings", 0))
                    if pd.notna(bsr.get("borrowings", 0))
                    else 0.0
                )
                oth_list.append(
                    float(bsr.get("other_liabilities", 0))
                    if pd.notna(bsr.get("other_liabilities", 0))
                    else 0.0
                )

        # Latest Cash Flow Waterfall
        latest_cf_row = cf_10y.iloc[-1] if not cf_10y.empty else pd.Series()
        cfo = (
            float(latest_cf_row.get("operating_activity", 0))
            if pd.notna(latest_cf_row.get("operating_activity", 0))
            else 0.0
        )
        cfi = (
            float(latest_cf_row.get("investing_activity", 0))
            if pd.notna(latest_cf_row.get("investing_activity", 0))
            else 0.0
        )
        cff = (
            float(latest_cf_row.get("financing_activity", 0))
            if pd.notna(latest_cf_row.get("financing_activity", 0))
            else 0.0
        )
        net_cf = (
            float(latest_cf_row.get("net_cash_flow", 0))
            if pd.notna(latest_cf_row.get("net_cash_flow", 0))
            else (cfo + cfi + cff)
        )

        # 8. Pros & Cons (from NLP output)
        pros = []
        cons = []
        if PROS_CONS_PATH.exists():
            try:
                pc_df = pd.read_csv(PROS_CONS_PATH)
                comp_pc = pc_df[
                    pc_df["Company ID"].astype(str).str.strip().str.upper()
                    == clean_ticker
                ]
                pros = comp_pc[comp_pc["Type"].str.upper() == "PRO"][
                    "Generated Text"
                ].tolist()
                cons = comp_pc[comp_pc["Type"].str.upper() == "CON"][
                    "Generated Text"
                ].tolist()
            except Exception as e:
                logger.warning(f"Error loading pros/cons CSV: {e}")

        # 9. Capital Allocation Label
        ca_label = "N/A"
        if CAPITAL_ALLOC_PATH.exists():
            try:
                ca_df = pd.read_csv(CAPITAL_ALLOC_PATH)
                comp_ca = ca_df[
                    ca_df["company_id"].astype(str).str.strip().str.upper()
                    == clean_ticker
                ]
                if not comp_ca.empty:
                    ca_label = str(comp_ca.iloc[-1]["pattern_label"]).strip()
            except Exception as e:
                logger.warning(f"Error loading capital allocation CSV: {e}")

        return {
            "ticker": clean_ticker,
            "company_name": str(comp_row.get("company_name", clean_ticker)).strip(),
            "sector": sector,
            "sub_sector": sub_sector,
            "mcap": mcap_val,
            "pe": pe_val,
            "roe": roe_val,
            "roce": roce_val,
            "de": de_val,
            "cagr": cagr_val,
            "pl_years": pl_years,
            "sales": sales_list,
            "net_profit": net_profit_list,
            "roe_series": roe_series,
            "roce_series": roce_series,
            "bs_years": bs_years,
            "equity": eq_list,
            "borrowings": bor_list,
            "other_liab": oth_list,
            "cfo": cfo,
            "cfi": cfi,
            "cff": cff,
            "net_cf": net_cf,
            "pros": pros,
            "cons": cons,
            "capital_allocation_label": ca_label,
        }

    finally:
        conn.close()


# ==============================================================================
# MATPLOTLIB CHART GENERATION HELPERS
# ==============================================================================


def generate_revenue_np_charts(
    years: List[str], sales: List[float], net_profit: List[float]
) -> io.BytesIO:
    """
    Render 10-Year Revenue & Net Profit side-by-side bar charts.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.4, 2.2), dpi=200)

    if not years:
        years = ["N/A"]
        sales = [0]
        net_profit = [0]

    # Revenue Bar Chart
    ax1.bar(years, sales, color="#2563EB", width=0.55)
    ax1.set_title(
        "10-Year Revenue Trend (₹ Cr)",
        fontsize=9,
        fontweight="bold",
        color="#0F172A",
        pad=5,
    )
    ax1.tick_params(axis="x", rotation=45, labelsize=6.5)
    ax1.tick_params(axis="y", labelsize=6.5)
    ax1.grid(axis="y", linestyle="--", alpha=0.35)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # Net Profit Bar Chart
    colors_np = ["#16A34A" if v >= 0 else "#DC2626" for v in net_profit]
    ax2.bar(years, net_profit, color=colors_np, width=0.55)
    ax2.set_title(
        "10-Year Net Profit Trend (₹ Cr)",
        fontsize=9,
        fontweight="bold",
        color="#0F172A",
        pad=5,
    )
    ax2.tick_params(axis="x", rotation=45, labelsize=6.5)
    ax2.tick_params(axis="y", labelsize=6.5)
    ax2.grid(axis="y", linestyle="--", alpha=0.35)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf


def generate_roe_roce_chart(
    years: List[str], roe_series: List[float], roce_series: List[float]
) -> io.BytesIO:
    """
    Render 10-Year ROE vs ROCE dual-axis line chart.
    """
    fig, ax_roe = plt.subplots(figsize=(7.4, 2.0), dpi=200)

    if not years:
        years = ["N/A"]
        roe_series = [0]
        roce_series = [0]

    # Clean NaN for plotting
    roe_clean = [np.nan if v is None or pd.isna(v) else v for v in roe_series]
    roce_clean = [np.nan if v is None or pd.isna(v) else v for v in roce_series]

    ax_roe.plot(
        years,
        roe_clean,
        color="#2563EB",
        marker="o",
        markersize=4,
        linewidth=1.8,
        label="ROE (%)",
    )
    ax_roe.set_ylabel("ROE (%)", color="#2563EB", fontsize=7.5, fontweight="bold")
    ax_roe.tick_params(axis="y", labelcolor="#2563EB", labelsize=6.5)
    ax_roe.tick_params(axis="x", labelsize=6.5)
    ax_roe.grid(axis="y", linestyle="--", alpha=0.35)

    ax_roce = ax_roe.twinx()
    ax_roce.plot(
        years,
        roce_clean,
        color="#DC2626",
        marker="s",
        markersize=4,
        linestyle="--",
        linewidth=1.8,
        label="ROCE (%)",
    )
    ax_roce.set_ylabel("ROCE (%)", color="#DC2626", fontsize=7.5, fontweight="bold")
    ax_roce.tick_params(axis="y", labelcolor="#DC2626", labelsize=6.5)

    # Combined legend
    lines1, labels1 = ax_roe.get_legend_handles_labels()
    lines2, labels2 = ax_roce.get_legend_handles_labels()
    ax_roe.legend(
        lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=6.5, frameon=True
    )

    plt.title(
        "10-Year Profitability Trajectory: Return on Equity (ROE) vs Return on Capital (ROCE)",
        fontsize=8.5,
        fontweight="bold",
        color="#0F172A",
        pad=5,
    )
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf


def generate_bs_composition_chart(
    years: List[str],
    equity: List[float],
    borrowings: List[float],
    other_liab: List[float],
) -> io.BytesIO:
    """
    Render Balance Sheet Composition stacked bar chart.
    """
    fig, ax = plt.subplots(figsize=(3.55, 2.1), dpi=200)

    if not years:
        years = ["N/A"]
        equity = [0]
        borrowings = [0]
        other_liab = [0]

    eq_arr = np.array([0.0 if pd.isna(v) else float(v) for v in equity])
    bor_arr = np.array([0.0 if pd.isna(v) else float(v) for v in borrowings])
    oth_arr = np.array([0.0 if pd.isna(v) else float(v) for v in other_liab])

    ax.bar(years, eq_arr, label="Equity", color="#1E3A8A", width=0.55)
    ax.bar(
        years, bor_arr, bottom=eq_arr, label="Borrowings", color="#DC2626", width=0.55
    )
    ax.bar(
        years,
        oth_arr,
        bottom=eq_arr + bor_arr,
        label="Other Liabilities",
        color="#0284C7",
        width=0.55,
    )

    ax.set_title(
        "Balance Sheet Composition (₹ Cr)",
        fontsize=8.5,
        fontweight="bold",
        color="#0F172A",
        pad=5,
    )
    ax.tick_params(axis="x", rotation=45, labelsize=6.0)
    ax.tick_params(axis="y", labelsize=6.0)
    ax.legend(fontsize=5.5, loc="upper left", frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf


def generate_cash_flow_waterfall_chart(
    cfo: float, cfi: float, cff: float, net_cf: float
) -> io.BytesIO:
    """
    Render Cash Flow Waterfall chart for latest year.
    """
    fig, ax = plt.subplots(figsize=(3.55, 2.1), dpi=200)

    categories = ["CFO", "CFI", "CFF", "Net Cash"]
    vals = [cfo, cfi, cff, net_cf]

    bottoms = [0, cfo, cfo + cfi, 0]
    heights = [cfo, cfi, cff, net_cf]
    colors_wf = ["#16A34A" if h >= 0 else "#DC2626" for h in heights]
    colors_wf[3] = "#2563EB"  # Net Cash Flow color

    ax.bar(categories, heights, bottom=bottoms, color=colors_wf, width=0.55)
    ax.axhline(0, color="black", linewidth=0.7, linestyle="--")

    ax.set_title(
        "Cash Flow Waterfall (Latest Year ₹ Cr)",
        fontsize=8.5,
        fontweight="bold",
        color="#0F172A",
        pad=5,
    )
    ax.tick_params(axis="x", labelsize=6.5)
    ax.tick_params(axis="y", labelsize=6.0)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Format text annotations inside or above bars
    for i, val in enumerate(vals):
        val_str = f"₹{val:,.0f}" if abs(val) < 100000 else f"₹{val/1000:.1f}k"
        y_pos = bottoms[i] + heights[i] / 2.0 if i < 3 else net_cf / 2.0
        ax.text(
            i,
            y_pos,
            val_str,
            ha="center",
            va="center",
            fontsize=5.0,
            color="white",
            fontweight="bold",
        )

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf


# ==============================================================================
# REPORTLAB PDF GENERATOR IMPLEMENTATION
# ==============================================================================


def generate_tearsheet_pdf(
    ticker: str,
    output_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> Path:
    """
    Generate a professional 2-page Company Tearsheet PDF for the given ticker.

    Args:
        ticker: NSE Ticker symbol (e.g., 'TCS', 'HDFCBANK', 'RELIANCE').
        output_path: Target PDF output path. Defaults to output/<TICKER>_tearsheet.pdf.
        db_path: SQLite database path.

    Returns:
        Path to generated PDF file.
    """
    clean_ticker = str(ticker).strip().upper()
    logger.info(f"Generating Company Tearsheet PDF for {clean_ticker}...")

    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / f"{clean_ticker}_tearsheet.pdf"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Fetch data
    data = fetch_tearsheet_data(clean_ticker, db_path)

    # 2. Setup Document (A4, 28pt margins)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=28,
        rightMargin=28,
        topMargin=28,
        bottomMargin=28,
    )

    usable_width = 539.27  # A4 width (595.27) - 56

    # Styles
    getSampleStyleSheet()

    header_title_style = ParagraphStyle(
        "HeaderTitle",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=18,
        textColor=colors.white,
    )
    header_sub_style = ParagraphStyle(
        "HeaderSub",
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#CBD5E1"),
    )
    section_heading_style = ParagraphStyle(
        "SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    kpi_title_style = ParagraphStyle(
        "KPITitle",
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    kpi_val_style = ParagraphStyle(
        "KPIVal",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=15,
        textColor=colors.HexColor("#1E3A8A"),
        alignment=1,
    )
    kpi_sub_style = ParagraphStyle(
        "KPISub",
        fontName="Helvetica",
        fontSize=6.5,
        leading=7.5,
        textColor=colors.HexColor("#64748B"),
        alignment=1,
    )
    pro_bullet_style = ParagraphStyle(
        "ProBullet",
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#14532D"),
    )
    con_bullet_style = ParagraphStyle(
        "ConBullet",
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#7F1D1D"),
    )

    story = []

    # --------------------------------------------------------------------------
    # PAGE 1 – COMPANY OVERVIEW
    # --------------------------------------------------------------------------

    # 1. Header Bar (Navy Background)
    header_content = [
        [
            Paragraph(
                f"{data['company_name']} <font size=11 color='#38BDF8'>({data['ticker']})</font>",
                header_title_style,
            ),
            Paragraph(
                f"<b>NSE Ticker:</b> {data['ticker']} &nbsp;|&nbsp; <b>Sector:</b> {data['sector']}",
                header_sub_style,
            ),
        ]
    ]
    header_table = Table(header_content, colWidths=[330, 209])
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 8))

    # 2. Key Performance Indicators (6 KPI Cards: 2 rows x 3 columns)
    def fmt_pct(v):
        """Format percentage value into string."""
        return f"{v:.1f}%" if v is not None and pd.notna(v) else "N/A"

    def fmt_num(v, fmt="{:.2f}"):
        """Format numeric value into string."""
        return fmt.format(v) if v is not None and pd.notna(v) else "N/A"

    def fmt_mcap(v):
        """Format Market Capitalization value."""
        if v is None or pd.isna(v):
            return "N/A"
        val = float(v)
        if val >= 100000:
            return f"₹{val/100000:.2f}L Cr"
        return f"₹{val:,.0f} Cr"

    kpi_cards_data = [
        [
            [
                Paragraph("RETURN ON EQUITY", kpi_title_style),
                Paragraph(fmt_pct(data["roe"]), kpi_val_style),
                Paragraph("ROE (Latest Year)", kpi_sub_style),
            ],
            [
                Paragraph("RETURN ON CAPITAL", kpi_title_style),
                Paragraph(fmt_pct(data["roce"]), kpi_val_style),
                Paragraph("ROCE (Latest Year)", kpi_sub_style),
            ],
            [
                Paragraph("P/E RATIO", kpi_title_style),
                Paragraph(fmt_num(data["pe"], "{:.1f}x"), kpi_val_style),
                Paragraph("Valuation Multiple", kpi_sub_style),
            ],
        ],
        [
            [
                Paragraph("REVENUE CAGR (5Y)", kpi_title_style),
                Paragraph(fmt_pct(data["cagr"]), kpi_val_style),
                Paragraph("5-Yr Growth Rate", kpi_sub_style),
            ],
            [
                Paragraph("DEBT-TO-EQUITY", kpi_title_style),
                Paragraph(fmt_num(data["de"]), kpi_val_style),
                Paragraph("Leverage Ratio", kpi_sub_style),
            ],
            [
                Paragraph("MARKET CAP", kpi_title_style),
                Paragraph(fmt_mcap(data["mcap"]), kpi_val_style),
                Paragraph("Total Valuation", kpi_sub_style),
            ],
        ],
    ]

    card_table_rows = []
    for row in kpi_cards_data:
        cell_row = []
        for card in row:
            t = Table([[card[0]], [card[1]], [card[2]]], colWidths=[173])
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#E2E8F0")),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            cell_row.append(t)
        card_table_rows.append(cell_row)

    kpi_grid_table = Table(card_table_rows, colWidths=[179, 179, 179])
    kpi_grid_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story.append(
        Paragraph(
            "<b>KEY FINANCIAL METRICS & VALUATION SUMMARY</b>", section_heading_style
        )
    )
    story.append(kpi_grid_table)
    story.append(Spacer(1, 8))

    # 3. 10-Year Revenue & Net Profit Bar Charts (Side-by-Side)
    story.append(
        Paragraph("<b>10-YEAR FINANCIAL PERFORMANCE TRENDS</b>", section_heading_style)
    )
    buf_rev_np = generate_revenue_np_charts(
        data["pl_years"], data["sales"], data["net_profit"]
    )
    img_rev_np = Image(buf_rev_np, width=usable_width, height=158)
    story.append(img_rev_np)
    story.append(Spacer(1, 8))

    # 4. 10-Year ROE vs ROCE Dual Axis Line Chart
    story.append(
        Paragraph(
            "<b>10-YEAR PROFITABILITY TRAJECTORY (ROE vs ROCE)</b>",
            section_heading_style,
        )
    )
    buf_roe_roce = generate_roe_roce_chart(
        data["pl_years"], data["roe_series"], data["roce_series"]
    )
    img_roe_roce = Image(buf_roe_roce, width=usable_width, height=145)
    story.append(img_roe_roce)

    # 5. Page Break to Page 2
    story.append(PageBreak())

    # --------------------------------------------------------------------------
    # PAGE 2 – FINANCIAL INTELLIGENCE & CAPITAL ALLOCATION
    # --------------------------------------------------------------------------

    # 1. Page 2 Header Banner
    p2_header_content = [
        [
            Paragraph(
                f"FINANCIAL INTELLIGENCE & CAPITAL ALLOCATION — {data['company_name']}",
                header_title_style,
            ),
            Paragraph("PAGE 2 OF 2", header_sub_style),
        ]
    ]
    p2_header_table = Table(p2_header_content, colWidths=[420, 119])
    p2_header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(p2_header_table)
    story.append(Spacer(1, 8))

    # 2. Balance Sheet Composition & Cash Flow Waterfall Charts Side-by-Side
    buf_bs = generate_bs_composition_chart(
        data["bs_years"], data["equity"], data["borrowings"], data["other_liab"]
    )
    buf_wf = generate_cash_flow_waterfall_chart(
        data["cfo"], data["cfi"], data["cff"], data["net_cf"]
    )

    img_bs = Image(buf_bs, width=265, height=155)
    img_wf = Image(buf_wf, width=265, height=155)

    charts_table = Table([[img_bs, img_wf]], colWidths=[269, 269])
    charts_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(charts_table)
    story.append(Spacer(1, 8))

    # 3. Capital Allocation Classification Badge
    ca_label = data["capital_allocation_label"]
    badge_bg = colors.HexColor("#EFF6FF")
    badge_border = colors.HexColor("#3B82F6")
    badge_text_color = "#1E40AF"

    if ca_label in ["Distress Signal"]:
        badge_bg = colors.HexColor("#FEF2F2")
        badge_border = colors.HexColor("#EF4444")
        badge_text_color = "#991B1B"
    elif ca_label in ["Growth Funded by Debt", "Liquidating Assets"]:
        badge_bg = colors.HexColor("#FFFBEB")
        badge_border = colors.HexColor("#F59E0B")
        badge_text_color = "#92400E"
    elif ca_label in ["Shareholder Returns", "Reinvestor", "Compounder"]:
        badge_bg = colors.HexColor("#F0FDF4")
        badge_border = colors.HexColor("#22C55E")
        badge_text_color = "#166534"

    badge_desc = f"Latest Capital Allocation Strategy classified as <b><font color='{badge_text_color}'>{ca_label}</font></b> based on operating, investing, and financing cash flow dynamics."
    badge_p = Paragraph(
        f"<b>CAPITAL ALLOCATION CLASSIFICATION:</b> <font color='{badge_text_color}'><b>{ca_label.upper()}</b></font><br/><font size=7.5 color='#475569'>{badge_desc}</font>",
        ParagraphStyle(
            "BadgeStyle",
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#0F172A"),
        ),
    )

    badge_table = Table([[badge_p]], colWidths=[usable_width])
    badge_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), badge_bg),
                ("BOX", (0, 0), (-1, -1), 1, badge_border),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(badge_table)
    story.append(Spacer(1, 8))

    # 4. Investment Insights – Pros & Cons (NLP Output)
    story.append(
        Paragraph(
            "<b>INVESTMENT INSIGHTS & QUANTITATIVE FLAGS</b>", section_heading_style
        )
    )

    pros_list = (
        data["pros"]
        if data["pros"]
        else [
            "Company maintains baseline operating profit margin stability.",
            "Positive historical operating cash flows recorded.",
        ]
    )
    cons_list = (
        data["cons"]
        if data["cons"]
        else [
            "Valuation multiples reflect market growth expectations.",
            "Monitor sector cyclicality and raw material cost inflation.",
        ]
    )

    pros_cells = [
        Paragraph(
            "<b>INVESTMENT STRENGTHS (PROS)</b>",
            ParagraphStyle(
                "ProHead",
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#15803D"),
            ),
        )
    ]
    for p_item in pros_list[:5]:  # Top 5 pros
        pros_cells.append(
            Paragraph(
                f"<font color='#16A34A'><b>•</b></font> {p_item}", pro_bullet_style
            )
        )

    cons_cells = [
        Paragraph(
            "<b>KEY RISKS & CONCERNS (CONS)</b>",
            ParagraphStyle(
                "ConHead",
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#B91C1C"),
            ),
        )
    ]
    for c_item in cons_list[:5]:  # Top 5 cons
        cons_cells.append(
            Paragraph(
                f"<font color='#DC2626'><b>•</b></font> {c_item}", con_bullet_style
            )
        )

    pros_table = Table([[cell] for cell in pros_cells], colWidths=[260])
    pros_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCFCE7")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F0FDF4")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#BBF7D0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    cons_table = Table([[cell] for cell in cons_cells], colWidths=[260])
    cons_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FEE2E2")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FEF2F2")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#FECACA")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    pc_grid_table = Table([[pros_table, cons_table]], colWidths=[269, 269])
    pc_grid_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story.append(pc_grid_table)

    # 5. Build Document
    def add_footer(canvas, doc):
        """Draw running footer on PDF page canvas."""
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        page_num = canvas.getPageNumber()
        footer_text = f"Nifty 100 Financial Intelligence Platform | {data['company_name']} ({clean_ticker}) Tearsheet | Page {page_num} of 2"
        canvas.drawString(28, 15, footer_text)
        canvas.drawRightString(
            A4[0] - 28, 15, "Confidential - Investment Research Report"
        )
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.5)
        canvas.line(28, 25, A4[0] - 28, 25)
        canvas.restoreState()

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    logger.info(
        f"Successfully generated tearsheet PDF for {clean_ticker} at: {output_path.resolve()}"
    )
    return output_path


def generate_all_tearsheets(
    tickers: Optional[List[str]] = None,
    output_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Path]:
    """
    Batch generate Company Tearsheet PDFs for multiple tickers.

    Args:
        tickers: List of NSE tickers (defaults to ['TCS', 'HDFCBANK', 'RELIANCE', 'SUNPHARMA', 'TATASTEEL']).
        output_dir: Output directory path.
        db_path: SQLite database path.

    Returns:
        Dict mapping ticker symbol to generated PDF Path.
    """
    if tickers is None:
        tickers = ["TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATASTEEL"]

    if output_dir is None:
        output_dir = OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for ticker in tickers:
        try:
            pdf_path = output_dir / f"{str(ticker).strip().upper()}_tearsheet.pdf"
            generate_tearsheet_pdf(ticker, pdf_path, db_path)
            results[ticker] = pdf_path
        except Exception as e:
            logger.error(f"Error generating tearsheet for {ticker}: {e}")

    return results


if __name__ == "__main__":
    generate_all_tearsheets()
