"""
GeNXcript Payroll SaaS — Main Streamlit App

Run with:  streamlit run app/main.py
"""

import sys
import mimetypes
from pathlib import Path

# ── Fix MIME types for font files (Windows Python doesn't register them) ──
# Without this, Streamlit's Tornado server sends wrong Content-Type for .woff2/.woff
# and the browser rejects the font files — breaking ALL Material Symbols icons.
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff",  ".woff")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="GeNXcript Payroll",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from app.auth import (
    is_logged_in, logout, get_current_user_email,
    restore_from_query_params, is_employee_role, is_admin,
    update_active_company, add_accessible_company,
    ensure_accessible_companies_loaded,
    change_own_password, get_current_display_name, update_own_display_name,
    exchange_recovery_code, set_new_password, get_user_from_access_token,
    get_accessible_pages, can_access_page, is_page_readonly,
    get_current_role, get_role_label, ROLE_COLORS,
)

# ── Sidebar: hide everything on first paint ───────────────────────────────────
# st.markdown() CSS goes through React's render queue and always arrives a few
# frames late — causing a visible sidebar flash on the login screen.
# components.html() injects a <style> tag directly into window.parent.document
# via JavaScript, which fires synchronously before React finishes painting,
# eliminating the flash entirely.  The id prevents duplicate injections on reruns.
#
# NOTE: The actual components.html() call is at the BOTTOM of this file
# (after page rendering) so the iframe wrapper doesn't add vertical space
# at the top of the page.  The JS still works identically because it injects
# into window.parent.document.head which is position-independent.
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
        '{display:none!important;}'
        + '[data-testid="stElementContainer"][height="0px"]'
        + '{height:0!important;min-height:0!important;margin:0!important;padding:0!important;overflow:hidden!important;}';
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
            st.markdown("## GeNXcript Payroll")
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
                st.markdown("## GeNXcript Payroll")
                st.error(f"Reset link expired or invalid — {_err_msg}\n\nPlease request a new password reset link.")
                if st.button("← Back to Sign In", use_container_width=True):
                    st.rerun()
            st.stop()

        from app.pages._login import render as render_login
        render_login()
    st.stop()

# ── Authenticated path — remove the early-hide style, re-show sidebar ─────────
components.html(
    """
    <script>
    (function(){
      var d = window.parent.document;
      var early = d.getElementById('gxp-hide-sidebar-early');
      if (early) early.remove();
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

st.sidebar.title("GeNXcript Payroll")
st.sidebar.caption(get_current_user_email())
st.sidebar.divider()

# ---- Employee portal (limited view) ----
if is_employee_role():
    # ── Hide Streamlit sidebar + header for employee portal ──────────────
    import json as _json_esc
    _emp_user_email = st.session_state.get("user_email", "")
    _emp_display = _emp_user_email.split("@")[0].title() if _emp_user_email else "Employee"
    _emp_company = st.session_state.get("company_name", "")
    # Escape for safe JS string interpolation (prevents XSS via session values)
    _emp_company_js = _json_esc.dumps(_emp_company)[1:-1]  # strip quotes, keep escaped content
    _emp_display_js = _json_esc.dumps(_emp_display)[1:-1]

    # Hidden sidebar button for sign-out (JS will click it)
    with st.sidebar:
        if st.button("Sign Out", key="emp_signout_btn"):
            logout()
            components.html('<script>window.parent.location.reload(true);</script>', height=0)
            st.stop()

    # Inject CSS to hide sidebar + header, and add topbar
    components.html(f"""<script>
    (function(){{
      var d = window.parent.document;

      /* Hide sidebar + header */
      var styleId = 'gxp-emp-portal-css';
      if(!d.getElementById(styleId)){{
        var s = d.createElement('style');
        s.id = styleId;
        s.textContent = [
          '[data-testid="stSidebar"]{{',
          '  position:fixed!important;left:-9999px!important;',
          '  width:1px!important;height:1px!important;',
          '  overflow:hidden!important;pointer-events:none!important;',
          '  opacity:0!important;z-index:-1!important;',
          '}}',
          '[data-testid="stSidebarCollapseButton"],',
          '[data-testid="collapsedControl"]{{display:none!important;}}',
          '[data-testid="stHeader"]{{display:none!important;}}',
          '[data-testid="stDecoration"]{{display:none!important;}}',
          '[data-testid="stAppViewContainer"]{{padding-left:0!important;}}',
          'section[data-testid="stMain"]{{margin-left:0!important;padding-left:0!important;}}',
          /* Push content down for topbar */
          'section[data-testid="stMain"] .stMainBlockContainer{{padding-top:56px!important;}}',
          /* Collapse CSS injection containers */
          '[data-testid="stElementContainer"]:has(.gxp-css-inject){{display:none!important;}}',
        ].join('');
        d.head.appendChild(s);
      }}

      /* Collapse empty/CSS-only stElementContainers */
      function collapseEmpty(){{
        d.querySelectorAll('[data-testid="stElementContainer"]').forEach(function(el){{
          if(el.getAttribute('height')==='0px'||el.getAttribute('height')==='0'){{
            el.style.display='none';
            return;
          }}
          // Check if stMarkdownContainer only contains <style> elements (no visible content)
          var mc=el.querySelector('[data-testid="stMarkdownContainer"]');
          if(!mc) return;
          var children=mc.children;
          var onlyStyle=true;
          for(var i=0;i<children.length;i++){{
            if(children[i].tagName!=='STYLE'){{ onlyStyle=false; break; }}
          }}
          if(onlyStyle && children.length>0){{
            el.style.display='none';
          }}
        }});
      }}
      collapseEmpty();
      setTimeout(collapseEmpty,200);
      setTimeout(collapseEmpty,800);

      /* Build topbar */
      var topbarId = 'gxp-emp-topbar';
      var existing = d.getElementById(topbarId);
      if(existing) existing.remove();

      var bar = d.createElement('div');
      bar.id = topbarId;
      bar.style.cssText = 'position:fixed;top:0;left:0;right:0;height:48px;'
        +'background:#ffffff;border-bottom:1px solid #e7e8e9;z-index:999;'
        +'display:flex;align-items:center;justify-content:space-between;'
        +'padding:0 20px;font-family:Plus Jakarta Sans,system-ui,sans-serif;'
        +'box-shadow:0 1px 4px rgba(0,0,0,0.04);';

      /* Left: company name */
      var left = d.createElement('div');
      left.style.cssText = 'display:flex;align-items:center;gap:8px;';
      left.innerHTML = '<span style="font-size:14px;font-weight:800;color:#191c1d;">'
        + '{_emp_company_js}'.replace(/</g,'&lt;') + '</span>'
        + '<span style="font-size:10px;font-weight:600;color:#727784;'
        + 'background:#f3f4f5;padding:2px 8px;border-radius:9999px;">Employee Portal</span>';

      /* Right: user chip + sign out */
      var right = d.createElement('div');
      right.style.cssText = 'display:flex;align-items:center;gap:10px;';

      var chip = d.createElement('span');
      chip.style.cssText = 'font-size:12px;font-weight:600;color:#005bc1;'
        +'background:#d8e2ff;padding:4px 12px;border-radius:9999px;';
      chip.textContent = '{_emp_display_js}';

      var signout = d.createElement('button');
      signout.style.cssText = 'font-size:11px;font-weight:600;color:#727784;'
        +'background:none;border:1px solid #e7e8e9;border-radius:9999px;'
        +'padding:4px 12px;cursor:pointer;transition:all 0.15s;'
        +'font-family:Plus Jakarta Sans,system-ui,sans-serif;';
      signout.textContent = 'Sign Out';
      signout.onmouseenter = function(){{ this.style.color='#dc2626';this.style.borderColor='#fca5a5';this.style.background='#fef2f2'; }};
      signout.onmouseleave = function(){{ this.style.color='#727784';this.style.borderColor='#e7e8e9';this.style.background='none'; }};
      signout.onclick = function(){{
        var btns = d.querySelectorAll('[data-testid="stSidebar"] [data-testid="stButton"] button');
        for(var i=0;i<btns.length;i++){{
          if(btns[i].textContent.indexOf('Sign Out')!==-1){{ btns[i].click(); return; }}
        }}
      }};

      right.appendChild(chip);
      right.appendChild(signout);
      bar.appendChild(left);
      bar.appendChild(right);

      var appView = d.querySelector('[data-testid="stAppViewContainer"]');
      if(appView) appView.parentElement.insertBefore(bar, appView);
      else d.body.appendChild(bar);

      /* Checkbox highlight fix handled by CSS in styles.py */
    }})();
    </script>""", height=0)

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


# Show the "Add / Switch Company" button in sidebar (admin only)
if is_admin():
    if st.sidebar.button("Add Company", width='stretch'):
        _add_company_dialog()

st.sidebar.divider()

# ============================================================
# Page navigation
# ============================================================

ALL_PAGES = [
    "Dashboard",
    "Employees",
    "Payroll Run",
    "Payroll Comparison",
    "Workforce Analytics",
    "Attendance",
    "Government Reports",
    "Calendar",
    "Company Setup",
    "Preferences",
]

# Filter pages based on current user's role + enabled modules
PAGES = get_accessible_pages()

# Super-admin gets Module Administration page
from app.auth import is_super_admin
if is_super_admin():
    PAGES.append("Module Admin")

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
        st.rerun()

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
_dirty_nav = False
if _intended != st.session_state.current_page and st.session_state.get("editing_id"):
    # Instead of showing a dialog (which conflicts with the edit dialog),
    # just silently close the edit and navigate.
    st.session_state.pop("editing_id", None)
    # Clear dialog state keys
    for _k in list(st.session_state):
        if _k.startswith(("d_", "dp_", "_dp_")):
            del st.session_state[_k]
    st.session_state.current_page = _intended

# ── Grouped sidebar navigation ────────────────────────────────────────────
_NAV_ICONS = {
    "Dashboard":          "view-dashboard",
    "Employees":          "account-group",
    "Payroll Run":        "cash-multiple",
    "Payroll Comparison": "chart-box-outline",
    "Workforce Analytics": "chart-bar",
    "Attendance":         "clock-outline",
    "Government Reports": "bank",
    "Calendar":           "calendar-month",
    "Company Setup":      "domain",
    "Preferences":        "cog",
    "Module Admin":       "puzzle",
}
_ALL_NAV_GROUPS = [
    ("Overview",    ["Dashboard"]),
    ("People",      ["Employees", "Attendance", "Calendar"]),
    ("Payroll",     ["Payroll Run", "Payroll Comparison", "Workforce Analytics"]),
    ("Compliance",  ["Government Reports"]),
    ("Settings",    ["Company Setup", "Preferences"]),
    ("Platform",    ["Module Admin"]),  # Super-admin only (filtered by PAGES)
]
# Filter groups to only include pages the current role can access
_NAV_GROUPS = [
    (name, [p for p in pages if p in PAGES])
    for name, pages in _ALL_NAV_GROUPS
]
_NAV_GROUPS = [(n, ps) for n, ps in _NAV_GROUPS if ps]  # drop empty groups
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
            # Skip reload if already on this page
            if _p == _active_page:
                pass
            else:
                st.session_state.nav_page = _p   # guard will catch dirty state
                if not st.session_state.get("editing_id"):
                    st.session_state.current_page = _p
                st.rerun()

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
_company_name   = st.session_state.get("company_name", "")
_user_email     = st.session_state.get("user_email", "")
# Derive a short display name: stored display_name > email prefix
_user_display   = st.session_state.get("display_name") or (
    _user_email.split("@")[0].replace(".", " ").title() if _user_email else "User"
)
_nav_pref_label = "Preferences"
_role_label     = get_role_label()
if is_super_admin():
    _role_fg, _role_bg = ("#005bc1", "#dbeafe")  # GeNXcript blue
else:
    _role_fg, _role_bg = ROLE_COLORS.get(get_current_role(), ("#64748b", "#f1f5f9"))

components.html(f"""
<script>
(function(){{
  var d=window.parent.document;

  // ── Remove login-page artifacts so sidebar is not hidden post-login ──────
  ['gxp-login-bg','gxp-login-style'].forEach(function(id){{
    var e=d.getElementById(id); if(e) e.remove();
  }});

  // ── Hide any page-transition loader left from nav click ──────────────
  var _pl=d.getElementById('gxp-page-loader');
  if(_pl){{ _pl.style.opacity='0'; setTimeout(function(){{ _pl.style.display='none'; }},180); }}

  var PAGES=[{_page_json}];
  var GROUPS=[{_grp_json}];
  var ACTIVE="{page}";
  var ACCT_LABEL="{_acct_label}", SIGNOUT_LABEL="{_signout_label}";
  var CO_LIST={_cos_json};
  var CUR_CO_ID="{_cur_co_id}";
  var COMPANY_NAME="{_company_name}";
  var USER_DISPLAY="{_user_display}";
  var USER_EMAIL="{_user_email}";
  var ROLE_LABEL="{_role_label}";
  var ROLE_FG="{_role_fg}";
  var ROLE_BG="{_role_bg}";
  var IS_SUPER={"true" if is_super_admin() else "false"};
  var COSW_PFX="__cosw__";
  var ID='gxp-lnav', CSS_ID='gxp-lnav-css', LS='gxp-lnav-c';
  var TB_ID='gxp-topbar';
  var EW=214, CW=54, PW=188;
  var TH=48;

  // ── Read CSS custom properties from parent page ──────────────────────
  function gc(n,fb){{
    try{{return getComputedStyle(d.documentElement).getPropertyValue(n).trim()||fb;}}
    catch(e){{return fb;}}
  }}

  // ── Page transition overlay ─────────────────────────────────────────
  function showPageLoader(){{
    var ov=d.getElementById('gxp-page-loader');
    if(!ov){{
      ov=d.createElement('div'); ov.id='gxp-page-loader';
      ov.style.cssText=
        'position:fixed;top:0;left:0;right:0;bottom:0;'+
        'background:rgba(255,255,255,0.70);backdrop-filter:blur(3px);'+
        '-webkit-backdrop-filter:blur(3px);z-index:99998;'+
        'display:flex;align-items:center;justify-content:center;'+
        'opacity:0;transition:opacity 0.15s ease;pointer-events:all;';
      var sp=d.createElement('div');
      sp.style.cssText=
        'width:40px;height:40px;border:3.5px solid #e5e7eb;'+
        'border-top-color:#2563eb;border-radius:50%;'+
        'animation:gxp-spin 0.7s linear infinite;';
      ov.appendChild(sp);
      // keyframes (in case not already present)
      if(!d.getElementById('gxp-spin-kf')){{
        var kf=d.createElement('style'); kf.id='gxp-spin-kf';
        kf.textContent='@keyframes gxp-spin{{to{{transform:rotate(360deg);}}}}';
        d.head.appendChild(kf);
      }}
      d.body.appendChild(ov);
    }}
    ov.style.display='flex';
    requestAnimationFrame(function(){{ ov.style.opacity='1'; }});
    // Auto-hide after Streamlit finishes re-rendering (watch for new content)
    var hideTimer=setTimeout(function(){{ hidePageLoader(); }},8000); // safety cap
    var obs=new MutationObserver(function(muts){{
      // Streamlit replaces page content — wait for the main area to settle
      clearTimeout(hideTimer);
      hideTimer=setTimeout(function(){{ obs.disconnect(); hidePageLoader(); }},400);
    }});
    var mainEl=d.querySelector('[data-testid="stMain"]')||d.body;
    obs.observe(mainEl,{{childList:true,subtree:true}});
  }}
  function hidePageLoader(){{
    var ov=d.getElementById('gxp-page-loader');
    if(ov){{ ov.style.opacity='0'; setTimeout(function(){{ ov.style.display='none'; }},180); }}
  }}

  // ── Click a Streamlit sidebar button by page name ────────────────────
  function clickNav(name){{
    // Skip reload if clicking the already-active page
    if(name===ACTIVE) return;
    var sb=d.querySelector('[data-testid="stSidebar"]');
    if(!sb) return;
    var btns=sb.querySelectorAll('[data-testid="stButton"] button');
    for(var i=0;i<btns.length;i++){{
      if(btns[i].textContent.indexOf(name)!==-1){{
        showPageLoader();
        btns[i].click();
        return;
      }}
    }}
  }}

  // ── Inject MDI (Pictogrammers) + Plus Jakarta Sans fonts ─────────────
  function injectFonts(){{
    if(d.getElementById('gxp-mdi-css')) return;

    // 1. MDI icon font from CDN (CSS-class based — always reliable)
    var mdiLink=d.createElement('link');
    mdiLink.id='gxp-mdi-css';
    mdiLink.rel='stylesheet';
    mdiLink.href='https://cdn.jsdelivr.net/npm/@mdi/font@7.4.47/css/materialdesignicons.min.css';
    d.head.appendChild(mdiLink);

    // 2. Plus Jakarta Sans — from Google Fonts (body text)
    var link2=d.createElement('link');
    link2.id='gxp-jakarta-css';
    link2.rel='stylesheet';
    link2.href='https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&display=swap';
    d.head.appendChild(link2);
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
      // MDI icon sizing overrides for sidebar / topbar
      '#gxp-lnav .mdi,#gxp-topbar .mdi{{line-height:1;}}',
      '[data-testid="stElementContainer"]:has(.gxp-css-inject){{display:none!important;}}',
    ].join('');
    d.head.appendChild(s);
  }}

  /* Collapse empty/CSS-only stElementContainers */
  function collapseEmpty(){{
    d.querySelectorAll('[data-testid="stElementContainer"]').forEach(function(el){{
      if(el.getAttribute('height')==='0px'||el.getAttribute('height')==='0'){{
        el.style.display='none';
        return;
      }}
      var mc=el.querySelector('[data-testid="stMarkdownContainer"]');
      if(!mc) return;
      var children=mc.children;
      var onlyStyle=true;
      for(var i=0;i<children.length;i++){{
        if(children[i].tagName!=='STYLE'){{ onlyStyle=false; break; }}
      }}
      if(onlyStyle && children.length>0){{
        el.style.display='none';
      }}
    }});
  }}
  collapseEmpty();
  setTimeout(collapseEmpty,200);
  setTimeout(collapseEmpty,800);

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

    var sf=gc('--gxp-surface','#ffffff'),
        sf2=gc('--gxp-surface2','#f3f4f5'),
        br=gc('--gxp-border','#edeeef'),
        tx=gc('--gxp-text','#191c1d'),
        t2=gc('--gxp-text2','#424753'),
        ac=gc('--gxp-accent','#005bc1'),
        ab=gc('--gxp-accent-bg','#d8e2ff');

    var nav=d.createElement('div'); nav.id=ID;
    nav.style.cssText=
      'position:fixed;left:0;top:0;bottom:0;'+
      'width:'+(isC?CW:EW)+'px;'+
      'background:'+sf+';border-right:1px solid '+br+';'+
      'z-index:99990;overflow:visible;'+
      'display:flex;flex-direction:column;'+
      'transition:width 0.22s cubic-bezier(0.4,0,0.2,1);'+
      'box-shadow:0 0 40px rgba(45,51,53,0.06);';

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

    // ── Header: brand + subtitle ───────────────────────────────────────────
    var hdr=d.createElement('div');
    hdr.style.cssText=
      'display:flex;align-items:center;'+
      'padding:20px 16px 16px;flex-shrink:0;'+
      'border-bottom:1px solid '+br+';';

    var brand=d.createElement('div');
    brand.style.cssText='display:flex;align-items:center;gap:8px;overflow:hidden;min-width:0;';
    brand.innerHTML=
      '<span class="mdi mdi-cash-register" style="font-size:22px;flex-shrink:0;line-height:1;color:'+ac+';"></span>'+
      '<div class="ln-brand" style="'+
      'white-space:nowrap;overflow:hidden;'+
      'transition:opacity 0.18s,max-width 0.18s;'+
      (isC?'opacity:0;max-width:0;':'opacity:1;max-width:160px;')+
      '"><div style="font-size:15px;font-weight:800;color:'+tx+';letter-spacing:-0.3px;line-height:1.2;">GeNXcript</div>'+
      '<div style="font-size:10px;color:'+t2+';font-weight:400;">Payroll Solutions</div></div>';

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
          'padding:8px 14px;background:'+(isA?ab:'transparent')+';'+
          'border:none;border-radius:'+(isA?'9999px':'8px')+';'+
          'color:'+(isA?ac:t2)+';cursor:pointer;text-align:left;'+
          'font-size:13px;font-weight:'+(isA?'600':'400')+';'+
          'font-family:inherit;white-space:nowrap;overflow:hidden;'+
          'transition:all 0.15s ease;outline:none;';

        var ico=d.createElement('span');
        ico.style.cssText=
          'font-size:20px;flex-shrink:0;width:24px;text-align:center;line-height:1;display:flex;align-items:center;justify-content:center;';
        ico.innerHTML='<span class="mdi mdi-'+(pi.i||'circle')+'" style="font-size:20px;"></span>';

        var lbl=d.createElement('span');
        lbl.className='ln-lbl';
        lbl.style.cssText=
          'overflow:hidden;white-space:nowrap;'+
          'transition:opacity 0.18s,max-width 0.18s;'+
          (isC?'opacity:0;max-width:0;':'opacity:1;max-width:160px;');
        lbl.textContent=pname;

        btn.appendChild(ico); btn.appendChild(lbl);
        if(!isA){{
          btn.onmouseenter=function(){{this.style.background=sf2;this.style.color=tx;this.style.borderRadius='9999px';}};
          btn.onmouseleave=function(){{this.style.background='transparent';this.style.color=t2;this.style.borderRadius='8px';}};
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
      coIcon.innerHTML='<span class="mdi mdi-domain" style="font-size:18px;flex-shrink:0;"></span>';

      var coName=d.createElement('span');
      coName.className='ln-lbl';
      coName.style.cssText=
        'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'+
        'transition:opacity 0.18s,max-width 0.18s;'+
        (isC?'opacity:0;max-width:0;':'opacity:1;max-width:140px;');
      coName.textContent=curCoName||'Select Company';
      if(CUR_CO_ID===defaultCoId){{
        var defBadge=d.createElement('span');
        defBadge.style.cssText=
          'font-size:8px;font-weight:700;background:#fef3c7;color:#92400e;'+
          'padding:1px 5px;border-radius:9999px;margin-left:4px;'+
          'text-transform:uppercase;letter-spacing:0.04em;vertical-align:middle;';
        defBadge.textContent='DEFAULT';
        coName.appendChild(defBadge);
      }}

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
        'background:'+sf+';border:1px solid '+br+';border-radius:12px;'+
        'box-shadow:0 -4px 24px rgba(45,51,53,0.12);'+
        'overflow:hidden;z-index:999999;';

      var LS_DEFAULT_CO='gxp-default-co';
      var defaultCoId=localStorage.getItem(LS_DEFAULT_CO)||'';

      CO_LIST.forEach(function(co){{
        var row=d.createElement('button');
        var isActive=co.id===CUR_CO_ID;
        var isDefault=co.id===defaultCoId;
        row.style.cssText=
          'display:flex;align-items:center;gap:8px;width:100%;'+
          'padding:9px 12px;background:'+(isActive?ab:'transparent')+';'+
          'color:'+(isActive?ac:tx)+';border:none;cursor:pointer;'+
          'font-size:12px;font-family:inherit;text-align:left;outline:none;'+
          'transition:background 0.12s;white-space:nowrap;overflow:hidden;';

        var rIcon=d.createElement('span');
        rIcon.innerHTML=isActive
          ?'<span class="mdi mdi-check-circle" style="font-size:18px;color:'+ac+';flex-shrink:0;"></span>'
          :'<span class="mdi mdi-domain" style="font-size:18px;flex-shrink:0;opacity:0.5;"></span>';

        var rName=d.createElement('span');
        rName.style.cssText='flex:1;overflow:hidden;text-overflow:ellipsis;';
        rName.textContent=co.name;

        /* ── Default star button ── */
        var star=d.createElement('span');
        star.className='mdi '+(isDefault?'mdi-star':'mdi-star-outline');
        star.title=isDefault?'Default company':'Set as default';
        star.style.cssText=
          'font-size:16px;flex-shrink:0;cursor:pointer;'+
          'color:'+(isDefault?'#f59e0b':'#9ca3af')+';'+
          'transition:color 0.15s,transform 0.15s;';
        star.onmouseenter=function(){{this.style.transform='scale(1.2)';this.style.color='#f59e0b';}};
        star.onmouseleave=function(){{
          var def=localStorage.getItem(LS_DEFAULT_CO)||'';
          this.style.transform='';
          this.style.color=(co.id===def)?'#f59e0b':'#9ca3af';
        }};
        star.onclick=function(e){{
          e.stopPropagation();
          var cur=localStorage.getItem(LS_DEFAULT_CO)||'';
          if(cur===co.id){{
            /* Unset default */
            localStorage.removeItem(LS_DEFAULT_CO);
            this.className='mdi mdi-star-outline';
            this.style.color='#9ca3af';
            this.title='Set as default';
          }} else {{
            /* Set as default — update all stars */
            localStorage.setItem(LS_DEFAULT_CO,co.id);
            var allStars=coPanel.querySelectorAll('.mdi-star,.mdi-star-outline');
            allStars.forEach(function(s){{
              s.className='mdi mdi-star-outline';
              s.style.color='#9ca3af';
              s.title='Set as default';
            }});
            this.className='mdi mdi-star';
            this.style.color='#f59e0b';
            this.title='Default company';
          }}
        }};

        row.appendChild(rIcon); row.appendChild(rName); row.appendChild(star);
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

      /* ── Auto-switch to default company on first load ── */
      if(defaultCoId && defaultCoId!==CUR_CO_ID){{
        var autoSwitchKey='gxp-auto-switched';
        if(!sessionStorage.getItem(autoSwitchKey)){{
          /* Only auto-switch once per browser session to avoid loops */
          var hasDefault=CO_LIST.some(function(c){{return c.id===defaultCoId;}});
          if(hasDefault){{
            sessionStorage.setItem(autoSwitchKey,'1');
            setTimeout(function(){{clickNav(COSW_PFX+defaultCoId);}},600);
          }}
        }}
      }}
    }}

    // My Account + Sign Out moved to topbar — no footer buttons here

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

  // ── Fix checkbox highlight ─────────────────────────────────────────────
  // "row-widget stCheckbox" classes on the wrapper div cause a blue highlight
  // when checked. The element is identified by data-testid, not its class,
  // so removing the class attribute entirely is safe and kills the highlight.
  /* Checkbox highlight fix handled by CSS in styles.py */
  function attachCheckboxFix(){{}}

  // ── Topbar ────────────────────────────────────────────────────────────────
  function buildTopbar(){{
    var old=d.getElementById(TB_ID); if(old) old.remove();

    var sf =gc('--gxp-surface','#ffffff'),
        sf2=gc('--gxp-surface2','#f3f4f5'),
        br =gc('--gxp-border','#edeeef'),
        tx =gc('--gxp-text','#191c1d'),
        t2 =gc('--gxp-text2','#424753'),
        ac =gc('--gxp-accent','#005bc1'),
        ab =gc('--gxp-accent-bg','#d8e2ff');

    var bar=d.createElement('div');
    bar.id=TB_ID;
    bar.style.cssText=
      'position:fixed;top:0;left:'+CW+'px;right:0;height:'+TH+'px;'+
      'background:'+sf+';border-bottom:1px solid '+br+';'+
      'display:flex;align-items:center;justify-content:space-between;'+
      'padding:0 20px 0 16px;z-index:99985;'+
      'box-shadow:0 1px 0 '+br+';'+
      'font-family:"Plus Jakarta Sans",sans-serif;';

    // ── Left: company name ─────────────────────────────────────────────────
    var left=d.createElement('div');
    left.style.cssText='display:flex;align-items:center;gap:8px;min-width:0;';
    left.innerHTML=
      '<span class="mdi mdi-domain" style="font-size:18px;color:'+ac+';flex-shrink:0;"></span>'+
      '<span style="font-size:13px;font-weight:600;color:'+tx+';white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px;">'+COMPANY_NAME+'</span>';

    // ── Right: user + quick actions ────────────────────────────────────────
    var right=d.createElement('div');
    right.style.cssText='display:flex;align-items:center;gap:4px;flex-shrink:0;';

    // Helper: create icon-pill button
    function tbBtn(icon, label, clickTarget, danger){{
      var b=d.createElement('button');
      b.title=label;
      b.style.cssText=
        'display:flex;align-items:center;gap:6px;padding:6px 12px;'+
        'background:transparent;border:none;border-radius:9999px;'+
        'color:'+(danger?gc('--gxp-danger','#ba1a1a'):t2)+';cursor:pointer;'+
        'font-size:12px;font-weight:500;font-family:inherit;'+
        'transition:background 0.12s,color 0.12s;white-space:nowrap;';
      b.innerHTML=
        '<span class="mdi mdi-'+icon+'" style="font-size:17px;"></span>'+
        '<span class="tb-lbl">'+label+'</span>';
      b.onmouseenter=function(){{
        this.style.background=danger?gc('--gxp-danger-bg','#ffdad6'):sf2;
        this.style.color=danger?gc('--gxp-danger','#ba1a1a'):tx;
      }};
      b.onmouseleave=function(){{
        this.style.background='transparent';
        this.style.color=danger?gc('--gxp-danger','#ba1a1a'):t2;
      }};
      b.onclick=function(){{clickNav(clickTarget);}};
      return b;
    }}

    // User chip (non-clickable display)
    var chip=d.createElement('div');
    chip.style.cssText=
      'display:flex;align-items:center;gap:6px;padding:5px 12px;'+
      'background:'+ab+';border-radius:9999px;margin-right:4px;';
    chip.innerHTML=
      '<span class="mdi mdi-account-circle" style="font-size:16px;color:'+ac+';"></span>'+
      '<span style="font-size:12px;font-weight:600;color:'+ac+';max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="'+USER_EMAIL+'">'+USER_DISPLAY+'</span>'+
      (IS_SUPER
        ? '<span style="font-size:10px;font-weight:800;background:#191c1d;padding:2px 10px;border-radius:9999px;white-space:nowrap;letter-spacing:0.03em;">'
          + '<span style="color:#fff;">GeN</span>'
          + '<span style="color:#3b82f6;">X</span>'
          + '<span style="color:#8b5cf6;">c</span>'
          + '<span style="color:#10b981;">r</span>'
          + '<span style="color:#f97316;">i</span>'
          + '<span style="color:#eab308;">p</span>'
          + '<span style="color:#06b6d4;">t</span>'
          + '</span>'
        : '<span style="font-size:10px;font-weight:700;color:'+ROLE_FG+';background:'+ROLE_BG+';padding:2px 8px;border-radius:9999px;white-space:nowrap;">'+ROLE_LABEL+'</span>'
      );

    // Divider
    var div=d.createElement('div');
    div.style.cssText='width:1px;height:22px;background:'+br+';margin:0 4px;';

    right.appendChild(chip);
    right.appendChild(tbBtn('cog','Preferences','{_nav_pref_label}',false));
    right.appendChild(tbBtn('account-cog','My Account',ACCT_LABEL,false));
    right.appendChild(div);
    right.appendChild(tbBtn('logout','Sign Out',SIGNOUT_LABEL,true));

    bar.appendChild(left);
    bar.appendChild(right);
    d.body.appendChild(bar);

    // Push main content down so it clears the topbar
    var mainStyle=d.getElementById('gxp-topbar-push');
    if(!mainStyle){{
      mainStyle=d.createElement('style');
      mainStyle.id='gxp-topbar-push';
      d.head.appendChild(mainStyle);
    }}
    mainStyle.textContent=
      '[data-testid="stAppViewContainer"]>[data-testid="stMain"]{{'+
      'padding-top:'+TH+'px!important;}}'+
      /* Hide Streamlit header entirely since topbar replaces it */
      '[data-testid="stHeader"]{{display:none!important;}}';
  }}

  function start(){{
    injectFonts(); injectCSS(); build(); buildTopbar(); attachCheckboxFix();
    new MutationObserver(function(ml){{
      for(var i=0;i<ml.length;i++){{
        for(var j=0;j<ml[i].addedNodes.length;j++){{
          var n=ml[i].addedNodes[j];
          if(n.getAttribute&&n.getAttribute('data-testid')==='stSidebar'){{
            build(); buildTopbar(); return;
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
        # Clear ALL cached data so every page reloads fresh for the new company
        st.cache_data.clear()
        st.session_state.nav_page = "Dashboard"
        st.rerun()

st.sidebar.caption("GeNXcript Payroll SaaS v0.1.0")

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
    # Clear any page-level dialog triggers so only one dialog opens per run
    st.session_state.pop("editing_id", None)
    _my_account_dialog()

# ============================================================
# Page Router
# ============================================================

def _render_page(page: str) -> None:
    # Access guard — deny pages the current role cannot see
    if not can_access_page(page):
        st.error("You do not have permission to access this page.")
        st.info("Contact your company administrator to request access.")
        return

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

    elif page == "Workforce Analytics":
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

    elif page == "Module Admin":
        from app.pages._module_admin import render as render_module_admin
        render_module_admin()


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
            icon="🔒",
        )
        st.rerun()
    else:
        raise
