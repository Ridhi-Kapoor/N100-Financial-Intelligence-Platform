"""
06_sectors.py - Sector Analysis Page for Nifty 100 Analytics.

Features:
- Dropdown to select any broad sector (or "All Sectors").
- Plotly Bubble Chart:
    * X-axis: Revenue (Sales - ₹ Cr)
    * Y-axis: ROE (Return on Equity %)
    * Bubble Size: Market Capitalization (₹ Cr)
    * Bubble Color: Sub-sector
- Bar Chart showing sector median KPIs (ROE %, ROCE %, P/E, Revenue CAGR 5Y %, OPM %, D/E) below the bubble chart.
- Dynamic layout updates on sector selection change.
"""

import sys
from pathlib import Path
import math
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Add project root and dashboard directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3] if len(Path(__file__).resolve().parents) > 3 else Path(__file__).resolve().parents[1]
DASHBOARD_DIR = PROJECT_ROOT / "src" / "dashboard"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from src.dashboard.utils.db import get_sectors, get_ratios, get_companies, get_pl, get_valuation

# Header
st.markdown('<h1 class="gradient-header">📊 Broad & Sub-Sector Analytics</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Interactive sector bubble visualization, ROE vs Revenue distribution, sub-sector coloring, and median KPI benchmark comparisons.</p>', unsafe_allow_html=True)

# Load base datasets
df_sec = get_sectors()
df_comp = get_companies()
df_mc = get_valuation()
df_rat = get_ratios(year=2024)
if df_rat.empty:
    df_rat = get_ratios()
df_pl = get_pl()

if df_sec.empty:
    st.error("No sector records found in database.")
    st.stop()

# Build merged master dataset for latest available year
df_pl_latest = df_pl[pd.to_numeric(df_pl["year"], errors="coerce") == 2024].drop_duplicates("company_id") if not df_pl.empty else pd.DataFrame()
if df_pl_latest.empty and not df_pl.empty:
    df_pl_latest = df_pl.sort_values("year").groupby("company_id").last().reset_index()

df_mc_latest = df_mc[pd.to_numeric(df_mc["year"], errors="coerce") == 2024].drop_duplicates("company_id") if not df_mc.empty else pd.DataFrame()
if df_mc_latest.empty and not df_mc.empty:
    df_mc_latest = df_mc.sort_values("year").groupby("company_id").last().reset_index()

df_rat_latest = df_rat.drop_duplicates("company_id").copy() if not df_rat.empty else pd.DataFrame()

# Clean company keys
df_sec_clean = df_sec.drop_duplicates("company_id")[["company_id", "broad_sector", "sub_sector"]].copy()

df_master = df_sec_clean.copy()

# Merge metadata
if not df_comp.empty:
    comp_sub = df_comp.drop_duplicates("id")[["id", "company_name", "roce_percentage", "roe_percentage"]].rename(columns={"id": "company_id"})
    df_master = df_master.merge(comp_sub, on="company_id", how="left")

if not df_pl_latest.empty:
    df_master = df_master.merge(df_pl_latest[["company_id", "sales", "net_profit"]], on="company_id", how="left")

if not df_mc_latest.empty:
    df_master = df_master.merge(df_mc_latest[["company_id", "market_cap_crore", "pe_ratio"]], on="company_id", how="left")

if not df_rat_latest.empty:
    rat_cols = [c for c in ["company_id", "return_on_equity_pct", "operating_profit_margin_pct", "debt_to_equity", "revenue_cagr_5yr"] if c in df_rat_latest.columns]
    df_master = df_master.merge(df_rat_latest[rat_cols], on="company_id", how="left")

# Clean numeric values
for col in ["sales", "net_profit", "market_cap_crore", "pe_ratio", "return_on_equity_pct", "roce_percentage", "operating_profit_margin_pct", "debt_to_equity", "revenue_cagr_5yr"]:
    if col in df_master.columns:
        df_master[col] = pd.to_numeric(df_master[col], errors="coerce")

# Prefer return_on_equity_pct over roe_percentage
if "return_on_equity_pct" in df_master.columns and "roe_percentage" in df_master.columns:
    df_master["roe_final"] = df_master["return_on_equity_pct"].fillna(df_master["roe_percentage"])
elif "return_on_equity_pct" in df_master.columns:
    df_master["roe_final"] = df_master["return_on_equity_pct"]
else:
    df_master["roe_final"] = df_master["roe_percentage"]

# Sector Filter Control
all_broad_sectors = sorted(df_master["broad_sector"].dropna().unique().tolist())
sector_options = ["All Sectors"] + all_broad_sectors

selected_sector = st.selectbox(
    "🏢 Select Sector to Analyze:",
    options=sector_options,
    index=0,
    help="Filter charts by broad sector or select 'All Sectors' for entire Nifty 100"
)

# Filter dataset based on selection
if selected_sector == "All Sectors":
    df_filtered = df_master.copy()
else:
    df_filtered = df_master[df_master["broad_sector"] == selected_sector].copy()

if df_filtered.empty:
    st.warning(f"No company records found for sector: {selected_sector}")
    st.stop()

# Metric summary cards
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Companies", len(df_filtered))
with c2:
    med_rev = df_filtered["sales"].median()
    st.metric("Median Revenue", f"₹{med_rev:,.0f} Cr" if pd.notna(med_rev) else "N/A")
with c3:
    med_roe = df_filtered["roe_final"].median()
    st.metric("Median ROE", f"{med_roe:.1f}%" if pd.notna(med_roe) else "N/A")
with c4:
    tot_mcap = df_filtered["market_cap_crore"].sum()
    st.metric("Total Market Cap", f"₹{tot_mcap:,.0f} Cr" if pd.notna(tot_mcap) else "N/A")

st.markdown("---")

# 1. Plotly Bubble Chart (X: Revenue, Y: ROE, Size: Market Cap, Color: Sub-sector)
st.subheader(f"🎈 Revenue vs ROE % Bubble Map ({selected_sector})")
st.caption("Bubble Size = Market Capitalization (₹ Cr) | Hover to inspect company metrics")

df_bubble = df_filtered.dropna(subset=["sales", "roe_final"]).copy()
df_bubble["market_cap_size"] = df_bubble["market_cap_crore"].fillna(5000).clip(lower=1000)

if not df_bubble.empty:
    fig_bubble = px.scatter(
        df_bubble,
        x="sales",
        y="roe_final",
        size="market_cap_size",
        color="sub_sector",
        hover_name="company_name",
        hover_data={
            "company_id": True,
            "broad_sector": True,
            "sub_sector": True,
            "sales": ":,.0f",
            "roe_final": ":.1f",
            "market_cap_crore": ":,.0f",
            "market_cap_size": False
        },
        labels={
            "sales": "Revenue (Sales - ₹ Cr)",
            "roe_final": "Return on Equity (ROE %)",
            "sub_sector": "Sub-Sector",
            "market_cap_crore": "Market Cap (₹ Cr)"
        },
        size_max=50
    )
    
    fig_bubble.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        font=dict(color="#e2e8f0", family="Plus Jakarta Sans"),
        legend=dict(
            bgcolor="rgba(15, 23, 42, 0.8)",
            bordercolor="#334155",
            borderwidth=1,
            title=dict(text="<b>Sub-Sector</b>")
        ),
        margin=dict(t=30, b=40, l=40, r=40),
        xaxis=dict(
            gridcolor="#1e293b",
            zerolinecolor="#334155"
        ),
        yaxis=dict(
            gridcolor="#1e293b",
            zerolinecolor="#334155"
        )
    )
    st.plotly_chart(fig_bubble, use_container_width=True)
else:
    st.info("Insufficient valid Revenue & ROE data to render bubble chart.")

st.markdown("---")

# 2. Bar Chart of Sector Median KPIs
st.subheader("📊 Sector Median KPI Benchmarks")
st.caption("Comparison of key financial metrics across sectors")

# Calculate medians by broad_sector
kpi_cols = {
    "ROE %": "roe_final",
    "ROCE %": "roce_percentage",
    "OPM %": "operating_profit_margin_pct",
    "P/E Ratio": "pe_ratio",
    "Revenue CAGR 5Y %": "revenue_cagr_5yr",
    "Debt-to-Equity": "debt_to_equity"
}

sector_medians_df = df_master.groupby("broad_sector").agg({
    v: "median" for v in kpi_cols.values() if v in df_master.columns
}).reset_index()

rename_dict = {v: k for k, v in kpi_cols.items() if v in df_master.columns}
sector_medians_df.rename(columns=rename_dict, inplace=True)

if selected_sector != "All Sectors":
    # Highlight selected sector vs other sectors
    sector_medians_df["Highlight"] = sector_medians_df["broad_sector"].apply(
        lambda x: "Selected Sector" if x == selected_sector else "Other Sectors"
    )
    color_discrete_map = {"Selected Sector": "#38bdf8", "Other Sectors": "#475569"}
else:
    sector_medians_df["Highlight"] = "All Sectors"
    color_discrete_map = {"All Sectors": "#818cf8"}

metric_to_chart = st.selectbox(
    "Select KPI Metric for Bar Chart Comparison:",
    options=list(rename_dict.values()),
    index=0
)

fig_kpi = px.bar(
    sector_medians_df.sort_values(metric_to_chart, ascending=False),
    x="broad_sector",
    y=metric_to_chart,
    color="Highlight",
    color_discrete_map=color_discrete_map,
    text_auto=".1f",
    labels={"broad_sector": "Broad Sector", metric_to_chart: f"Median {metric_to_chart}"},
    title=f"<b>Median {metric_to_chart} by Broad Sector</b>"
)

fig_kpi.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15, 23, 42, 0.6)",
    font=dict(color="#e2e8f0", family="Plus Jakarta Sans"),
    showlegend=False,
    margin=dict(t=40, b=40, l=40, r=40),
    xaxis=dict(gridcolor="#1e293b", tickangle=-30),
    yaxis=dict(gridcolor="#1e293b", zerolinecolor="#334155")
)

st.plotly_chart(fig_kpi, use_container_width=True)

# Sector Detailed Data Table
with st.expander(f"📋 View All Companies in {selected_sector} ({len(df_filtered)} records)"):
    table_cols = ["company_id", "company_name", "sub_sector", "sales", "net_profit", "market_cap_crore", "roe_final", "pe_ratio"]
    table_show = df_filtered[[c for c in table_cols if c in df_filtered.columns]].rename(columns={
        "company_id": "Ticker",
        "company_name": "Company Name",
        "sub_sector": "Sub-Sector",
        "sales": "Revenue (₹ Cr)",
        "net_profit": "Net Profit (₹ Cr)",
        "market_cap_crore": "Market Cap (₹ Cr)",
        "roe_final": "ROE %",
        "pe_ratio": "P/E Ratio"
    })
    st.dataframe(table_show.style.format(precision=2, na_rep="N/A"), use_container_width=True, hide_index=True)
