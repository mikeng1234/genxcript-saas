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
from datetime import date as _date, timedelta as _timedelta
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
# Remittance Log — DB helpers
# ============================================================

_AGENCY_FORMS = {
    "SSS":        "R3 / R5",
    "PhilHealth": "RF-1",
    "Pag-IBIG":   "MCRF",
    "BIR":        "1601-C",
}

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _ref_month(today: "_date") -> "_date":
    """Return the first day of the current 'reference month' (mirrors deadlines.py logic)."""
    if today.day <= 20:
        return today.replace(day=1)
    nxt = today.replace(day=28) + _timedelta(days=4)
    return nxt.replace(day=1)


def _load_remittance_records(year: int | None = None) -> list[dict]:
    """Load all remittance_records for this company, optionally filtered by year."""
    db = get_db()
    q = (
        db.table("remittance_records")
        .select("*")
        .eq("company_id", get_company_id())
        .order("period_year", desc=True)
        .order("period_month", desc=True)
        .order("agency")
    )
    if year is not None:
        q = q.eq("period_year", year)
    return q.execute().data


def _load_remittance_for_period(year: int, month: int) -> dict[str, dict | None]:
    """Return {agency: row_or_None} for a specific year/month."""
    db = get_db()
    rows = (
        db.table("remittance_records")
        .select("*")
        .eq("company_id", get_company_id())
        .eq("period_year",  year)
        .eq("period_month", month)
        .execute()
    ).data
    result: dict[str, dict | None] = {a: None for a in _AGENCY_FORMS}
    for row in rows:
        result[row["agency"]] = row
    return result


def _upsert_remittance(agency: str, year: int, month: int,
                       remitted_date: "_date", reference_no: str,
                       amount_centavos: int, notes: str) -> None:
    db = get_db()
    db.table("remittance_records").upsert({
        "company_id":      get_company_id(),
        "agency":          agency,
        "form":            _AGENCY_FORMS[agency],
        "period_year":     year,
        "period_month":    month,
        "remitted_date":   str(remitted_date),
        "reference_no":    reference_no or None,
        "amount_centavos": amount_centavos or None,
        "notes":           notes or None,
    }, on_conflict="company_id,agency,period_year,period_month").execute()


def _delete_remittance(record_id: str) -> None:
    db = get_db()
    db.table("remittance_records").delete().eq("id", record_id).execute()


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
    # Tab layout
    # ============================================================
    tab_monthly, tab_annual, tab_remit = st.tabs([
        "📅 Monthly Reports", "📑 Annual Reports", "📋 Remittance Log",
    ])

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

    # ============================================================
    # REMITTANCE LOG TAB
    # ============================================================
    with tab_remit:
        today = _date.today()
        ref   = _ref_month(today)

        # ── Period selector ───────────────────────────────────────────────────
        col_yr, col_mo, _ = st.columns([2, 2, 5])
        with col_yr:
            year_opts  = [today.year - i for i in range(3)]
            sel_year   = st.selectbox("Year", year_opts, key="remit_log_year")
        with col_mo:
            month_opts = list(range(1, 13))
            sel_month  = st.selectbox(
                "Month",
                month_opts,
                index=(ref.month - 1),
                format_func=lambda m: _MONTH_NAMES[m - 1],
                key="remit_log_month",
            )

        period_label = f"{_MONTH_NAMES[sel_month - 1]} {sel_year}"
        st.markdown(f"#### Remittance status for **{period_label}**")
        st.caption(
            "Mark each agency as remitted once you have submitted the payment. "
            "Remitted agencies are suppressed from the dashboard overdue alerts."
        )
        st.divider()

        # ── Load current status for selected period ───────────────────────────
        status = _load_remittance_for_period(sel_year, sel_month)

        agency_colors = {
            "SSS":        "#7c3aed",
            "PhilHealth": "#0891b2",
            "Pag-IBIG":   "#059669",
            "BIR":        "#dc2626",
        }

        for agency, form in _AGENCY_FORMS.items():
            rec = status[agency]
            color = agency_colors[agency]

            left_col, right_col = st.columns([3, 2])

            with left_col:
                if rec:
                    # ── Already remitted ──
                    ref_display  = rec.get("reference_no") or "—"
                    date_display = rec.get("remitted_date", "")
                    amt_raw      = rec.get("amount_centavos")
                    amt_display  = f"₱{amt_raw / 100:,.2f}" if amt_raw else "—"
                    notes_display = rec.get("notes") or ""

                    st.markdown(
                        f'<div style="border-left:4px solid {color};padding:10px 14px;'
                        f'background:#f0fdf4;border-radius:6px;margin-bottom:4px">'
                        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
                        f'<span style="font-weight:700;font-size:14px;color:#1f2937">{agency}</span>'
                        f'<span style="font-size:11px;color:#6b7280">({form})</span>'
                        f'<span style="background:#dcfce7;color:#16a34a;font-size:10px;'
                        f'font-weight:700;padding:2px 8px;border-radius:10px">✓ Remitted</span>'
                        f'</div>'
                        f'<div style="display:flex;gap:24px;font-size:12px;color:#374151">'
                        f'<span>📅 <b>Date:</b> {date_display}</span>'
                        f'<span>🔖 <b>Ref No:</b> {ref_display}</span>'
                        f'<span>💰 <b>Amount:</b> {amt_display}</span>'
                        f'</div>'
                        + (f'<div style="font-size:11px;color:#6b7280;margin-top:4px">📝 {notes_display}</div>' if notes_display else '')
                        + f'</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    # ── Not yet remitted ──
                    st.markdown(
                        f'<div style="border-left:4px solid {color};padding:10px 14px;'
                        f'background:#fafafa;border-radius:6px;margin-bottom:4px">'
                        f'<div style="display:flex;align-items:center;gap:8px">'
                        f'<span style="font-weight:700;font-size:14px;color:#1f2937">{agency}</span>'
                        f'<span style="font-size:11px;color:#6b7280">({form})</span>'
                        f'<span style="background:#f3f4f6;color:#9ca3af;font-size:10px;'
                        f'font-weight:700;padding:2px 8px;border-radius:10px">Pending</span>'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            with right_col:
                if rec:
                    # Edit / Undo buttons
                    btn_edit, btn_undo = st.columns(2)
                    with btn_edit:
                        if st.button("✏️ Edit", key=f"remit_edit_{agency}_{sel_year}_{sel_month}", width="stretch"):
                            st.session_state[f"remit_form_{agency}"] = True
                    with btn_undo:
                        if st.button("↩ Undo", key=f"remit_undo_{agency}_{sel_year}_{sel_month}", width="stretch"):
                            _delete_remittance(rec["id"])
                            st.success(f"{agency} remittance for {period_label} removed.")
                            st.rerun()
                else:
                    if st.button(
                        f"✓ Mark {agency} as Remitted",
                        key=f"remit_mark_{agency}_{sel_year}_{sel_month}",
                        width="stretch",
                        type="primary",
                    ):
                        st.session_state[f"remit_form_{agency}"] = True

            # ── Inline form (shown after clicking Mark / Edit) ────────────────
            form_key = f"remit_form_{agency}"
            if st.session_state.get(form_key):
                with st.form(key=f"remit_submit_{agency}_{sel_year}_{sel_month}"):
                    st.markdown(f"**Record {agency} remittance — {period_label}**")
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        default_date = (
                            _date.fromisoformat(rec["remitted_date"])
                            if rec and rec.get("remitted_date")
                            else today
                        )
                        f_date = st.date_input("Date Remitted", value=default_date)
                        f_ref  = st.text_input(
                            "Reference / ORN / Batch No.",
                            value=(rec.get("reference_no") or "") if rec else "",
                        )
                    with fc2:
                        f_amt_str = st.text_input(
                            "Amount Remitted (₱)",
                            value=(
                                f"{rec['amount_centavos'] / 100:.2f}"
                                if rec and rec.get("amount_centavos")
                                else ""
                            ),
                            help="Enter the total amount you actually remitted (e.g. 16725.00)",
                        )
                        f_notes = st.text_area(
                            "Notes (optional)",
                            value=(rec.get("notes") or "") if rec else "",
                            height=68,
                        )
                    sub_col, cancel_col = st.columns([2, 1])
                    submitted = sub_col.form_submit_button(
                        f"💾 Save {agency} Remittance",
                        type="primary",
                        use_container_width=True,
                    )
                    cancelled = cancel_col.form_submit_button(
                        "Cancel",
                        use_container_width=True,
                    )

                if submitted:
                    try:
                        amt_centavos = int(float(f_amt_str) * 100) if f_amt_str.strip() else 0
                    except ValueError:
                        amt_centavos = 0
                    _upsert_remittance(
                        agency=agency,
                        year=sel_year,
                        month=sel_month,
                        remitted_date=f_date,
                        reference_no=f_ref,
                        amount_centavos=amt_centavos,
                        notes=f_notes,
                    )
                    st.session_state.pop(form_key, None)
                    st.success(f"✓ {agency} remittance for {period_label} saved.")
                    st.rerun()
                if cancelled:
                    st.session_state.pop(form_key, None)
                    st.rerun()

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        # ── History table ─────────────────────────────────────────────────────
        st.divider()
        st.markdown("#### Remittance History")

        hist_year_opts = [today.year - i for i in range(5)]
        col_hy, _ = st.columns([2, 7])
        with col_hy:
            hist_year = st.selectbox("Filter by year", hist_year_opts, key="remit_hist_year")

        all_records = _load_remittance_records(year=hist_year)

        if not all_records:
            st.info(f"No remittance records found for {hist_year}.")
        else:
            hist_rows = []
            for r in all_records:
                amt = r.get("amount_centavos")
                hist_rows.append({
                    "Period":       f"{_MONTH_NAMES[r['period_month'] - 1]} {r['period_year']}",
                    "Agency":       r["agency"],
                    "Form":         r["form"],
                    "Date Remitted": r.get("remitted_date", "—"),
                    "Reference No.": r.get("reference_no") or "—",
                    "Amount":       f"₱{amt / 100:,.2f}" if amt else "—",
                    "Notes":        r.get("notes") or "",
                })
            st.dataframe(hist_rows, hide_index=True, use_container_width=True)
