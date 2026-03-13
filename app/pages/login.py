"""
Login Page — Streamlit page.

Email + password login via Supabase Auth.
Links to the registration page for new companies.
"""

import streamlit as st
from app.auth import login


def render():
    # Centered layout
    _, col, _ = st.columns([1, 1.5, 1])

    with col:
        st.markdown("## GenXcript Payroll")
        st.markdown("#### Sign In")
        st.caption("Philippine SME Payroll System")
        st.divider()

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@company.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", type="primary", width="stretch")

        if submitted:
            if not email.strip() or not password:
                st.error("Please enter your email and password.")
            else:
                with st.spinner("Signing in..."):
                    success, error = login(email.strip(), password)

                if success:
                    st.rerun()
                else:
                    st.error(error)

        st.divider()
        st.caption("New company? Create an account:")
        if st.button("Register your company", width="stretch"):
            st.session_state.show_register = True
            st.rerun()
