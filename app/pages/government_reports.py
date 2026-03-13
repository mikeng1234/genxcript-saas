"""
Government Reports — Streamlit page.

Generate and download mandatory government remittance reports:
- SSS R3 / R5 — Monthly Collection List
- PhilHealth RF-1 — Monthly Remittance Report
- Pag-IBIG MCRF — Monthly Collection Remittance Form
- BIR 1601-C — Monthly Withholding Tax Remittance

Only shows finalized/paid pay periods (draft periods have incomplete data).
"""

import streamlit as st
from app.db_helper import get_db, get_company_id
from reports.government_reports_pdf import (
    generate_sss_r3,
    generate_philhealth_rf1,
    generate_pagibig_mcrf,
    generate_bir_1601c,
)


# ============================================================
# Helpers
# ============================================================

def _fmt(centavos: int) -> str:
    return f"₱{centavos / 100:,.2f}"


# ============================================================
# Database Operations
# ============================================================

def _load_company() -> dict:
    db = get_db()
    result = db.table("companies").select("*").eq("id", get_company_id()).execute()
    return result.data[0] if result.data else {}


def _load_pay_periods() -> list[dict]:
    """Load finalized/paid pay periods (reports only make sense for these)."""
    db = get_db()
    result = (
        db.table("pay_periods")
        .select("*")
        .eq("company_id", get_company_id())
        .in_("status", ["finalized", "paid"])
        .order("period_start", desc=True)
        .execute()
    )
    return result.data


def _load_employees() -> list[dict]:
    """Load all employees (including inactive — they may have entries for the period)."""
    db = get_db()
    result = (
        db.table("employees")
        .select("*")
        .eq("company_id", get_company_id())
        .order("last_name")
        .execute()
    )
    return result.data


def _load_payroll_entries(pay_period_id: str) -> dict:
    """Load payroll entries for a period, keyed by employee_id."""
    db = get_db()
    result = (
        db.table("payroll_entries")
        .select("*")
        .eq("pay_period_id", pay_period_id)
        .execute()
    )
    return {row["employee_id"]: row for row in result.data}


# ============================================================
# Report Definitions
# ============================================================

REPORTS = {
    "sss": {
        "title": "SSS R3 / R5",
        "subtitle": "Monthly Collection List",
        "icon": "🏛️",
        "description": "Employee/employer SSS contributions with Monthly Salary Credit breakdown.",
        "generator": generate_sss_r3,
        "filename_prefix": "SSS_R3",
    },
    "philhealth": {
        "title": "PhilHealth RF-1",
        "subtitle": "Monthly Remittance Report",
        "icon": "🏥",
        "description": "Employee/employer PhilHealth premium contributions.",
        "generator": generate_philhealth_rf1,
        "filename_prefix": "PhilHealth_RF1",
    },
    "pagibig": {
        "title": "Pag-IBIG MCRF",
        "subtitle": "Monthly Collection Remittance Form",
        "icon": "🏠",
        "description": "Employee/employer Pag-IBIG Fund contributions.",
        "generator": generate_pagibig_mcrf,
        "filename_prefix": "PagIBIG_MCRF",
    },
    "bir": {
        "title": "BIR 1601-C",
        "subtitle": "Monthly Withholding Tax Remittance",
        "icon": "📋",
        "description": "Withholding tax on compensation — gross, non-taxable, taxable income, and tax withheld.",
        "generator": generate_bir_1601c,
        "filename_prefix": "BIR_1601C",
    },
}


# ============================================================
# Preview Tables (on-screen summary before download)
# ============================================================

def _preview_sss(employees, entries):
    """Show SSS contribution preview table."""
    rows = []
    total_ee, total_er = 0, 0
    for emp in employees:
        entry = entries.get(emp["id"])
        if not entry:
            continue
        ee = entry["sss_employee"]
        er = entry["sss_employer"]
        total_ee += ee
        total_er += er
        rows.append({
            "Employee": f"{emp['last_name']}, {emp['first_name']}",
            "SSS No.": emp.get("sss_no", "") or "—",
            "EE Share": _fmt(ee),
            "ER Share": _fmt(er),
            "Total": _fmt(ee + er),
        })

    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Employee Total", _fmt(total_ee))
        with col2:
            st.metric("Employer Total", _fmt(total_er))
        with col3:
            st.metric("Grand Total", _fmt(total_ee + total_er))


def _preview_philhealth(employees, entries):
    """Show PhilHealth contribution preview table."""
    rows = []
    total_ee, total_er = 0, 0
    for emp in employees:
        entry = entries.get(emp["id"])
        if not entry:
            continue
        ee = entry["philhealth_employee"]
        er = entry["philhealth_employer"]
        total_ee += ee
        total_er += er
        rows.append({
            "Employee": f"{emp['last_name']}, {emp['first_name']}",
            "PhilHealth No.": emp.get("philhealth_no", "") or "—",
            "EE Share": _fmt(ee),
            "ER Share": _fmt(er),
            "Total Premium": _fmt(ee + er),
        })

    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Employee Total", _fmt(total_ee))
        with col2:
            st.metric("Employer Total", _fmt(total_er))
        with col3:
            st.metric("Grand Total", _fmt(total_ee + total_er))


def _preview_pagibig(employees, entries):
    """Show Pag-IBIG contribution preview table."""
    rows = []
    total_ee, total_er = 0, 0
    for emp in employees:
        entry = entries.get(emp["id"])
        if not entry:
            continue
        ee = entry["pagibig_employee"]
        er = entry["pagibig_employer"]
        total_ee += ee
        total_er += er
        rows.append({
            "Employee": f"{emp['last_name']}, {emp['first_name']}",
            "Pag-IBIG MID": emp.get("pagibig_no", "") or "—",
            "EE Share": _fmt(ee),
            "ER Share": _fmt(er),
            "Total": _fmt(ee + er),
        })

    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Employee Total", _fmt(total_ee))
        with col2:
            st.metric("Employer Total", _fmt(total_er))
        with col3:
            st.metric("Grand Total", _fmt(total_ee + total_er))


def _preview_bir(employees, entries):
    """Show BIR withholding tax preview table."""
    rows = []
    total_gross, total_nontax, total_mandatory, total_taxable, total_wht = 0, 0, 0, 0, 0
    for emp in employees:
        entry = entries.get(emp["id"])
        if not entry:
            continue
        gross = entry["gross_pay"]
        nontax = entry["allowances_nontaxable"]
        mandatory = entry["sss_employee"] + entry["philhealth_employee"] + entry["pagibig_employee"]
        taxable = gross - nontax - mandatory
        wht = entry["withholding_tax"]
        total_gross += gross
        total_nontax += nontax
        total_mandatory += mandatory
        total_taxable += taxable
        total_wht += wht
        rows.append({
            "Employee": f"{emp['last_name']}, {emp['first_name']}",
            "TIN": emp.get("bir_tin", "") or "—",
            "Gross": _fmt(gross),
            "Non-Taxable": _fmt(nontax),
            "Mandatory Ded.": _fmt(mandatory),
            "Taxable Income": _fmt(taxable),
            "Tax Withheld": _fmt(wht),
        })

    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Gross", _fmt(total_gross))
        with col2:
            st.metric("Total Taxable", _fmt(total_taxable))
        with col3:
            st.metric("Total Tax Withheld", _fmt(total_wht))
        with col4:
            st.metric("Employees", str(len(rows)))


PREVIEW_FUNCS = {
    "sss": _preview_sss,
    "philhealth": _preview_philhealth,
    "pagibig": _preview_pagibig,
    "bir": _preview_bir,
}


# ============================================================
# Main Page Render
# ============================================================

def render():
    st.title("Government Reports")

    # Load finalized pay periods
    periods = _load_pay_periods()

    if not periods:
        st.info("No finalized pay periods yet. Finalize a payroll run first to generate reports.")
        return

    # ---- Controls: Period selector + Report type ----
    col_period, col_report = st.columns([3, 2])

    with col_period:
        period_labels = {
            p["id"]: f"{p['period_start']} to {p['period_end']}  [{p['status'].upper()}]"
            for p in periods
        }
        selected_id = st.selectbox(
            "Select Pay Period",
            options=[p["id"] for p in periods],
            format_func=lambda x: period_labels[x],
        )
        period = next(p for p in periods if p["id"] == selected_id)

    with col_report:
        report_options = {k: f"{v['icon']} {v['title']} — {v['subtitle']}" for k, v in REPORTS.items()}
        selected_report = st.selectbox(
            "Select Report",
            options=list(report_options.keys()),
            format_func=lambda x: report_options[x],
        )

    report_info = REPORTS[selected_report]
    period_label = f"{period['period_start']} to {period['period_end']}"

    st.divider()

    # ---- Load data ----
    company = _load_company()
    all_employees = _load_employees()
    entries = _load_payroll_entries(period["id"])

    # Filter to employees that have entries for this period
    employees = [e for e in all_employees if e["id"] in entries]

    if not employees:
        st.warning("No payroll entries found for this period. Compute payroll first.")
        return

    # ---- Report Header ----
    st.subheader(f"{report_info['icon']} {report_info['title']}")
    st.caption(f"{report_info['description']}")
    st.markdown(f"**Period:** {period_label}  |  **Employees:** {len(employees)}")

    # ---- Preview Table ----
    preview_func = PREVIEW_FUNCS[selected_report]
    preview_func(employees, entries)

    st.divider()

    # ---- Download PDF ----
    pdf_bytes = report_info["generator"](company, employees, entries, period_label)
    filename = f"{report_info['filename_prefix']}_{period['period_start']}_to_{period['period_end']}.pdf"

    st.download_button(
        label=f"Download {report_info['title']} (PDF)",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        type="primary",
        width="stretch",
    )
