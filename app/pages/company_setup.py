"""
Company Setup — Streamlit page.

One-time onboarding and settings:
- Company name, address, region
- BIR TIN, SSS/PhilHealth/Pag-IBIG employer numbers
- Pay frequency
"""

import streamlit as st
from app.db_helper import get_db, get_company_id


# ============================================================
# Constants
# ============================================================

PAY_FREQUENCIES = ["semi-monthly", "monthly", "weekly"]

REGIONS = [
    "NCR", "CAR", "Region I", "Region II", "Region III",
    "Region IV-A", "Region IV-B", "Region V", "Region VI",
    "Region VII", "Region VIII", "Region IX", "Region X",
    "Region XI", "Region XII", "Region XIII", "BARMM",
]


# ============================================================
# Database operations
# ============================================================

def _load_company() -> dict:
    db = get_db()
    result = db.table("companies").select("*").eq("id", get_company_id()).execute()
    return result.data[0] if result.data else {}


def _update_company(data: dict) -> dict:
    db = get_db()
    result = db.table("companies").update(data).eq("id", get_company_id()).execute()
    return result.data[0]


# ============================================================
# Main Page Render
# ============================================================

def render():
    st.title("Company Setup")
    st.caption("Configure your company details. These appear on payslips and government reports.")

    # Show confirmation after save
    if st.session_state.pop("company_saved", False):
        st.success("Company settings saved successfully.")

    company = _load_company()

    if not company:
        st.error("No company found. Please contact your administrator.")
        return

    with st.form("company_setup_form"):

        # --- Company Information ---
        st.subheader("Company Information")
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Company Name *", value=company.get("name", ""))
        with col2:
            region_index = REGIONS.index(company.get("region", "NCR")) if company.get("region", "NCR") in REGIONS else 0
            region = st.selectbox(
                "Region *",
                options=REGIONS,
                index=region_index,
                help="Affects minimum wage computation",
            )

        address = st.text_area("Company Address", value=company.get("address", "") or "", height=80)

        freq_index = PAY_FREQUENCIES.index(company.get("pay_frequency", "semi-monthly"))
        pay_frequency = st.selectbox(
            "Pay Frequency",
            options=PAY_FREQUENCIES,
            index=freq_index,
            help="How often employees are paid",
        )

        # --- Government Registration Numbers ---
        st.subheader("Government Registration Numbers")
        st.caption("These are used in government remittance reports.")

        col1, col2 = st.columns(2)
        with col1:
            bir_tin = st.text_input("BIR TIN", value=company.get("bir_tin", "") or "")
            sss_no = st.text_input("SSS Employer No.", value=company.get("sss_employer_no", "") or "")
        with col2:
            philhealth_no = st.text_input("PhilHealth Employer No.", value=company.get("philhealth_employer_no", "") or "")
            pagibig_no = st.text_input("Pag-IBIG Employer No.", value=company.get("pagibig_employer_no", "") or "")

        # --- Submit ---
        submitted = st.form_submit_button("Save Company Settings", type="primary", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("Company name is required.")
            else:
                try:
                    _update_company({
                        "name": name.strip(),
                        "address": address.strip(),
                        "region": region,
                        "pay_frequency": pay_frequency,
                        "bir_tin": bir_tin.strip(),
                        "sss_employer_no": sss_no.strip(),
                        "philhealth_employer_no": philhealth_no.strip(),
                        "pagibig_employer_no": pagibig_no.strip(),
                    })
                    st.session_state.company_saved = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")
