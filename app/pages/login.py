"""
Login Page — Streamlit page.

Email + password login via Supabase Auth.
Links to the registration page for new companies.
Includes Forgot Password flow for employees and admins.
"""

import streamlit as st
from app.auth import login, send_password_reset


def render():
    # Centered layout
    _, col, _ = st.columns([1, 1.5, 1])

    with col:
        st.markdown("## GenXcript Payroll")

        # Toggle between Sign In and Forgot Password views
        view = st.session_state.get("login_view", "signin")

        if view == "forgot":
            _render_forgot_password(col)
        else:
            _render_signin(col)


def _render_signin(col):
    st.markdown("#### Sign In")
    st.caption("Philippine SME Payroll System")
    st.divider()
    st.info(
        "**First time here?** Check your email for a temporary password from your employer. "
        "Sign in with your **Employee ID** (e.g. EMP-001) or your email address. "
        "After logging in, use **Forgot Password** to set your own password.",
        icon="ℹ️",
    )

    with st.form("login_form"):
        identifier = st.text_input(
            "Employee ID or Email",
            placeholder="EMP-001  or  you@company.com",
        )
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In", type="primary", width="stretch")

    if submitted:
        if not identifier.strip() or not password:
            st.error("Please enter your Employee ID (or email) and password.")
        else:
            with st.spinner("Signing in..."):
                success, error = login(identifier.strip(), password)

            if success:
                st.rerun()
            else:
                st.error(error)

    # Forgot password link (below form, before divider)
    fp_col, _ = st.columns([1, 1])
    with fp_col:
        if st.button("Forgot Password?", key="goto_forgot", use_container_width=True):
            st.session_state.login_view = "forgot"
            st.rerun()

    st.divider()
    st.caption("New company? Create an account:")
    if st.button("Register your company", width="stretch"):
        st.session_state.show_register = True
        st.rerun()


def _render_forgot_password(col):
    st.markdown("#### Reset Password")
    st.caption("Enter your email and we'll send a reset link.")
    st.divider()

    with st.form("forgot_form"):
        email = st.text_input("Email", placeholder="you@company.com")
        submitted = st.form_submit_button("Send Reset Link", type="primary", width="stretch")

    if submitted:
        if not email.strip():
            st.error("Please enter your email address.")
        else:
            with st.spinner("Sending reset link..."):
                ok, err = send_password_reset(email.strip())
            if ok:
                st.success(
                    f"Password reset email sent to **{email.strip()}**. "
                    "Check your inbox and click the link to set a new password, then come back to sign in."
                )
            else:
                st.error(err)

    st.divider()
    if st.button("← Back to Sign In", key="back_to_signin", width="stretch"):
        st.session_state.login_view = "signin"
        st.rerun()
