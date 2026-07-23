"""
03_screener.py - Stock Screener Screen for Nifty 100 Analytics.

Interactive quantitative screener featuring 10 sidebar filter sliders,
6 strategy presets (Quality, Value, Growth, Dividend, Debt-Free, Turnaround),
live results table, summary KPIs, risk-return visualization, and CSV export.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

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

from src.dashboard.utils.db import get_db_path
from src.screener.presets import load_and_score_data
from src.screener.engine import apply_screener_filters

# Default slider values (relaxed filter baseline)
DEFAULT_SLIDERS = {
    "roe_min": 0.0,
    "de_max": 3.0,
    "fcf_min": -1000.0,
    "rev_cagr_min": -20.0,
    "pat_cagr_min": -20.0,
    "opm_min": 0.0,
    "pe_max": 100.0,
    "pb_max": 25.0,
    "div_yield_min": 0.0,
    "icr_min": 0.0,
}

# Strategy Presets dictionary mapping 6 presets to slider values
PRESET_CONFIGS_MAP = {
    "Quality": {
        "roe_min": 15.0,
        "de_max": 0.5,
        "fcf_min": 0.0,
        "rev_cagr_min": 5.0,
        "pat_cagr_min": 5.0,
        "opm_min": 12.0,
        "pe_max": 60.0,
        "pb_max": 15.0,
        "div_yield_min": 0.0,
        "icr_min": 3.0,
    },
    "Value": {
        "roe_min": 12.0,
        "de_max": 1.2,
        "fcf_min": 0.0,
        "rev_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 8.0,
        "pe_max": 35.0,
        "pb_max": 5.0,
        "div_yield_min": 1.0,
        "icr_min": 1.5,
    },
    "Growth": {
        "roe_min": 12.0,
        "de_max": 2.0,
        "fcf_min": 0.0,
        "rev_cagr_min": 12.0,
        "pat_cagr_min": 12.0,
        "opm_min": 10.0,
        "pe_max": 100.0,
        "pb_max": 25.0,
        "div_yield_min": 0.0,
        "icr_min": 1.5,
    },
    "Dividend": {
        "roe_min": 10.0,
        "de_max": 1.2,
        "fcf_min": 0.0,
        "rev_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 5.0,
        "pe_max": 50.0,
        "pb_max": 10.0,
        "div_yield_min": 2.0,
        "icr_min": 1.5,
    },
    "Debt-Free": {
        "roe_min": 12.0,
        "de_max": 0.05,
        "fcf_min": 0.0,
        "rev_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 5.0,
        "pe_max": 100.0,
        "pb_max": 25.0,
        "div_yield_min": 0.0,
        "icr_min": 3.0,
    },
    "Turnaround": {
        "roe_min": 8.0,
        "de_max": 1.5,
        "fcf_min": -500.0,
        "rev_cagr_min": -5.0,
        "pat_cagr_min": 0.0,
        "opm_min": 3.0,
        "pe_max": 40.0,
        "pb_max": 8.0,
        "div_yield_min": 0.0,
        "icr_min": 1.0,
    },
}


@st.cache_data(ttl=600)
def fetch_screener_base_data() -> pd.DataFrame:
    """Load and score Nifty 100 base data cached for performance."""
    db_path = get_db_path()
    return load_and_score_data(db_path, year=2024)


# Page Header
st.markdown(
    '<h1 class="gradient-header">🔍 Quantitative Stock Screener</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-header">Multi-Factor Screening Engine with Strategy Presets & Live Sector Overrides</p>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Sidebar Controls & Preset Buttons
# ---------------------------------------------------------
st.sidebar.markdown("### ⚡ Strategy Presets")
st.sidebar.caption("Click a preset to automatically update filter sliders:")

# Initialize session state for all 10 slider keys if not present
for key, default_val in DEFAULT_SLIDERS.items():
    if key not in st.session_state:
        st.session_state[key] = default_val

# Render 6 Preset Buttons in 2 columns
col_p1, col_p2 = st.sidebar.columns(2)

with col_p1:
    if st.button(
        "🏆 Quality",
        use_container_width=True,
        help="High return on equity, strong margins & low debt",
    ):
        for k, v in PRESET_CONFIGS_MAP["Quality"].items():
            st.session_state[k] = float(v)
        st.rerun()

    if st.button(
        "🚀 Growth",
        use_container_width=True,
        help="High revenue & earnings 5-year CAGR",
    ):
        for k, v in PRESET_CONFIGS_MAP["Growth"].items():
            st.session_state[k] = float(v)
        st.rerun()

    if st.button(
        "🛡️ Debt-Free",
        use_container_width=True,
        help="Near-zero leverage & strong cash flow",
    ):
        for k, v in PRESET_CONFIGS_MAP["Debt-Free"].items():
            st.session_state[k] = float(v)
        st.rerun()

with col_p2:
    if st.button(
        "💎 Value",
        use_container_width=True,
        help="Low P/E, low P/B & healthy profitability",
    ):
        for k, v in PRESET_CONFIGS_MAP["Value"].items():
            st.session_state[k] = float(v)
        st.rerun()

    if st.button(
        "💰 Dividend",
        use_container_width=True,
        help="High dividend yield & stable balance sheet",
    ):
        for k, v in PRESET_CONFIGS_MAP["Dividend"].items():
            st.session_state[k] = float(v)
        st.rerun()

    if st.button(
        "🔄 Turnaround",
        use_container_width=True,
        help="Improving leverage profile & profit recovery",
    ):
        for k, v in PRESET_CONFIGS_MAP["Turnaround"].items():
            st.session_state[k] = float(v)
        st.rerun()

if st.sidebar.button("🔄 Reset All Filters", use_container_width=True):
    for k, v in DEFAULT_SLIDERS.items():
        st.session_state[k] = float(v)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Filter Sliders (10 Metrics)")

# 10 Sidebar Sliders
roe_min = st.sidebar.slider(
    "ROE (Minimum) (%)",
    min_value=-20.0,
    max_value=100.0,
    key="roe_min",
    step=1.0,
    help="Minimum Return on Equity percentage",
)

de_max = st.sidebar.slider(
    "Debt-to-Equity (Maximum)",
    min_value=0.0,
    max_value=5.0,
    key="de_max",
    step=0.1,
    help="Maximum Debt-to-Equity ratio (waived for Financial sector)",
)

fcf_min = st.sidebar.slider(
    "Free Cash Flow (Minimum) (₹ Cr)",
    min_value=-2000.0,
    max_value=10000.0,
    key="fcf_min",
    step=100.0,
    help="Minimum Free Cash Flow in Crores",
)

rev_cagr_min = st.sidebar.slider(
    "Revenue CAGR (Minimum) (%)",
    min_value=-30.0,
    max_value=50.0,
    key="rev_cagr_min",
    step=1.0,
    help="Minimum 5-Year Revenue CAGR percentage",
)

pat_cagr_min = st.sidebar.slider(
    "PAT CAGR (Minimum) (%)",
    min_value=-30.0,
    max_value=50.0,
    key="pat_cagr_min",
    step=1.0,
    help="Minimum 5-Year Net Profit (PAT) CAGR percentage",
)

opm_min = st.sidebar.slider(
    "Operating Profit Margin (Minimum) (%)",
    min_value=-20.0,
    max_value=60.0,
    key="opm_min",
    step=1.0,
    help="Minimum Operating Profit Margin percentage",
)

pe_max = st.sidebar.slider(
    "P/E Ratio (Maximum)",
    min_value=0.0,
    max_value=150.0,
    key="pe_max",
    step=1.0,
    help="Maximum Price-to-Earnings ratio",
)

pb_max = st.sidebar.slider(
    "P/B Ratio (Maximum)",
    min_value=0.0,
    max_value=50.0,
    key="pb_max",
    step=0.5,
    help="Maximum Price-to-Book ratio",
)

div_yield_min = st.sidebar.slider(
    "Dividend Yield (Minimum) (%)",
    min_value=0.0,
    max_value=10.0,
    key="div_yield_min",
    step=0.1,
    help="Minimum Dividend Yield percentage",
)

icr_min = st.sidebar.slider(
    "Interest Coverage Ratio (Minimum)",
    min_value=0.0,
    max_value=50.0,
    key="icr_min",
    step=0.5,
    help="Minimum Interest Coverage Ratio (waived for debt-free companies)",
)

# ---------------------------------------------------------
# Load Base Data & Run Screening Engine
# ---------------------------------------------------------
df_base = fetch_screener_base_data()

if df_base.empty:
    st.error("Unable to load financial database records for screening.")
    st.stop()

# Construct filter dictionary using exact YAML configuration keys
filter_config = {
    "filters": {
        "ROE": {"min": roe_min},
        "Debt-to-Equity": {"max": de_max},
        "Free Cash Flow": {"min": fcf_min},
        "Revenue CAGR 5Y": {"min": rev_cagr_min},
        "PAT CAGR 5Y": {"min": pat_cagr_min},
        "Operating Profit Margin": {"min": opm_min},
        "P/E": {"max": pe_max},
        "P/B": {"max": pb_max},
        "Dividend Yield": {"min": div_yield_min},
        "Interest Coverage Ratio": {"min": icr_min},
    }
}

# Execute screener filtering
df_filtered = apply_screener_filters(df_base, filter_config)

# Ensure proper sorting by composite quality score
if not df_filtered.empty and "composite_quality_score" in df_filtered.columns:
    df_filtered = df_filtered.sort_values(
        by="composite_quality_score", ascending=False
    ).reset_index(drop=True)

# ---------------------------------------------------------
# Main Page Content & Visuals
# ---------------------------------------------------------

# Results Summary Metric Row
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric("Filtered Companies", f"{len(df_filtered)}", f"out of {len(df_base)}")

with m2:
    avg_roe_val = (
        df_filtered["return_on_equity_pct"].mean() if not df_filtered.empty else 0.0
    )
    st.metric(
        "Avg Filtered ROE", f"{avg_roe_val:.2f}%" if not df_filtered.empty else "N/A"
    )

with m3:
    med_pe_val = df_filtered["pe_ratio"].median() if not df_filtered.empty else 0.0
    st.metric(
        "Median Filtered P/E", f"{med_pe_val:.2f}x" if not df_filtered.empty else "N/A"
    )

with m4:
    avg_qs = (
        df_filtered["composite_quality_score"].mean() if not df_filtered.empty else 0.0
    )
    st.metric(
        "Avg Quality Score", f"{avg_qs:.1f} / 100" if not df_filtered.empty else "N/A"
    )

st.markdown("---")

# Header Label & Action Buttons
col_title, col_btn = st.columns([3, 1])

with col_title:
    st.markdown(f"### 🎯 Results: `{len(df_filtered)} companies` match your filters")

with col_btn:
    if not df_filtered.empty:
        # Prepare CSV download
        export_cols = [
            "company_id",
            "company_name",
            "broad_sector",
            "composite_quality_score",
            "return_on_equity_pct",
            "debt_to_equity",
            "free_cash_flow_cr",
            "revenue_cagr_5yr",
            "pat_cagr_5yr",
            "operating_profit_margin_pct",
            "pe_ratio",
            "pb_ratio",
            "dividend_yield_pct",
            "interest_coverage",
        ]
        export_cols_clean = [c for c in export_cols if c in df_filtered.columns]
        csv_bytes = df_filtered[export_cols_clean].to_csv(index=False).encode("utf-8")

        st.download_button(
            label="📥 Download CSV",
            data=csv_bytes,
            file_name="nifty100_screener_results.csv",
            mime="text/csv",
            use_container_width=True,
            help="Export currently filtered company list to CSV",
        )

# Visual Scatter Plot if data is non-empty
if not df_filtered.empty:
    st.markdown("#### 📊 Risk vs. Return Matrix (ROE % vs Debt-to-Equity)")
    fig_scatter = px.scatter(
        df_filtered,
        x="debt_to_equity",
        y="return_on_equity_pct",
        size="composite_quality_score",
        color="broad_sector",
        hover_name="company_name",
        hover_data={
            "company_id": True,
            "composite_quality_score": ":.1f",
            "pe_ratio": ":.1f",
            "free_cash_flow_cr": ":,.0f",
        },
        labels={
            "debt_to_equity": "Debt-to-Equity Ratio",
            "return_on_equity_pct": "Return on Equity (ROE %)",
            "broad_sector": "Sector",
            "composite_quality_score": "Quality Score",
        },
        title="Screened Universe: ROE vs Leverage (Bubble Size = Composite Quality Score)",
    )
    fig_scatter.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        xaxis=dict(gridcolor="#1e293b"),
        yaxis=dict(gridcolor="#1e293b"),
        margin=dict(t=40, b=20, l=20, r=20),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    # ---------------------------------------------------------
    # Display Table with all required metrics
    # Show: Company ID, Company Name, Sector, Composite Score, and all filtered metrics
    # ---------------------------------------------------------
    st.markdown("#### 📋 Detailed Results Table")

    # Prepare display DataFrame
    df_display = df_filtered.copy()

    # Format and rename for clean presentation
    display_columns = {
        "company_id": "Company ID",
        "company_name": "Company Name",
        "broad_sector": "Sector",
        "composite_quality_score": "Composite Score",
        "return_on_equity_pct": "ROE (%)",
        "debt_to_equity": "Debt-to-Equity",
        "free_cash_flow_cr": "Free Cash Flow (Cr)",
        "revenue_cagr_5yr": "Revenue CAGR (5Y)",
        "pat_cagr_5yr": "PAT CAGR (5Y)",
        "operating_profit_margin_pct": "OPM (%)",
        "pe_ratio": "P/E Ratio",
        "pb_ratio": "P/B Ratio",
        "dividend_yield_pct": "Dividend Yield (%)",
        "interest_coverage": "Interest Coverage",
    }

    available_display_cols = [
        col for col in display_columns.keys() if col in df_display.columns
    ]
    df_table = df_display[available_display_cols].rename(columns=display_columns)

    st.dataframe(
        df_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Company ID": st.column_config.TextColumn(
                "Company ID", help="NSE Ticker Symbol"
            ),
            "Company Name": st.column_config.TextColumn("Company Name"),
            "Sector": st.column_config.TextColumn("Sector"),
            "Composite Score": st.column_config.NumberColumn(
                "Composite Score", format="%.1f / 100"
            ),
            "ROE (%)": st.column_config.NumberColumn("ROE (%)", format="%.2f%%"),
            "Debt-to-Equity": st.column_config.NumberColumn(
                "Debt-to-Equity", format="%.2f"
            ),
            "Free Cash Flow (Cr)": st.column_config.NumberColumn(
                "Free Cash Flow (Cr)", format="₹%,.0f Cr"
            ),
            "Revenue CAGR (5Y)": st.column_config.NumberColumn(
                "Revenue CAGR (5Y)", format="%.2f%%"
            ),
            "PAT CAGR (5Y)": st.column_config.NumberColumn(
                "PAT CAGR (5Y)", format="%.2f%%"
            ),
            "OPM (%)": st.column_config.NumberColumn("OPM (%)", format="%.2f%%"),
            "P/E Ratio": st.column_config.NumberColumn("P/E Ratio", format="%.2fx"),
            "P/B Ratio": st.column_config.NumberColumn("P/B Ratio", format="%.2fx"),
            "Dividend Yield (%)": st.column_config.NumberColumn(
                "Dividend Yield (%)", format="%.2f%%"
            ),
            "Interest Coverage": st.column_config.NumberColumn(
                "Interest Coverage", format="%.2fx"
            ),
        },
    )

else:
    # Graceful handling for empty results
    st.warning("⚠️ No companies match all your selected filter criteria.")
    st.info(
        "💡 **Tips to expand results:**\n"
        "- Click one of the **Strategy Presets** in the sidebar (e.g. *Quality* or *Value*).\n"
        "- Relax strict slider thresholds like **Minimum ROE** or **Maximum Debt-to-Equity**.\n"
        "- Click **Reset All Filters** to view all Nifty 100 companies."
    )
