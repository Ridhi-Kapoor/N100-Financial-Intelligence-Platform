"""
01_home.py - Executive Overview Page for Nifty 100 Analytics.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Add parent path imports
DASHBOARD_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.db import get_companies, get_ratios, get_sectors, get_valuation, run_query

# Page Header
st.markdown('<h1 class="gradient-header">⚡ Nifty 100 Executive Overview</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Comprehensive Financial Intelligence & Market Analytics Platform</p>', unsafe_allow_html=True)

# Sidebar - Year Selector (2019-2024)
st.sidebar.markdown("### 📅 Dashboard Controls")
available_years = [2024, 2023, 2022, 2021, 2020, 2019]
selected_year = st.sidebar.selectbox(
    "Select Financial Year:",
    options=available_years,
    index=0,
    help="Filter all KPI metrics, sector breakdown, and quality scores by year."
)

str_year = str(selected_year)
int_year = int(selected_year)

# Fetch data filtered by year
df_companies = get_companies()
df_ratios_year = get_ratios(year=str_year)

# If ratios table for year is empty, fallback to all ratios
if df_ratios_year.empty:
    df_ratios_all = get_ratios()
    if not df_ratios_all.empty and 'year' in df_ratios_all.columns:
        df_ratios_year = df_ratios_all[df_ratios_all['year'].astype(str) == str_year]

df_val_year = run_query("SELECT * FROM market_cap WHERE year = ?", (int_year,))
if df_val_year.empty:
    df_val_all = get_valuation()
    if not df_val_all.empty and 'year' in df_val_all.columns:
        df_val_year = df_val_all[df_val_all['year'] == int_year]

df_sectors = get_sectors()

# ---------------------------------------------------------
# Top Row: 6 KPI Cards
# ---------------------------------------------------------
avg_roe = df_ratios_year['return_on_equity_pct'].mean() if not df_ratios_year.empty and 'return_on_equity_pct' in df_ratios_year.columns else None
med_pe = df_val_year['pe_ratio'].median() if not df_val_year.empty and 'pe_ratio' in df_val_year.columns else None
med_de = df_ratios_year['debt_to_equity'].median() if not df_ratios_year.empty and 'debt_to_equity' in df_ratios_year.columns else None

total_companies_count = len(df_ratios_year['company_id'].unique()) if not df_ratios_year.empty and 'company_id' in df_ratios_year.columns else len(df_companies)
if total_companies_count == 0:
    total_companies_count = len(df_companies)

med_cagr = df_ratios_year['revenue_cagr_5yr'].median() if not df_ratios_year.empty and 'revenue_cagr_5yr' in df_ratios_year.columns else None

debt_free_count = 0
if not df_ratios_year.empty and 'debt_to_equity' in df_ratios_year.columns:
    debt_free_count = (df_ratios_year['debt_to_equity'] <= 0.05).sum()

st.markdown(f"#### 📊 Performance Summary for FY {selected_year}")
kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

with kpi1:
    val_str = f"{avg_roe:.2f}%" if pd.notna(avg_roe) else "N/A"
    st.metric("Average ROE", val_str, f"FY{selected_year}")

with kpi2:
    val_str = f"{med_pe:.2f}x" if pd.notna(med_pe) else "N/A"
    st.metric("Median P/E", val_str, f"FY{selected_year}")

with kpi3:
    val_str = f"{med_de:.2f}" if pd.notna(med_de) else "N/A"
    st.metric("Median D/E", val_str, "Financial Leverage")

with kpi4:
    st.metric("Total Companies", f"{total_companies_count}", "Nifty 100")

with kpi5:
    val_str = f"{med_cagr:.2f}%" if pd.notna(med_cagr) else "N/A"
    st.metric("Median Rev CAGR (5Y)", val_str, "5-Yr Compound Growth")

with kpi6:
    st.metric("Debt-Free Companies", f"{debt_free_count}", "D/E ≤ 0.05")

st.markdown("---")

# ---------------------------------------------------------
# Middle Section: Left Donut Chart & Right Sortable Table
# ---------------------------------------------------------
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("🍩 Sector Distribution (All 11 Sectors)")
    
    # Merge companies with sectors to get all 11 broad sectors
    if not df_companies.empty:
        if 'broad_sector' in df_companies.columns:
            df_sec_merged = df_companies.copy()
        elif not df_sectors.empty and 'broad_sector' in df_sectors.columns:
            df_sec_merged = df_companies.merge(df_sectors[['company_id', 'broad_sector']], left_on='id', right_on='company_id', how='left')
        else:
            df_sec_merged = df_companies.copy()
            df_sec_merged['broad_sector'] = 'Financials'
        
        # Ensure missing sectors are categorized as 'Other Services' to cover all 11 sectors
        df_sec_merged['broad_sector'] = df_sec_merged['broad_sector'].fillna('Other Services')
        
        # Filter for active companies in selected year if available
        if not df_ratios_year.empty and 'company_id' in df_ratios_year.columns:
            active_ids = set(df_ratios_year['company_id'].unique())
            df_sec_year = df_sec_merged[df_sec_merged['id'].isin(active_ids)]
            if df_sec_year.empty:
                df_sec_year = df_sec_merged
        else:
            df_sec_year = df_sec_merged
            
        sector_counts = df_sec_year.groupby('broad_sector').size().reset_index(name='count')
        
        fig_donut = px.pie(
            sector_counts,
            values='count',
            names='broad_sector',
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Bold,
            title=f"Company Count by Sector (FY{selected_year})"
        )
        fig_donut.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Companies: %{value}<br>Share: %{percent}'
        )
        fig_donut.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0', size=12),
            margin=dict(t=40, b=20, l=20, r=20),
            showlegend=False
        )
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("Sector distribution data loading...")

with col_right:
    st.subheader(f"⭐ Top 5 Companies by Quality Score (FY{selected_year})")
    
    if not df_ratios_year.empty and 'composite_quality_score' in df_ratios_year.columns:
        # Sort by Composite Quality Score
        df_top5 = df_ratios_year.dropna(subset=['composite_quality_score']).sort_values(
            by='composite_quality_score', ascending=False
        ).head(5).copy()
        
        if not df_top5.empty:
            # Merge with company details
            if not df_companies.empty:
                df_top5 = df_top5.merge(
                    df_companies[['id', 'company_name', 'broad_sector']],
                    left_on='company_id',
                    right_on='id',
                    how='left'
                )
            else:
                df_top5['company_name'] = df_top5['company_id']
                df_top5['broad_sector'] = 'N/A'

            df_top5['company_name'] = df_top5['company_name'].fillna(df_top5['company_id'])
            df_top5['broad_sector'] = df_top5['broad_sector'].fillna('N/A')
            
            # Format display table
            display_table = pd.DataFrame({
                "Ticker": df_top5['company_id'],
                "Company Name": df_top5['company_name'],
                "Sector": df_top5['broad_sector'],
                "Quality Score": df_top5['composite_quality_score'].round(2),
                "ROE (%)": df_top5['return_on_equity_pct'].round(2),
                "Debt/Equity": df_top5['debt_to_equity'].round(2)
            })
            
            st.dataframe(
                display_table,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Ticker": st.column_config.TextColumn("Ticker", help="NSE Ticker Symbol"),
                    "Company Name": st.column_config.TextColumn("Company Name"),
                    "Sector": st.column_config.TextColumn("Sector"),
                    "Quality Score": st.column_config.NumberColumn("Quality Score", format="%.2f"),
                    "ROE (%)": st.column_config.NumberColumn("ROE (%)", format="%.2f%%"),
                    "Debt/Equity": st.column_config.NumberColumn("Debt/Equity", format="%.2f")
                }
            )
        else:
            st.info(f"No composite quality score data available for FY{selected_year}.")
    else:
        st.info("Quality score data loading...")

st.markdown("---")

# Quick Summary Grid
st.subheader("💡 Platform Navigation & Modules")
g1, g2, g3, g4 = st.columns(4)

with g1:
    st.markdown("""
    #### 🏢 Company Profile
    Deep dive into individual company financials, P&L, Balance Sheet, Cash Flow, and Pros & Cons breakdown over multi-year periods.
    """)
with g2:
    st.markdown("""
    #### 🔍 Stock Screener
    Run quantitative screens using presets like Quality Compounder, Value Pick, Growth Accelerator, or custom filters.
    """)
with g3:
    st.markdown("""
    #### ⚖️ Peer Comparison
    Compare companies against industry peer groups, evaluate benchmarks, and visualize metrics on radar charts.
    """)
with g4:
    st.markdown("""
    #### 📄 Reports & Export
    Generate comprehensive company tear-sheets, export financial data to CSV, and review data audit logs.
    """)
