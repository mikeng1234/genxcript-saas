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

from app.auth import (
    is_logged_in, logout, get_current_user_email,
    restore_from_query_params, is_employee_role,
    update_active_company, add_accessible_company,
    ensure_accessible_companies_loaded,
)

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

# Lazy-load accessible_companies for sessions that pre-date the
# multi-company feature (server-cache cleared, old sid token, etc.)
ensure_accessible_companies_loaded()

# ============================================================
# Company Switcher (sidebar)
# ============================================================

accessible = st.session_state.get("accessible_companies") or []

if len(accessible) > 1:
    # Build options list and display names
    company_ids   = [c["id"]   for c in accessible]
    company_names = {c["id"]: c["name"] for c in accessible}

    current_id = st.session_state.get("company_id", company_ids[0])
    # Fallback if current_id somehow not in the list
    if current_id not in company_ids:
        current_id = company_ids[0]

    selected_id = st.sidebar.selectbox(
        "Active Company",
        options=company_ids,
        format_func=lambda cid: company_names.get(cid, cid),
        index=company_ids.index(current_id),
        key="company_switcher",
    )

    if selected_id != current_id:
        new_role = next(
            (c["role"] for c in accessible if c["id"] == selected_id), "admin"
        )
        new_name = company_names.get(selected_id, "")
        update_active_company(selected_id, new_role, new_name)
        # Return to Dashboard after switching so stale data doesn't show
        st.session_state.nav_page = "Dashboard"
        st.rerun()

    st.sidebar.divider()

elif len(accessible) == 1:
    # Single company — show name as a caption, no dropdown needed
    st.sidebar.caption(f"🏢 {accessible[0]['name']}")
    st.sidebar.divider()


# ============================================================
# Add New Company dialog
# ============================================================

@st.dialog("➕ Add New Company")
def _add_company_dialog():
    st.write("Create a new company. You will be set as admin.")
    new_name = st.text_input("Company Name", max_chars=100)
    new_region = st.selectbox(
        "Region",
        ["NCR", "CAR", "Region I", "Region II", "Region III",
         "Region IV-A", "Region IV-B", "Region V", "Region VI",
         "Region VII", "Region VIII", "Region IX", "Region X",
         "Region XI", "Region XII", "Region XIII", "BARMM"],
    )
    new_freq = st.selectbox(
        "Pay Frequency",
        ["Semi-monthly", "Monthly", "Weekly", "Bi-weekly"],
    )

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("Create Company", type="primary", use_container_width=True):
            if not new_name.strip():
                st.error("Company name is required.")
                return
            try:
                from app.db_helper import get_db
                db   = get_db()
                uid  = st.session_state.get("user_id")

                # Insert company
                comp_result = db.table("companies").insert({
                    "name":          new_name.strip(),
                    "region":        new_region,
                    "pay_frequency": new_freq,
                }).execute()

                if not comp_result.data:
                    st.error("Failed to create company. Please try again.")
                    return

                new_company_id = comp_result.data[0]["id"]

                # Grant admin access
                db.table("user_company_access").insert({
                    "user_id":    uid,
                    "company_id": new_company_id,
                    "role":       "admin",
                }).execute()

                # Update session
                new_company = {
                    "id":   new_company_id,
                    "name": new_name.strip(),
                    "role": "admin",
                }
                add_accessible_company(new_company)
                update_active_company(new_company_id, "admin", new_name.strip())

                # Switch to the new company and reset navigation
                st.session_state.nav_page = "Dashboard"
                st.rerun()

            except Exception as exc:
                st.error(f"Error: {exc}")

    with col_cancel:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


# Show the "Add / Switch Company" button in sidebar (admin/viewer only)
if st.sidebar.button("➕ Add New Company", use_container_width=True):
    _add_company_dialog()

st.sidebar.divider()

# ============================================================
# Page navigation
# ============================================================

PAGES = [
    "Dashboard",
    "Employees",
    "Payroll Run",
    "Payslips",
    "Payroll Comparison",
    "OT Analytics",
    "Government Reports",
    "Calendar",
    "Company Setup",
]

# current_page = what is actually rendered (source of truth)
# nav_page     = st.sidebar.radio key (what user clicked)
# They diverge temporarily when dirty-nav guard fires.
if "current_page" not in st.session_state:
    _url_page = st.query_params.get("page", "Dashboard")
    _start    = _url_page if _url_page in PAGES else "Dashboard"
    st.session_state.current_page = _start
    st.session_state.nav_page     = _start

# Consume programmatic redirect (e.g. "Run Payroll" button)
if "_nav_redirect" in st.session_state:
    _target = st.session_state.pop("_nav_redirect")
    if _target in PAGES:
        st.session_state.nav_page     = _target
        st.session_state.current_page = _target

# ---- Unsaved-changes guard ----------------------------------------
# Must check + revert nav_page BEFORE the radio is instantiated —
# Streamlit forbids writing to a widget key after it renders.
@st.dialog("⚠️ Unsaved Changes")
def _unsaved_nav_dialog(intended: str) -> None:
    st.warning(
        "You have an employee edit open. "
        "Navigating away will discard any unsaved changes."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Stay & Keep Editing", type="primary", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("Discard & Leave", use_container_width=True):
            st.session_state.editing_id   = None
            for _k in [k for k in st.session_state if k.startswith(("_pos_select_edit_", "_pos_new_edit_", "_dept_select_edit_", "_dept_new_edit_"))]:
                del st.session_state[_k]
            st.session_state.nav_page     = intended
            st.session_state.current_page = intended
            st.rerun()


_intended = st.session_state.get("nav_page", st.session_state.current_page)
_dirty_nav = (
    _intended != st.session_state.current_page
    and bool(st.session_state.get("editing_id"))
)
if _dirty_nav:
    # Revert BEFORE the radio renders so Streamlit doesn't complain
    st.session_state.nav_page = st.session_state.current_page

st.sidebar.radio("Navigate", options=PAGES, key="nav_page")

if _dirty_nav:
    _unsaved_nav_dialog(_intended)
    # Don't st.stop() — let the current page render behind the dialog overlay

st.session_state.current_page = st.session_state.nav_page
page = st.session_state.nav_page

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

elif page == "OT Analytics":
    from app.pages.ot_heatmap import render as render_ot
    render_ot()

elif page == "Government Reports":
    from app.pages.government_reports import render as render_gov_reports
    render_gov_reports()

elif page == "Calendar":
    from app.pages.calendar_view import render as render_calendar
    render_calendar()

elif page == "Company Setup":
    from app.pages.company_setup import render as render_company
    render_company()
