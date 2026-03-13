"""
GenXcript Payroll SaaS — Main Streamlit App

Run with:  streamlit run app/main.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(
    page_title="GenXcript Payroll",
    page_icon="💰",
    layout="wide",
)

from app.auth import is_logged_in, logout, get_current_user_email, restore_from_query_params

# Hide Streamlit's auto-generated page navigation (it scans the pages/
# folder and shows all files as links, bypassing our auth gate).
# We use our own sidebar radio for navigation instead.
st.markdown(
    "<style>[data-testid='stSidebarNav'] { display: none; }</style>",
    unsafe_allow_html=True,
)

# ============================================================
# Session restore — runs on every page load including F5 refresh.
# Reads the session token from the URL (?sid=...) and restores
# user_id / company_id from the server-side session cache.
# ============================================================

restore_from_query_params()

# ============================================================
# Auth Gate
# ============================================================

if not is_logged_in():
    if st.session_state.get("show_register"):
        from app.pages.register import render as render_register
        render_register()
    else:
        from app.pages.login import render as render_login
        render_login()
    st.stop()

# ============================================================
# Sidebar (only shown when logged in)
# ============================================================

st.sidebar.title("GenXcript Payroll")
st.sidebar.caption(get_current_user_email())
st.sidebar.divider()

PAGES = [
    "Dashboard",
    "Employees",
    "Payroll Run",
    "Payslips",
    "Payroll Comparison",
    "Government Reports",
    "Calendar",
    "Company Setup",
]

# On the first render of a new session, seed the radio selection
# from the URL so F5 refresh lands on the correct page.
# After that, the radio widget manages its own state via the key.
if "nav_page" not in st.session_state:
    _url_page = st.query_params.get("page", "Dashboard")
    st.session_state.nav_page = _url_page if _url_page in PAGES else "Dashboard"

page = st.sidebar.radio(
    "Navigate",
    options=PAGES,
    key="nav_page",
)

# Keep URL in sync — only update when the page actually changed
# to avoid triggering unnecessary reruns.
if st.query_params.get("page") != page:
    st.query_params["page"] = page

st.sidebar.divider()
st.sidebar.caption("GenXcript Payroll SaaS v0.1.0")

if st.sidebar.button("Sign Out", width="stretch"):
    logout()
    st.rerun()

# ============================================================
# Page Router
# ============================================================

if page == "Dashboard":
    from app.pages.dashboard import render as render_dashboard
    render_dashboard()

elif page == "Employees":
    from app.pages.employees import render
    render()

elif page == "Payroll Run":
    from app.pages.payroll_run import render as render_payroll
    render_payroll()

elif page == "Payslips":
    from app.pages.payslips import render as render_payslips
    render_payslips()

elif page == "Payroll Comparison":
    from app.pages.payroll_comparison import render as render_comparison
    render_comparison()

elif page == "Government Reports":
    from app.pages.government_reports import render as render_gov_reports
    render_gov_reports()

elif page == "Calendar":
    from app.pages.calendar_view import render as render_calendar
    render_calendar()

elif page == "Company Setup":
    from app.pages.company_setup import render as render_company
    render_company()
