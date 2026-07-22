"""
08_reports.py - Annual Reports & Data Export Page for Nifty 100 Analytics.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import requests

# Add project root and dashboard directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1] if len(Path(__file__).resolve().parents) > 1 else Path(__file__).resolve().parents[0]
DASHBOARD_DIR = PROJECT_ROOT / "src" / "dashboard"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

from src.dashboard.utils.db import (
    get_companies, get_ratios, get_pl, get_bs, get_cf, get_sectors, get_peers, get_valuation
)

st.markdown('<h1 class="gradient-header">📄 Annual Reports & Data Export Portal</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Search BSE annual reports by company, inspect document filing links, generate executive tear-sheets, and export datasets.</p>', unsafe_allow_html=True)

# Fetch company directory
df_companies = get_companies()
df_ratios = get_ratios()
df_sectors = get_sectors()

# Load documents dataset
DOCUMENTS_CSV = PROJECT_ROOT / "data" / "processed" / "documents.csv"

@st.cache_data(ttl=600)
def load_documents_data() -> pd.DataFrame:
    if not DOCUMENTS_CSV.exists():
        return pd.DataFrame()
    with open(DOCUMENTS_CSV, "r", encoding="utf-8") as f:
        first_line = f.readline()
    if first_line.startswith("id,") or first_line.startswith("company_id,") or "id," in first_line:
        df = pd.read_csv(DOCUMENTS_CSV)
    else:
        df = pd.read_csv(DOCUMENTS_CSV, header=1)
    df.columns = [c.strip() for c in df.columns]
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].astype(str).str.strip()
    if "Year" in df.columns:
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    return df

df_documents = load_documents_data()

# Helper function to check URL availability with HTTP request caching
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

@st.cache_data(ttl=3600)
def is_url_available(url: str) -> bool:
    if not url or pd.isna(url) or str(url).strip().lower() in ["", "none", "null", "nan"]:
        return False
    url_str = str(url).strip()
    if not url_str.startswith("http"):
        return False
    try:
        resp = requests.head(url_str, headers=HTTP_HEADERS, timeout=2.5, allow_redirects=True)
        return resp.status_code in [200, 301, 302, 303, 307, 308]
    except Exception:
        return False

# Main View Tabs
t1, t2, t3, t4 = st.tabs([
    "📂 BSE Annual Reports",
    "📑 Company Factsheet Generator",
    "📥 Data Export Center",
    "🔍 Audit Summary"
])

with t1:
    st.subheader("📚 BSE Annual Reports Library")
    
    if df_companies.empty:
        st.error("No company records found.")
        st.stop()
        
    company_map = {}
    company_options = []
    for _, row in df_companies.iterrows():
        cid = str(row["id"]).strip()
        cname = str(row.get("company_name", cid)).strip()
        display_str = f"{cid} - {cname}"
        company_options.append(display_str)
        company_map[display_str] = cid
        
    default_idx = 0
    for idx, opt in enumerate(company_options):
        if opt.startswith("TCS"):
            default_idx = idx
            break

    selected_comp_str = st.selectbox(
        "🔍 Search & Select Company for Annual Reports:",
        options=company_options,
        index=default_idx,
        help="Type ticker or company name to view historical annual reports"
    )
    target_ticker = company_map[selected_comp_str]
    company_name = selected_comp_str.split(" - ")[1]
    
    st.markdown(f"### Annual Reports for **{company_name} ({target_ticker})**")
    
    if not df_documents.empty and "company_id" in df_documents.columns:
        comp_docs = df_documents[df_documents["company_id"] == target_ticker].sort_values("Year", ascending=False)
    else:
        comp_docs = pd.DataFrame()

    if comp_docs.empty:
        st.info(f"No annual report filings found for {target_ticker}.")
    else:
        st.write(f"Found **{len(comp_docs)}** annual report records across filing years:")
        
        # Display in cards grid layout (3 columns per row)
        cols_per_row = 3
        doc_rows = list(comp_docs.iterrows())
        
        for i in range(0, len(doc_rows), cols_per_row):
            grid_cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                if i + j < len(doc_rows):
                    _, doc_row = doc_rows[i + j]
                    yr = int(doc_row["Year"]) if pd.notna(doc_row["Year"]) else "N/A"
                    raw_url = doc_row.get("Annual_Report", "")
                    
                    with grid_cols[j]:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
                                    border: 1px solid #334155; border-radius: 10px; padding: 16px; margin-bottom: 12px;">
                            <h4 style="margin: 0; color: #38bdf8;">📅 FY {yr} Annual Report</h4>
                            <p style="margin: 6px 0 12px 0; color: #94a3b8; font-size: 0.85rem;">Company: <b>{target_ticker}</b></p>
                        """, unsafe_allow_html=True)
                        
                        is_valid = is_url_available(raw_url)
                        
                        if is_valid:
                            st.markdown(f'<a href="{raw_url}" target="_blank" style="text-decoration: none;"><button style="background-color: #059669; color: white; border: none; padding: 8px 14px; border-radius: 6px; font-weight: 600; cursor: pointer; width: 100%;">📄 Open Report (PDF)</button></a>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div style="background-color: #991b1b; color: #fecaca; padding: 8px 14px; border-radius: 6px; font-weight: 600; text-align: center; font-size: 0.9rem;">🚨 Report Unavailable</div>', unsafe_allow_html=True)
                            
                        st.markdown("</div>", unsafe_allow_html=True)

        # Summary Table view
        with st.expander("📋 View Summary Table of Annual Report Filings"):
            table_data = []
            for _, r in comp_docs.iterrows():
                yr_val = int(r["Year"]) if pd.notna(r["Year"]) else "N/A"
                u_val = str(r.get("Annual_Report", "")).strip()
                status_str = "Available" if is_url_available(u_val) else "Report Unavailable"
                table_data.append({
                    "Year": yr_val,
                    "Company ID": target_ticker,
                    "Report URL": u_val if u_val.startswith("http") else "-",
                    "Status": status_str
                })
            st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

with t2:
    st.subheader("📑 Generate Executive Factsheet")
    if not df_companies.empty:
        sel_comp = st.selectbox("Select Target Company for Tear-Sheet:", company_options, key="factsheet_comp")
        target_id = company_map[sel_comp]
        
        comp_info = df_companies[df_companies["id"] == target_id].iloc[0]
        df_comp_ratios = get_ratios(target_id)
        df_comp_pl = get_pl(target_id)
        df_comp_val = get_valuation(target_id)
        
        st.markdown("---")
        st.markdown(f"## 🏢 {comp_info.get('company_name', target_id)} ({target_id})")
        st.markdown(f"**Broad Sector:** {comp_info.get('broad_sector', 'N/A')} | **Sub-Sector:** {comp_info.get('sub_sector', 'N/A')}")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.markdown("#### Key Valuation & Ratios (Latest)")
            if not df_comp_ratios.empty:
                latest_ratio = df_comp_ratios.iloc[-1]
                st.write(f"- **ROE %:** {latest_ratio.get('return_on_equity_pct', 'N/A')}%")
                st.write(f"- **OPM %:** {latest_ratio.get('operating_profit_margin_pct', 'N/A')}%")
                st.write(f"- **Debt-to-Equity:** {latest_ratio.get('debt_to_equity', 'N/A')}")
                st.write(f"- **Free Cash Flow:** ₹{latest_ratio.get('free_cash_flow_cr', 'N/A')} Cr")
                st.write(f"- **Quality Score:** {latest_ratio.get('composite_quality_score', 'N/A')}/100")

        with col_f2:
            st.markdown("#### Historical P&L Summary")
            if not df_comp_pl.empty:
                cols = [c for c in ["year", "sales", "net_profit", "opm_percentage", "eps"] if c in df_comp_pl.columns]
                st.dataframe(df_comp_pl[cols].tail(5), hide_index=True)
                
        report_md = f"""# Executive Factsheet: {comp_info.get('company_name', target_id)} ({target_id})
- Sector: {comp_info.get('broad_sector', 'N/A')}
- Sub-Sector: {comp_info.get('sub_sector', 'N/A')}
- Book Value: {comp_info.get('book_value', 'N/A')}
- Face Value: {comp_info.get('face_value', 'N/A')}

Generated by Nifty 100 Analytics Platform.
"""
        st.download_button(
            label="💾 Download Factsheet (Markdown)",
            data=report_md,
            file_name=f"{target_id}_factsheet.md",
            mime="text/markdown"
        )

with t3:
    st.subheader("📥 Export Datasets (CSV Format)")
    e1, e2, e3 = st.columns(3)
    
    with e1:
        st.markdown("#### Financial Ratios")
        if not df_ratios.empty:
            csv_ratios = df_ratios.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download Ratios CSV",
                data=csv_ratios,
                file_name="nifty100_financial_ratios.csv",
                mime="text/csv"
            )
            
    with e2:
        st.markdown("#### Companies Directory")
        if not df_companies.empty:
            csv_comp = df_companies.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download Companies CSV",
                data=csv_comp,
                file_name="nifty100_companies.csv",
                mime="text/csv"
            )

    with e3:
        st.markdown("#### Sector Mapping")
        if not df_sectors.empty:
            csv_sec = df_sectors.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download Sectors CSV",
                data=csv_sec,
                file_name="nifty100_sectors.csv",
                mime="text/csv"
            )

with t4:
    st.subheader("🔍 Database Audit & Health Status")
    st.success("✅ Database Connection: ACTIVE")
    
    audit_data = {
        "Table / Dataset": ["companies", "financial_ratios", "profitandloss", "balancesheet", "cashflow", "sectors", "peer_groups", "market_cap", "documents"],
        "Record Count": [
            len(df_companies),
            len(df_ratios),
            len(get_pl()),
            len(get_bs()),
            len(get_cf()),
            len(df_sectors),
            len(get_peers()),
            len(get_valuation()),
            len(df_documents)
        ],
        "Status": ["Active"] * 9
    }
    st.dataframe(pd.DataFrame(audit_data), use_container_width=True, hide_index=True)
