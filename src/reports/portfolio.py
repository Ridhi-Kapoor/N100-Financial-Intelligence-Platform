"""
Portfolio Summary PDF Generator using ReportLab.

Generates a comprehensive executive Portfolio Summary PDF containing:
- 1 page per company, sorted alphabetically by NSE ticker symbol.
- Company Name, NSE Ticker, Sector, and Sub-sector metadata.
- Top 6 financial KPI cards (ROE, ROCE, NPM, Debt-to-Equity, Revenue CAGR, FCF).
- YoY Trend Indicators for each KPI:
  * ⬆️ / ▲ (Up Arrow) -> Metric improved compared to previous year (>= +2%)
  * ⬇️ / ▼ (Down Arrow) -> Metric declined compared to previous year (<= -2%)
  * ➡️ / ► (Right Arrow) -> Metric changed by less than ±2% (considered stable)
- Financial performance trends, Capital Allocation Badge, and Pros/Cons insights.

Output path: reports/portfolio/portfolio_summary.pdf
"""

import io
import logging
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
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
PORTFOLIO_DIR = PROJECT_ROOT / "reports" / "portfolio"
PORTFOLIO_PDF_PATH = PORTFOLIO_DIR / "portfolio_summary.pdf"
PROS_CONS_PATH = OUTPUT_DIR / "pros_cons_generated.csv"
CAPITAL_ALLOC_PATH = OUTPUT_DIR / "capital_allocation.csv"

# Configure logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("portfolio_summary_generator")
logger.setLevel(logging.INFO)

if not logger.handlers:
    log_file = LOG_DIR / "portfolio_summary_generator.log"
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


# ==============================================================================
# TREND ARROW CALCULATION HELPERS
# ==============================================================================


def calculate_kpi_trend(
    curr_val: Optional[float],
    prev_val: Optional[float],
    lower_is_better: bool = False,
) -> Tuple[str, str, str]:
    """
    Calculate the YoY percentage change and determine trend arrow & status label.

    Rules:
    - Change < ±2%: ➡️ / ► (Stable)
    - Change >= +2%: ⬆️ / ▲ (Improved) [or ⬇️ if lower_is_better]
    - Change <= -2%: ⬇️ / ▼ (Declined) [or ⬆️ if lower_is_better]

    Args:
        curr_val: Current year KPI value.
        prev_val: Previous year KPI value.
        lower_is_better: If True, a reduction in metric is considered an improvement (e.g. D/E).

    Returns:
        Tuple[str, str, str]:
            - Formatted trend string (e.g. "+4.5%" or "-1.2%").
            - Arrow HTML markup (e.g. "<font color='#16A34A'><b>▲</b></font>").
            - Simple text label ("Improved", "Declined", "Stable", or "N/A").
    """
    if curr_val is None or prev_val is None or pd.isna(curr_val) or pd.isna(prev_val):
        return "N/A", "<font color='#64748B'><b>►</b></font>", "N/A"

    try:
        c = float(curr_val)
        p = float(prev_val)
    except (ValueError, TypeError):
        return "N/A", "<font color='#64748B'><b>►</b></font>", "N/A"

    if p == 0.0:
        pct_change = 0.0
    else:
        pct_change = ((c - p) / abs(p)) * 100.0

    pct_str = f"{pct_change:+.1f}%"

    if abs(pct_change) < 2.0:
        arrow_html = "<font color='#64748B'><b>►</b></font>"
        label = "Stable"
    elif pct_change >= 2.0:
        if lower_is_better:
            arrow_html = "<font color='#DC2626'><b>▼</b></font>"
            label = "Declined"
        else:
            arrow_html = "<font color='#16A34A'><b>▲</b></font>"
            label = "Improved"
    else:
        if lower_is_better:
            arrow_html = "<font color='#16A34A'><b>▲</b></font>"
            label = "Improved"
        else:
            arrow_html = "<font color='#DC2626'><b>▼</b></font>"
            label = "Declined"

    return pct_str, arrow_html, label


# ==============================================================================
# DATA EXTRACTION FOR ALL COMPANIES
# ==============================================================================


def fetch_portfolio_companies_data(db_path: Optional[Path] = None) -> List[Dict]:
    """
    Fetch comprehensive portfolio metrics, trend data, Pros/Cons, and Capital Allocation labels
    for all master Nifty 100 companies, sorted alphabetically by NSE ticker.

    Args:
        db_path: Path to SQLite database.

    Returns:
        List[Dict]: List of company data dictionaries.
    """
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(db_path)

    try:
        # 1. Fetch companies sorted by ticker
        comp_df = pd.read_sql("SELECT * FROM companies ORDER BY id ASC", conn)
        sec_df = pd.read_sql("SELECT * FROM sectors", conn)
        sec_map = {}
        sub_sec_map = {}
        if not sec_df.empty:
            for _, r in sec_df.iterrows():
                cid = str(r["company_id"]).strip()
                sec_map[cid] = str(r.get("broad_sector", "N/A")).strip()
                sub_sec_map[cid] = str(r.get("sub_sector", "N/A")).strip()

        ratios_df = pd.read_sql("SELECT * FROM financial_ratios", conn)
        pl_df = pd.read_sql("SELECT * FROM profitandloss", conn)
        bs_df = pd.read_sql("SELECT * FROM balancesheet", conn)
        cf_df = pd.read_sql("SELECT * FROM cashflow", conn)

        pc_df = (
            pd.read_csv(PROS_CONS_PATH) if PROS_CONS_PATH.exists() else pd.DataFrame()
        )
        ca_df = (
            pd.read_csv(CAPITAL_ALLOC_PATH)
            if CAPITAL_ALLOC_PATH.exists()
            else pd.DataFrame()
        )

        portfolio_data = []

        for _, comp in comp_df.iterrows():
            ticker = str(comp["id"]).strip().upper()
            cname = str(comp.get("company_name", ticker)).strip()
            sector = sec_map.get(ticker, "N/A")
            sub_sector = sub_sec_map.get(ticker, "N/A")

            # Financial Ratios for latest and previous year
            c_ratios = ratios_df[
                ratios_df["company_id"].astype(str).str.strip().str.upper() == ticker
            ]
            if not c_ratios.empty:
                c_ratios_clean = c_ratios[
                    c_ratios["year"].astype(str).str.isdigit()
                ].copy()
                c_ratios_clean["year_num"] = c_ratios_clean["year"].astype(int)
                c_ratios_clean = c_ratios_clean.sort_values("year_num")
                curr_ratio = (
                    c_ratios_clean.iloc[-1] if not c_ratios_clean.empty else pd.Series()
                )
                prev_ratio = (
                    c_ratios_clean.iloc[-2] if len(c_ratios_clean) >= 2 else pd.Series()
                )
            else:
                curr_ratio = pd.Series()
                prev_ratio = pd.Series()

            # P&L series
            c_pl = pl_df[
                pl_df["company_id"].astype(str).str.strip().str.upper() == ticker
            ]
            if not c_pl.empty:
                c_pl_clean = c_pl[c_pl["year"].astype(str).str.isdigit()].copy()
                c_pl_clean["year_num"] = c_pl_clean["year"].astype(int)
                pl_10y = c_pl_clean.sort_values("year_num").tail(10)
            else:
                pl_10y = pd.DataFrame()

            # Balance Sheet series
            c_bs = bs_df[
                bs_df["company_id"].astype(str).str.strip().str.upper() == ticker
            ]
            if not c_bs.empty:
                c_bs_clean = c_bs[c_bs["year"].astype(str).str.isdigit()].copy()
                c_bs_clean["year_num"] = c_bs_clean["year"].astype(int)
                bs_10y = c_bs_clean.sort_values("year_num").tail(10)
            else:
                bs_10y = pd.DataFrame()

            # Cash Flow series
            c_cf = cf_df[
                cf_df["company_id"].astype(str).str.strip().str.upper() == ticker
            ]
            if not c_cf.empty:
                c_cf_clean = c_cf[c_cf["year"].astype(str).str.isdigit()].copy()
                c_cf_clean["year_num"] = c_cf_clean["year"].astype(int)
                c_cf_clean.sort_values("year_num").tail(10)
            else:
                pd.DataFrame()

            # ------------------------------------------------------------------
            # Calculate 6 Top Financial KPIs & Trends
            # ------------------------------------------------------------------

            # 1. ROE (%)
            roe_curr = curr_ratio.get("return_on_equity_pct")
            roe_prev = prev_ratio.get("return_on_equity_pct")
            if (roe_curr is None or pd.isna(roe_curr)) and pd.notna(
                comp.get("roe_percentage")
            ):
                raw_roe = float(comp["roe_percentage"])
                roe_curr = raw_roe * 100.0 if raw_roe <= 1.0 else raw_roe
            roe_chg, roe_arrow, roe_lbl = calculate_kpi_trend(roe_curr, roe_prev)

            # 2. ROCE (%)
            roce_curr = comp.get("roce_percentage")
            roce_prev = (
                prev_ratio.get("roce_percentage") if not prev_ratio.empty else None
            )
            if pd.isna(roce_curr) and not curr_ratio.empty:
                roce_curr = curr_ratio.get("roce_percentage")
            roce_chg, roce_arrow, roce_lbl = calculate_kpi_trend(roce_curr, roce_prev)

            # 3. Net Profit Margin (%)
            npm_curr = curr_ratio.get("net_profit_margin_pct")
            npm_prev = prev_ratio.get("net_profit_margin_pct")
            npm_chg, npm_arrow, npm_lbl = calculate_kpi_trend(npm_curr, npm_prev)

            # 4. Debt-to-Equity
            de_curr = curr_ratio.get("debt_to_equity")
            de_prev = prev_ratio.get("debt_to_equity")
            de_chg, de_arrow, de_lbl = calculate_kpi_trend(
                de_curr, de_prev, lower_is_better=True
            )

            # 5. Revenue CAGR (5Y %)
            cagr_curr = curr_ratio.get("revenue_cagr_5yr")
            cagr_prev = prev_ratio.get("revenue_cagr_5yr")
            cagr_chg, cagr_arrow, cagr_lbl = calculate_kpi_trend(cagr_curr, cagr_prev)

            # 6. Free Cash Flow (₹ Cr)
            fcf_curr = curr_ratio.get("free_cash_flow_cr")
            fcf_prev = prev_ratio.get("free_cash_flow_cr")
            fcf_chg, fcf_arrow, fcf_lbl = calculate_kpi_trend(fcf_curr, fcf_prev)

            # Build P&L Time Series Lists
            pl_years = pl_10y["year"].tolist() if not pl_10y.empty else []
            sales_list = (
                pl_10y["sales"].tolist()
                if not pl_10y.empty and "sales" in pl_10y.columns
                else []
            )
            np_list = (
                pl_10y["net_profit"].tolist()
                if not pl_10y.empty and "net_profit" in pl_10y.columns
                else []
            )

            # Build ROE & ROCE Series for Line Chart
            roe_series = []
            roce_series = []
            for _, r in pl_10y.iterrows():
                y_num = r["year_num"]
                r_row = (
                    c_ratios[pd.to_numeric(c_ratios["year"], errors="coerce") == y_num]
                    if not c_ratios.empty
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
                    else roe_curr
                )
                roe_series.append(
                    float(r_roe) if r_roe is not None and pd.notna(r_roe) else np.nan
                )

                # ROCE
                pbt = (
                    float(r.get("profit_before_tax", r.get("net_profit", 0)))
                    if pd.notna(r.get("profit_before_tax", r.get("net_profit", 0)))
                    else 0.0
                )
                interest = (
                    float(r.get("interest", 0))
                    if pd.notna(r.get("interest", 0))
                    else 0.0
                )
                ebit = pbt + interest

                if not bs_row.empty:
                    eq_cap = (
                        float(bs_row.get("equity_capital", pd.Series([0])).values[0])
                        if pd.notna(
                            bs_row.get("equity_capital", pd.Series([0])).values[0]
                        )
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
                    calc_roce = (ebit / cap_emp * 100.0) if cap_emp > 0 else roce_curr
                else:
                    calc_roce = roce_curr

                roce_series.append(
                    float(calc_roce)
                    if calc_roce is not None and pd.notna(calc_roce)
                    else np.nan
                )

            # Pros & Cons
            c_pc = (
                pc_df[pc_df["Company ID"].astype(str).str.strip().str.upper() == ticker]
                if not pc_df.empty
                else pd.DataFrame()
            )
            pros = (
                c_pc[c_pc["Type"].str.upper() == "PRO"]["Generated Text"].tolist()
                if not c_pc.empty
                else []
            )
            cons = (
                c_pc[c_pc["Type"].str.upper() == "CON"]["Generated Text"].tolist()
                if not c_pc.empty
                else []
            )

            # Capital Allocation Badge
            c_ca = (
                ca_df[ca_df["company_id"].astype(str).str.strip().str.upper() == ticker]
                if not ca_df.empty
                else pd.DataFrame()
            )
            ca_label = (
                str(c_ca.iloc[-1]["pattern_label"]).strip() if not c_ca.empty else "N/A"
            )

            portfolio_data.append(
                {
                    "ticker": ticker,
                    "company_name": cname,
                    "sector": sector,
                    "sub_sector": sub_sector,
                    "kpis": {
                        "roe": (roe_curr, roe_chg, roe_arrow, roe_lbl),
                        "roce": (roce_curr, roce_chg, roce_arrow, roce_lbl),
                        "npm": (npm_curr, npm_chg, npm_arrow, npm_lbl),
                        "de": (de_curr, de_chg, de_arrow, de_lbl),
                        "cagr": (cagr_curr, cagr_chg, cagr_arrow, cagr_lbl),
                        "fcf": (fcf_curr, fcf_chg, fcf_arrow, fcf_lbl),
                    },
                    "pl_years": pl_years,
                    "sales": sales_list,
                    "net_profit": np_list,
                    "roe_series": roe_series,
                    "roce_series": roce_series,
                    "pros": pros,
                    "cons": cons,
                    "capital_allocation_label": ca_label,
                }
            )

        logger.info(f"Loaded portfolio data for {len(portfolio_data)} companies.")
        return portfolio_data

    finally:
        conn.close()


# ==============================================================================
# FAST COMPACT MATPLOTLIB CHARTS FOR PORTFOLIO SUMMARY
# ==============================================================================


def generate_compact_revenue_np_chart(
    years: List[str], sales: List[float], net_profit: List[float]
) -> io.BytesIO:
    """
    Render 10-Year Revenue & Net Profit trend bar charts for 1-page summary.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.4, 2.0), dpi=180)

    if not years:
        years = ["N/A"]
        sales = [0]
        net_profit = [0]

    ax1.bar(years, sales, color="#2563EB", width=0.55)
    ax1.set_title(
        "10-Year Revenue Trend (₹ Cr)",
        fontsize=8.5,
        fontweight="bold",
        color="#0F172A",
        pad=4,
    )
    ax1.tick_params(axis="x", rotation=45, labelsize=6.0)
    ax1.tick_params(axis="y", labelsize=6.0)
    ax1.grid(axis="y", linestyle="--", alpha=0.3)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    colors_np = ["#16A34A" if v >= 0 else "#DC2626" for v in net_profit]
    ax2.bar(years, net_profit, color=colors_np, width=0.55)
    ax2.set_title(
        "10-Year Net Profit Trend (₹ Cr)",
        fontsize=8.5,
        fontweight="bold",
        color="#0F172A",
        pad=4,
    )
    ax2.tick_params(axis="x", rotation=45, labelsize=6.0)
    ax2.tick_params(axis="y", labelsize=6.0)
    ax2.grid(axis="y", linestyle="--", alpha=0.3)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf


def generate_compact_roe_roce_chart(
    years: List[str], roe_series: List[float], roce_series: List[float]
) -> io.BytesIO:
    """
    Render 10-Year ROE vs ROCE line chart for 1-page summary.
    """
    fig, ax_roe = plt.subplots(figsize=(7.4, 1.9), dpi=180)

    if not years:
        years = ["N/A"]
        roe_series = [0]
        roce_series = [0]

    roe_clean = [np.nan if v is None or pd.isna(v) else v for v in roe_series]
    roce_clean = [np.nan if v is None or pd.isna(v) else v for v in roce_series]

    ax_roe.plot(
        years,
        roe_clean,
        color="#2563EB",
        marker="o",
        markersize=3.5,
        linewidth=1.5,
        label="ROE (%)",
    )
    ax_roe.set_ylabel("ROE (%)", color="#2563EB", fontsize=7.0, fontweight="bold")
    ax_roe.tick_params(axis="y", labelcolor="#2563EB", labelsize=6.0)
    ax_roe.tick_params(axis="x", labelsize=6.0)
    ax_roe.grid(axis="y", linestyle="--", alpha=0.3)

    ax_roce = ax_roe.twinx()
    ax_roce.plot(
        years,
        roce_clean,
        color="#DC2626",
        marker="s",
        markersize=3.5,
        linestyle="--",
        linewidth=1.5,
        label="ROCE (%)",
    )
    ax_roce.set_ylabel("ROCE (%)", color="#DC2626", fontsize=7.0, fontweight="bold")
    ax_roce.tick_params(axis="y", labelcolor="#DC2626", labelsize=6.0)

    lines1, labels1 = ax_roe.get_legend_handles_labels()
    lines2, labels2 = ax_roce.get_legend_handles_labels()
    ax_roe.legend(
        lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=6.0, frameon=True
    )

    plt.title(
        "10-Year Profitability Trajectory: ROE vs ROCE",
        fontsize=8.0,
        fontweight="bold",
        color="#0F172A",
        pad=4,
    )
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf


# ==============================================================================
# MAIN PORTFOLIO PDF GENERATOR
# ==============================================================================


def generate_portfolio_summary_pdf(
    output_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> Path:
    """
    Generate the Portfolio Summary PDF containing one page per company, sorted alphabetically by NSE Ticker.

    Args:
        output_path: Destination path for generated PDF. Defaults to reports/portfolio/portfolio_summary.pdf.
        db_path: Path to nifty100.db SQLite database.

    Returns:
        Path to generated PDF file.
    """
    logger.info("Starting Portfolio Summary PDF Generation...")

    if output_path is None:
        PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
        output_path = PORTFOLIO_PDF_PATH
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Fetch portfolio data (sorted by ticker ASC)
    companies_data = fetch_portfolio_companies_data(db_path)
    total_companies = len(companies_data)

    if total_companies == 0:
        logger.error("No company records found for Portfolio Summary PDF.")
        raise ValueError("No company records available.")

    # 2. Setup Document (A4, 28pt margins)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=28,
        rightMargin=28,
        topMargin=28,
        bottomMargin=28,
    )

    usable_width = 539.27

    # Styles
    header_title_style = ParagraphStyle(
        "PHeaderTitle",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        textColor=colors.white,
    )
    header_sub_style = ParagraphStyle(
        "PHeaderSub",
        fontName="Helvetica",
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor("#CBD5E1"),
    )
    section_heading_style = ParagraphStyle(
        "PSectionHeading",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=3,
    )
    kpi_title_style = ParagraphStyle(
        "PKPITitle",
        fontName="Helvetica-Bold",
        fontSize=6.5,
        leading=7.5,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    kpi_val_style = ParagraphStyle(
        "PKPIVal",
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=13.5,
        textColor=colors.HexColor("#1E3A8A"),
        alignment=1,
    )
    kpi_sub_style = ParagraphStyle(
        "PKPISub",
        fontName="Helvetica",
        fontSize=6.0,
        leading=7.0,
        textColor=colors.HexColor("#64748B"),
        alignment=1,
    )
    pro_bullet_style = ParagraphStyle(
        "PProBullet",
        fontName="Helvetica",
        fontSize=7.0,
        leading=8.5,
        textColor=colors.HexColor("#14532D"),
    )
    con_bullet_style = ParagraphStyle(
        "PConBullet",
        fontName="Helvetica",
        fontSize=7.0,
        leading=8.5,
        textColor=colors.HexColor("#7F1D1D"),
    )

    story = []

    def fmt_val_pct(v):
        """Format percentage value into string."""
        return f"{float(v):.1f}%" if v is not None and pd.notna(v) else "N/A"

    def fmt_val_num(v, fmt="{:.2f}"):
        """Format numeric value into string."""
        return fmt.format(float(v)) if v is not None and pd.notna(v) else "N/A"

    def fmt_val_fcf(v):
        """Format Free Cash Flow in Crores/Thousands."""
        if v is None or pd.isna(v):
            return "N/A"
        val = float(v)
        if abs(val) >= 100000:
            return f"₹{val/1000:.1f}k Cr"
        return f"₹{val:,.0f} Cr"

    # Build 1 page per company
    for idx, data in enumerate(companies_data):
        # 1. Header Bar (Navy Background)
        header_content = [
            [
                Paragraph(
                    f"{data['company_name']} <font size=9.5 color='#38BDF8'>({data['ticker']})</font>",
                    header_title_style,
                ),
                Paragraph(
                    f"<b>Ticker:</b> {data['ticker']} &nbsp;|&nbsp; <b>Sector:</b> {data['sector']}",
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
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(header_table)
        story.append(Spacer(1, 6))

        # 2. Top 6 KPI Cards (2 rows x 3 columns) with YoY Trend Indicators
        kpis = data["kpis"]
        roe_v, roe_c, roe_a, roe_l = kpis["roe"]
        roce_v, roce_c, roce_a, roce_l = kpis["roce"]
        npm_v, npm_c, npm_a, npm_l = kpis["npm"]
        de_v, de_c, de_a, de_l = kpis["de"]
        cagr_v, cagr_c, cagr_a, cagr_l = kpis["cagr"]
        fcf_v, fcf_c, fcf_a, fcf_l = kpis["fcf"]

        kpi_grid = [
            [
                [
                    Paragraph("RETURN ON EQUITY", kpi_title_style),
                    Paragraph(f"{fmt_val_pct(roe_v)} &nbsp; {roe_a}", kpi_val_style),
                    Paragraph(f"YoY: {roe_c}", kpi_sub_style),
                ],
                [
                    Paragraph("RETURN ON CAPITAL", kpi_title_style),
                    Paragraph(f"{fmt_val_pct(roce_v)} &nbsp; {roce_a}", kpi_val_style),
                    Paragraph(f"YoY: {roce_c}", kpi_sub_style),
                ],
                [
                    Paragraph("NET PROFIT MARGIN", kpi_title_style),
                    Paragraph(f"{fmt_val_pct(npm_v)} &nbsp; {npm_a}", kpi_val_style),
                    Paragraph(f"YoY: {npm_c}", kpi_sub_style),
                ],
            ],
            [
                [
                    Paragraph("DEBT-TO-EQUITY", kpi_title_style),
                    Paragraph(f"{fmt_val_num(de_v)} &nbsp; {de_a}", kpi_val_style),
                    Paragraph(f"YoY: {de_c}", kpi_sub_style),
                ],
                [
                    Paragraph("REVENUE CAGR (5Y)", kpi_title_style),
                    Paragraph(f"{fmt_val_pct(cagr_v)} &nbsp; {cagr_a}", kpi_val_style),
                    Paragraph(f"YoY: {cagr_c}", kpi_sub_style),
                ],
                [
                    Paragraph("FREE CASH FLOW", kpi_title_style),
                    Paragraph(f"{fmt_val_fcf(fcf_v)} &nbsp; {fcf_a}", kpi_val_style),
                    Paragraph(f"YoY: {fcf_c}", kpi_sub_style),
                ],
            ],
        ]

        card_table_rows = []
        for row in kpi_grid:
            cell_row = []
            for card in row:
                t = Table([[card[0]], [card[1]], [card[2]]], colWidths=[173])
                t.setStyle(
                    TableStyle(
                        [
                            (
                                "BACKGROUND",
                                (0, 0),
                                (-1, -1),
                                colors.HexColor("#F8FAFC"),
                            ),
                            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#E2E8F0")),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
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
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        story.append(
            Paragraph(
                "<b>KEY FINANCIAL KPIS & YoY TREND INDICATORS</b>",
                section_heading_style,
            )
        )
        story.append(kpi_grid_table)
        story.append(Spacer(1, 6))

        # 3. 10-Year Revenue & Net Profit Bar Charts
        story.append(
            Paragraph(
                "<b>FINANCIAL PERFORMANCE & PROFITABILITY TRAJECTORY</b>",
                section_heading_style,
            )
        )
        buf_rev_np = generate_compact_revenue_np_chart(
            data["pl_years"], data["sales"], data["net_profit"]
        )
        img_rev_np = Image(buf_rev_np, width=usable_width, height=140)
        story.append(img_rev_np)
        story.append(Spacer(1, 5))

        # 4. 10-Year ROE vs ROCE Dual Axis Line Chart
        buf_roe_roce = generate_compact_roe_roce_chart(
            data["pl_years"], data["roe_series"], data["roce_series"]
        )
        img_roe_roce = Image(buf_roe_roce, width=usable_width, height=132)
        story.append(img_roe_roce)
        story.append(Spacer(1, 6))

        # 5. Capital Allocation Classification Badge
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

        badge_p = Paragraph(
            f"<b>CAPITAL ALLOCATION CLASSIFICATION:</b> <font color='{badge_text_color}'><b>{ca_label.upper()}</b></font> &nbsp;|&nbsp; <font size=7 color='#475569'>Operating & Financing Cash Flow Dynamics</font>",
            ParagraphStyle(
                "PBadgeStyle",
                fontName="Helvetica",
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#0F172A"),
            ),
        )

        badge_table = Table([[badge_p]], colWidths=[usable_width])
        badge_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), badge_bg),
                    ("BOX", (0, 0), (-1, -1), 0.75, badge_border),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(badge_table)
        story.append(Spacer(1, 6))

        # 6. Pros & Cons Insights (NLP Generated)
        pros_list = (
            data["pros"]
            if data["pros"]
            else [
                "Company maintains robust baseline operating margins.",
                "Positive historical operating cash flow generation.",
            ]
        )
        cons_list = (
            data["cons"]
            if data["cons"]
            else [
                "Valuation multiples reflect earnings expectations.",
                "Monitor sector cyclicality and input cost trends.",
            ]
        )

        pros_cells = [
            Paragraph(
                "<b>INVESTMENT STRENGTHS (PROS)</b>",
                ParagraphStyle(
                    "PProHead",
                    fontName="Helvetica-Bold",
                    fontSize=7.5,
                    leading=9,
                    textColor=colors.HexColor("#15803D"),
                ),
            )
        ]
        for p_item in pros_list[:3]:  # Top 3 pros
            pros_cells.append(
                Paragraph(
                    f"<font color='#16A34A'><b>•</b></font> {p_item}", pro_bullet_style
                )
            )

        cons_cells = [
            Paragraph(
                "<b>KEY RISKS & CONCERNS (CONS)</b>",
                ParagraphStyle(
                    "PConHead",
                    fontName="Helvetica-Bold",
                    fontSize=7.5,
                    leading=9,
                    textColor=colors.HexColor("#B91C1C"),
                ),
            )
        ]
        for c_item in cons_list[:3]:  # Top 3 cons
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
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BBF7D0")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )

        cons_table = Table([[cell] for cell in cons_cells], colWidths=[260])
        cons_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FEE2E2")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FEF2F2")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#FECACA")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
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

        # PageBreak between companies (except after last company)
        if idx < total_companies - 1:
            story.append(PageBreak())

    # 3. Canvas Footer Callback
    def add_portfolio_footer(canvas, doc):
        """Draw running footer on PDF page canvas."""
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        page_num = canvas.getPageNumber()
        footer_text = f"Nifty 100 Financial Intelligence Platform | Executive Portfolio Summary Report | Page {page_num} of {total_companies}"
        canvas.drawString(28, 15, footer_text)
        canvas.drawRightString(A4[0] - 28, 15, "Confidential - Portfolio Intelligence")
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.5)
        canvas.line(28, 25, A4[0] - 28, 25)
        canvas.restoreState()

    doc.build(
        story, onFirstPage=add_portfolio_footer, onLaterPages=add_portfolio_footer
    )
    logger.info(
        f"Successfully generated Portfolio Summary PDF ({total_companies} pages) at: {output_path.resolve()}"
    )

    # Also save a copy in output/ directory if path is in reports/portfolio/
    output_copy = OUTPUT_DIR / "portfolio_summary.pdf"
    output_copy.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "rb") as src, open(output_copy, "wb") as dst:
        dst.write(src.read())

    return output_path


if __name__ == "__main__":
    generate_portfolio_summary_pdf()
