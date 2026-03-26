"""
Login Page — Material 3 "Tactile Sanctuary" redesign.

Split-panel layout inspired by Google Stitch reference (01_login.html):
  Left  (40%) — Branded gradient panel with feature highlights
  Right (60%) — Login card with pill inputs / pill CTA

CSS targets Streamlit column selectors directly (st.markdown wrappers
don't actually wrap widgets — each markdown call is its own DOM node).

Cookie keys
-----------
gxp_remember_id      : last-used employee ID / email
gxp_remember_company : last-used company name (display only)
"""

import datetime
import streamlit as st
import extra_streamlit_components as stx
from app.auth import login, send_password_reset


# ── Cookie helper ──────────────────────────────────────────────────────────────
_REMEMBER_ID_KEY      = "gxp_remember_id"
_REMEMBER_COMPANY_KEY = "gxp_remember_company"
_COOKIE_DAYS          = 30

_cookie_manager_instance = None

def _cm():
    global _cookie_manager_instance
    if _cookie_manager_instance is None:
        _cookie_manager_instance = stx.CookieManager(key="gxp_cookies")
    return _cookie_manager_instance


def _get_cookie(key: str) -> str:
    try:
        return _cm().get(key) or ""
    except Exception:
        return ""


def _set_cookie(key: str, value: str) -> None:
    try:
        expires = datetime.datetime.now() + datetime.timedelta(days=_COOKIE_DAYS)
        _cm().set(key, value, expires_at=expires)
    except Exception:
        pass


def _delete_cookie(key: str) -> None:
    try:
        _cm().delete(key)
    except Exception:
        pass


# ── Tiny spacer ───────────────────────────────────────────────────────────────
def _gap(px: int) -> None:
    st.markdown(f"<div style='height:{px}px'></div>", unsafe_allow_html=True)


# ── Login-page CSS — self-contained (inject_css not called on login) ─────────
# CSS uses column selectors to style Streamlit widgets directly.
# Left column  = :nth-child(1) — branded gradient panel
# Right column = :nth-child(2) — form card
_LOGIN_CSS = """
<style>
/* ── Fonts ─────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

/* ── Root tokens (M3 Tactile) ──────────────────────────────────── */
:root {
    --login-bg:         #f8f9fa;
    --login-surface:    #ffffff;
    --login-surface2:   #ebeef0;
    --login-text:       #191c1d;
    --login-text2:      #424753;
    --login-text3:      #727784;
    --login-accent:     #005bc1;
    --login-accent-end: #3d89ff;
    --login-green:      #89fa9b;
    --login-shadow:     0px 20px 40px rgba(45, 51, 53, 0.06);
}

/* ── Global overrides for login page ───────────────────────────── */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
[data-testid="stAppViewContainer"] {
    background: var(--login-bg) !important;
}
/* Hide header/footer/hamburger */
[data-testid="stHeader"],
footer,
#MainMenu { display: none !important; }
/* Remove default padding so split layout fills viewport */
.stMainBlockContainer,
[data-testid="stAppViewBlockContainer"],
.block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    max-width: 100% !important;
}
/* Prevent scrolling — fit everything in viewport */
section[data-testid="stMain"] {
    overflow: hidden !important;
    max-height: 100vh !important;
}
[data-testid="stAppViewContainer"] {
    overflow: hidden !important;
}

/* ── Split column container ────────────────────────────────────── */
[data-testid="stHorizontalBlock"]:has(.login-brand-marker) {
    min-height: 100vh;
    gap: 0 !important;
    align-items: stretch !important;
}

/* ── Left column — logo as full background ─────────────────────── */
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(1) {
    background-size: cover;
    background-position: 55% center;
    background-repeat: no-repeat;
    overflow: hidden;
    border-radius: 0 2rem 2rem 0;
    margin: 1.5rem 0;
    min-height: 100vh;
}
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(1) > div {
    height: 100%;
}
/* Hide all content inside left column (only background matters) */
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(1) .stMarkdown {
    display: none !important;
}
.login-brand-subtitle {
    font-size: 0.7rem;
    font-weight: 700;
    color: rgba(255,255,255,0.75);
    text-transform: uppercase;
    letter-spacing: 0.3em;
    margin: 0 0 2.5rem;
    position: relative;
    z-index: 1;
}
.login-features {
    list-style: none;
    padding: 0;
    margin: 0;
    position: relative;
    z-index: 1;
}
.login-features li {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: rgba(255,255,255,0.9);
    font-weight: 500;
    font-size: 0.95rem;
    margin-bottom: 1.25rem;
}
.login-features .mdi {
    color: var(--login-green);
    font-size: 22px;
}

/* ── Right column — card styling ───────────────────────────────── */
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) {
    background: var(--login-bg);
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2)
  > div:first-child {
    background: var(--login-surface);
    border-radius: 1rem;
    padding: 2.5rem 2.5rem 2rem;
    box-shadow: var(--login-shadow);
    max-width: 420px;
    width: 100%;
    margin: 2rem;
}

/* ── Typography ────────────────────────────────────────────────── */
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) h2 {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    color: var(--login-text) !important;
    margin: 0 0 0.25rem !important;
    line-height: 1.2 !important;
}
.login-subtitle {
    font-size: 0.95rem;
    font-weight: 500;
    color: var(--login-text2);
    margin: 0 0 1.5rem;
}

/* ── Pill inputs ──────────────────────────────────────────────── */
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stTextInput"] label {
    font-size: 0.6875rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: var(--login-text2) !important;
    padding-left: 1rem !important;
}
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stTextInput"] input {
    background: var(--login-surface2) !important;
    border: none !important;
    border-radius: 9999px !important;
    padding: 0.85rem 1.5rem !important;
    font-size: 0.875rem !important;
    color: var(--login-text) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    transition: box-shadow 0.2s ease !important;
}
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stTextInput"] input:focus {
    box-shadow: 0 0 0 3px rgba(0,91,193,0.15) !important;
    outline: none !important;
}
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stTextInput"] input::placeholder {
    color: #9ca3af !important;
}

/* ── Checkbox ──────────────────────────────────────────────────── */
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stCheckbox"] label span {
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    color: var(--login-text2) !important;
}

/* ── Primary button (Sign In) — pill gradient ──────────────────── */
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, var(--login-accent) 0%, var(--login-accent-end) 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 9999px !important;
    padding: 0.85rem 2rem !important;
    min-height: 48px !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    box-shadow: 0 8px 24px rgba(0,91,193,0.25) !important;
    transition: opacity 0.2s, transform 0.1s !important;
    letter-spacing: 0.01em !important;
}
/* Keep button container height stable during Sign In transition */
.st-key-signin_btn {
    min-height: 48px !important;
}
.st-key-signin_btn .stButton {
    min-height: 48px !important;
}
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button[kind="primary"]:hover {
    opacity: 0.92 !important;
}
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button[kind="primary"]:active {
    transform: scale(0.98) !important;
}

/* ── Secondary button (Forgot password / Back) — text style ──── */
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button[kind="secondary"] {
    background: transparent !important;
    color: var(--login-accent) !important;
    border: none !important;
    border-radius: 9999px !important;
    font-weight: 700 !important;
    font-size: 0.8rem !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    box-shadow: none !important;
    transition: opacity 0.2s !important;
}
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button[kind="secondary"]:hover {
    background: rgba(0,91,193,0.06) !important;
}

/* ── Divider ───────────────────────────────────────────────────── */
.login-divider {
    width: 100%;
    height: 1px;
    background: var(--login-surface2);
    margin: 0;
}
/* ── Footer brand ──────────────────────────────────────────────── */
.login-footer-brand {
    text-align: center;
    font-size: 0.625rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: var(--login-text3);
    margin: 0;
}

/* ── Alert overrides ───────────────────────────────────────────── */
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stAlert"] {
    border-radius: 0.75rem !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.85rem !important;
}

/* ── Spinner ───────────────────────────────────────────────────── */
[data-testid="stHorizontalBlock"]:has(.login-brand-marker)
  > [data-testid="stColumn"]:nth-child(2) [data-testid="stSpinner"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* ── Responsive ───────────────────────────────────────────────── */
@media (max-width: 768px) {
    [data-testid="stHorizontalBlock"]:has(.login-brand-marker)
      > [data-testid="stColumn"]:nth-child(1) {
        display: none !important;
    }
    [data-testid="stHorizontalBlock"]:has(.login-brand-marker)
      > [data-testid="stColumn"]:nth-child(2)
      > div:first-child {
        margin: 1rem;
        padding: 2rem;
    }
}
</style>
"""

# ── Page entry ─────────────────────────────────────────────────────────────────
def render():
    # Inject login-specific CSS (self-contained — inject_css() is NOT called here)
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    # Split layout: 40% brand | 60% form
    col_brand, col_form = st.columns([2, 3], gap="small")

    with col_brand:
        # Tiny marker so CSS :has() selectors can find the login layout
        st.markdown('<div class="login-brand-marker"></div>', unsafe_allow_html=True)

        # Set background-image on the left column via JS
        import base64, os as _os
        import streamlit.components.v1 as _stc
        _logo_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "static", "logo.jpeg")
        try:
            with open(_logo_path, "rb") as _f:
                _logo_b64 = base64.b64encode(_f.read()).decode()
            _logo_src = f"data:image/jpeg;base64,{_logo_b64}"
        except Exception:
            _logo_src = "app/static/logo.jpeg"

        _stc.html(f"""<script>
        (function(){{
          var pd = window.parent.document;
          var marker = pd.querySelector('.login-brand-marker');
          if(!marker) return;
          var col = marker.closest('[data-testid="stColumn"]');
          if(!col) return;
          col.style.backgroundImage = 'url("{_logo_src}")';
          col.style.backgroundPosition = '0% center';
          col.style.backgroundSize = 'cover';
          col.style.backgroundRepeat = 'no-repeat';
        }})();
        </script>""", height=0)

    with col_form:
        view = st.session_state.get("login_view", "signin")
        if view == "forgot":
            _render_forgot_password()
        else:
            _render_signin()


# ── Sign-in view ───────────────────────────────────────────────────────────────
def _render_signin():
    remembered_id      = _get_cookie(_REMEMBER_ID_KEY)
    remembered_company = _get_cookie(_REMEMBER_COMPANY_KEY)

    # ── Heading ────────────────────────────────────────────────────
    st.markdown("<h2>Welcome back!</h2>", unsafe_allow_html=True)

    if remembered_company:
        subtitle = f'Signing in to <strong>{remembered_company}</strong>'
    else:
        subtitle = "Sign in to your account to continue."
    st.markdown(f'<p class="login-subtitle">{subtitle}</p>', unsafe_allow_html=True)

    # ── Form wrapper prevents widget reruns during login ─────────
    with st.form("signin_form"):
        identifier = st.text_input(
            "Employee ID or Email",
            value=remembered_id,
            placeholder="e.g. GX-12345",
        )
        _gap(4)
        password = st.text_input("Password", type="password", placeholder="••••••••")

        _gap(4)

        # ── Remember Me ────────────────────────────────────────────────
        remember_me = st.checkbox(
            "Remember me",
            value=bool(remembered_id),
            help="Saves your Employee ID/email and company for 30 days. Never saves your password.",
        )

        _gap(8)

        # ── Primary CTA ────────────────────────────────────────────────
        signin_clicked = st.form_submit_button("Sign In", type="primary", use_container_width=True)

    if signin_clicked:
        if not identifier.strip() or not password:
            st.error("Please fill in both fields.")
        else:
            # Show spinner on the button via JS
            import streamlit.components.v1 as _stc_login
            _stc_login.html("""<script>
            (function(){
              var pd = window.parent.document;
              var btn = pd.querySelector('[data-testid="stFormSubmitButton"] button');
              if(!btn) return;
              btn.disabled = true;
              btn.style.opacity = '0.7';
              btn.style.pointerEvents = 'none';
              var span = btn.querySelector('p') || btn.querySelector('span span') || btn;
              span.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" style="animation:gxp-spin 0.8s linear infinite;vertical-align:middle;margin-right:6px"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="30 70" stroke-linecap="round"/></svg> Signing in';
              if(!pd.getElementById('gxp-spin-css')){
                var s=pd.createElement('style');s.id='gxp-spin-css';
                s.textContent='@keyframes gxp-spin{to{transform:rotate(360deg)}}';
                pd.head.appendChild(s);
              }
            })();
            </script>""", height=0)

            success, error = login(identifier.strip(), password)
            if success:
                if remember_me:
                    _set_cookie(_REMEMBER_ID_KEY, identifier.strip())
                    company_name = st.session_state.get("company_name", "")
                    if company_name:
                        _set_cookie(_REMEMBER_COMPANY_KEY, company_name)
                else:
                    _delete_cookie(_REMEMBER_ID_KEY)
                    _delete_cookie(_REMEMBER_COMPANY_KEY)
                st.rerun()
            else:
                st.error(error)

    _gap(4)

    # ── Forgot password link ───────────────────────────────────────
    if st.button("Forgot your password?", key="goto_forgot", use_container_width=True):
        st.session_state.login_view = "forgot"
        st.rerun()

    _gap(4)


# ── Forgot-password view ──────────────────────────────────────────────────────
def _render_forgot_password():
    st.markdown("<h2>Reset password</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p class="login-subtitle">Enter your email and we\'ll send a reset link.</p>',
        unsafe_allow_html=True,
    )

    email = st.text_input("Email address", placeholder="you@company.com")
    _gap(8)

    if st.button("Send Reset Link", type="primary", use_container_width=True):
        if not email.strip():
            st.error("Please enter your email address.")
        else:
            with st.spinner("Sending reset link…"):
                ok, err = send_password_reset(email.strip())
            if ok:
                st.success(
                    f"Reset link sent to **{email.strip()}**. "
                    "Check your inbox, then come back to sign in."
                )
            else:
                st.error(err)

    _gap(8)

    if st.button("← Back to Sign In", key="back_to_signin", use_container_width=True):
        st.session_state.login_view = "signin"
        st.rerun()

    _gap(16)

    st.markdown('<div class="login-divider"></div>', unsafe_allow_html=True)
    _gap(16)
    st.markdown('<p class="login-footer-brand">GenXcript</p>', unsafe_allow_html=True)
