"""
Registration Page — Streamlit page.

Self-signup for new companies.
Creates a Supabase Auth user + company record + user_company_access link.
"""

import streamlit as st
from app.auth import signup


REGIONS = [
    "NCR", "CAR", "Region I", "Region II", "Region III",
    "Region IV-A", "Region IV-B", "Region V", "Region VI",
    "Region VII", "Region VIII", "Region IX", "Region X",
    "Region XI", "Region XII", "Region XIII", "BARMM",
]

PAY_FREQUENCIES = ["semi-monthly", "monthly", "weekly"]


def render():
    # Centered layout
    _, col, _ = st.columns([1, 1.5, 1])

    with col:
        st.markdown("## GeNXcript Payroll")
        st.markdown("#### Create Your Company Account")
        st.caption("Set up your payroll system in seconds.")
        st.divider()

        with st.form("register_form"):
            st.markdown("**Company Details**")
            company_name = st.text_input("Company Name *", placeholder="ABC Trading Corp.")

            col1, col2 = st.columns(2)
            with col1:
                region = st.selectbox("Region *", options=REGIONS, help="Affects minimum wage rates")
            with col2:
                pay_frequency = st.selectbox("Pay Frequency *", options=PAY_FREQUENCIES)

            st.markdown("**Account Details**")
            email = st.text_input("Email Address *", placeholder="you@company.com")
            password = st.text_input("Password *", type="password", help="At least 6 characters")
            confirm = st.text_input("Confirm Password *", type="password")

            submitted = st.form_submit_button("Create Account", type="primary", width="stretch")

        if submitted:
            # Validation
            error = None
            if not company_name.strip():
                error = "Company name is required."
            elif not email.strip():
                error = "Email address is required."
            elif not password:
                error = "Password is required."
            elif len(password) < 6:
                error = "Password must be at least 6 characters."
            elif password != confirm:
                error = "Passwords do not match."

            if error:
                st.error(error)
            else:
                with st.spinner("Creating your account..."):
                    success, result = signup(
                        email=email.strip(),
                        password=password,
                        company_name=company_name,
                        region=region,
                        pay_frequency=pay_frequency,
                    )

                if not success:
                    st.error(result)
                elif result == "CHECK_EMAIL":
                    st.success("Account created! Check your email to confirm your address, then come back to sign in.")
                    st.session_state.show_register = False
                else:
                    # Auto-logged in (email confirmation disabled)
                    st.rerun()

        st.divider()
        st.caption("Already have an account?")
        if st.button("Back to Sign In", width="stretch"):
            st.session_state.show_register = False
            st.rerun()
