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

from app.auth import is_logged_in, logout, get_current_user_email, restore_from_query_params, is_employee_role

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

# ---- Employee portal (limited view) ----
if is_employee_role():
    PAGES = ["My Portal"]

    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "My Portal"

    page = st.sidebar.radio("Navigate", options=PAGES, key="nav_page")

    st.sidebar.divider()
    st.sidebar.caption("GenXcript Payroll SaaS v0.1.0")

    if st.sidebar.button("Sign Out", width="stretch"):
        logout()
        st.rerun()

    from app.pages.employee_portal import render as render_portal
    render_portal()
    st.stop()

# ---- Admin / Viewer view ----
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

# Seed nav from URL on first render only.
# For programmatic navigation (e.g. "Run Payroll" button), pages set
# _nav_redirect in session_state before rerun, which we consume here.
if "nav_page" not in st.session_state:
    _url_page = st.query_params.get("page", "Dashboard")
    st.session_state.nav_page = _url_page if _url_page in PAGES else "Dashboard"
elif "_nav_redirect" in st.session_state:
    _target = st.session_state.pop("_nav_redirect")
    if _target in PAGES:
        st.session_state.nav_page = _target

page = st.sidebar.radio(
    "Navigate",
    options=PAGES,
    key="nav_page",
)

# Keep URL in sync so F5 refresh lands on the right page.
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
