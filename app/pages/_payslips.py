"""
Payslips — Streamlit page.

Features:
- Select a finalized pay period
- Preview payslip breakdown per employee
- Download individual payslip as PDF
- Download all payslips as a single combined PDF
"""

import streamlit as st
from app.db_helper import get_db, get_company_id
from app.styles import inject_css
from reports.payslip_pdf import generate_payslip_pdf, generate_all_payslips_pdf


# ============================================================
# Helpers
# ============================================================

def _fmt(centavos: int) -> str:
    return f"₱{centavos / 100:,.2f}"


# ============================================================
# Database operations
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def _load_company(_cid: str = "") -> dict:
    db = get_db()
    result = db.table("companies").select("*").eq("id", _cid or get_company_id()).execute()
    return result.data[0] if result.data else {}


@st.cache_data(ttl=120, show_spinner=False)
def _load_pay_periods(_cid: str = "") -> list[dict]:
    """Load finalized/paid pay periods. Cached 2 min."""
    db = get_db()
    result = (
        db.table("pay_periods")
        .select("*")
        .eq("company_id", _cid or get_company_id())
        .in_("status", ["finalized", "paid"])
        .order("period_start", desc=True)
        .execute()
    )
    return result.data


@st.cache_data(ttl=120, show_spinner=False)
def _load_all_pay_periods(_cid: str = "") -> list[dict]:
    """Load all pay periods. Cached 2 min."""
    db = get_db()
    result = (
        db.table("pay_periods")
        .select("*")
        .eq("company_id", _cid or get_company_id())
        .order("period_start", desc=True)
        .execute()
    )
    return result.data


@st.cache_data(ttl=300, show_spinner=False)
def _load_employees(_cid: str = "") -> list[dict]:
    db = get_db()
    result = (
        db.table("employees")
        .select("*")
        .eq("company_id", _cid or get_company_id())
        .order("last_name")
        .execute()
    )
    return result.data


@st.cache_data(ttl=120, show_spinner=False)
def _load_payroll_entries(pay_period_id: str) -> dict:
    db = get_db()
    result = (
        db.table("payroll_entries")
        .select("*")
        .eq("pay_period_id", pay_period_id)
        .execute()
    )
    return {row["employee_id"]: row for row in result.data}


# ============================================================
# Main Page Render
# ============================================================

def render():
    inject_css()
    st.title("Payslips")

    # Load pay periods (show all, but note which are finalized)
    all_periods = _load_all_pay_periods(_cid=get_company_id())

    if not all_periods:
        st.info("No pay periods found. Create one in Payroll Run first.")
        return

    # Period selector
    period_labels = {
        p["id"]: f"{p['period_start']} to {p['period_end']}  [{p['status'].upper()}]"
        for p in all_periods
    }
    selected_id = st.selectbox(
        "Select Pay Period",
        options=[p["id"] for p in all_periods],
        format_func=lambda x: period_labels[x],
    )
    period = next(p for p in all_periods if p["id"] == selected_id)

    if period["status"] == "draft":
        st.warning("This pay period is still a draft. Finalize it in Payroll Run before generating payslips.")
        return

    # Load data
    company = _load_company(_cid=get_company_id())
    all_employees = _load_employees(_cid=get_company_id())
    entries = _load_payroll_entries(period["id"])

    # Filter to employees with computed entries
    employees = [e for e in all_employees if e["id"] in entries]

    if not employees:
        st.warning("No computed payroll entries for this period.")
        return

    st.divider()

    # --- Generate All Payslips button ---
    col_info, col_gen = st.columns([3, 1])
    with col_info:
        st.markdown(f"**Period:** {period['period_start']} to {period['period_end']}  |  **{len(employees)} payslips**")
    with col_gen:
        all_pdf = generate_all_payslips_pdf(company, employees, period, entries)
        st.download_button(
            label="Generate All Payslips (PDF)",
            data=all_pdf,
            file_name=f"payslips_{period['period_start']}_to_{period['period_end']}.pdf",
            mime="application/pdf",
            type="primary",
            width="stretch",
        )

    st.divider()

    # --- Individual payslips ---
    for emp in employees:
        entry = entries[emp["id"]]
        name = f"{emp['first_name']} {emp['last_name']}"

        with st.expander(f"{emp['employee_no']} — {name}  |  Net Pay: {_fmt(entry['net_pay'])}"):
            # Quick summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Gross Pay", _fmt(entry["gross_pay"]))
            with col2:
                st.metric("Total Deductions", _fmt(entry["total_deductions"]))
            with col3:
                st.metric("Net Pay", _fmt(entry["net_pay"]))

            # Detailed breakdown
            col_earn, col_ded = st.columns(2)

            with col_earn:
                st.markdown("**Earnings**")
                st.text(f"Basic Pay:           {_fmt(entry['basic_pay'])}")
                if entry["overtime_pay"]:
                    st.text(f"Overtime:            {_fmt(entry['overtime_pay'])}")
                if entry["holiday_pay"]:
                    st.text(f"Holiday Pay:         {_fmt(entry['holiday_pay'])}")
                if entry["night_differential"]:
                    st.text(f"Night Differential:  {_fmt(entry['night_differential'])}")
                if entry["allowances_nontaxable"]:
                    st.text(f"Allowances (NT):     {_fmt(entry['allowances_nontaxable'])}")
                if entry["allowances_taxable"]:
                    st.text(f"Allowances (Tax):    {_fmt(entry['allowances_taxable'])}")
                if entry["commission"]:
                    st.text(f"Commission:          {_fmt(entry['commission'])}")
                if entry["thirteenth_month_accrual"]:
                    st.text(f"13th Month Accrual:  {_fmt(entry['thirteenth_month_accrual'])}")

            with col_ded:
                st.markdown("**Deductions**")
                st.text(f"SSS:                 {_fmt(entry['sss_employee'])}")
                st.text(f"PhilHealth:          {_fmt(entry['philhealth_employee'])}")
                st.text(f"Pag-IBIG:            {_fmt(entry['pagibig_employee'])}")
                st.text(f"Withholding Tax:     {_fmt(entry['withholding_tax'])}")
                if entry["sss_loan"]:
                    st.text(f"SSS Loan:            {_fmt(entry['sss_loan'])}")
                if entry["pagibig_loan"]:
                    st.text(f"Pag-IBIG Loan:       {_fmt(entry['pagibig_loan'])}")
                if entry["cash_advance"]:
                    st.text(f"Cash Advance:        {_fmt(entry['cash_advance'])}")
                if entry["other_deductions"]:
                    st.text(f"Other:               {_fmt(entry['other_deductions'])}")

            # Individual payslip download
            pdf_bytes = generate_payslip_pdf(company, emp, period, entry)
            st.download_button(
                label=f"Generate Payslip — {name}",
                data=pdf_bytes,
                file_name=f"payslip_{emp['employee_no']}_{period['period_start']}.pdf",
                mime="application/pdf",
                key=f"dl_{emp['id']}",
            )
