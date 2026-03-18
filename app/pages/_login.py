"""
Login Page — Streamlit page.

Email + password login via Supabase Auth.
Includes Forgot Password flow and Remember Me (browser cookie).

Cookie keys
-----------
gxp_remember_id      : last-used employee ID / email
gxp_remember_company : last-used company name (display only)

Spacing system: 8pt grid — 4 · 8 · 16 · 24 · 32 · 48px
"""

import datetime
import streamlit as st
import extra_streamlit_components as stx
from app.auth import login, send_password_reset


# ── Cookie helper ──────────────────────────────────────────────────────────────
# CookieManager renders a hidden Streamlit component — instantiating it at
# module level causes "cannot import name 'render'" because the widget call
# fails before def render() is reached.  Lazy-init inside _cm() so it only
# runs when a render function is actually executing inside Streamlit.

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


# ── Tiny spacer ────────────────────────────────────────────────────────────────
def _gap(px: int) -> None:
    st.markdown(f"<div style='height:{px}px'></div>", unsafe_allow_html=True)


# ── Page entry ─────────────────────────────────────────────────────────────────
def render():
    # ── Card styling — targets the middle column's inner wrapper ─────
    # Uses the nth-child(2) column selector so it only affects the center
    # column of the login layout and nothing else on any other page.
    st.markdown(
        """
        <style>
        /* Scope to the login columns only — nth-child(2) = center column */
        [data-testid="stHorizontalBlock"]
          > [data-testid="stColumn"]:nth-child(2)
          > div:first-child {
            background  : #ffffff;
            border-radius : 16px;
            box-shadow  : 0 1px 3px rgba(0,0,0,0.06),
                          0 4px 12px rgba(0,0,0,0.08),
                          0 16px 40px rgba(0,0,0,0.07);
            padding     : 8px 20px 20px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _gap(64)
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        view = st.session_state.get("login_view", "signin")
        if view == "forgot":
            _render_forgot_password()
        else:
            _render_signin()


# ── Sign-in view ───────────────────────────────────────────────────────────────
def _render_signin():
    # Pull remembered values from cookie
    remembered_id      = _get_cookie(_REMEMBER_ID_KEY)
    remembered_company = _get_cookie(_REMEMBER_COMPANY_KEY)

    # ── Heading — centered ───────────────────────────────────────────
    st.markdown(
        "<h2 style='margin:0; font-size:26px; font-weight:700;"
        "line-height:1.2; text-align:center;'>"
        "Welcome back!"
        "</h2>",
        unsafe_allow_html=True,
    )
    _gap(4)

    # Show last-used company if remembered; otherwise generic subtitle
    if remembered_company:
        subtitle = f"Signing in to <strong>{remembered_company}</strong>"
    else:
        subtitle = "Sign in to your account to continue."

    st.markdown(
        f"<p style='margin:0; font-size:14px; color:#888; text-align:center;'>"
        f"{subtitle}"
        f"</p>",
        unsafe_allow_html=True,
    )

    _gap(32)

    # ── Inputs (outside form so Remember Me checkbox can interact) ───
    identifier = st.text_input(
        "Employee ID or Email",
        value=remembered_id,
        placeholder="EMP-001  or  you@company.com",
    )
    _gap(8)
    password = st.text_input("Password", type="password")

    _gap(8)

    # ── Remember Me ──────────────────────────────────────────────────
    # Stored in browser cookie — persists 30 days across browser sessions.
    # Saves: employee ID/email + company name (never the password).
    remember_me = st.checkbox(
        "Remember me",
        value=bool(remembered_id),
        help="Saves your Employee ID/email and company for 30 days on this device. Never saves your password.",
    )

    _gap(16)

    # ── Primary CTA ──────────────────────────────────────────────────
    if st.button("Sign In", type="primary", use_container_width=True):
        if not identifier.strip() or not password:
            st.error("Please fill in both fields.")
        else:
            with st.spinner("Signing in…"):
                success, error = login(identifier.strip(), password)
            if success:
                if remember_me:
                    _set_cookie(_REMEMBER_ID_KEY, identifier.strip())
                    # Company name is now in session — save it too
                    company_name = st.session_state.get("company_name", "")
                    if company_name:
                        _set_cookie(_REMEMBER_COMPANY_KEY, company_name)
                else:
                    _delete_cookie(_REMEMBER_ID_KEY)
                    _delete_cookie(_REMEMBER_COMPANY_KEY)
                st.rerun()
            else:
                st.error(error)

    _gap(8)

    # ── Secondary action ─────────────────────────────────────────────
    if st.button("Forgot your password?", key="goto_forgot", use_container_width=True):
        st.session_state.login_view = "forgot"
        st.rerun()

    _gap(32)

    # ── Footer ───────────────────────────────────────────────────────
    st.markdown(
        "<hr style='border:none; border-top:1px solid #e5e5e5; margin:0 0 16px;'>",
        unsafe_allow_html=True,
    )
    # CTA — above the legal copy so it gets seen first
    st.markdown(
        "<p style='text-align:center; font-size:12px; color:#555; margin:0 0 4px;'>"
        "Ready to automate your HR process?"
        "</p>"
        "<p style='text-align:center; font-size:12px; margin:0 0 12px;'>"
        "<a href='https://www.facebook.com/GenNexaSmartHome' target='_blank' "
        "style='color:#1877f2; font-weight:600; text-decoration:none;'>"
        "Contact us now!"
        "</a>"
        "</p>",
        unsafe_allow_html=True,
    )
    # Terms & Privacy
    st.markdown(
        "<p style='text-align:center; font-size:11px; color:#aaa; margin:0 0 8px; line-height:1.6;'>"
        "<a href='#' style='color:inherit; text-decoration:none;'>Terms &amp; Conditions</a>"
        "&nbsp;&nbsp;·&nbsp;&nbsp;"
        "<a href='#' style='color:inherit; text-decoration:none;'>Data Privacy</a>"
        "</p>",
        unsafe_allow_html=True,
    )
    # Brand — smallest, least prominent — sits below legal copy
    st.markdown(
        "<p style='text-align:center; font-size:10px; font-weight:600;"
        "letter-spacing:1.5px; text-transform:uppercase; color:#ccc; margin:0;'>"
        "GenXcript Payroll System"
        "</p>",
        unsafe_allow_html=True,
    )

    _gap(32)


# ── Forgot-password view ───────────────────────────────────────────────────────
def _render_forgot_password():
    st.markdown(
        "<h2 style='margin:0; font-size:26px; font-weight:700;"
        "line-height:1.2; text-align:center;'>"
        "Reset password"
        "</h2>",
        unsafe_allow_html=True,
    )
    _gap(4)
    st.markdown(
        "<p style='margin:0; font-size:14px; color:#888; text-align:center;'>"
        "Enter your email and we'll send a reset link."
        "</p>",
        unsafe_allow_html=True,
    )

    _gap(32)

    email = st.text_input("Email address", placeholder="you@company.com")
    _gap(16)

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

    _gap(16)

    if st.button("← Back to Sign In", key="back_to_signin", use_container_width=True):
        st.session_state.login_view = "signin"
        st.rerun()

    _gap(32)

    st.markdown(
        "<hr style='border:none; border-top:1px solid #e5e5e5; margin:0 0 12px;'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; font-size:11px; color:#aaa; margin:0 0 8px;'>"
        "<a href='#' style='color:inherit; text-decoration:none;'>Terms &amp; Conditions</a>"
        "&nbsp;&nbsp;·&nbsp;&nbsp;"
        "<a href='#' style='color:inherit; text-decoration:none;'>Data Privacy</a>"
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; font-size:10px; font-weight:600;"
        "letter-spacing:1.5px; text-transform:uppercase; color:#ccc; margin:0;'>"
        "GenXcript Payroll System"
        "</p>",
        unsafe_allow_html=True,
    )

    _gap(32)
