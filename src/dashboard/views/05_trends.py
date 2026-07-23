"""
05_trends.py - Multi-Year Financial Trend Analysis Page.

Features:
- Company search box with autocomplete.
- Multi-select dropdown allowing users to overlay up to 3 financial metrics.
- 10-Year interactive Plotly line chart displaying selected metrics.
- Year-over-Year (YoY) percentage change annotations on data points.
- Dual Y-axes for multi-unit metric overlays, responsive legends, and hover tooltips.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add project root and dashboard directory to sys.path
PROJECT_ROOT = (
    Path(__file__).resolve().parents[3]
    if len(Path(__file__).resolve().parents) > 3
    else Path(__file__).resolve().parents[1]
)
DASHBOARD_DIR = PROJECT_ROOT / "src" / "dashboard"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from src.dashboard.utils.db import (
    get_companies,
    get_pl,
    get_ratios,
    get_valuation,
    get_cf,
)

# Page Header
st.markdown(
    '<h1 class="gradient-header">📈 Multi-Year Financial Trend Analysis</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-header">Analyze historical performance trajectories, overlay key financial metrics, and inspect Year-over-Year (YoY) growth rates.</p>',
    unsafe_allow_html=True,
)

# Fetch company directory
df_companies = get_companies()
if df_companies.empty:
    st.error("No company records found in database.")
    st.stop()

# Build company search dropdown format: "TCS - Tata Consultancy Services Ltd"
company_map = {}
company_options = []
for _, row in df_companies.iterrows():
    cid = str(row["id"]).strip()
    cname = str(row.get("company_name", cid)).strip()
    display_str = f"{cid} - {cname}"
    company_options.append(display_str)
    company_map[display_str] = cid

# Default selection to TCS if available, else first company
default_idx = 0
for idx, opt in enumerate(company_options):
    if opt.startswith("TCS"):
        default_idx = idx
        break

# UI Control Bar
col_search, col_metrics = st.columns([1, 2])

with col_search:
    selected_company_str = st.selectbox(
        "🔍 Search & Select Company:",
        options=company_options,
        index=default_idx,
        help="Type ticker symbol or company name to search",
    )
    selected_ticker = company_map[selected_company_str]

# Metric definitions mapping
METRIC_DEFINITIONS = {
    "Revenue (Sales - ₹ Cr)": ("pl", "sales", "₹ Cr", False),
    "Net Profit (PAT - ₹ Cr)": ("pl", "net_profit", "₹ Cr", False),
    "Operating Profit (EBIT - ₹ Cr)": ("pl", "operating_profit", "₹ Cr", False),
    "OPM % (Operating Margin)": ("pl", "operating_profit_margin_pct", "%", True),
    "ROE % (Return on Equity)": ("ratios", "return_on_equity_pct", "%", True),
    "ROCE % (Return on Capital)": ("companies", "roce_percentage", "%", True),
    "EPS (Earnings per Share - ₹)": ("ratios", "earnings_per_share", "₹", False),
    "FCF (Free Cash Flow - ₹ Cr)": ("ratios", "free_cash_flow_cr", "₹ Cr", False),
    "Market Cap (₹ Cr)": ("valuation", "market_cap_crore", "₹ Cr", False),
    "P/E Ratio": ("valuation", "pe_ratio", "x", True),
    "Debt-to-Equity": ("ratios", "debt_to_equity", "x", True),
}

with col_metrics:
    selected_metric_keys = st.multiselect(
        "📊 Overlay Financial Metrics (Select 1 to 3):",
        options=list(METRIC_DEFINITIONS.keys()),
        default=[
            "Revenue (Sales - ₹ Cr)",
            "Net Profit (PAT - ₹ Cr)",
            "ROE % (Return on Equity)",
        ],
        max_selections=3,
        help="Select up to 3 metrics to overlay on the trend chart",
    )

if not selected_metric_keys:
    st.warning("⚠️ Please select at least one metric to display trends.")
    st.stop()

# Fetch all historical tables for target company
df_pl = get_pl(selected_ticker)
df_ratios = get_ratios(selected_ticker)
df_val = get_valuation(selected_ticker)
df_cf = get_cf(selected_ticker)

# Load base years (numeric 10-year window e.g., 2013 to 2024)
years = set()
for df_tmp in [df_pl, df_ratios, df_val, df_cf]:
    if not df_tmp.empty and "year" in df_tmp.columns:
        valid_yrs = (
            pd.to_numeric(df_tmp["year"], errors="coerce").dropna().astype(int).tolist()
        )
        years.update(valid_yrs)

sorted_years = sorted([y for y in years if y >= 2011])
if not sorted_years:
    st.warning(
        f"⚠️ **Limited historical data available:** No financial records available for {selected_company_str.split(' - ')[1]} ({selected_ticker})."
    )
    st.stop()

if len(sorted_years) < 10:
    st.info(
        f"ℹ️ **Limited historical data available:** Displaying {len(sorted_years)} years of financial trends for {selected_company_str.split(' - ')[1]} ({selected_ticker})."
    )

# Build historical master DataFrame for selected company across years
history_records = []
for y in sorted_years:
    rec = {"year": y}

    # P&L
    if not df_pl.empty and "year" in df_pl.columns:
        sub_pl = df_pl[pd.to_numeric(df_pl["year"], errors="coerce") == y]
        if not sub_pl.empty:
            for col in [
                "sales",
                "net_profit",
                "operating_profit",
                "operating_profit_margin_pct",
            ]:
                if col in sub_pl.columns:
                    rec[col] = sub_pl.iloc[0][col]

    # Ratios
    if not df_ratios.empty and "year" in df_ratios.columns:
        sub_rat = df_ratios[pd.to_numeric(df_ratios["year"], errors="coerce") == y]
        if not sub_rat.empty:
            for col in [
                "return_on_equity_pct",
                "earnings_per_share",
                "free_cash_flow_cr",
                "debt_to_equity",
            ]:
                if col in sub_rat.columns:
                    rec[col] = sub_rat.iloc[0][col]

    # Valuation
    if not df_val.empty and "year" in df_val.columns:
        sub_val = df_val[pd.to_numeric(df_val["year"], errors="coerce") == y]
        if not sub_val.empty:
            for col in ["market_cap_crore", "pe_ratio"]:
                if col in sub_val.columns:
                    rec[col] = sub_val.iloc[0][col]

    history_records.append(rec)

df_hist = pd.DataFrame(history_records).sort_values("year").reset_index(drop=True)

st.markdown("---")

# Determine Y-axis assignment (Primary vs Secondary axis based on units)
has_cr_unit = any(METRIC_DEFINITIONS[m][2] == "₹ Cr" for m in selected_metric_keys)
has_other_unit = any(
    METRIC_DEFINITIONS[m][2] in ["%", "₹", "x"] for m in selected_metric_keys
)

use_secondary_y = has_cr_unit and has_other_unit

if use_secondary_y:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
else:
    fig = go.Figure()

colors = ["#38bdf8", "#34d399", "#f43f5e"]

for idx, metric_key in enumerate(selected_metric_keys):
    src_tbl, col_name, unit_str, is_ratio = METRIC_DEFINITIONS[metric_key]

    if col_name not in df_hist.columns:
        continue

    y_vals = pd.to_numeric(df_hist[col_name], errors="coerce").values
    x_yrs = df_hist["year"].values

    # Calculate YoY % changes
    yoy_pcts = []
    text_labels = []

    for i in range(len(y_vals)):
        v_curr = y_vals[i]
        if i == 0 or pd.isna(v_curr) or pd.isna(y_vals[i - 1]) or y_vals[i - 1] == 0:
            yoy_pcts.append(None)
            text_labels.append(f"{v_curr:.1f}" if pd.notna(v_curr) else "")
        else:
            v_prev = y_vals[i - 1]
            pct = ((v_curr - v_prev) / abs(v_prev)) * 100.0
            yoy_pcts.append(pct)
            sign_str = "+" if pct >= 0 else ""
            text_labels.append(f"{v_curr:.1f}<br>({sign_str}{pct:.1f}%)")

    is_sec = use_secondary_y and (unit_str in ["%", "₹", "x"])
    color_hex = colors[idx % len(colors)]

    trace = go.Scatter(
        x=x_yrs,
        y=y_vals,
        name=f"{metric_key}",
        mode="lines+markers+text",
        text=text_labels,
        textposition="top center",
        textfont=dict(size=10, color=color_hex),
        marker=dict(size=8, color=color_hex, symbol="circle"),
        line=dict(width=3, color=color_hex),
        hovertemplate=f"<b>Year: %{{x}}</b><br>{metric_key}: %{{y:.2f}} {unit_str}<extra></extra>",
    )

    if use_secondary_y:
        fig.add_trace(trace, secondary_y=is_sec)
    else:
        fig.add_trace(trace)

# Update layout styling
fig.update_layout(
    title=dict(
        text=f"<b>10-Year Trajectory: {selected_company_str.split(' - ')[1]} ({selected_ticker})</b>",
        font=dict(size=18, color="#e2e8f0"),
    ),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15, 23, 42, 0.6)",
    font=dict(color="#e2e8f0", family="Plus Jakarta Sans"),
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        bgcolor="rgba(15, 23, 42, 0.8)",
        bordercolor="#334155",
        borderwidth=1,
    ),
    margin=dict(t=70, b=40, l=40, r=40),
    xaxis=dict(
        title="Fiscal Year",
        gridcolor="#1e293b",
        dtick=1,
        tickfont=dict(color="#94a3b8"),
    ),
    yaxis=dict(
        title="Values (₹ Cr)" if has_cr_unit else "Ratio / Percentage",
        gridcolor="#1e293b",
        zerolinecolor="#334155",
        tickfont=dict(color="#94a3b8"),
    ),
)

if use_secondary_y:
    fig.update_yaxes(
        title_text="Percentage (%) / Ratios",
        secondary_y=True,
        gridcolor="rgba(0,0,0,0)",
    )

st.plotly_chart(fig, use_container_width=True)

# Detailed Data Table
st.markdown("### 📋 Historical Financial Metrics & YoY Breakdown")
df_table = df_hist.copy()
df_table["Year"] = df_table["year"].astype(str)

display_cols = ["Year"]
for metric_key in selected_metric_keys:
    col_name = METRIC_DEFINITIONS[metric_key][1]
    if col_name in df_table.columns:
        display_cols.append(col_name)

df_table_show = df_table[display_cols].rename(
    columns={
        "sales": "Revenue (₹ Cr)",
        "net_profit": "Net Profit (₹ Cr)",
        "operating_profit": "Operating Profit (₹ Cr)",
        "operating_profit_margin_pct": "OPM %",
        "return_on_equity_pct": "ROE %",
        "roce_percentage": "ROCE %",
        "earnings_per_share": "EPS (₹)",
        "free_cash_flow_cr": "FCF (₹ Cr)",
        "market_cap_crore": "Market Cap (₹ Cr)",
        "pe_ratio": "P/E Ratio",
        "debt_to_equity": "Debt-to-Equity",
    }
)

st.dataframe(
    df_table_show.style.format(precision=2, na_rep="N/A"),
    use_container_width=True,
    hide_index=True,
)
