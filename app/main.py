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
    initial_sidebar_state="collapsed",
)

from app.auth import (
    is_logged_in, logout, get_current_user_email,
    restore_from_query_params, is_employee_role,
    update_active_company, add_accessible_company,
    ensure_accessible_companies_loaded,
    change_own_password, get_current_display_name, update_own_display_name,
    exchange_recovery_code, set_new_password, get_user_from_access_token,
)

# ── Sidebar: hide everything on first paint ───────────────────────────────────
# st.markdown() CSS goes through React's render queue and always arrives a few
# frames late — causing a visible sidebar flash on the login screen.
# components.html() injects a <style> tag directly into window.parent.document
# via JavaScript, which fires synchronously before React finishes painting,
# eliminating the flash entirely.  The id prevents duplicate injections on reruns.
components.html(
    """
    <script>
    (function(){
      var d = window.parent.document;
      if (d.getElementById('gxp-hide-sidebar-early')) return;
      var s = d.createElement('style');
      s.id = 'gxp-hide-sidebar-early';
      s.textContent =
        '[data-testid="stSidebar"],'
        '[data-testid="stSidebarCollapsedControl"],'
        '[data-testid="stSidebarNav"]'
        '{display:none!important;}';
      d.head.appendChild(s);
    })();
    </script>
    """,
    height=0,
    scrolling=False,
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
            st.info(f"Setting password for **{_ru['email']}**", icon=":material/key:")
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
                        st.success("Password updated! You can now sign in.")
                        st.balloons()
                    else:
                        st.error(_err)
    elif st.session_state.get("show_register"):
        from app.pages._register import render as render_register
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
                st.error(f"Reset link expired or invalid — {_err_msg}\n\nPlease request a new password reset link.")
                if st.button("← Back to Sign In", use_container_width=True):
                    st.rerun()
            st.stop()

        from app.pages._login import render as render_login
        render_login()
    st.stop()

# ── Authenticated path — remove the early-hide style, re-show sidebar ─────────
# The components.html() above injected 'gxp-hide-sidebar-early' into <head>
# which hides the sidebar for ALL renders (login + authenticated).
# Here we remove that tag so the native sidebar is visible again for logged-in
# users (our JS overlay then moves it off-screen and builds its own nav).
# stSidebarNav stays hidden via a separate rule (we use our own radio nav).
components.html(
    """
    <script>
    (function(){
      var d = window.parent.document;
      // Remove the early-hide rule so sidebar is visible for authenticated renders
      var early = d.getElementById('gxp-hide-sidebar-early');
      if (early) early.remove();
      // Keep pages/ auto-nav hidden (we use our own nav)
      if (!d.getElementById('gxp-hide-sidebar-nav')) {
        var s = d.createElement('style');
        s.id = 'gxp-hide-sidebar-nav';
        s.textContent = '[data-testid="stSidebarNav"]{display:none!important;}';
        d.head.appendChild(s);
      }
    })();
    </script>
    """,
    height=0,
    scrolling=False,
)

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
        components.html('<script>window.parent.location.reload(true);</script>', height=0)
        st.stop()

    from app.pages._employee_portal import render as render_portal
    render_portal()
    st.stop()

# ---- Admin / Viewer view ----

# Lazy-load accessible_companies for sessions that pre-date the
# multi-company feature (server-cache cleared, old sid token, etc.)
ensure_accessible_companies_loaded()


# ============================================================
# Add New Company dialog
# ============================================================

@st.dialog("Add New Company")
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
if st.sidebar.button("Add Company", width='stretch'):
    _add_company_dialog()

st.sidebar.divider()

# ============================================================
# Page navigation
# ============================================================

PAGES = [
    "Dashboard",
    "Employees",
    "Payroll Run",
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
@st.dialog("Unsaved Changes")
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
    st.session_state.nav_page = st.session_state.current_page

# ── Grouped sidebar navigation ────────────────────────────────────────────
_NAV_ICONS = {
    "Dashboard":          "view-dashboard",
    "Employees":          "account-group",
    "Payroll Run":        "cash-multiple",
    "Payroll Comparison": "chart-line",
    "OT Analytics":       "fire",
    "Attendance":         "clock-outline",
    "Government Reports": "bank-outline",
    "Calendar":           "calendar-month-outline",
    "Company Setup":      "office-building-outline",
    "Preferences":        "cog-outline",
}
_NAV_GROUPS = [
    ("Overview",    ["Dashboard"]),
    ("People",      ["Employees", "Attendance", "Calendar"]),
    ("Payroll",     ["Payroll Run", "Payroll Comparison", "OT Analytics"]),
    ("Compliance",  ["Government Reports"]),
    ("Settings",    ["Company Setup", "Preferences"]),
]
_active_page = st.session_state.current_page   # stable source of truth for highlight

for _grp_name, _grp_pages in _NAV_GROUPS:
    st.sidebar.markdown(
        f'<p class="gxp-nav-group">{_grp_name}</p>',
        unsafe_allow_html=True,
    )
    for _p in _grp_pages:
        # Marker div: active state is encoded here so CSS can highlight the
        # immediately following button via adjacent-sibling selector.
        _marker_cls = "gxp-nav-marker gxp-nav-active" if _p == _active_page else "gxp-nav-marker"
        st.sidebar.markdown(f'<div class="{_marker_cls}"></div>', unsafe_allow_html=True)
        if st.sidebar.button(
            f"{_NAV_ICONS.get(_p, '')}  {_p}",
            key=f"nav_btn_{_p}",
            use_container_width=True,
        ):
            st.session_state.nav_page = _p   # guard will catch dirty state
            if not st.session_state.get("editing_id"):
                st.session_state.current_page = _p
            st.rerun()

if _dirty_nav:
    _unsaved_nav_dialog(_intended)

st.session_state.current_page = st.session_state.nav_page
page = st.session_state.nav_page

# ── Custom collapsible left sidebar ───────────────────────────────────────
# Replaces the old collapsed-sidebar top nav bar.
# Injects a fixed left sidebar into the parent page (window.parent.document).
# The Streamlit sidebar is hidden visually but kept in the DOM so JS can
# still click its buttons as navigation targets.
_page_json = ", ".join(
    '{{"n":"{n}","i":"{i}"}}'.format(n=p, i=_NAV_ICONS.get(p, ""))
    for p in PAGES
)
_grp_json = ", ".join(
    '{{"name":"{g}","pages":[{ps}]}}'.format(
        g=grp[0],
        ps=", ".join(f'"{p}"' for p in grp[1])
    )
    for grp in _NAV_GROUPS
)
_acct_label = "My Account"
_signout_label = "Sign Out"

import json as _json
_accessible_now = st.session_state.get("accessible_companies") or []
_cos_json       = _json.dumps([{"id": c["id"], "name": c["name"]} for c in _accessible_now])
_cur_co_id      = st.session_state.get("company_id", "")

components.html(f"""
<script>
(function(){{
  var d=window.parent.document;

  // ── Remove login-page artifacts so sidebar is not hidden post-login ──────
  ['gxp-login-bg','gxp-login-style'].forEach(function(id){{
    var e=d.getElementById(id); if(e) e.remove();
  }});

  var PAGES=[{_page_json}];
  var GROUPS=[{_grp_json}];
  var ACTIVE="{page}";
  var ACCT_LABEL="{_acct_label}", SIGNOUT_LABEL="{_signout_label}";
  var CO_LIST={_cos_json};
  var CUR_CO_ID="{_cur_co_id}";
  var COSW_PFX="__cosw__";
  var ID='gxp-lnav', CSS_ID='gxp-lnav-css', LS='gxp-lnav-c';
  var EW=214, CW=54, PW=188;

  // ── Read CSS custom properties from parent page ──────────────────────
  function gc(n,fb){{
    try{{return getComputedStyle(d.documentElement).getPropertyValue(n).trim()||fb;}}
    catch(e){{return fb;}}
  }}

  // ── Click a Streamlit sidebar button by page name ────────────────────
  function clickNav(name){{
    var sb=d.querySelector('[data-testid="stSidebar"]');
    if(!sb) return;
    var btns=sb.querySelectorAll('[data-testid="stButton"] button');
    for(var i=0;i<btns.length;i++){{
      if(btns[i].textContent.indexOf(name)!==-1){{ btns[i].click(); return; }}
    }}
  }}

  // ── Inject MDI font ───────────────────────────────────────────────────
  function injectMDI(){{
    if(d.getElementById('gxp-mdi-css')) return;
    var link=d.createElement('link');
    link.id='gxp-mdi-css';
    link.rel='stylesheet';
    link.href='https://cdn.jsdelivr.net/npm/@mdi/font@7.4.47/css/materialdesignicons.min.css';
    d.head.appendChild(link);
  }}

  // ── Inject CSS: hide Streamlit sidebar + top toolbar, remove layout gaps ─
  function injectCSS(){{
    if(d.getElementById(CSS_ID)) return;
    var s=d.createElement('style'); s.id=CSS_ID;
    s.textContent=[
      '[data-testid="stSidebar"]{{',
      '  position:fixed!important;left:-9999px!important;',
      '  width:1px!important;height:1px!important;',
      '  overflow:hidden!important;pointer-events:none!important;',
      '  opacity:0!important;z-index:-1!important;',
      '}}',
      '[data-testid="stSidebarCollapseButton"],',
      '[data-testid="collapsedControl"]{{display:none!important;}}',
      // Hide Streamlit's top toolbar so our sidebar tab is always visible
      '[data-testid="stHeader"]{{display:none!important;}}',
      '[data-testid="stDecoration"]{{display:none!important;}}',
      // Kill the gap Streamlit reserves for the sidebar
      '[data-testid="stAppViewContainer"]{{padding-left:0!important;}}',
      'section[data-testid="stMain"]{{margin-left:0!important;padding-left:0!important;}}',
    ].join('');
    d.head.appendChild(s);
  }}

  // ── Offset main content by sidebar width ─────────────────────────────
  function setOffset(w){{
    var targets=[
      '[data-testid="stMain"]',
      'section[data-testid="stMain"]',
    ];
    for(var i=0;i<targets.length;i++){{
      var el=d.querySelector(targets[i]);
      if(el){{ el.style.setProperty('padding-left',w+'px','important'); break; }}
    }}
  }}

  // ── Collapse state ────────────────────────────────────────────────────
  var isC=localStorage.getItem(LS)==='1';
  var isPeek=false;

  // ── Visual update ─────────────────────────────────────────────────────
  function updateState(nav){{
    var w=isC?(isPeek?PW:CW):EW;
    nav.style.width=w+'px';
    var show=!isC||isPeek;
    // Group labels
    nav.querySelectorAll('.ln-grp').forEach(function(el){{
      el.style.opacity=show?'1':'0';
      el.style.height=show?'auto':'0';
      el.style.overflow='hidden';
      el.style.paddingTop=show?'10px':'0';
      el.style.paddingBottom=show?'4px':'0';
    }});
    // Button labels
    nav.querySelectorAll('.ln-lbl').forEach(function(el){{
      el.style.opacity=show?'1':'0';
      el.style.maxWidth=show?'160px':'0';
    }});
    // Brand text
    var bt=nav.querySelector('.ln-brand');
    if(bt){{ bt.style.opacity=show?'1':'0'; bt.style.maxWidth=show?'140px':'0'; }}
    // Toggle icon
    var ti=nav.querySelector('.ln-ti');
    if(ti) ti.textContent=isC?'\u25b6':'\u25c0';
    setOffset(isC&&!isPeek?CW:EW);
  }}

  // ── Build sidebar ─────────────────────────────────────────────────────
  function build(){{
    var old=d.getElementById(ID); if(old) old.remove();

    var sf=gc('--gxp-surface','#1e2530'),
        sf2=gc('--gxp-surface2','#161d28'),
        br=gc('--gxp-border','#2d3748'),
        tx=gc('--gxp-text','#e2e8f0'),
        t2=gc('--gxp-text2','#94a3b8'),
        ac=gc('--gxp-accent','#3b82f6'),
        ab=gc('--gxp-accent-bg','#1e3a5f');

    var nav=d.createElement('div'); nav.id=ID;
    nav.style.cssText=
      'position:fixed;left:0;top:0;bottom:0;'+
      'width:'+(isC?CW:EW)+'px;'+
      'background:'+sf+';border-right:1px solid '+br+';'+
      'z-index:99990;overflow:visible;'+
      'display:flex;flex-direction:column;'+
      'transition:width 0.22s cubic-bezier(0.4,0,0.2,1);'+
      'box-shadow:2px 0 18px rgba(0,0,0,0.26);';

    // ── Inner wrapper (clips content, lets floating tab protrude) ─────────
    var inner=d.createElement('div');
    inner.style.cssText=
      'display:flex;flex-direction:column;flex:1;overflow:hidden;min-height:0;';

    // ── Floating toggle tab (always visible on the right edge) ────────────
    var tab=d.createElement('button');
    tab.style.cssText=
      'position:absolute;top:18px;right:-14px;'+
      'width:28px;height:28px;border-radius:50%;'+
      'background:'+ac+';border:2px solid '+sf+';color:#fff;'+
      'cursor:pointer;display:flex;align-items:center;justify-content:center;'+
      'font-size:11px;z-index:99991;'+
      'box-shadow:2px 0 8px rgba(0,0,0,0.35);outline:none;'+
      'transition:background 0.15s,transform 0.22s;';
    tab.innerHTML='<span class="ln-ti">'+(isC?'\u25b6':'\u25c0')+'</span>';
    tab.onmouseenter=function(){{this.style.background='#2563eb';}};
    tab.onmouseleave=function(){{this.style.background=ac;}};
    tab.onclick=function(e){{
      e.stopPropagation();
      isC=!isC; isPeek=false;
      localStorage.setItem(LS,isC?'1':'0');
      updateState(nav);
    }};
    nav.appendChild(tab);

    // ── Header: logo only (toggle moved to floating tab) ──────────────────
    var hdr=d.createElement('div');
    hdr.style.cssText=
      'display:flex;align-items:center;'+
      'padding:14px 10px 12px;flex-shrink:0;'+
      'border-bottom:1px solid '+br+';';

    var brand=d.createElement('div');
    brand.style.cssText='display:flex;align-items:center;gap:7px;overflow:hidden;min-width:0;';
    brand.innerHTML=
      '<span style="font-size:20px;flex-shrink:0;line-height:1;"><i class="mdi mdi-cash" style="color:'+ac+';"></i></span>'+
      '<span class="ln-brand" style="font-size:13px;font-weight:700;color:'+tx+';'+
      'white-space:nowrap;letter-spacing:-0.3px;overflow:hidden;'+
      'transition:opacity 0.18s,max-width 0.18s;'+
      (isC?'opacity:0;max-width:0;':'opacity:1;max-width:140px;')+
      '">GenXcript</span>';

    hdr.appendChild(brand);
    inner.appendChild(hdr);

    // ── Scrollable nav items ───────────────────────────────────────────
    var body=d.createElement('div');
    body.style.cssText=
      'flex:1;overflow-y:auto;overflow-x:hidden;padding:6px 0;scrollbar-width:none;min-height:0;';

    GROUPS.forEach(function(grp){{
      var grpEl=d.createElement('div');
      grpEl.className='ln-grp';
      grpEl.style.cssText=
        'font-size:9px;font-weight:700;letter-spacing:1.1px;'+
        'text-transform:uppercase;color:'+t2+';padding:10px 14px 4px;'+
        'white-space:nowrap;overflow:hidden;'+
        'transition:opacity 0.18s,height 0.18s,padding 0.18s;'+
        (isC?'opacity:0;height:0;padding-top:0;padding-bottom:0;':'opacity:1;');
      grpEl.textContent=grp.name;
      body.appendChild(grpEl);

      grp.pages.forEach(function(pname){{
        var pi=PAGES.find(function(p){{return p.n===pname;}})||{{n:pname,i:''}};
        var isA=(pname===ACTIVE);

        var btn=d.createElement('button');
        btn.style.cssText=
          'display:flex;align-items:center;gap:10px;width:100%;'+
          'padding:8px 12px;background:'+(isA?ab:'transparent')+';'+
          'border:none;border-left:3px solid '+(isA?ac:'transparent')+';'+
          'color:'+(isA?ac:t2)+';cursor:pointer;text-align:left;'+
          'font-size:13px;font-weight:'+(isA?'600':'400')+';'+
          'font-family:inherit;white-space:nowrap;overflow:hidden;'+
          'transition:background 0.12s,color 0.12s;outline:none;';

        var ico=d.createElement('span');
        ico.style.cssText=
          'font-size:18px;flex-shrink:0;width:24px;text-align:center;line-height:1;display:flex;align-items:center;justify-content:center;';
        ico.innerHTML='<i class="mdi mdi-'+(pi.i||'circle-small')+'" style="font-size:18px;"></i>';

        var lbl=d.createElement('span');
        lbl.className='ln-lbl';
        lbl.style.cssText=
          'overflow:hidden;white-space:nowrap;'+
          'transition:opacity 0.18s,max-width 0.18s;'+
          (isC?'opacity:0;max-width:0;':'opacity:1;max-width:160px;');
        lbl.textContent=pname;

        btn.appendChild(ico); btn.appendChild(lbl);
        if(!isA){{
          btn.onmouseenter=function(){{this.style.background=sf2;this.style.color=tx;}};
          btn.onmouseleave=function(){{this.style.background='transparent';this.style.color=t2;}};
        }}
        btn.onclick=function(){{ clickNav(pname); }};
        body.appendChild(btn);
      }});
    }});

    inner.appendChild(body);

    // ── Footer: Company switcher + Account + Sign out ──────────────────
    var foot=d.createElement('div');
    foot.style.cssText=
      'flex-shrink:0;border-top:1px solid '+br+';padding:8px 0;';

    // Company switcher (custom dropdown — only rendered when >1 company)
    if(CO_LIST.length>1){{
      var curCoName=CO_LIST.reduce(function(a,c){{return c.id===CUR_CO_ID?c.name:a;}},'');

      var coWrap=d.createElement('div');
      coWrap.style.cssText=
        'padding:6px 10px 8px;border-bottom:1px solid '+br+';margin-bottom:4px;position:relative;';

      // Group label (hidden when collapsed)
      var coLbl=d.createElement('div');
      coLbl.className='ln-lbl';
      coLbl.style.cssText=
        'font-size:9.5px;font-weight:700;letter-spacing:0.08em;'+
        'color:'+t2+';text-transform:uppercase;margin-bottom:5px;'+
        'overflow:hidden;white-space:nowrap;'+
        'transition:opacity 0.18s,max-width 0.18s;'+
        (isC?'opacity:0;max-width:0;height:0;margin:0;':'opacity:1;max-width:160px;');
      coLbl.textContent='Active Company';

      // Trigger button
      var coTrig=d.createElement('button');
      coTrig.style.cssText=
        'display:flex;align-items:center;gap:8px;width:100%;'+
        'padding:7px 10px;background:'+sf2+';color:'+tx+';'+
        'border:1px solid '+br+';border-radius:7px;cursor:pointer;'+
        'font-size:12px;font-family:inherit;text-align:left;outline:none;'+
        'transition:border-color 0.15s,background 0.15s;'+
        'overflow:hidden;white-space:nowrap;'+
        (isC?'justify-content:center;':'');

      var coIcon=d.createElement('span');
      coIcon.innerHTML='<i class="mdi mdi-office-building-outline" style="font-size:15px;flex-shrink:0;"></i>';

      var coName=d.createElement('span');
      coName.className='ln-lbl';
      coName.style.cssText=
        'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'+
        'transition:opacity 0.18s,max-width 0.18s;'+
        (isC?'opacity:0;max-width:0;':'opacity:1;max-width:140px;');
      coName.textContent=curCoName||'Select Company';

      var coArrow=d.createElement('span');
      coArrow.className='ln-lbl';
      coArrow.style.cssText=
        'font-size:10px;flex-shrink:0;color:'+t2+';'+
        'transition:opacity 0.18s,max-width 0.18s,transform 0.15s;'+
        (isC?'opacity:0;max-width:0;':'opacity:1;max-width:16px;');
      coArrow.textContent='▾';

      coTrig.appendChild(coIcon);
      coTrig.appendChild(coName);
      coTrig.appendChild(coArrow);
      coTrig.onmouseenter=function(){{this.style.borderColor=ac;this.style.background=ab;}};
      coTrig.onmouseleave=function(){{this.style.borderColor=br;this.style.background=sf2;}};

      // Dropdown panel (floating, shown on click)
      var coPanel=d.createElement('div');
      coPanel.style.cssText=
        'display:none;position:absolute;left:10px;right:10px;'+
        'bottom:calc(100% + 2px);'+
        'background:'+sf+';border:1px solid '+br+';border-radius:8px;'+
        'box-shadow:0 -4px 24px rgba(0,0,0,0.4);'+
        'overflow:hidden;z-index:999999;';

      CO_LIST.forEach(function(co){{
        var row=d.createElement('button');
        var isActive=co.id===CUR_CO_ID;
        row.style.cssText=
          'display:flex;align-items:center;gap:8px;width:100%;'+
          'padding:9px 12px;background:'+(isActive?ab:'transparent')+';'+
          'color:'+(isActive?ac:tx)+';border:none;cursor:pointer;'+
          'font-size:12px;font-family:inherit;text-align:left;outline:none;'+
          'transition:background 0.12s;white-space:nowrap;overflow:hidden;';

        var rIcon=d.createElement('span');
        rIcon.innerHTML=isActive
          ?'<i class="mdi mdi-check-circle" style="font-size:14px;color:'+ac+';flex-shrink:0;"></i>'
          :'<i class="mdi mdi-office-building-outline" style="font-size:14px;flex-shrink:0;opacity:0.5;"></i>';

        var rName=d.createElement('span');
        rName.style.cssText='flex:1;overflow:hidden;text-overflow:ellipsis;';
        rName.textContent=co.name;

        row.appendChild(rIcon); row.appendChild(rName);
        if(!isActive){{
          row.onmouseenter=function(){{this.style.background=sf2;}};
          row.onmouseleave=function(){{this.style.background='transparent';}};
        }}
        row.onclick=(function(id){{return function(){{
          coPanel.style.display='none';
          coArrow.style.transform='rotate(0deg)';
          clickNav(COSW_PFX+id);
        }};}})(co.id);
        coPanel.appendChild(row);
      }});

      // Toggle panel on trigger click
      var panelOpen=false;
      coTrig.onclick=function(){{
        panelOpen=!panelOpen;
        coPanel.style.display=panelOpen?'block':'none';
        coArrow.style.transform=panelOpen?'rotate(180deg)':'rotate(0deg)';
      }};

      // Close panel when clicking outside
      d.addEventListener('click',function(e){{
        if(panelOpen&&!coWrap.contains(e.target)){{
          panelOpen=false;
          coPanel.style.display='none';
          coArrow.style.transform='rotate(0deg)';
        }}
      }});

      coWrap.appendChild(coLbl);
      coWrap.appendChild(coTrig);
      coWrap.appendChild(coPanel);
      foot.appendChild(coWrap);
    }}

    // [clickTarget, displayText, mdiIcon]
    [
      [ACCT_LABEL, 'My Account', 'account-circle-outline'],
      [SIGNOUT_LABEL, 'Sign Out', 'logout']
    ].forEach(function(item){{
      var clickTarget=item[0], displayText=item[1], mdiIcon=item[2];
      var fbtn=d.createElement('button');
      fbtn.style.cssText=
        'display:flex;align-items:center;gap:10px;width:100%;'+
        'padding:8px 12px;background:transparent;border:none;border-left:3px solid transparent;'+
        'color:'+t2+';cursor:pointer;text-align:left;'+
        'font-size:13px;font-family:inherit;white-space:nowrap;overflow:hidden;'+
        'transition:background 0.12s,color 0.12s;outline:none;';
      var fi=d.createElement('span');
      fi.style.cssText='font-size:18px;flex-shrink:0;width:24px;text-align:center;display:flex;align-items:center;justify-content:center;';
      fi.innerHTML='<i class="mdi mdi-'+mdiIcon+'" style="font-size:18px;"></i>';
      var fl=d.createElement('span');
      fl.className='ln-lbl';
      fl.style.cssText=
        'overflow:hidden;white-space:nowrap;'+
        'transition:opacity 0.18s,max-width 0.18s;'+
        (isC?'opacity:0;max-width:0;':'opacity:1;max-width:160px;');
      fl.textContent=displayText;
      fbtn.appendChild(fi); fbtn.appendChild(fl);
      fbtn.onmouseenter=function(){{this.style.background=sf2;this.style.color=tx;}};
      fbtn.onmouseleave=function(){{this.style.background='transparent';this.style.color=t2;}};
      fbtn.onclick=(function(t){{return function(){{clickNav(t);}};}})(clickTarget);
      foot.appendChild(fbtn);
    }});

    inner.appendChild(foot);
    nav.appendChild(inner);

    // ── Peek on hover when collapsed ───────────────────────────────────
    nav.onmouseenter=function(){{
      if(isC){{ isPeek=true; updateState(nav); }}
    }};
    nav.onmouseleave=function(){{
      if(isC){{ isPeek=false; updateState(nav); }}
    }};

    d.body.appendChild(nav);
    setOffset(isC?CW:EW);
  }}

  function start(){{
    injectMDI(); injectCSS(); build();
    // Re-run on Streamlit hot-reload (sidebar element replaced)
    new MutationObserver(function(ml){{
      for(var i=0;i<ml.length;i++){{
        for(var j=0;j<ml[i].addedNodes.length;j++){{
          var n=ml[i].addedNodes[j];
          if(n.getAttribute&&n.getAttribute('data-testid')==='stSidebar'){{
            build(); return;
          }}
        }}
      }}
    }}).observe(d.body,{{childList:true,subtree:false}});
  }}

  if(d.readyState==='loading') d.addEventListener('DOMContentLoaded',start);
  else setTimeout(start,60);
}})();
</script>
""", height=0, scrolling=False)


# Keep URL in sync so F5 refresh lands on the right page.

if st.query_params.get("page") != page:
    st.query_params["page"] = page

st.sidebar.divider()

# ============================================================
# Hidden company-switch trigger buttons
# The JS overlay's <select> calls clickNav("__cosw__{id}")
# which finds these hidden buttons and clicks them.
# ============================================================
for _co in _accessible_now:
    _cosw_key = f"__cosw__{_co['id']}"
    if st.sidebar.button(_cosw_key, key=f"_cosw_{_co['id']}"):
        update_active_company(_co["id"], _co["role"], _co["name"])
        st.session_state.nav_page = "Dashboard"
        st.rerun()

st.sidebar.caption("GenXcript Payroll SaaS v0.1.0")

if st.sidebar.button("My Account", width="stretch"):
    st.session_state["_show_my_account"] = True
    st.rerun()

if st.sidebar.button("Sign Out", width="stretch"):
    logout()
    components.html('<script>window.parent.location.reload(true);</script>', height=0)
    st.stop()

# ============================================================
# My Account dialog
# ============================================================

@st.dialog("My Account")
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
                st.toast("Display name updated!", icon=":material/check_circle:")
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

def _render_page(page: str) -> None:
    if page == "Dashboard":
        from app.pages._dashboard import render as render_dashboard
        render_dashboard()

    elif page == "Employees":
        from app.pages._employees import render
        render()

    elif page == "Payroll Run":
        from app.pages._payroll_run import render as render_payroll
        render_payroll()

    elif page == "Payroll Comparison":
        from app.pages._payroll_comparison import render as render_comparison
        render_comparison()

    elif page == "OT Analytics":
        from app.pages._ot_heatmap import render as render_ot
        render_ot()

    elif page == "Attendance":
        from app.pages._dtr import render as render_dtr
        render_dtr()

    elif page == "Government Reports":
        from app.pages._government_reports import render as render_gov_reports
        render_gov_reports()

    elif page == "Calendar":
        from app.pages._calendar_view import render as render_calendar
        render_calendar()

    elif page == "Company Setup":
        from app.pages._company_setup import render as render_company
        render_company()

    elif page == "Preferences":
        from app.pages._preferences import render as render_preferences
        render_preferences()


try:
    _render_page(page)
except Exception as _page_exc:
    _exc_msg = str(_page_exc)
    if "jwt expired" in _exc_msg.lower() or "PGRST303" in _exc_msg:
        # Cached admin DB client has stale JWT state — clear cache and force re-login.
        try:
            from app.db_helper import get_db
            get_db.clear()
        except Exception:
            pass
        logout()
        st.error(
            "Your session has expired. Please sign in again.",
            icon=":material/lock:",
        )
        st.rerun()
    else:
        raise
