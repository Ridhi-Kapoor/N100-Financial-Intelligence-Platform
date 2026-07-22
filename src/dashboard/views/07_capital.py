"""
07_capital.py - Capital Allocation Map Page for Nifty 100 Analytics.

Features:
- Plotly Treemap of all 92 companies grouped by the 8 Capital Allocation Patterns.
- Each rectangle represents a company sized by Market Capitalization.
- Interactive filter to inspect companies belonging to selected allocation patterns.
- Detailed hover information (Ticker, Company Name, Sector, CFO, CFI, CFF, PAT, Market Cap).
- Filterable data table displaying pattern members.
"""

import sys
from pathlib import Path
import math
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Add project root and dashboard directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3] if len(Path(__file__).resolve().parents) > 3 else Path(__file__).resolve().parents[1]
DASHBOARD_DIR = PROJECT_ROOT / "src" / "dashboard"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from src.dashboard.utils.db import get_sectors, get_companies, get_cf, get_pl, get_valuation
from src.analytics.cashflow import classify_capital_allocation

# Header
st.markdown('<h1 class="gradient-header">💰 Capital Allocation Map & Cash Flow Patterns</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Categorize all 92 Nifty 100 companies into the 8 cash flow allocation patterns based on CFO, CFI, and CFF dynamics.</p>', unsafe_allow_html=True)

# Load base datasets
df_sec = get_sectors()
df_comp = get_companies()
df_cf = get_cf()
df_pl = get_pl()
df_mc = get_valuation()

if df_sec.empty or df_cf.empty:
    st.error("Required cashflow or sector datasets not found in database.")
    st.stop()

# Get latest financial year (2024)
df_cf_latest = df_cf[pd.to_numeric(df_cf["year"], errors="coerce") == 2024].drop_duplicates("company_id")
if df_cf_latest.empty:
    df_cf_latest = df_cf.sort_values("year").groupby("company_id").last().reset_index()

df_pl_latest = df_pl[pd.to_numeric(df_pl["year"], errors="coerce") == 2024].drop_duplicates("company_id")
if df_pl_latest.empty and not df_pl.empty:
    df_pl_latest = df_pl.sort_values("year").groupby("company_id").last().reset_index()

df_mc_latest = df_mc[pd.to_numeric(df_mc["year"], errors="coerce") == 2024].drop_duplicates("company_id")
if df_mc_latest.empty and not df_mc.empty:
    df_mc_latest = df_mc.sort_values("year").groupby("company_id").last().reset_index()

# Clean company keys
df_sec_clean = df_sec.drop_duplicates("company_id")[["company_id", "broad_sector"]].copy()

df_master = df_sec_clean.copy()

if not df_comp.empty:
    comp_sub = df_comp.drop_duplicates("id")[["id", "company_name"]].rename(columns={"id": "company_id"})
    df_master = df_master.merge(comp_sub, on="company_id", how="left")
else:
    df_master["company_name"] = df_master["company_id"]

df_master = df_master.merge(df_cf_latest[["company_id", "operating_activity", "investing_activity", "financing_activity"]], on="company_id", how="left")

if not df_pl_latest.empty:
    df_master = df_master.merge(df_pl_latest[["company_id", "net_profit"]], on="company_id", how="left")

if not df_mc_latest.empty:
    df_master = df_master.merge(df_mc_latest[["company_id", "market_cap_crore"]], on="company_id", how="left")

# Apply capital allocation classifier for each company
res = df_master.apply(
    lambda r: classify_capital_allocation(
        r.get("operating_activity"),
        r.get("investing_activity"),
        r.get("financing_activity"),
        r.get("net_profit")
    ),
    axis=1
)

df_master["cfo_sign"] = [x[0] for x in res]
df_master["cfi_sign"] = [x[1] for x in res]
df_master["cff_sign"] = [x[2] for x in res]
df_master["allocation_pattern"] = [x[3] for x in res]

# Fill missing market cap
df_master["market_cap_crore"] = pd.to_numeric(df_master["market_cap_crore"], errors="coerce").fillna(5000)
df_master["market_cap_size"] = df_master["market_cap_crore"].clip(lower=1000)

# Format strings for hover
df_master["display_label"] = df_master["company_id"] + "<br>" + df_master["company_name"]

# Summary cards for top patterns
pattern_counts = df_master["allocation_pattern"].value_counts()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Shareholder Returns", pattern_counts.get("Shareholder Returns", 0), "CFO (+), CFI (-), CFF (-)")
with c2:
    st.metric("Reinvestor", pattern_counts.get("Reinvestor", 0), "High Capex Reinvestment")
with c3:
    st.metric("Growth Funded by Debt", pattern_counts.get("Growth Funded by Debt", 0), "CFF (+), CFI (-)")
with c4:
    st.metric("Distress / Liquidating", pattern_counts.get("Distress Signal", 0) + pattern_counts.get("Liquidating Assets", 0))

st.markdown("---")

# 1. Plotly Treemap
st.subheader("🧩 Capital Allocation Treemap")
st.caption("Rectangle size = Market Capitalization (₹ Cr) | Color = Capital Allocation Pattern")

# Color palette for 8 allocation patterns
pattern_colors = {
    "Shareholder Returns": "#34d399",      # Green
    "Reinvestor": "#38bdf8",              # Light Blue
    "Mixed": "#818cf8",                   # Indigo
    "Growth Funded by Debt": "#fbbf24",    # Amber
    "Liquidating Assets": "#f97316",       # Orange
    "Distress Signal": "#ef4444",          # Red
    "Pre-Revenue": "#a855f7",              # Purple
    "Cash Accumulator": "#06b6d4"          # Cyan
}

fig_treemap = px.treemap(
    df_master,
    path=[px.Constant("All Nifty 100 Companies"), "allocation_pattern", "display_label"],
    values="market_cap_size",
    color="allocation_pattern",
    color_discrete_map=pattern_colors,
    hover_data={
        "company_id": True,
        "company_name": True,
        "broad_sector": True,
        "operating_activity": ":,.0f",
        "investing_activity": ":,.0f",
        "financing_activity": ":,.0f",
        "net_profit": ":,.0f",
        "market_cap_crore": ":,.0f",
        "market_cap_size": False,
        "display_label": False
    }
)

fig_treemap.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15, 23, 42, 0.6)",
    font=dict(color="#e2e8f0", family="Plus Jakarta Sans"),
    margin=dict(t=30, b=30, l=20, r=20)
)

st.plotly_chart(fig_treemap, use_container_width=True)

st.markdown("---")

# 2. Interactive Pattern Selector & Detailed Table
st.subheader("📋 Companies by Capital Allocation Pattern")

all_patterns = sorted(df_master["allocation_pattern"].unique().tolist())
pattern_select_options = ["All Patterns"] + all_patterns

selected_pattern = st.selectbox(
    "Select Capital Allocation Pattern to Inspect:",
    options=pattern_select_options,
    index=0
)

if selected_pattern == "All Patterns":
    df_table_filtered = df_master.copy()
else:
    df_table_filtered = df_master[df_master["allocation_pattern"] == selected_pattern].copy()

st.write(f"Displaying **{len(df_table_filtered)}** companies matching pattern: `{selected_pattern}`")

table_cols = [
    "company_id", "company_name", "broad_sector", "allocation_pattern",
    "operating_activity", "investing_activity", "financing_activity", "net_profit", "market_cap_crore"
]

table_show = df_table_filtered[table_cols].rename(columns={
    "company_id": "Ticker",
    "company_name": "Company Name",
    "broad_sector": "Sector",
    "allocation_pattern": "Pattern",
    "operating_activity": "CFO (₹ Cr)",
    "investing_activity": "CFI (₹ Cr)",
    "financing_activity": "CFF (₹ Cr)",
    "net_profit": "PAT (₹ Cr)",
    "market_cap_crore": "Market Cap (₹ Cr)"
})

st.dataframe(
    table_show.style.format({
        "CFO (₹ Cr)": "{:,.0f}",
        "CFI (₹ Cr)": "{:,.0f}",
        "CFF (₹ Cr)": "{:,.0f}",
        "PAT (₹ Cr)": "{:,.0f}",
        "Market Cap (₹ Cr)": "{:,.0f}"
    }, na_rep="N/A"),
    use_container_width=True,
    hide_index=True
)
