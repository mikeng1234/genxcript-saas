"""
Government Reports — Streamlit page.

Generate and download mandatory government remittance reports:
- SSS R3 / R5 — Monthly Collection List
- PhilHealth RF-1 — Monthly Remittance Report
- Pag-IBIG MCRF — Monthly Collection Remittance Form
- BIR 1601-C — Monthly Withholding Tax Remittance
- BIR 2316  — Annual Certificate per Employee
- BIR 1604-C — Annual Return + Alphalist

Only shows finalized/paid pay periods (draft periods have incomplete data).
"""

import streamlit as st
from datetime import date as _date
from app.db_helper import get_db, get_company_id
from app.styles import inject_css
from reports.government_reports_pdf import (
    generate_sss_r3,
    generate_philhealth_rf1,
    generate_pagibig_mcrf,
    generate_bir_1601c,
)
from reports.bir2316_pdf import generate_bir2316_pdf
from reports.bir1604c_pdf import generate_bir1604c_pdf, generate_bir1604c_alphalist


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


_ANNUAL_FIELDS = [
    "gross_pay", "basic_pay", "overtime_pay", "holiday_pay", "night_differential",
    "allowances_nontaxable", "allowances_taxable", "commission",
    "thirteenth_month_accrual",
    "sss_employee", "philhealth_employee", "pagibig_employee", "withholding_tax",
]


def _load_monthly_taxes(year: int) -> dict:
    """Return {month_number 1-12: total_withholding_centavos} for all
    finalized/paid pay periods whose period_start falls in `year`."""
    db = get_db()
    period_result = (
        db.table("pay_periods")
        .select("id, period_start")
        .eq("company_id", get_company_id())
        .in_("status", ["finalized", "paid"])
        .gte("period_start", f"{year}-01-01")
        .lte("period_start", f"{year}-12-31")
        .execute()
    )
    if not period_result.data:
        return {}

    period_months = {
        row["id"]: int(row["period_start"][5:7])
        for row in period_result.data
    }

    entry_result = (
        db.table("payroll_entries")
        .select("pay_period_id, withholding_tax")
        .in_("pay_period_id", list(period_months.keys()))
        .execute()
    )

    monthly: dict[int, int] = {}
    for row in entry_result.data:
        month = period_months[row["pay_period_id"]]
        monthly[month] = monthly.get(month, 0) + (row.get("withholding_tax") or 0)

    return monthly


def _load_annual_entries(year: int) -> dict:
    """Aggregate payroll_entries for all finalized/paid periods in `year`.

    Returns {employee_id: aggregated_dict} with summed centavo values.
    Returns {} if no periods found.
    """
    db = get_db()
    period_result = (
        db.table("pay_periods")
        .select("id")
        .eq("company_id", get_company_id())
        .in_("status", ["finalized", "paid"])
        .gte("period_start", f"{year}-01-01")
        .lte("period_start", f"{year}-12-31")
        .execute()
    )
    period_ids = [row["id"] for row in period_result.data]
    if not period_ids:
        return {}

    entry_result = (
        db.table("payroll_entries")
        .select("*")
        .in_("pay_period_id", period_ids)
        .execute()
    )

    aggregated: dict = {}
    for row in entry_result.data:
        eid = row["employee_id"]
        if eid not in aggregated:
            aggregated[eid] = {f: 0 for f in _ANNUAL_FIELDS}
        for f in _ANNUAL_FIELDS:
            aggregated[eid][f] += row.get(f) or 0

    return aggregated


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
    inject_css()
    st.title("Government Reports")

    company      = _load_company()
    all_employees = _load_employees()

    # ============================================================
    # Tab layout — Monthly vs Annual
    # ============================================================
    tab_monthly, tab_annual = st.tabs(["📅 Monthly Reports", "📑 Annual Reports"])

    # ============================================================
    # MONTHLY REPORTS TAB
    # ============================================================
    with tab_monthly:
        periods = _load_pay_periods()

        if not periods:
            st.info("No finalized pay periods yet. Finalize a payroll run first to generate reports.")
        else:
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

            report_info  = REPORTS[selected_report]
            period_label = f"{period['period_start']} to {period['period_end']}"

            st.divider()

            entries   = _load_payroll_entries(period["id"])
            employees = [e for e in all_employees if e["id"] in entries]

            if not employees:
                st.warning("No payroll entries found for this period. Compute payroll first.")
            else:
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
                filename  = (
                    f"{report_info['filename_prefix']}_"
                    f"{period['period_start']}_to_{period['period_end']}.pdf"
                )
                st.download_button(
                    label=f"Download {report_info['title']} (PDF)",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    type="primary",
                    width="stretch",
                )

    # ============================================================
    # ANNUAL REPORTS TAB
    # ============================================================
    with tab_annual:
        today = _date.today()
        col_year, _ = st.columns([2, 5])
        with col_year:
            year_options  = [today.year - i for i in range(0, 3)]
            selected_year = st.selectbox("Tax Year", year_options, index=0)

        annual_entries = _load_annual_entries(selected_year)
        monthly_taxes  = _load_monthly_taxes(selected_year)

        if not annual_entries:
            st.info(f"No finalized payroll data found for {selected_year}.")
        else:
            emp_in_year = [e for e in all_employees if e["id"] in annual_entries]

            # ── BIR Form 2316 ─────────────────────────────────────────────────
            st.subheader("📄 BIR Form 2316")
            st.caption(
                "Certificate of Compensation Payment / Tax Withheld — "
                "one PDF per employee, covering the full calendar year."
            )
            st.markdown(f"**{len(emp_in_year)} employee(s) with payroll data for {selected_year}**")

            hc = st.columns([3, 2, 2, 2, 1.5])
            for col, label in zip(hc, ["Employee", "BIR TIN", "Gross Compensation", "Tax Withheld", ""]):
                col.markdown(f"**{label}**")
            st.divider()

            for emp in emp_in_year:
                agg = annual_entries.get(emp["id"])
                if not agg:
                    continue
                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1.5])
                c1.write(f"{emp['last_name']}, {emp['first_name']}")
                c2.write(emp.get("bir_tin") or "—")
                c3.write(f"PHP {agg['gross_pay'] / 100:,.2f}")
                c4.write(f"PHP {agg['withholding_tax'] / 100:,.2f}")
                with c5:
                    st.download_button(
                        "⬇ 2316",
                        data=generate_bir2316_pdf(company, emp, agg, selected_year),
                        file_name=f"BIR2316_{emp.get('employee_no', emp['id'])}_{selected_year}.pdf",
                        mime="application/pdf",
                        key=f"bir2316_{emp['id']}_{selected_year}",
                    )

            # ── BIR Form 1604-C ───────────────────────────────────────────────
            st.divider()
            st.subheader("📑 BIR Form 1604-C")
            st.caption(
                "Annual Information Return of Income Taxes Withheld on Compensation — "
                "due **January 31** of the following year."
            )

            total_tw = sum(monthly_taxes.values())
            st.markdown(
                f"**{len(emp_in_year)} employee(s)** · "
                f"**Total taxes withheld {selected_year}: PHP {total_tw / 100:,.2f}**"
            )

            MONTH_NAMES = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December",
            ]
            preview_rows = [
                {
                    "Month": mname,
                    "Taxes Withheld": (
                        f"PHP {monthly_taxes[mi] / 100:,.2f}"
                        if (mi := i + 1) in monthly_taxes else "—"
                    ),
                }
                for i, mname in enumerate(MONTH_NAMES)
            ]
            with st.expander("Monthly Taxes Withheld — Part II preview", expanded=False):
                st.dataframe(preview_rows, hide_index=True, use_container_width=True)
                st.caption(
                    "Remittance dates, bank, and TRA/eROR numbers are left blank — "
                    "fill those in manually on the printed form."
                )

            col_form, col_alphalist = st.columns(2)

            with col_form:
                st.download_button(
                    label="⬇ Download 1604-C Main Return",
                    data=generate_bir1604c_pdf(company, selected_year, monthly_taxes),
                    file_name=f"BIR_1604C_{selected_year}.pdf",
                    mime="application/pdf",
                    type="primary",
                    width='stretch',
                    key=f"bir1604c_form_{selected_year}",
                )
                st.caption("Portrait A4 · Pre-filled company info + monthly taxes withheld")

            with col_alphalist:
                sorted_emps = sorted(emp_in_year, key=lambda e: (
                    (e.get("last_name") or "").upper(),
                    (e.get("first_name") or "").upper(),
                ))
                st.download_button(
                    label="⬇ Download Alphalist (Annex A)",
                    data=generate_bir1604c_alphalist(
                        company, sorted_emps, annual_entries, selected_year
                    ),
                    file_name=f"BIR_1604C_Alphalist_{selected_year}.pdf",
                    mime="application/pdf",
                    type="secondary",
                    width='stretch',
                    key=f"bir1604c_alpha_{selected_year}",
                )
                st.caption(
                    f"Landscape A4 · Schedule 1 — "
                    f"{len(emp_in_year)} employee(s) sorted A-Z"
                )
