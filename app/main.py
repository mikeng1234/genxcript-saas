"""
GenXcript Payroll SaaS — Main Streamlit App

Run with:  streamlit run app/main.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import streamlit.components.v1 as components

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
    change_own_password, get_current_display_name, update_own_display_name,
    exchange_recovery_code, set_new_password, get_user_from_access_token,
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

# ── PKCE flow: ?code=TOKEN ────────────────────────────────────────────────────
if not is_logged_in() and "pw_reset_user" not in st.session_state:
    _code = st.query_params.get("code")
    if _code:
        _ru = exchange_recovery_code(_code)
        if _ru:
            st.session_state["pw_reset_user"] = _ru
            st.query_params.clear()
            st.rerun()

# ============================================================
# Auth Gate
# ============================================================

if not is_logged_in():
    if st.session_state.get("pw_reset_user"):
        # ── Set New Password form ─────────────────────────────
        _, _col, _ = st.columns([1, 1.5, 1])
        with _col:
            st.markdown("## GenXcript Payroll")
            st.markdown("#### Set New Password")
            st.divider()
            _ru = st.session_state["pw_reset_user"]
            st.info(f"Setting password for **{_ru['email']}**", icon="🔑")
            with st.form("set_pw_form"):
                _new_pw   = st.text_input("New password", type="password",
                                          help="Minimum 6 characters")
                _conf_pw  = st.text_input("Confirm new password", type="password")
                _save_btn = st.form_submit_button("Save Password", type="primary",
                                                  use_container_width=True)
            if _save_btn:
                if len(_new_pw) < 6:
                    st.error("Password must be at least 6 characters.")
                elif _new_pw != _conf_pw:
                    st.error("Passwords do not match.")
                else:
                    _ok, _err = set_new_password(_ru["user_id"], _new_pw)
                    if _ok:
                        st.session_state.pop("pw_reset_user", None)
                        st.success("✅ Password updated! You can now sign in.")
                        st.balloons()
                    else:
                        st.error(_err)
    elif st.session_state.get("show_register"):
        from app.pages.register import render as render_register
        render_register()
    else:
        # ── Implicit flow: #access_token=TOKEN in URL hash ────
        # declare_component iframes have allow-same-origin so JS can
        # read window.parent.location.hash and call setComponentValue.
        # The component fires on every login page render; on recovery
        # it returns {type, access_token} triggering a rerun.
        if not st.session_state.get("_hash_checked"):
            from app.components.hash_auth import read_hash_auth
            _hash_val = read_hash_auth(key="hash_auth_reader", default=None)
            if isinstance(_hash_val, dict):
                if _hash_val.get("type") == "recovery":
                    _token = _hash_val.get("access_token", "")
                    _ru = get_user_from_access_token(_token) if _token else None
                    st.session_state["_hash_checked"] = True
                    if _ru:
                        st.session_state["pw_reset_user"] = _ru
                    st.rerun()
                elif _hash_val.get("type") == "error":
                    st.session_state["_hash_checked"] = True
                    st.session_state["_hash_error"] = _hash_val.get("desc", "Link expired")
                    st.rerun()
                else:
                    st.session_state["_hash_checked"] = True

        if st.session_state.get("_hash_error"):
            _err_msg = st.session_state.pop("_hash_error")
            st.session_state.pop("_hash_checked", None)
            _, _col, _ = st.columns([1, 1.5, 1])
            with _col:
                st.markdown("## GenXcript Payroll")
                st.error(f"⚠️ Reset link expired or invalid — {_err_msg}\n\nPlease request a new password reset link.")
                if st.button("← Back to Sign In", use_container_width=True):
                    st.rerun()
            st.stop()

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
    # Single company — show name as a label, not a tiny caption
    st.sidebar.markdown(
        f"<div style='font-size:13px;font-weight:600;padding:2px 0 4px 0;'>"
        f"🏢 {accessible[0]['name']}</div>",
        unsafe_allow_html=True,
    )
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
        if st.button("Create Company", type="primary", width='stretch'):
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
        if st.button("Cancel", width='stretch'):
            st.rerun()


# Show the "Add / Switch Company" button in sidebar (admin/viewer only)
if st.sidebar.button("➕ Add New Company", width='stretch'):
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
    "Attendance",
    "Government Reports",
    "Calendar",
    "Company Setup",
    "Preferences",
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
        if st.button("Stay & Keep Editing", type="primary", width='stretch'):
            st.rerun()
    with col2:
        if st.button("Discard & Leave", width='stretch'):
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

# ── Collapsed-sidebar top navigation bar ───────────────────────
# Rendered as a 0-height component so the JS executes without
# taking up any visual space. The script injects a fixed top bar
# into the *parent* page (window.parent.document) and shows/hides
# it based on the sidebar's aria-expanded attribute.
_NAV_ICONS = {
    "Dashboard": "📊", "Employees": "👥", "Payroll Run": "💸",
    "Payslips": "📄", "Payroll Comparison": "📈", "OT Analytics": "🔥",
    "Attendance": "🕐", "Government Reports": "🏛️", "Calendar": "📅",
    "Company Setup": "🏢", "Preferences": "⚙️",
}
_nav_json = ", ".join(
    '{{"n":"{n}","i":"{i}"}}'.format(n=p, i=_NAV_ICONS.get(p, ""))
    for p in PAGES
)
components.html(f"""
<script>
(function(){{
  var PAGES=[{_nav_json}], ACTIVE="{page}", ID='gxp-topnav', H=48;
  var d=window.parent.document;

  function gc(n,fb){{
    try{{var v=getComputedStyle(d.documentElement).getPropertyValue(n).trim();return v||fb;}}
    catch(e){{return fb;}}
  }}

  function isSidebarCollapsed(){{
    var sb=d.querySelector('[data-testid="stSidebar"]');
    if(!sb) return false;
    // Primary: aria-expanded attribute
    var ae=sb.getAttribute('aria-expanded');
    if(ae==='false') return true;
    if(ae==='true')  return false;
    // Fallback: measure actual rendered width (collapsed sidebar ~0-80px)
    var w=sb.getBoundingClientRect().width;
    if(w>0) return w<100;
    // Fallback: check collapse button aria state
    var btn=d.querySelector('[data-testid="stSidebarCollapseButton"] button,[aria-label="Close sidebar"],[aria-label="Collapse sidebar"]');
    if(btn) return false; // button present means it's open
    return false;
  }}

  function clickNav(name){{
    // First try to expand sidebar and click the radio
    var sb=d.querySelector('[data-testid="stSidebar"]');
    if(!sb) return;
    var labels=sb.querySelectorAll('label');
    for(var i=0;i<labels.length;i++){{
      if(labels[i].textContent.trim()===name){{
        var inp=labels[i].querySelector('input[type="radio"]');
        if(inp){{ inp.click(); return; }}
        labels[i].click(); return;
      }}
    }}
  }}

  function getStHeaderHeight(){{
    var h=d.querySelector('[data-testid="stHeader"]');
    return h ? h.getBoundingClientRect().height : 0;
  }}

  function setMainPad(collapsed){{
    var extra=collapsed?(getStHeaderHeight()+H+4):0;
    var selectors=[
      '[data-testid="stMainBlockContainer"]',
      '.stMainBlockContainer',
      '[data-testid="block-container"]',
      '.block-container'
    ];
    for(var i=0;i<selectors.length;i++){{
      var el=d.querySelector(selectors[i]);
      if(el){{ el.style.paddingTop=extra?extra+'px':''; break; }}
    }}
  }}

  function build(){{
    var old=d.getElementById(ID); if(old) old.remove();
    var sf=gc('--gxp-surface','#1e2530'), br=gc('--gxp-border','#2d3748'),
        tx=gc('--gxp-text','#e2e8f0'),   t2=gc('--gxp-text2','#94a3b8'),
        ac=gc('--gxp-accent','#3b82f6'), ab=gc('--gxp-accent-bg','#1e3a5f');
    var hh=getStHeaderHeight();

    var nav=d.createElement('div'); nav.id=ID;
    nav.style.cssText=
      'position:fixed;top:'+hh+'px;left:0;right:0;z-index:99990;'+
      'background:'+sf+';border-bottom:1px solid '+br+';'+
      'display:none;align-items:center;gap:2px;'+
      'padding:0 14px;height:'+H+'px;'+
      'overflow-x:auto;white-space:nowrap;'+
      'box-shadow:0 2px 12px rgba(0,0,0,0.28);scrollbar-width:none;';

    // Logo
    var logo=d.createElement('div');
    logo.innerHTML='<span style="font-size:17px">💰</span>'+
      '<span style="font-size:14px;font-weight:700;color:'+tx+';margin-left:5px;letter-spacing:-0.3px">GenXcript</span>';
    logo.style.cssText='display:flex;align-items:center;flex-shrink:0;margin-right:12px;';
    nav.appendChild(logo);

    var sep=d.createElement('div');
    sep.style.cssText='width:1px;height:20px;background:'+br+';margin-right:8px;flex-shrink:0;';
    nav.appendChild(sep);

    PAGES.forEach(function(p){{
      var isA=(p.n===ACTIVE);
      var btn=d.createElement('button');
      btn.textContent=(p.i?p.i+'\u00a0':'')+p.n;
      btn.style.cssText=
        'border:1px solid '+(isA?ac:'transparent')+';'+
        'background:'+(isA?ab:'transparent')+';'+
        'color:'+(isA?ac:t2)+';cursor:pointer;'+
        'padding:5px 11px;border-radius:6px;font-size:12px;'+
        'font-weight:'+(isA?'600':'400')+';'+
        'white-space:nowrap;flex-shrink:0;font-family:inherit;'+
        'transition:background 0.12s,color 0.12s;outline:none;';
      if(!isA){{
        btn.onmouseenter=function(){{this.style.background=gc('--gxp-surface2','#161d28');this.style.color=tx;}};
        btn.onmouseleave=function(){{this.style.background='transparent';this.style.color=t2;}};
      }}
      btn.onclick=function(){{ clickNav(p.n); }};
      nav.appendChild(btn);
    }});

    d.body.appendChild(nav);
  }}

  function sync(){{
    var collapsed=isSidebarCollapsed();
    var nav=d.getElementById(ID);
    if(!nav){{ build(); nav=d.getElementById(ID); }}
    // Always recompute top offset in case Streamlit header rendered late
    nav.style.top=getStHeaderHeight()+'px';
    nav.style.display=collapsed?'flex':'none';
    setMainPad(collapsed);
  }}

  var _sbObs=null;
  function watchSidebar(){{
    var sb=d.querySelector('[data-testid="stSidebar"]');
    if(!sb) return;
    if(_sbObs) _sbObs.disconnect();
    _sbObs=new MutationObserver(sync);
    _sbObs.observe(sb,{{attributes:true,attributeFilter:['aria-expanded','class','style']}});
  }}

  function start(){{
    build(); sync(); watchSidebar();
    // Re-watch if sidebar element is replaced (Streamlit hot-reload)
    new MutationObserver(function(ml){{
      for(var i=0;i<ml.length;i++){{
        var added=ml[i].addedNodes;
        for(var j=0;j<added.length;j++){{
          if(added[j].getAttribute&&added[j].getAttribute('data-testid')==='stSidebar'){{
            watchSidebar(); sync(); return;
          }}
        }}
      }}
    }}).observe(d.body,{{childList:true,subtree:false}});
    // Polling fallback — covers any cases MutationObserver misses
    setInterval(sync, 600);
  }}

  if(d.readyState==='loading') d.addEventListener('DOMContentLoaded',start);
  else setTimeout(start, 120);
}})();
</script>
""", height=0, scrolling=False)

# Keep URL in sync so F5 refresh lands on the right page.

if st.query_params.get("page") != page:
    st.query_params["page"] = page

st.sidebar.divider()
st.sidebar.caption("GenXcript Payroll SaaS v0.1.0")

if st.sidebar.button("👤 My Account", width="stretch"):
    st.session_state["_show_my_account"] = True
    st.rerun()

if st.sidebar.button("Sign Out", width="stretch"):
    logout()
    st.rerun()

# ============================================================
# My Account dialog
# ============================================================

@st.dialog("👤 My Account")
def _my_account_dialog():
    email = get_current_user_email()
    display_name = get_current_display_name()

    st.markdown(f"**Email** &nbsp; `{email}`")
    st.divider()

    # ── Display name ─────────────────────────────────────────
    st.markdown("#### Display Name")
    new_name = st.text_input(
        "Name shown in the sidebar",
        value=display_name,
        placeholder="e.g. Juan dela Cruz",
        key="ma_display_name",
    )
    if st.button("Update Name", key="ma_save_name", type="primary"):
        if not new_name.strip():
            st.error("Display name cannot be empty.")
        else:
            ok, err = update_own_display_name(new_name)
            if ok:
                st.toast("Display name updated!", icon="✅")
                st.rerun()
            else:
                st.error(err)

    st.divider()

    # ── Change password ───────────────────────────────────────
    st.markdown("#### Change Password")
    cur_pw  = st.text_input("Current password",  type="password", key="ma_cur_pw")
    new_pw  = st.text_input("New password",       type="password", key="ma_new_pw",
                             help="Minimum 6 characters")
    conf_pw = st.text_input("Confirm new password", type="password", key="ma_conf_pw")

    if st.button("Change Password", key="ma_change_pw"):
        if not cur_pw:
            st.error("Enter your current password.")
        elif len(new_pw) < 6:
            st.error("New password must be at least 6 characters.")
        elif new_pw != conf_pw:
            st.error("New passwords do not match.")
        else:
            ok, err = change_own_password(cur_pw, new_pw)
            if ok:
                st.success("Password changed successfully!")
            else:
                st.error(err)

if st.session_state.pop("_show_my_account", False):
    _my_account_dialog()

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

elif page == "Attendance":
    from app.pages.dtr import render as render_dtr
    render_dtr()

elif page == "Government Reports":
    from app.pages.government_reports import render as render_gov_reports
    render_gov_reports()

elif page == "Calendar":
    from app.pages.calendar_view import render as render_calendar
    render_calendar()

elif page == "Company Setup":
    from app.pages.company_setup import render as render_company
    render_company()

elif page == "Preferences":
    from app.pages.preferences import render as render_preferences
    render_preferences()
