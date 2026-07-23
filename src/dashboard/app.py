"""
Nifty 100 Analytics - Main Application Entrypoint.

Configures wide layout, expanded sidebar, custom styling, and multi-page navigation.
"""

import sys
from pathlib import Path
import streamlit as st

# Ensure project root and dashboard directory are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

# Page configuration
st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Global Styling for Premium UI
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }
    
    .gradient-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #94a3b8;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.7) 100%);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
</style>
""",
    unsafe_allow_html=True,
)

# Navigation definition for all 8 views
views_dir = DASHBOARD_DIR / "views"

pg = st.navigation(
    [
        st.Page(
            str(views_dir / "01_home.py"),
            title="Executive Overview",
            icon="🏠",
            default=True,
        ),
        st.Page(str(views_dir / "02_profile.py"), title="Company Profile", icon="🏢"),
        st.Page(str(views_dir / "03_screener.py"), title="Stock Screener", icon="🔍"),
        st.Page(str(views_dir / "04_peers.py"), title="Peer Comparison", icon="⚖️"),
        st.Page(str(views_dir / "05_trends.py"), title="Financial Trends", icon="📈"),
        st.Page(str(views_dir / "06_sectors.py"), title="Sector Analysis", icon="📊"),
        st.Page(str(views_dir / "07_capital.py"), title="Capital Structure", icon="💰"),
        st.Page(str(views_dir / "08_reports.py"), title="Reports & Export", icon="📄"),
    ]
)

pg.run()
