"""
02_profile.py - Company Profile Page for Nifty 100 Analytics.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add parent path imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = PROJECT_ROOT / "src" / "dashboard"
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.utils.db import (
    get_companies, get_ratios, get_pl, get_bs, get_cf, get_valuation, get_sectors
)

st.markdown('<h1 class="gradient-header">🏢 Company Profile & Deep-Dive</h1>', unsafe_allow_html=True)

df_companies = get_companies()

if df_companies.empty:
    st.error("No company records found in database.")
    st.stop()

# ---------------------------------------------------------
# Top Section: Search box with autocomplete for name or ticker
# ---------------------------------------------------------
df_sectors = get_sectors()
if not df_sectors.empty and 'broad_sector' in df_sectors.columns:
    df_companies = df_companies.merge(
        df_sectors[['company_id', 'broad_sector', 'sub_sector']],
        left_on='id',
        right_on='company_id',
        how='left',
        suffixes=('', '_sec')
    )

# Prepare autocomplete choices
company_lookup = {}
search_options = []

for _, row in df_companies.iterrows():
    ticker = str(row['id']).strip().upper()
    name = str(row.get('company_name', ticker)).strip()
    label = f"{ticker} - {name}"
    search_options.append(label)
    company_lookup[ticker] = row
    company_lookup[name.lower()] = row
    company_lookup[label.lower()] = row

col_search1, col_search2 = st.columns([3, 1])

with col_search1:
    selected_option = st.selectbox(
        "🔍 Search Company (by Name or Ticker):",
        options=search_options,
        index=0,
        help="Type to search company by name or NSE ticker symbol."
    )

with col_search2:
    text_search = st.text_input("Or enter custom Ticker:", value="", help="Direct ticker query").strip().upper()

# Resolve selected company
selected_ticker = None

if text_search:
    if text_search in company_lookup:
        selected_ticker = text_search
    else:
        # Check if text_search matches part of company name or ticker
        matches = [t for t in company_lookup.keys() if text_search.lower() in t.lower()]
        if matches:
            selected_ticker = company_lookup[matches[0]]['id']
        else:
            st.error("Ticker not found — please try another.")
            st.stop()
else:
    if selected_option:
        selected_ticker = selected_option.split(" - ")[0].strip().upper()

if not selected_ticker or selected_ticker not in company_lookup:
    st.error("Ticker not found — please try another.")
    st.stop()

# Company row details
company_info = company_lookup[selected_ticker]

# ---------------------------------------------------------
# Company Information Card
# ---------------------------------------------------------
comp_name = company_info.get("company_name", selected_ticker)
nse_ticker = company_info.get("id", selected_ticker)
sector = company_info.get("broad_sector", "N/A")
if pd.isna(sector) or str(sector) == "nan":
    sector = "Financials & Services"

sub_sector = company_info.get("sub_sector", "N/A")
if pd.isna(sub_sector) or str(sub_sector) == "nan":
    sub_sector = "Diversified"

about_desc = company_info.get("about_company", "Comprehensive financial profile for Nifty 100 constituent.")
if pd.isna(about_desc) or str(about_desc) == "nan":
    about_desc = "Leading Nifty 100 enterprise with strong fundamentals and historical performance track record."

website = company_info.get("website", "")

st.markdown(f"""
<div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%); 
            border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 25px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <h2 style="margin: 0; color: #f8fafc; font-size: 1.8rem;">{comp_name} <span style="color: #38bdf8; font-size: 1.2rem;">({nse_ticker})</span></h2>
        <span style="background-color: #1e293b; border: 1px solid #475569; color: #38bdf8; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem;">
            NSE Ticker: {nse_ticker}
        </span>
    </div>
    <p style="margin: 4px 0; color: #94a3b8; font-size: 0.95rem;">
        <strong>Sector:</strong> {sector} &nbsp;|&nbsp; <strong>Sub-Sector:</strong> {sub_sector}
    </p>
    <p style="margin-top: 12px; color: #cbd5e1; font-size: 0.92rem; line-height: 1.5;">
        {about_desc}
    </p>
</div>
""", unsafe_allow_html=True)

# Fetch company financial tables
df_ratios = get_ratios(selected_ticker)
df_pl = get_pl(selected_ticker)
df_bs = get_bs(selected_ticker)
df_cf = get_cf(selected_ticker)
df_val = get_valuation(selected_ticker)

# Get latest year ratio record
latest_ratio = df_ratios.iloc[-1] if not df_ratios.empty else pd.Series()
latest_val = df_val.iloc[-1] if not df_val.empty else pd.Series()

# ---------------------------------------------------------
# KPI Section: 6 KPI Cards
# ---------------------------------------------------------
roe_val = company_info.get("roe_percentage")
if pd.isna(roe_val) and not latest_ratio.empty:
    roe_val = latest_ratio.get("return_on_equity_pct")

roce_val = company_info.get("roce_percentage")
if pd.isna(roce_val) and not latest_ratio.empty:
    roce_val = latest_ratio.get("roce_percentage")

npm_val = latest_ratio.get("net_profit_margin_pct") if not latest_ratio.empty else None
de_val = latest_ratio.get("debt_to_equity") if not latest_ratio.empty else None
cagr_val = latest_ratio.get("revenue_cagr_5yr") if not latest_ratio.empty else None
fcf_val = latest_ratio.get("free_cash_flow_cr") if not latest_ratio.empty else None

st.markdown("### 🔑 Key Performance Indicators")
k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.metric("ROE", f"{roe_val:.2f}%" if pd.notna(roe_val) else "N/A", "Return on Equity")

with k2:
    st.metric("ROCE", f"{roce_val:.2f}%" if pd.notna(roce_val) else "N/A", "Return on Capital")

with k3:
    st.metric("Net Profit Margin", f"{npm_val:.2f}%" if pd.notna(npm_val) else "N/A", "PAT Margin")

with k4:
    st.metric("Debt-to-Equity", f"{de_val:.2f}" if pd.notna(de_val) else "N/A", "Leverage Ratio")

with k5:
    st.metric("Revenue CAGR (5Y)", f"{cagr_val:.2f}%" if pd.notna(cagr_val) else "N/A", "5-Year Growth")

with k6:
    fcf_str = f"₹{fcf_val:,.0f} Cr" if pd.notna(fcf_val) else "N/A"
    st.metric("Latest FCF", fcf_str, "Free Cash Flow")

st.markdown("---")

# ---------------------------------------------------------
# Charts Section:
# 1. 10-year Revenue and Net Profit (Bar chart)
# 2. Dual-axis Plotly line chart for 10-year ROE and ROCE
# ---------------------------------------------------------
st.markdown("### 📈 10-Year Financial Performance & Profitability Trends")
c_left, c_right = st.columns(2)

# Filter 10-year numeric P&L data
if not df_pl.empty and 'year' in df_pl.columns:
    df_pl_clean = df_pl[df_pl['year'].astype(str).str.isdigit()].copy()
    df_pl_clean['year_num'] = df_pl_clean['year'].astype(int)
    df_pl_clean = df_pl_clean.sort_values('year_num').tail(10)
else:
    df_pl_clean = pd.DataFrame()

with c_left:
    st.subheader("📊 10-Year Revenue & Net Profit")
    if not df_pl_clean.empty and 'sales' in df_pl_clean.columns and 'net_profit' in df_pl_clean.columns:
        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(
            x=df_pl_clean['year'],
            y=df_pl_clean['sales'],
            name="Revenue (Sales)",
            marker_color="#38bdf8"
        ))
        fig_rev.add_trace(go.Bar(
            x=df_pl_clean['year'],
            y=df_pl_clean['net_profit'],
            name="Net Profit (PAT)",
            marker_color="#22c55e"
        ))
        fig_rev.update_layout(
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            xaxis=dict(title="Financial Year", gridcolor="#1e293b"),
            yaxis=dict(title="Amount (₹ Crores)", gridcolor="#1e293b"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=30, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_rev, use_container_width=True)
    else:
        st.info("Historical P&L data loading...")

# Prepare 10-year ROE & ROCE data
if not df_pl_clean.empty:
    df_chart_10y = df_pl_clean.copy()
    
    # Merge ROE from ratios if available
    if not df_ratios.empty and 'year' in df_ratios.columns:
        df_ratios_clean = df_ratios[df_ratios['year'].astype(str).str.isdigit()].copy()
        df_ratios_clean['year_num'] = df_ratios_clean['year'].astype(int)
        df_chart_10y = df_chart_10y.merge(
            df_ratios_clean[['year_num', 'return_on_equity_pct']],
            on='year_num',
            how='left'
        )
    else:
        df_chart_10y['return_on_equity_pct'] = roe_val

    # Merge Balance sheet for ROCE calculation
    if not df_bs.empty and 'year' in df_bs.columns:
        df_bs_clean = df_bs[df_bs['year'].astype(str).str.isdigit()].copy()
        df_bs_clean['year_num'] = df_bs_clean['year'].astype(int)
        df_chart_10y = df_chart_10y.merge(
            df_bs_clean[['year_num', 'equity_capital', 'reserves', 'borrowings']],
            on='year_num',
            how='left'
        )
        
        # Calculate ROCE = (EBIT / Capital Employed) * 100
        pbt = df_chart_10y['profit_before_tax'].fillna(0) if 'profit_before_tax' in df_chart_10y.columns else df_chart_10y['net_profit'].fillna(0)
        interest = df_chart_10y['interest'].fillna(0) if 'interest' in df_chart_10y.columns else 0
        ebit = pbt + interest
        
        eq = df_chart_10y['equity_capital'].fillna(0) if 'equity_capital' in df_chart_10y.columns else 0
        res = df_chart_10y['reserves'].fillna(0) if 'reserves' in df_chart_10y.columns else 0
        debt = df_chart_10y['borrowings'].fillna(0) if 'borrowings' in df_chart_10y.columns else 0
        capital_employed = eq + res + debt
        capital_employed = capital_employed.replace(0, pd.NA)
        
        df_chart_10y['roce_calc'] = (ebit / capital_employed) * 100
    else:
        df_chart_10y['roce_calc'] = roce_val
else:
    df_chart_10y = pd.DataFrame()

with c_right:
    st.subheader("⚡ 10-Year ROE & ROCE Trends (Dual Axis)")
    if not df_chart_10y.empty:
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig_dual.add_trace(
            go.Scatter(
                x=df_chart_10y['year'],
                y=df_chart_10y['return_on_equity_pct'],
                name="ROE (%)",
                mode="lines+markers",
                line=dict(color="#38bdf8", width=3),
                marker=dict(size=6)
            ),
            secondary_y=False
        )
        
        fig_dual.add_trace(
            go.Scatter(
                x=df_chart_10y['year'],
                y=df_chart_10y['roce_calc'],
                name="ROCE (%)",
                mode="lines+markers",
                line=dict(color="#c084fc", width=3, dash="dot"),
                marker=dict(size=6)
            ),
            secondary_y=True
        )
        
        fig_dual.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            xaxis=dict(title="Financial Year", gridcolor="#1e293b"),
            yaxis=dict(title="ROE (%)", gridcolor="#1e293b", title_font=dict(color="#38bdf8"), tickfont=dict(color="#38bdf8")),
            yaxis2=dict(title="ROCE (%)", overlaying="y", side="right", title_font=dict(color="#c084fc"), tickfont=dict(color="#c084fc")),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=30, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_dual, use_container_width=True)
    else:
        st.info("Historical ROE/ROCE data loading...")

st.markdown("---")

# ---------------------------------------------------------
# Bottom Section: Display company Pros & Cons
# ---------------------------------------------------------
st.markdown("### ⚖️ Company Fundamentals Evaluation")

pros = []
cons = []

if pd.notna(de_val) and de_val <= 0.1:
    pros.append("Virtually debt-free company with minimal financial leverage")
elif pd.notna(de_val) and de_val > 1.0:
    cons.append(f"Elevated debt-to-equity ratio of {de_val:.2f}")

if pd.notna(roe_val) and roe_val >= 18:
    pros.append(f"Strong Return on Equity (ROE) track record of {roe_val:.2f}%")
elif pd.notna(roe_val) and roe_val < 10:
    cons.append(f"Subdued Return on Equity (ROE) of {roe_val:.2f}%")

if pd.notna(roce_val) and roce_val >= 20:
    pros.append(f"High Return on Capital Employed (ROCE) of {roce_val:.2f}%")
elif pd.notna(roce_val) and roce_val < 10:
    cons.append(f"Subdued Return on Capital Employed (ROCE) of {roce_val:.2f}%")

if pd.notna(cagr_val) and cagr_val >= 10:
    pros.append(f"Healthy 5-Year Revenue CAGR growth of {cagr_val:.2f}%")
elif pd.notna(cagr_val) and cagr_val < 5:
    cons.append(f"Low 5-Year Revenue CAGR of {cagr_val:.2f}%")

if pd.notna(npm_val) and npm_val >= 15:
    pros.append(f"Robust Net Profit Margin of {npm_val:.2f}%")
elif pd.notna(npm_val) and npm_val < 5:
    cons.append(f"Low Net Profit Margin of {npm_val:.2f}%")

if pd.notna(fcf_val) and fcf_val > 0:
    pros.append(f"Strong positive Free Cash Flow generation (₹{fcf_val:,.0f} Cr)")
elif pd.notna(fcf_val) and fcf_val < 0:
    cons.append(f"Negative Free Cash Flow generation (₹{abs(fcf_val):,.0f} Cr)")

if not latest_val.empty:
    pe_ratio_val = latest_val.get("pe_ratio")
    if pd.notna(pe_ratio_val) and pe_ratio_val > 45:
        cons.append(f"Stock is trading at a high valuation multiple (P/E {pe_ratio_val:.1f}x)")

if not pros:
    pros.append("Maintains stable operational track record within its sector")
if not cons:
    cons.append("No critical balance sheet or profitability warnings identified")

col_pros, col_cons = st.columns(2)

with col_pros:
    st.markdown("#### ✅ Pros")
    for pro in pros:
        st.markdown(f"""
        <div style="background-color: rgba(6, 78, 59, 0.3); border-left: 4px solid #10b981; 
                    padding: 10px 14px; margin-bottom: 8px; border-radius: 4px; color: #a7f3d0; font-size: 0.92rem;">
            ✅ {pro}
        </div>
        """, unsafe_allow_html=True)

with col_cons:
    st.markdown("#### ❌ Cons")
    for con in cons:
        st.markdown(f"""
        <div style="background-color: rgba(127, 29, 29, 0.3); border-left: 4px solid #f43f5e; 
                    padding: 10px 14px; margin-bottom: 8px; border-radius: 4px; color: #fecdd3; font-size: 0.92rem;">
            ❌ {con}
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# Full Statement Tabs
t1, t2, t3, t4 = st.tabs(["📊 Profit & Loss Table", "🏦 Balance Sheet Table", "💸 Cash Flow Table", "📈 Ratios & Valuation"])

with t1:
    st.subheader("Profit & Loss Statement (₹ Crores)")
    if not df_pl.empty:
        display_cols = [c for c in ["year", "sales", "expenses", "operating_profit", "opm_percentage", "other_income", "interest", "depreciation", "profit_before_tax", "tax_percentage", "net_profit", "eps"] if c in df_pl.columns]
        st.dataframe(df_pl[display_cols].sort_values("year", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No P&L statement records found for this ticker.")

with t2:
    st.subheader("Balance Sheet Statement (₹ Crores)")
    if not df_bs.empty:
        display_cols = [c for c in ["year", "equity_capital", "reserves", "borrowings", "other_liabilities", "total_liabilities", "fixed_assets", "investments", "other_asset", "total_assets"] if c in df_bs.columns]
        st.dataframe(df_bs[display_cols].sort_values("year", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No Balance Sheet records found for this ticker.")

with t3:
    st.subheader("Cash Flow Statement (₹ Crores)")
    if not df_cf.empty:
        display_cols = [c for c in ["year", "operating_activity", "investing_activity", "financing_activity", "net_cash_flow"] if c in df_cf.columns]
        st.dataframe(df_cf[display_cols].sort_values("year", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No Cash Flow statement records found for this ticker.")

with t4:
    cr1, cr2 = st.columns(2)
    with cr1:
        st.subheader("Key Financial Ratios")
        if not df_ratios.empty:
            ratio_cols = [c for c in ["year", "net_profit_margin_pct", "operating_profit_margin_pct", "return_on_equity_pct", "debt_to_equity", "interest_coverage", "free_cash_flow_cr", "composite_quality_score"] if c in df_ratios.columns]
            st.dataframe(df_ratios[ratio_cols].sort_values("year", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No financial ratios recorded for this ticker.")

    with cr2:
        st.subheader("Historical Valuation Metrics")
        if not df_val.empty:
            val_cols = [c for c in ["year", "market_cap_crore", "pe_ratio", "pb_ratio", "ev_ebitda", "dividend_yield_pct"] if c in df_val.columns]
            st.dataframe(df_val[val_cols].sort_values("year", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No valuation metrics recorded for this ticker.")
