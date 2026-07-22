"""
04_peers.py - Peer Comparison Screen for Nifty 100 Analytics.

Interactive peer comparison tool featuring:
1. Selection across all 11 peer groups.
2. Target company selector within the selected peer group.
3. Plotly Scatterpolar (Radar Chart) comparing the selected company's 8 key metrics with the peer group average.
4. Side-by-side KPI comparison table highlighting the benchmark company.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Resolve project imports
current_file = Path(__file__).resolve()
if "src" in current_file.parts:
    PROJECT_ROOT = current_file.parents[3]
else:
    PROJECT_ROOT = current_file.parents[1]

DASHBOARD_DIR = PROJECT_ROOT / "src" / "dashboard"
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import get_peers, get_db_path
from src.screener.presets import load_and_score_data
from src.analytics.radar import load_radar_data, RADAR_METRIC_LABELS

# List of all 11 peer groups in Nifty 100
PEER_GROUPS_LIST = [
    "Private Banks",
    "Public Sector Banks",
    "IT Services",
    "Pharmaceuticals",
    "Automobiles",
    "Life Insurance",
    "Oil & Gas",
    "Power & Utilities",
    "Steel",
    "FMCG",
    "Consumer Finance"
]

RADAR_SCORE_COLS = [
    "ROE_score",
    "ROCE_score",
    "Net_Profit_Margin_score",
    "Debt_to_Equity_score",
    "FCF_Score",
    "PAT_CAGR_5Y_score",
    "Revenue_CAGR_5Y_score",
    "Composite_Quality_Score"
]


@st.cache_data(ttl=600)
def load_peer_comparison_datasets():
    """
    Load database peer groups, scored financials, and radar score metrics cached for performance.
    """
    db_path = get_db_path()
    df_peers_all = get_peers()
    df_scored_all = load_and_score_data(db_path, year=2024)
    df_radar_all = load_radar_data(db_path, year="2024")
    return df_peers_all, df_scored_all, df_radar_all


# Page Header
st.markdown('<h1 class="gradient-header">⚖️ Peer Comparison & Industry Benchmarking</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Evaluate fundamental performance, radar metrics & side-by-side KPIs across 11 industry peer groups</p>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Load Datasets
# ---------------------------------------------------------
df_peers_all, df_scored_all, df_radar_all = load_peer_comparison_datasets()

if df_peers_all.empty:
    st.error("No peer group data available in database.")
    st.stop()

# ---------------------------------------------------------
# Selection Controls: Peer Group & Target Company
# ---------------------------------------------------------
col_sel1, col_sel2 = st.columns([1, 1])

# Available peer groups from DB
available_db_groups = df_peers_all["peer_group_name"].dropna().unique().tolist()
ordered_groups = [g for g in PEER_GROUPS_LIST if g in available_db_groups] + [g for g in available_db_groups if g not in PEER_GROUPS_LIST]

with col_sel1:
    selected_peer_group = st.selectbox(
        "📂 Select Industry Peer Group (11 Groups):",
        options=ordered_groups,
        index=0,
        help="Choose one of the 11 Nifty 100 industry peer groups."
    )

# Filter companies belonging to selected peer group
df_pg_members = df_peers_all[df_peers_all["peer_group_name"] == selected_peer_group].copy()

if df_pg_members.empty:
    st.warning(f"No constituents found for peer group '{selected_peer_group}'. Please select another group.")
    st.stop()

# Identify Benchmark Company in peer group
benchmark_match = df_pg_members[
    df_pg_members["is_benchmark"].astype(str).str.lower().isin(["true", "1", "yes"])
]
benchmark_ticker = benchmark_match["company_id"].iloc[0] if not benchmark_match.empty else df_pg_members["company_id"].iloc[0]

# Build dropdown choices for company selector
company_options = []
company_ticker_map = {}

for _, row in df_pg_members.iterrows():
    cid = str(row["company_id"]).strip()
    cname = str(row.get("company_name", cid)).strip()
    is_b = str(row.get("is_benchmark", "")).lower() in ["true", "1", "yes"]
    badge = " (⭐ Benchmark)" if is_b else ""
    label = f"{cid} - {cname}{badge}"
    company_options.append(label)
    company_ticker_map[label] = cid

# Determine default index (select benchmark company by default)
default_idx = 0
for idx, opt in enumerate(company_options):
    if company_ticker_map[opt] == benchmark_ticker:
        default_idx = idx
        break

with col_sel2:
    selected_company_label = st.selectbox(
        "🏢 Select Company to Compare:",
        options=company_options,
        index=default_idx,
        help="Select a specific company in the peer group for 8-axis radar comparison."
    )

selected_company_id = company_ticker_map[selected_company_label]

st.markdown("---")

# ---------------------------------------------------------
# Merge Scored & Radar Financial Data for Peer Group
# ---------------------------------------------------------
# Merge peer group definition with scored financial dataset
df_peer_merged = pd.merge(
    df_pg_members[["company_id", "peer_group_name", "is_benchmark"]],
    df_scored_all,
    on="company_id",
    how="left"
)

# Also merge radar percentile scores if missing
if not df_radar_all.empty:
    radar_cols_needed = ["id"] + [c for c in RADAR_SCORE_COLS if c not in df_peer_merged.columns or df_peer_merged[c].isna().any()]
    if len(radar_cols_needed) > 1:
        df_radar_sub = df_radar_all[radar_cols_needed].drop_duplicates(subset=["id"])
        df_peer_merged = df_peer_merged.merge(df_radar_sub, left_on="company_id", right_on="id", how="left")

# Fill missing company names
df_peer_merged["company_name"] = df_peer_merged["company_name"].fillna(df_peer_merged["company_id"])

# Extract target company row
target_rows = df_peer_merged[df_peer_merged["company_id"] == selected_company_id]

if target_rows.empty:
    st.warning(f"Financial record for target company '{selected_company_id}' is unavailable.")
    target_row = pd.Series({"company_id": selected_company_id, "company_name": selected_company_id})
else:
    target_row = target_rows.iloc[0]

# Extract benchmark company row
benchmark_rows = df_peer_merged[df_peer_merged["company_id"] == benchmark_ticker]
benchmark_row = benchmark_rows.iloc[0] if not benchmark_rows.empty else target_row

# ---------------------------------------------------------
# Top Row: 4 Metric Highlight Cards (Target vs Peer Group Avg)
# ---------------------------------------------------------
pg_name_str = selected_peer_group
target_name_str = target_row.get("company_name", selected_company_id)

st.markdown(f"### 📊 Key Performance Comparison: `{target_name_str}` vs. `{pg_name_str}`")

kc1, kc2, kc3, kc4 = st.columns(4)

with kc1:
    target_roe = target_row.get("return_on_equity_pct")
    peer_avg_roe = df_peer_merged["return_on_equity_pct"].mean()
    t_roe_str = f"{target_roe:.2f}%" if pd.notna(target_roe) else "N/A"
    p_roe_str = f"{peer_avg_roe:.2f}%" if pd.notna(peer_avg_roe) else "N/A"
    st.metric("ROE (%)", t_roe_str, delta=f"Peer Avg: {p_roe_str}", delta_color="normal")

with kc2:
    target_qs = target_row.get("composite_quality_score")
    peer_avg_qs = df_peer_merged["composite_quality_score"].mean()
    t_qs_str = f"{target_qs:.1f}" if pd.notna(target_qs) else "N/A"
    p_qs_str = f"{peer_avg_qs:.1f}" if pd.notna(peer_avg_qs) else "N/A"
    st.metric("Composite Quality Score", t_qs_str, delta=f"Peer Avg: {p_qs_str}", delta_color="normal")

with kc3:
    target_de = target_row.get("debt_to_equity")
    peer_avg_de = df_peer_merged["debt_to_equity"].mean()
    t_de_str = f"{target_de:.2f}" if pd.notna(target_de) else "N/A"
    p_de_str = f"{peer_avg_de:.2f}" if pd.notna(peer_avg_de) else "N/A"
    st.metric("Debt-to-Equity", t_de_str, delta=f"Peer Avg: {p_de_str}", delta_color="inverse")

with kc4:
    target_fcf = target_row.get("free_cash_flow_cr")
    peer_avg_fcf = df_peer_merged["free_cash_flow_cr"].mean()
    t_fcf_str = f"₹{target_fcf:,.0f} Cr" if pd.notna(target_fcf) else "N/A"
    p_fcf_str = f"₹{peer_avg_fcf:,.0f} Cr" if pd.notna(peer_avg_fcf) else "N/A"
    st.metric("Free Cash Flow (Cr)", t_fcf_str, delta=f"Peer Avg: {p_fcf_str}", delta_color="normal")

st.markdown("---")

# ---------------------------------------------------------
# Plotly Scatterpolar (Radar Chart) Section
# ---------------------------------------------------------
col_radar_left, col_radar_right = st.columns([3, 2])

with col_radar_left:
    st.subheader(f"🎯 8-Axis Radar Performance Profile ({selected_company_id})")
    
    # Define 8 radar axes
    radar_labels = [
        "ROE",
        "ROCE",
        "Net Profit Margin",
        "Debt-to-Equity Score",
        "FCF Score",
        "PAT CAGR 5Y",
        "Revenue CAGR 5Y",
        "Composite Quality"
    ]
    
    # Helper to retrieve score safely (0 to 100)
    def get_score_vector(row_series):
        scores = []
        for col in RADAR_SCORE_COLS:
            val = row_series.get(col)
            if pd.isna(val) or val is None:
                scores.append(50.0)
            else:
                scores.append(float(val))
        return scores

    target_scores = get_score_vector(target_row)
    
    # Calculate peer group average scores
    peer_scores_list = []
    for col in RADAR_SCORE_COLS:
        vals = df_peer_merged[col].dropna()
        if not vals.empty:
            peer_scores_list.append(float(vals.mean()))
        else:
            peer_scores_list.append(50.0)
            
    benchmark_scores = get_score_vector(benchmark_row)
    
    # Close loops for polar plot (append first element to end)
    r_target = target_scores + target_scores[:1]
    r_peer = peer_scores_list + peer_scores_list[:1]
    r_bench = benchmark_scores + benchmark_scores[:1]
    theta_labels = radar_labels + radar_labels[:1]
    
    # Build Plotly Scatterpolar chart
    fig_radar = go.Figure()
    
    # 1. Target Company Trace (Filled Polygon)
    fig_radar.add_trace(go.Scatterpolar(
        r=r_target,
        theta=theta_labels,
        fill="toself",
        name=f"{target_name_str} ({selected_company_id})",
        line=dict(color="#38bdf8", width=3),
        fillcolor="rgba(56, 189, 248, 0.35)",
        hovertemplate="<b>%{theta} Score</b>: %{r:.1f} / 100<extra></extra>"
    ))
    
    # 2. Peer Group Average Trace (Dashed Polygon)
    fig_radar.add_trace(go.Scatterpolar(
        r=r_peer,
        theta=theta_labels,
        fill="toself",
        name=f"{selected_peer_group} Average",
        line=dict(color="#f43f5e", width=2, dash="dash"),
        fillcolor="rgba(244, 63, 94, 0.15)",
        hovertemplate="<b>%{theta} Peer Avg</b>: %{r:.1f} / 100<extra></extra>"
    ))
    
    # 3. Benchmark Company Trace (Dotted Polygon if target is not benchmark)
    if selected_company_id != benchmark_ticker:
        fig_radar.add_trace(go.Scatterpolar(
            r=r_bench,
            theta=theta_labels,
            fill="none",
            name=f"⭐ Benchmark: {benchmark_ticker}",
            line=dict(color="#34d399", width=2, dash="dot"),
            hovertemplate="<b>%{theta} Benchmark</b>: %{r:.1f} / 100<extra></extra>"
        ))
        
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor="#334155",
                tickfont=dict(color="#94a3b8", size=9)
            ),
            angularaxis=dict(
                gridcolor="#334155",
                tickfont=dict(color="#f8fafc", size=11, weight="bold")
            ),
            bgcolor="rgba(0,0,0,0)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.12,
            xanchor="center",
            x=0.5
        ),
        margin=dict(t=50, b=30, l=40, r=40)
    )
    
    st.plotly_chart(fig_radar, use_container_width=True)

with col_radar_right:
    st.subheader("💡 Radar Metric Insights")
    st.markdown(f"""
    The radar chart evaluates fundamental parameters on a normalized **0-100 percentile scale** relative to all Nifty 100 companies:
    
    - **ROE & ROCE**: Capital efficiency and return on invested equity/capital.
    - **Net Profit Margin**: Bottom-line profitability per rupee of revenue.
    - **Debt-to-Equity Score**: Inverse leverage score (*higher score = lower financial risk*).
    - **FCF Score**: Free Cash Flow generation quality.
    - **CAGRs (5Y)**: 5-year compounding trajectory for revenue and PAT.
    - **Composite Quality**: Overall weighted multi-factor financial strength score.
    """)
    
    st.info(f"**Benchmark Company for {selected_peer_group}:**\n\n"
            f"⭐ **{benchmark_ticker}** ({df_peer_merged[df_peer_merged['company_id']==benchmark_ticker]['company_name'].values[0] if not df_peer_merged[df_peer_merged['company_id']==benchmark_ticker].empty else benchmark_ticker})")

st.markdown("---")

# ---------------------------------------------------------
# Side-by-Side KPI Comparison Table
# ---------------------------------------------------------
st.markdown(f"### 📋 Side-by-Side Peer Group KPI Comparison (`{selected_peer_group}`)")
st.caption("Benchmark company row is highlighted below for clear visual contrast:")

# Prepare comparison table
df_kpi_table = df_peer_merged.copy()

# Add benchmark status column
df_kpi_table["Benchmark Status"] = df_kpi_table["company_id"].apply(
    lambda cid: "⭐ Benchmark" if cid == benchmark_ticker else "Peer Constituent"
)

# Define display column mapping
kpi_columns_map = {
    "company_id": "Ticker",
    "company_name": "Company Name",
    "Benchmark Status": "Benchmark",
    "composite_quality_score": "Composite Score",
    "return_on_equity_pct": "ROE (%)",
    "roce_percentage": "ROCE (%)",
    "net_profit_margin_pct": "NPM (%)",
    "debt_to_equity": "Debt-to-Equity",
    "free_cash_flow_cr": "FCF (₹ Cr)",
    "revenue_cagr_5yr": "Rev CAGR (5Y)",
    "pat_cagr_5yr": "PAT CAGR (5Y)",
    "pe_ratio": "P/E Ratio"
}

available_kpi_cols = [c for c in kpi_columns_map.keys() if c in df_kpi_table.columns]
df_table_render = df_kpi_table[available_kpi_cols].rename(columns=kpi_columns_map)

# Sort table to place Benchmark row at top or highlighted position
df_table_render = df_table_render.sort_values(by="Benchmark", ascending=False).reset_index(drop=True)

# Highlight benchmark row using Pandas Styler
def highlight_benchmark_row(row):
    is_b = str(row.get("Benchmark", "")).startswith("⭐")
    if is_b:
        return ["background-color: rgba(56, 189, 248, 0.25); font-weight: bold; border-left: 4px solid #38bdf8"] * len(row)
    return [""] * len(row)

styled_kpi_df = df_table_render.style.apply(highlight_benchmark_row, axis=1)

st.dataframe(
    styled_kpi_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", help="NSE Ticker Symbol"),
        "Company Name": st.column_config.TextColumn("Company Name"),
        "Benchmark": st.column_config.TextColumn("Benchmark", help="Peer group benchmark designation"),
        "Composite Score": st.column_config.NumberColumn("Composite Score", format="%.1f / 100"),
        "ROE (%)": st.column_config.NumberColumn("ROE (%)", format="%.2f%%"),
        "ROCE (%)": st.column_config.NumberColumn("ROCE (%)", format="%.2f%%"),
        "NPM (%)": st.column_config.NumberColumn("NPM (%)", format="%.2f%%"),
        "Debt-to-Equity": st.column_config.NumberColumn("Debt-to-Equity", format="%.2f"),
        "FCF (₹ Cr)": st.column_config.NumberColumn("FCF (₹ Cr)", format="₹%,.0f Cr"),
        "Rev CAGR (5Y)": st.column_config.NumberColumn("Rev CAGR (5Y)", format="%.2f%%"),
        "PAT CAGR (5Y)": st.column_config.NumberColumn("PAT CAGR (5Y)", format="%.2f%%"),
        "P/E Ratio": st.column_config.NumberColumn("P/E Ratio", format="%.2fx")
    }
)

# ---------------------------------------------------------
# Action / Export Row
# ---------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
col_exp1, col_exp2 = st.columns([3, 1])

with col_exp2:
    csv_peer_bytes = df_table_render.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"📥 Download {selected_peer_group} KPIs (CSV)",
        data=csv_peer_bytes,
        file_name=f"{selected_peer_group.lower().replace(' ', '_')}_peer_kpis.csv",
        mime="text/csv",
        use_container_width=True
    )
