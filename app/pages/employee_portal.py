"""
Employee Self-Service Portal — Streamlit page.

Accessible only to users with role='employee'.
Employees can:
- View their own payslips (with PDF download)
- Update their personal profile (employee_profiles)
"""

import streamlit as st
import datetime
from datetime import date, timedelta, timezone
from app.db_helper import get_db, get_company_id
from app.auth import get_current_user_email
from app.styles import inject_css, status_badge
from reports.payslip_pdf import generate_payslip_pdf
from reports.coe_pdf import generate_coe_pdf
from reports.bir2316_pdf import generate_bir2316_pdf
from backend.dtr import (
    compute_dtr, resolve_schedule_for_date, schedule_expected_hours,
    nearest_location, haversine_distance_m, _parse_time,
)
from app.components.geolocation import get_location


# ============================================================
# Constants
# ============================================================

CIVIL_STATUSES = ["Single", "Married", "Widowed", "Separated", "Divorced"]
SEXES = ["Male", "Female", "Prefer not to say"]

PROVINCES = [
    "Metro Manila", "Abra", "Agusan del Norte", "Agusan del Sur", "Aklan",
    "Albay", "Antique", "Apayao", "Aurora", "Basilan", "Bataan", "Batanes",
    "Batangas", "Benguet", "Biliran", "Bohol", "Bukidnon", "Bulacan",
    "Cagayan", "Camarines Norte", "Camarines Sur", "Camiguin", "Capiz",
    "Catanduanes", "Cavite", "Cebu", "Compostela Valley", "Cotabato",
    "Davao del Norte", "Davao del Sur", "Davao Occidental", "Davao Oriental",
    "Dinagat Islands", "Eastern Samar", "Guimaras", "Ifugao", "Ilocos Norte",
    "Ilocos Sur", "Iloilo", "Isabela", "Kalinga", "La Union", "Laguna",
    "Lanao del Norte", "Lanao del Sur", "Leyte", "Maguindanao", "Marinduque",
    "Masbate", "Misamis Occidental", "Misamis Oriental", "Mountain Province",
    "Negros Occidental", "Negros Oriental", "Northern Samar", "Nueva Ecija",
    "Nueva Vizcaya", "Occidental Mindoro", "Oriental Mindoro", "Palawan",
    "Pampanga", "Pangasinan", "Quezon", "Quirino", "Rizal", "Romblon",
    "Samar", "Sarangani", "Shariff Kabunsuan", "Siquijor", "Sorsogon",
    "South Cotabato", "Southern Leyte", "Sultan Kudarat", "Sulu", "Surigao del Norte",
    "Surigao del Sur", "Tarlac", "Tawi-Tawi", "Zambales", "Zamboanga del Norte",
    "Zamboanga del Sur", "Zamboanga Sibugay",
]


# ============================================================
# Formatters
# ============================================================

def _fmt(centavos: int) -> str:
    return f"₱{(centavos or 0) / 100:,.2f}"


def _p(centavos: int) -> float:
    return (centavos or 0) / 100


# ============================================================
# Database helpers
# ============================================================

def _load_company() -> dict:
    db = get_db()
    result = db.table("companies").select("*").eq("id", get_company_id()).execute()
    return result.data[0] if result.data else {}


_ANNUAL_FIELDS = [
    "gross_pay", "basic_pay", "overtime_pay", "holiday_pay", "night_differential",
    "allowances_nontaxable", "allowances_taxable", "commission",
    "thirteenth_month_accrual",
    "sss_employee", "philhealth_employee", "pagibig_employee", "withholding_tax",
]


def _load_employee_annual(employee_id: str, year: int) -> dict | None:
    """Aggregate payroll_entries for one employee across all finalized/paid periods in `year`.

    Returns a summed centavo dict or None if no data.
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
        return None

    entry_result = (
        db.table("payroll_entries")
        .select("*")
        .eq("employee_id", employee_id)
        .in_("pay_period_id", period_ids)
        .execute()
    )
    if not entry_result.data:
        return None

    agg = {f: 0 for f in _ANNUAL_FIELDS}
    for row in entry_result.data:
        for f in _ANNUAL_FIELDS:
            agg[f] += row.get(f) or 0
    return agg


def _get_employee_record() -> dict | None:
    """Get the employees row linked to the current logged-in user."""
    db = get_db()
    user_id = st.session_state.get("user_id")
    result = (
        db.table("employees")
        .select("*")
        .eq("user_id", user_id)
        .eq("company_id", get_company_id())
        .execute()
    )
    return result.data[0] if result.data else None


def _get_profile(employee_id: str) -> dict | None:
    """Get employee_profiles row for this employee (may not exist yet)."""
    db = get_db()
    result = (
        db.table("employee_profiles")
        .select("*")
        .eq("employee_id", employee_id)
        .execute()
    )
    return result.data[0] if result.data else None


def _save_profile(employee_id: str, data: dict):
    """Upsert employee_profiles row."""
    db = get_db()
    existing = _get_profile(employee_id)
    data["updated_at"] = "now()"
    if existing:
        db.table("employee_profiles").update(data).eq("employee_id", employee_id).execute()
    else:
        data["employee_id"] = employee_id
        data["company_id"]  = get_company_id()
        db.table("employee_profiles").insert(data).execute()


def _get_payslips(employee_id: str) -> list[dict]:
    """Get finalized payroll entries for this employee, newest first."""
    db = get_db()
    result = (
        db.table("payroll_entries")
        .select("*, pay_periods(period_start, period_end, payment_date, status)")
        .eq("employee_id", employee_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [
        r for r in (result.data or [])
        if r.get("pay_periods", {}).get("status") in ("finalized", "paid")
    ]


# ============================================================
# Section 1: Hero Welcome Card
# ============================================================

def _render_hero(emp: dict, company: dict):
    hired = emp.get("date_hired", "")
    position = emp.get("position", "Employee")
    emp_no = emp.get("employee_no", "—")
    email = get_current_user_email()
    company_name = company.get("name", "Your Company")
    initial = emp["first_name"][0].upper() if emp.get("first_name") else "?"

    st.markdown(
        f'<div class="gxp-portal-hero">'
        f'<div class="gxp-portal-hero-avatar">{initial}</div>'
        f'<div class="gxp-portal-hero-info">'
        f'<div class="gxp-portal-hero-name">{emp["first_name"]} {emp["last_name"]}</div>'
        f'<div class="gxp-portal-hero-meta">{position} &nbsp;·&nbsp; {emp_no} &nbsp;·&nbsp; {company_name}</div>'
        f'<div class="gxp-portal-hero-sub">{email}'
        + (f' &nbsp;·&nbsp; Hired {hired}' if hired else '')
        + '</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# Section 2: Payslips Tab
# ============================================================

def _build_chart(payslips: list[dict]):
    """Render a stacked bar chart: Net Pay / Statutory / Loan breakdowns per period."""
    import pandas as pd
    import altair as alt
    from datetime import date as _date

    rows = []
    # Use newest-first list; reverse for chronological chart order
    for entry in reversed(payslips[:12]):
        pp = entry.get("pay_periods") or {}
        raw = pp.get("period_start", "")
        try:
            dt    = _date.fromisoformat(raw)
            label = dt.strftime("%b '%y")
        except Exception:
            label = raw or "?"

        statutory = _p(
            (entry.get("sss_employee")       or 0)
            + (entry.get("philhealth_employee") or 0)
            + (entry.get("pagibig_employee")    or 0)
            + (entry.get("withholding_tax")     or 0)
        )
        loans = _p(
            (entry.get("sss_loan")          or 0)
            + (entry.get("pagibig_loan")    or 0)
            + (entry.get("cash_advance")    or 0)
            + (entry.get("other_deductions") or 0)
        )
        net = _p(entry.get("net_pay") or 0)

        rows.append({"Period": label, "Category": "Net Pay",               "Amount": net,       "sort": 0})
        rows.append({"Period": label, "Category": "Statutory Deductions",  "Amount": statutory, "sort": 1})
        rows.append({"Period": label, "Category": "Loan & Other Deduc.",   "Amount": loans,     "sort": 2})

    df = pd.DataFrame(rows)
    period_order = df["Period"].unique().tolist()

    color_scale = alt.Scale(
        domain=["Net Pay", "Statutory Deductions", "Loan & Other Deduc."],
        range=["#16a34a", "#2563eb", "#f59e0b"],
    )

    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("Period:O", sort=period_order, title=None,
                    axis=alt.Axis(labelAngle=0, labelFontSize=11, labelPadding=6)),
            y=alt.Y("Amount:Q", title="Amount (₱)",
                    axis=alt.Axis(format=",.0f", labelFontSize=10)),
            color=alt.Color("Category:N", scale=color_scale,
                            legend=alt.Legend(orient="bottom", title=None,
                                              labelFontSize=11, symbolSize=80)),
            order=alt.Order("sort:Q"),
            tooltip=[
                alt.Tooltip("Period:O",   title="Period"),
                alt.Tooltip("Category:N", title="Category"),
                alt.Tooltip("Amount:Q",   title="Amount (₱)", format=",.2f"),
            ],
        )
        .properties(height=260)
    )

    st.altair_chart(chart, use_container_width=True)


def _render_gross_pie(entry: dict):
    """Donut chart showing how gross pay is distributed across all components."""
    import pandas as pd
    import altair as alt

    # All slices with colour tokens — zero-value items are excluded automatically
    slices_raw = [
        ("Net Pay",          _p(entry.get("net_pay")              or 0), "#16a34a"),
        ("SSS",              _p(entry.get("sss_employee")         or 0), "#2563eb"),
        ("PhilHealth",       _p(entry.get("philhealth_employee")  or 0), "#0891b2"),
        ("Pag-IBIG",         _p(entry.get("pagibig_employee")     or 0), "#7c3aed"),
        ("Withholding Tax",  _p(entry.get("withholding_tax")      or 0), "#dc2626"),
        ("SSS Loan",         _p(entry.get("sss_loan")             or 0), "#f59e0b"),
        ("Pag-IBIG Loan",    _p(entry.get("pagibig_loan")         or 0), "#f97316"),
        ("Cash Advance",     _p(entry.get("cash_advance")         or 0), "#84cc16"),
        ("Other Deductions", _p(entry.get("other_deductions")     or 0), "#94a3b8"),
    ]
    slices = [(lbl, val, col) for lbl, val, col in slices_raw if val > 0]
    if not slices:
        return

    df = pd.DataFrame(slices, columns=["Category", "Amount", "_color"])

    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=55, outerRadius=110, stroke="#fff", strokeWidth=2)
        .encode(
            theta=alt.Theta("Amount:Q", stack=True),
            color=alt.Color(
                "Category:N",
                scale=alt.Scale(
                    domain=[s[0] for s in slices],
                    range=[s[2]  for s in slices],
                ),
                legend=alt.Legend(
                    orient="right",
                    title=None,
                    labelFontSize=11,
                    symbolSize=90,
                    labelLimit=160,
                ),
            ),
            tooltip=[
                alt.Tooltip("Category:N", title="Category"),
                alt.Tooltip("Amount:Q",   title="Amount (₱)", format=",.2f"),
            ],
        )
        .properties(height=250)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_payslip_detail(entry: dict, emp: dict, company: dict):
    """Renders the full payslip breakdown inside an expander."""
    pp          = entry.get("pay_periods") or {}
    period_label = f"{pp.get('period_start', '?')} – {pp.get('period_end', '?')}"
    payment_date = pp.get("payment_date", "—")
    badge        = status_badge(pp.get("status", "finalized"))
    net          = _p(entry.get("net_pay")          or 0)
    gross        = _p(entry.get("gross_pay")         or 0)
    total_ded    = _p(entry.get("total_deductions")  or 0)

    # Header row inside expander (no blank lines = safe from markdown parser)
    st.markdown(
        f'<div class="gxp-payslip-header" style="margin-bottom:12px">'
        f'<div><div class="gxp-payslip-period">{period_label}</div>'
        f'<div class="gxp-payslip-payment">Payment date: {payment_date} &nbsp;{badge}</div></div>'
        f'<div class="gxp-payslip-net">₱{net:,.2f}'
        f'<span class="gxp-payslip-net-label"> net pay</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Summary KPIs + Donut chart side-by-side ───────────────────────────────
    kpi_col, chart_col = st.columns([1, 1.6])
    with kpi_col:
        st.metric("Gross Pay",        f"₱{gross:,.2f}")
        st.metric("Total Deductions", f"₱{total_ded:,.2f}")
        st.metric("Net Pay",          f"₱{net:,.2f}")
    with chart_col:
        st.markdown(
            '<div style="font-size:12px;font-weight:600;color:#6b7280;'
            'text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">'
            'Gross Pay Breakdown</div>',
            unsafe_allow_html=True,
        )
        _render_gross_pie(entry)

    st.markdown('<div class="gxp-payslip-section-label">Earnings</div>', unsafe_allow_html=True)
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Basic Pay",   f"₱{_p(entry.get('basic_pay')           or 0):,.2f}")
    e2.metric("Overtime",    f"₱{_p(entry.get('overtime_pay')        or 0):,.2f}")
    e3.metric("Holiday Pay", f"₱{_p(entry.get('holiday_pay')         or 0):,.2f}")
    e4.metric("Night Diff.", f"₱{_p(entry.get('night_differential')  or 0):,.2f}")

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Non-Tax. Allow.", f"₱{_p(entry.get('allowances_nontaxable')     or 0):,.2f}")
    a2.metric("Tax. Allow.",     f"₱{_p(entry.get('allowances_taxable')        or 0):,.2f}")
    a3.metric("Commission",      f"₱{_p(entry.get('commission')                or 0):,.2f}")
    a4.metric("13th Mo. Accrl.", f"₱{_p(entry.get('thirteenth_month_accrual') or 0):,.2f}")

    st.markdown('<div class="gxp-payslip-section-label">Deductions</div>', unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("SSS",             f"₱{_p(entry.get('sss_employee')       or 0):,.2f}")
    d2.metric("PhilHealth",      f"₱{_p(entry.get('philhealth_employee') or 0):,.2f}")
    d3.metric("Pag-IBIG",        f"₱{_p(entry.get('pagibig_employee')   or 0):,.2f}")
    d4.metric("Withholding Tax", f"₱{_p(entry.get('withholding_tax')    or 0):,.2f}")

    l1, l2, l3, l4 = st.columns(4)
    l1.metric("SSS Loan",         f"₱{_p(entry.get('sss_loan')          or 0):,.2f}")
    l2.metric("Pag-IBIG Loan",    f"₱{_p(entry.get('pagibig_loan')      or 0):,.2f}")
    l3.metric("Cash Advance",     f"₱{_p(entry.get('cash_advance')      or 0):,.2f}")
    l4.metric("Other Deductions", f"₱{_p(entry.get('other_deductions')  or 0):,.2f}")

    _, dl_col = st.columns([3, 1])
    with dl_col:
        try:
            pay_period_dict = {
                "period_start": pp.get("period_start"),
                "period_end":   pp.get("period_end"),
                "payment_date": pp.get("payment_date"),
                "status":       pp.get("status"),
            }
            pdf_bytes = generate_payslip_pdf(company, emp, pay_period_dict, entry)
            st.download_button(
                label="⬇ Download PDF",
                data=pdf_bytes,
                file_name=f"payslip_{emp['employee_no']}_{pp.get('period_start', 'unknown')}.pdf",
                mime="application/pdf",
                width='stretch',
                key=f"dl_{entry['id']}",
            )
        except Exception as ex:
            st.caption(f"PDF unavailable: {ex}")


def _render_payslips(emp: dict, company: dict):
    payslips = _get_payslips(emp["id"])

    if not payslips:
        st.markdown(
            '<div class="gxp-panel" style="text-align:center;padding:40px 24px">'
            '<div style="font-size:32px;margin-bottom:12px">📄</div>'
            '<div style="font-size:15px;font-weight:600;color:#6b7280">No payslips yet</div>'
            '<div style="font-size:13px;margin-top:4px;color:#9ca3af">'
            'Your payslips will appear here once payroll is finalized by HR.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Bar chart (last 12 months, chronological) ─────────────────────────────
    n = min(len(payslips), 12)
    st.markdown(
        f"##### Payroll Summary — Last {n} {'Period' if n == 1 else 'Periods'}",
    )
    _build_chart(payslips)
    st.divider()

    # ── Individual payslip entries (collapsed by default) ─────────────────────
    st.markdown("##### Payslip History")
    for entry in payslips:
        pp  = entry.get("pay_periods") or {}
        net = _p(entry.get("net_pay") or 0)
        period_start = pp.get("period_start", "?")
        period_end   = pp.get("period_end",   "?")
        label        = f"📄  {period_start} – {period_end}  ·  Net Pay: ₱{net:,.2f}"
        with st.expander(label, expanded=False):
            _render_payslip_detail(entry, emp, company)


# ============================================================
# Section 3: Profile Form
# ============================================================

def _render_profile_form(emp: dict, profile: dict | None):
    p = profile or {}

    st.info(
        "Fill in your personal details below. "
        "Fields labelled **(HR)** can only be updated by your employer — contact HR to make changes.",
        icon="ℹ️",
    )

    with st.form("employee_profile_form"):

        # --- Personal Information ---
        st.markdown("#### Personal Information")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("First Name", value=emp.get("first_name", ""), disabled=True)
        with col2:
            middle_name = st.text_input("Middle Name", value=p.get("middle_name", "") or "")
        with col3:
            st.text_input("Last Name", value=emp.get("last_name", ""), disabled=True)

        col1, col2 = st.columns(2)
        with col1:
            suffix = st.text_input("Suffix (Jr., Sr., III…)", value=p.get("suffix", "") or "")
        with col2:
            mobile_no = st.text_input(
                "Mobile Number *",
                value=p.get("mobile_no", "") or "",
                placeholder="09XX-XXX-XXXX",
            )

        col1, col2, col3 = st.columns(3)
        with col1:
            dob_val = p.get("date_of_birth")
            if isinstance(dob_val, str):
                dob_val = date.fromisoformat(dob_val)
            date_of_birth = st.date_input(
                "Date of Birth *",
                value=dob_val or date(1990, 1, 1),
                min_value=date(1940, 1, 1),
                max_value=date.today(),
            )
        with col2:
            place_of_birth = st.text_input("Place of Birth", value=p.get("place_of_birth", "") or "")
        with col3:
            nationality = st.text_input(
                "Nationality",
                value=p.get("nationality", "Filipino") or "Filipino",
            )

        col1, col2, col3 = st.columns(3)
        with col1:
            sex_idx = SEXES.index(p["sex"]) if p.get("sex") in SEXES else 0
            sex = st.selectbox("Sex", SEXES, index=sex_idx)
        with col2:
            cs_idx = CIVIL_STATUSES.index(p["civil_status"]) if p.get("civil_status") in CIVIL_STATUSES else 0
            civil_status = st.selectbox("Civil Status *", CIVIL_STATUSES, index=cs_idx)
        with col3:
            religion = st.text_input("Religion", value=p.get("religion", "") or "")

        # --- Government IDs ---
        st.markdown("#### Government IDs")
        st.caption("Managed by HR. Contact your employer to update these.")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.text_input("SSS No. (HR)", value=emp.get("sss_no", "") or "", disabled=True)
        with col2:
            st.text_input("PhilHealth No. (HR)", value=emp.get("philhealth_no", "") or "", disabled=True)
        with col3:
            st.text_input("Pag-IBIG No. (HR)", value=emp.get("pagibig_no", "") or "", disabled=True)
        with col4:
            st.text_input("BIR TIN (HR)", value=emp.get("bir_tin", "") or "", disabled=True)

        col1, col2 = st.columns(2)
        with col1:
            philsys_no = st.text_input("PhilSys / National ID No.", value=p.get("philsys_no", "") or "")
        with col2:
            umid_no = st.text_input("UMID No.", value=p.get("umid_no", "") or "")

        # --- Bank ---
        st.markdown("#### Bank / Payment Details")
        col1, col2 = st.columns(2)
        with col1:
            bank_name = st.text_input(
                "Bank Name *",
                value=p.get("bank_name", "") or "",
                placeholder="e.g. BDO, BPI, GCash",
            )
        with col2:
            st.text_input(
                "Bank Account No. (HR)",
                value=emp.get("bank_account", "") or "",
                disabled=True,
            )

        # --- Present Address ---
        st.markdown("#### Present Address")
        col1, col2 = st.columns(2)
        with col1:
            present_street = st.text_input(
                "House No. / Street / Subdivision",
                value=p.get("present_address_street", "") or "",
            )
        with col2:
            present_barangay = st.text_input("Barangay", value=p.get("present_address_barangay", "") or "")

        col1, col2, col3 = st.columns(3)
        with col1:
            present_city = st.text_input("City / Municipality", value=p.get("present_address_city", "") or "")
        with col2:
            prov_idx = (
                PROVINCES.index(p["present_address_province"])
                if p.get("present_address_province") in PROVINCES else 0
            )
            present_province = st.selectbox("Province", PROVINCES, index=prov_idx, key="prov_present")
        with col3:
            present_zip = st.text_input("ZIP Code", value=p.get("present_address_zip", "") or "")

        # --- Permanent Address ---
        st.markdown("#### Permanent Address")
        perm_same = st.checkbox("Same as present address", value=p.get("perm_address_same", True))

        perm_street = perm_barangay = perm_city = perm_province = perm_zip = ""
        if not perm_same:
            col1, col2 = st.columns(2)
            with col1:
                perm_street = st.text_input(
                    "House No. / Street / Subdivision",
                    value=p.get("perm_address_street", "") or "",
                    key="perm_str",
                )
            with col2:
                perm_barangay = st.text_input(
                    "Barangay",
                    value=p.get("perm_address_barangay", "") or "",
                    key="perm_brgy",
                )
            col1, col2, col3 = st.columns(3)
            with col1:
                perm_city = st.text_input(
                    "City / Municipality",
                    value=p.get("perm_address_city", "") or "",
                    key="perm_city",
                )
            with col2:
                perm_prov_idx = (
                    PROVINCES.index(p["perm_address_province"])
                    if p.get("perm_address_province") in PROVINCES else 0
                )
                perm_province = st.selectbox("Province", PROVINCES, index=perm_prov_idx, key="prov_perm")
            with col3:
                perm_zip = st.text_input("ZIP Code", value=p.get("perm_address_zip", "") or "", key="perm_zip")

        # --- Emergency Contact ---
        st.markdown("#### Emergency Contact *")
        col1, col2, col3 = st.columns(3)
        with col1:
            emergency_name = st.text_input("Full Name *", value=p.get("emergency_name", "") or "")
        with col2:
            emergency_relationship = st.text_input(
                "Relationship *",
                value=p.get("emergency_relationship", "") or "",
                placeholder="e.g. Spouse, Parent, Sibling",
            )
        with col3:
            emergency_phone = st.text_input("Contact Number *", value=p.get("emergency_phone", "") or "")
        emergency_address = st.text_input("Address", value=p.get("emergency_address", "") or "")

        # --- Spouse ---
        spouse_name = spouse_occupation = spouse_employer = spouse_contact = ""
        if civil_status == "Married":
            st.markdown("#### Spouse Information")
            col1, col2 = st.columns(2)
            with col1:
                spouse_name = st.text_input("Full Name *", value=p.get("spouse_name", "") or "", key="sp_name")
                spouse_occupation = st.text_input("Occupation", value=p.get("spouse_occupation", "") or "")
            with col2:
                spouse_employer = st.text_input("Employer", value=p.get("spouse_employer", "") or "")
                spouse_contact = st.text_input("Contact Number", value=p.get("spouse_contact", "") or "")

        # --- Additional Contact Information ---
        st.markdown("#### Additional Contact")
        _ac1, _ac2, _ac3 = st.columns(3)
        with _ac1:
            home_phone = st.text_input("Home Phone", value=p.get("home_phone", "") or "",
                                       placeholder="e.g. (02) 8123-4567")
        with _ac2:
            work_phone = st.text_input("Work Phone", value=p.get("work_phone", "") or "",
                                       placeholder="e.g. +63 2 1234 5678")
        with _ac3:
            personal_email = st.text_input("Personal Email", value=p.get("personal_email", "") or "",
                                           placeholder="e.g. juan@gmail.com")

        # --- Educational Background ---
        st.markdown("#### Educational Background")
        _ed1, _ed2, _ed3 = st.columns([3, 3, 1])
        with _ed1:
            education_degree = st.text_input("Degree / Course",
                                             value=p.get("education_degree", "") or "",
                                             placeholder="e.g. BS Computer Science, BSBA")
        with _ed2:
            education_school = st.text_input("School / University",
                                             value=p.get("education_school", "") or "",
                                             placeholder="e.g. University of the Philippines")
        with _ed3:
            _yr_raw = p.get("education_year")
            education_year = st.number_input("Year Graduated",
                                             min_value=1950, max_value=2030,
                                             value=int(_yr_raw) if _yr_raw else 2000,
                                             step=1)

        # --- Social / Online Presence ---
        st.markdown("#### Social Links *(optional)*")
        _sl1, _sl2 = st.columns(2)
        with _sl1:
            facebook = st.text_input("Facebook", value=p.get("facebook", "") or "",
                                     placeholder="Profile URL or username")
        with _sl2:
            linkedin = st.text_input("LinkedIn", value=p.get("linkedin", "") or "",
                                     placeholder="Profile URL or username")

        submitted = st.form_submit_button("Save Profile", type="primary", width='stretch')

    if submitted:
        errors = []
        if not mobile_no.strip():
            errors.append("Mobile number is required.")
        if not emergency_name.strip():
            errors.append("Emergency contact name is required.")
        if not emergency_relationship.strip():
            errors.append("Emergency contact relationship is required.")
        if not emergency_phone.strip():
            errors.append("Emergency contact number is required.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            profile_data = {
                "middle_name":              middle_name.strip() or None,
                "suffix":                   suffix.strip() or None,
                "date_of_birth":            date_of_birth.isoformat(),
                "place_of_birth":           place_of_birth.strip() or None,
                "sex":                      sex,
                "civil_status":             civil_status,
                "nationality":              nationality.strip() or "Filipino",
                "religion":                 religion.strip() or None,
                "mobile_no":                mobile_no.strip(),
                "philsys_no":               philsys_no.strip() or None,
                "umid_no":                  umid_no.strip() or None,
                "bank_name":                bank_name.strip() or None,
                "present_address_street":   present_street.strip() or None,
                "present_address_barangay": present_barangay.strip() or None,
                "present_address_city":     present_city.strip() or None,
                "present_address_province": present_province,
                "present_address_zip":      present_zip.strip() or None,
                "perm_address_same":        perm_same,
                "perm_address_street":      perm_street.strip() or None,
                "perm_address_barangay":    perm_barangay.strip() or None,
                "perm_address_city":        perm_city.strip() or None,
                "perm_address_province":    perm_province if not perm_same else None,
                "perm_address_zip":         perm_zip.strip() or None,
                "emergency_name":           emergency_name.strip(),
                "emergency_relationship":   emergency_relationship.strip(),
                "emergency_phone":          emergency_phone.strip(),
                "emergency_address":        emergency_address.strip() or None,
                "spouse_name":              spouse_name.strip() or None,
                "spouse_occupation":        spouse_occupation.strip() or None,
                "spouse_employer":          spouse_employer.strip() or None,
                "spouse_contact":           spouse_contact.strip() or None,
                # Phase 3B additions
                "home_phone":               home_phone.strip() or None,
                "work_phone":               work_phone.strip() or None,
                "personal_email":           personal_email.strip() or None,
                "education_degree":         education_degree.strip() or None,
                "education_school":         education_school.strip() or None,
                "education_year":           int(education_year) if education_year else None,
                "facebook":                 facebook.strip() or None,
                "linkedin":                 linkedin.strip() or None,
            }
            try:
                _save_profile(emp["id"], profile_data)
                st.success("Profile saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving profile: {e}")


# ============================================================
# Section 4: Time & Leave Tab
# ============================================================

_LEAVE_TYPES  = {"VL": "Vacation Leave", "SL": "Sick Leave", "CL": "Casual/Emergency Leave"}
_STATUS_COLOR = {"pending": "#f59e0b", "approved": "#16a34a", "rejected": "#dc2626"}


def _leave_period_bounds(company: dict, emp: dict) -> tuple[date, date]:
    """Return (period_start, period_end) for the current balance period."""
    policy    = company.get("leave_replenishment", "annual")
    today     = date.today()
    if policy == "anniversary":
        hired_str = emp.get("date_hired", "")
        try:
            hired = date.fromisoformat(hired_str)
            # anniversary this calendar year
            ann = hired.replace(year=today.year)
            if ann > today:
                ann = hired.replace(year=today.year - 1)
            return ann, ann.replace(year=ann.year + 1) - datetime.timedelta(days=1)
        except Exception:
            pass
    # Default: annual (Jan 1 – Dec 31)
    return date(today.year, 1, 1), date(today.year, 12, 31)


def _get_leave_template(emp: dict) -> dict | None:
    """
    Load the leave entitlement template assigned to this employee.
    Returns the template row dict, or None if no template is assigned.
    """
    tmpl_id = emp.get("leave_template_id")
    if not tmpl_id:
        return None
    db = get_db()
    result = (
        db.table("leave_entitlement_templates")
        .select("*")
        .eq("id", tmpl_id)
        .execute()
    )
    return result.data[0] if result.data else None


_COMPANY_DEFAULTS = {"VL": 15, "SL": 15, "CL": 5}


def _get_leave_balance(employee_id: str, company: dict, emp: dict) -> tuple[dict, dict | None]:
    """
    Compute VL / SL / CL used & remaining for the current period.

    Returns:
        (balance_dict, template_or_None)
        balance_dict = {
            'VL': {'total': N, 'used': M, 'remaining': R},
            'SL': ...,
            'CL': ...,
        }
        template_or_None = the assigned leave_entitlement_templates row, or None
    """
    start, end = _leave_period_bounds(company, emp)

    # ── Determine entitlements (template > company columns > hard defaults) ───
    template = _get_leave_template(emp)
    if template:
        entitlement = {
            "VL": int(template.get("vl_days", _COMPANY_DEFAULTS["VL"])),
            "SL": int(template.get("sl_days", _COMPANY_DEFAULTS["SL"])),
            "CL": int(template.get("cl_days", _COMPANY_DEFAULTS["CL"])),
        }
    else:
        entitlement = {
            "VL": int(company.get("leave_vl_days", _COMPANY_DEFAULTS["VL"])),
            "SL": int(company.get("leave_sl_days", _COMPANY_DEFAULTS["SL"])),
            "CL": int(company.get("leave_cl_days", _COMPANY_DEFAULTS["CL"])),
        }

    # ── Override with leave_balance row if HR has set a carry-over opening balance ──
    # leave_balance stores the FULL allocation for the year (template days + carry-over),
    # so it replaces the template/default value entirely when present.
    lb_result = (
        get_db().table("leave_balance")
        .select("leave_type, opening_balance")
        .eq("employee_id", employee_id)
        .eq("year", start.year)
        .execute()
    )
    for row in (lb_result.data or []):
        lt = row.get("leave_type", "")
        if lt in entitlement:
            entitlement[lt] = float(row["opening_balance"])

    # ── Query approved leave taken in current period ──────────────────────────
    db = get_db()
    result = (
        db.table("leave_requests")
        .select("leave_type, days")
        .eq("employee_id", employee_id)
        .eq("status", "approved")
        .gte("start_date", start.isoformat())
        .lte("start_date", end.isoformat())
        .execute()
    )
    used: dict[str, float] = {"VL": 0.0, "SL": 0.0, "CL": 0.0}
    for r in (result.data or []):
        lt = r.get("leave_type", "")
        if lt in used:
            used[lt] += float(r.get("days") or 0)

    balance = {
        lt: {
            "total":     entitlement[lt],
            "used":      used[lt],
            "remaining": max(0.0, entitlement[lt] - used[lt]),
        }
        for lt in ("VL", "SL", "CL")
    }
    return balance, template


def _get_leave_requests(employee_id: str) -> list[dict]:
    db = get_db()
    return (
        db.table("leave_requests")
        .select("*")
        .eq("employee_id", employee_id)
        .order("created_at", desc=True)
        .execute()
    ).data or []


def _get_ot_requests(employee_id: str) -> list[dict]:
    db = get_db()
    return (
        db.table("overtime_requests")
        .select("*")
        .eq("employee_id", employee_id)
        .order("created_at", desc=True)
        .execute()
    ).data or []


def _status_badge_html(status: str) -> str:
    color = _STATUS_COLOR.get(status, "#94a3b8")
    return (
        f'<span style="background:{color};color:#fff;padding:2px 10px;'
        f'border-radius:4px;font-size:11px;font-weight:700;letter-spacing:.3px">'
        f'{status.upper()}</span>'
    )


def _request_card_html(title: str, subtitle: str, status: str, note: str = "") -> str:
    badge = _status_badge_html(status)
    note_html = (
        f'<div style="font-size:12px;color:#6b7280;margin-top:4px">{note}</div>'
        if note else ""
    )
    return (
        f'<div style="padding:12px 16px;border:1px solid #e5e7eb;border-radius:8px;'
        f'margin-bottom:8px;background:#fafafa">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<div><strong style="font-size:14px">{title}</strong>'
        f'<span style="font-size:13px;color:#6b7280;margin-left:8px">{subtitle}</span></div>'
        f'{badge}</div>{note_html}</div>'
    )


def _render_time_leave(emp: dict, company: dict):
    company_id = get_company_id()
    today      = date.today()

    # ── Leave balance cards ────────────────────────────────────────────────────
    policy      = company.get("leave_replenishment", "annual")
    p_start, _  = _leave_period_bounds(company, emp)
    policy_label = (
        "Annual — resets every Jan 1"
        if policy == "annual"
        else f"Anniversary — resets on hire date · current period from {p_start}"
    )
    balance, template = _get_leave_balance(emp["id"], company, emp)

    st.markdown("##### Leave Balance")

    # Show which template (or default) is in effect
    if template:
        st.caption(f"Template: **{template['name']}** &nbsp;·&nbsp; Policy: {policy_label}")
    else:
        st.caption(
            f"Policy: {policy_label} &nbsp;·&nbsp; "
            "_No leave template assigned — using company default. "
            "Contact HR to have a leave tier assigned to your account._"
        )

    b1, b2, b3 = st.columns(3)
    for col, (lt, info) in zip([b1, b2, b3], balance.items()):
        col.metric(
            f"{lt} · {_LEAVE_TYPES[lt]}",
            f"{info['remaining']:.1f} days left",
            delta=f"{info['used']:.1f} used of {info['total']} days",
            delta_color="inverse",
        )

    st.divider()

    # ── File a new request ─────────────────────────────────────────────────────
    st.markdown("##### File a New Request")
    req_type = st.radio(
        "Request type", ["🏖 Leave", "⏰ Overtime"],
        horizontal=True, key="portal_req_type", label_visibility="collapsed",
    )

    if req_type == "🏖 Leave":
        with st.form("leave_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([1.2, 1, 1])
            lt_key   = c1.selectbox(
                "Leave Type",
                list(_LEAVE_TYPES.keys()),
                format_func=lambda k: f"{k} — {_LEAVE_TYPES[k]}",
            )
            lv_start = c2.date_input("Start Date", value=today, min_value=today)
            lv_end   = c3.date_input("End Date",   value=today, min_value=today)
            reason   = st.text_area("Reason (optional)", placeholder="Brief reason…")
            submitted = st.form_submit_button("Submit Leave Request", type="primary", width='stretch')

        if submitted:
            if lv_end < lv_start:
                st.error("End date must be on or after the start date.")
            else:
                days = (lv_end - lv_start).days + 1
                remaining = balance[lt_key]["remaining"]  # balance is still in scope
                if days > remaining:
                    st.warning(
                        f"You have {remaining:.1f} {lt_key} days remaining but are requesting {days}. "
                        "HR will review — submit anyway if this is a special case."
                    )
                try:
                    get_db().table("leave_requests").insert({
                        "company_id": company_id,
                        "employee_id": emp["id"],
                        "leave_type": lt_key,
                        "start_date": lv_start.isoformat(),
                        "end_date":   lv_end.isoformat(),
                        "days":       days,
                        "reason":     reason.strip() or None,
                        "status":     "pending",
                    }).execute()
                    st.success(f"✅ Leave request filed for {days} day(s). HR will review shortly.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error: {ex}")

    else:
        with st.form("ot_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            ot_date    = c1.date_input("Date", value=today)
            ot_start   = c2.time_input("Start Time", value=datetime.time(17, 0), step=1800)
            ot_end     = c3.time_input("End Time",   value=datetime.time(20, 0), step=1800)
            reason_ot  = st.text_area("Reason", placeholder="Brief reason for overtime…")
            submitted_ot = st.form_submit_button("Submit OT Request", type="primary", width='stretch')

        if submitted_ot:
            start_dt = datetime.datetime.combine(ot_date, ot_start)
            end_dt   = datetime.datetime.combine(ot_date, ot_end)
            hours    = (end_dt - start_dt).total_seconds() / 3600
            if hours <= 0:
                st.error("End time must be after start time.")
            else:
                try:
                    get_db().table("overtime_requests").insert({
                        "company_id": company_id,
                        "employee_id": emp["id"],
                        "ot_date":     ot_date.isoformat(),
                        "start_time":  ot_start.strftime("%H:%M"),
                        "end_time":    ot_end.strftime("%H:%M"),
                        "hours":       round(hours, 1),
                        "reason":      reason_ot.strip() or None,
                        "status":      "pending",
                    }).execute()
                    st.success(f"✅ OT request filed for {hours:.1f} hour(s). HR will review shortly.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error: {ex}")

    st.divider()

    # ── Request history + Attendance ───────────────────────────────────────────
    st.markdown("##### Request History & Attendance")
    hist_leave, hist_ot, hist_dtr = st.tabs([
        "Leave Requests", "Overtime Requests", "⏱️ Attendance"
    ])

    with hist_leave:
        leave_reqs = _get_leave_requests(emp["id"])
        if not leave_reqs:
            st.caption("No leave requests filed yet.")
        else:
            for r in leave_reqs:
                title    = f"{r['leave_type']} — {_LEAVE_TYPES.get(r['leave_type'], r['leave_type'])}"
                days_lbl = f"{float(r['days']):.1g} day{'s' if float(r['days']) != 1 else ''}"
                subtitle = f"{r['start_date']} – {r['end_date']}  ({days_lbl})"
                note     = r.get("reason", "") or ""
                if r.get("admin_notes"):
                    note += f"  ·  HR note: {r['admin_notes']}"
                st.markdown(_request_card_html(title, subtitle, r["status"], note), unsafe_allow_html=True)

    with hist_ot:
        ot_reqs = _get_ot_requests(emp["id"])
        if not ot_reqs:
            st.caption("No overtime requests filed yet.")
        else:
            for r in ot_reqs:
                title    = "Overtime"
                subtitle = f"{r['ot_date']}  ·  {r['start_time']}–{r['end_time']}  ({r['hours']} hrs)"
                note     = r.get("reason", "") or ""
                if r.get("admin_notes"):
                    note += f"  ·  HR note: {r['admin_notes']}"
                st.markdown(_request_card_html(title, subtitle, r["status"], note), unsafe_allow_html=True)

    with hist_dtr:
        _render_employee_dtr(emp, company)


# ============================================================
# Section 4B: DTR / Attendance Sub-tab helpers
# ============================================================

def _load_own_time_logs(employee_id: str, start: date, end: date) -> list[dict]:
    return (
        get_db().table("time_logs")
        .select("*")
        .eq("employee_id", employee_id)
        .gte("work_date", str(start))
        .lte("work_date", str(end))
        .order("work_date", desc=True)
        .execute()
    ).data or []


def _load_active_locations() -> list[dict]:
    return (
        get_db().table("company_locations")
        .select("*")
        .eq("company_id", get_company_id())
        .eq("is_active", True)
        .execute()
    ).data or []


def _load_employee_schedules(emp: dict) -> tuple[dict, dict]:
    """Returns (schedules_dict, overrides_dict) for the employee."""
    schedules_rows = (
        get_db().table("schedules")
        .select("*")
        .eq("company_id", get_company_id())
        .execute()
    ).data or []
    schedules = {r["id"]: r for r in schedules_rows}
    return schedules, {}


def _upsert_portal_time_log(row: dict):
    existing = (
        get_db().table("time_logs")
        .select("id")
        .eq("employee_id", row["employee_id"])
        .eq("work_date", row["work_date"])
        .execute()
    ).data
    if existing:
        get_db().table("time_logs").update(row).eq("id", existing[0]["id"]).execute()
    else:
        row["company_id"] = get_company_id()
        get_db().table("time_logs").insert(row).execute()


def _submit_dtr_correction(employee_id: str, work_date: str, time_log_id: str | None,
                            req_in, req_out, reason: str):
    get_db().table("dtr_corrections").insert({
        "company_id":          get_company_id(),
        "employee_id":         employee_id,
        "time_log_id":         time_log_id,
        "work_date":           work_date,
        "requested_time_in":   str(req_in) if req_in else None,
        "requested_time_out":  str(req_out) if req_out else None,
        "reason":              reason,
    }).execute()


def _upload_snapshot(company_id: str, employee_id: str, work_date: date,
                     suffix: str, img_bytes: bytes) -> str | None:
    """
    Upload a face snapshot to Supabase Storage bucket 'dtr-snapshots'.
    Returns the public URL or None on failure.
    Bucket must be created in Supabase dashboard (Storage → New bucket → 'dtr-snapshots', public).
    """
    try:
        path = f"{company_id}/{employee_id}/{work_date}_{suffix}.jpg"
        get_db().storage.from_("dtr-snapshots").upload(
            path=path,
            file=img_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "true"},
        )
        return get_db().storage.from_("dtr-snapshots").get_public_url(path)
    except Exception:
        return None


def _fmt_time_portal(t) -> str:
    if t is None:
        return "—"
    if isinstance(t, str):
        return t[:5]
    return t.strftime("%H:%M")


def _dtr_status_badge(status: str) -> str:
    mapping = {
        "present":    ("✅ Present",    "#15803d", "#dcfce7"),
        "half_day":   ("½ Half Day",   "#92400e", "#fef3c7"),
        "absent":     ("❌ Absent",     "#b91c1c", "#fee2e2"),
        "on_leave":   ("🏖 On Leave",  "#1e40af", "#dbeafe"),
        "holiday":    ("🎉 Holiday",   "#6d28d9", "#ede9fe"),
        "rest_day":   ("😴 Rest Day",  "#475569", "#f1f5f9"),
        "no_schedule": ("— No Sched",  "#475569", "#f1f5f9"),
    }
    label, color, bg = mapping.get(status, ("? Unknown", "#6b7280", "#f3f4f6"))
    return (
        f'<span style="background:{bg};color:{color};padding:2px 10px;'
        f'border-radius:4px;font-size:12px;font-weight:600;">{label}</span>'
    )


@st.dialog("File DTR Correction")
def _correction_dialog(emp_id: str, log: dict):
    work_date = log["work_date"]
    st.caption(f"Correction request for **{work_date}**")
    st.text(f"Current Time In:  {_fmt_time_portal(log.get('time_in'))}")
    st.text(f"Current Time Out: {_fmt_time_portal(log.get('time_out'))}")
    st.divider()
    req_in  = st.time_input("Correct Time In",  value=datetime.time(8, 0))
    req_out = st.time_input("Correct Time Out", value=datetime.time(17, 0))
    reason  = st.text_area("Reason *", placeholder="e.g. Forgot to punch out, worked from site office")
    if st.button("Submit Correction", type="primary", width="stretch"):
        if not reason.strip():
            st.error("Please enter a reason.")
        else:
            try:
                _submit_dtr_correction(
                    emp_id, work_date, log.get("id"), req_in, req_out, reason.strip()
                )
                st.success("Correction request submitted. HR will review shortly.")
                st.rerun()
            except Exception as ex:
                st.error(f"Error: {ex}")


def _render_employee_dtr(emp: dict, company: dict):
    """DTR view + web clock-in/out for the employee portal."""
    today = date.today()
    emp_id = emp["id"]

    # ── Web Clock-In / Clock-Out ──────────────────────────────────────────────
    locations = _load_active_locations()
    if locations:
        st.markdown("#### Clock In / Clock Out")
        # Check if there's already a log for today
        today_log = (
            get_db().table("time_logs")
            .select("*")
            .eq("employee_id", emp_id)
            .eq("work_date", str(today))
            .execute()
        ).data
        today_log = today_log[0] if today_log else None

        has_in  = today_log and today_log.get("time_in")
        has_out = today_log and today_log.get("time_out")

        if has_in and has_out:
            st.success(
                f"✅ You've clocked in at **{_fmt_time_portal(today_log['time_in'])}** "
                f"and out at **{_fmt_time_portal(today_log['time_out'])}** today."
            )
        elif has_in:
            st.info(f"Clocked in at **{_fmt_time_portal(today_log['time_in'])}**. Remember to clock out!")
        else:
            st.info("You haven't clocked in yet today.")

        action = None
        if not has_in:
            action = "in"
        elif has_in and not has_out:
            action = "out"

        if action:
            btn_label = "🕐 Clock In" if action == "in" else "🕐 Clock Out"
            if st.button(btn_label, type="primary", key=f"dtr_clock_{action}"):
                st.session_state[f"dtr_show_clock_{action}"] = True

            if st.session_state.get(f"dtr_show_clock_{action}"):
                st.markdown(f"**Step 1 — Take a photo**")
                snapshot = st.camera_input("Face snapshot for verification",
                                           key=f"dtr_cam_{action}",
                                           label_visibility="collapsed")

                st.markdown("**Step 2 — Allow location access**")
                st.caption("Click Allow when your browser asks for location permission.")
                loc_data = get_location(key=f"dtr_geo_{action}")

                # Allow submit even without snapshot/location (graceful degradation)
                can_submit = True  # always allow, data stored if available
                if st.button("Confirm Clock " + ("In" if action == "in" else "Out"),
                             type="primary", key=f"dtr_confirm_{action}"):
                    now_utc = datetime.datetime.now(timezone.utc)
                    now_time = datetime.datetime.now().time()

                    # Upload snapshot
                    snapshot_url = None
                    if snapshot is not None:
                        img_bytes = snapshot.getvalue()
                        snapshot_url = _upload_snapshot(
                            get_company_id(), emp_id, today, action, img_bytes
                        )

                    # Process location
                    clat = clng = cdist = None
                    cloc_id = None
                    is_oor = False
                    if loc_data and not loc_data.get("error"):
                        clat = loc_data["lat"]
                        clng = loc_data["lng"]
                        nearest = nearest_location(clat, clng, locations)
                        if nearest:
                            cdist    = nearest["distance_m"]
                            cloc_id  = nearest["id"]
                            is_oor   = cdist > nearest["radius_m"]
                    elif loc_data and loc_data.get("error"):
                        st.warning(f"Location not available: {loc_data['error']}")

                    # Resolve schedule for DTR computation
                    schedules, overrides = _load_employee_schedules(emp)
                    sched = resolve_schedule_for_date(emp, schedules, overrides, today)

                    if action == "in":
                        log_row: dict = {
                            "employee_id":      emp_id,
                            "work_date":        str(today),
                            "time_in":          str(now_time.replace(microsecond=0)),
                            "time_in_at":       now_utc.isoformat(),
                            "time_in_method":   "portal",
                            "time_in_lat":      clat,
                            "time_in_lng":      clng,
                            "time_in_distance_m": cdist,
                            "time_in_location_id": cloc_id,
                            "time_in_snapshot_url": snapshot_url,
                            "is_out_of_range":  is_oor,
                        }
                        if sched:
                            log_row.update({
                                "schedule_id":    sched["id"],
                                "expected_start": str(_parse_time(sched["start_time"])),
                                "expected_end":   str(_parse_time(sched["end_time"])),
                                "expected_hours": schedule_expected_hours(sched),
                            })
                    else:
                        # Clock out — compute DTR
                        result = None
                        if today_log and today_log.get("time_in") and sched:
                            exp_h = schedule_expected_hours(sched)
                            result = compute_dtr(
                                _parse_time(today_log["time_in"]),
                                now_time.replace(microsecond=0),
                                _parse_time(sched["start_time"]),
                                _parse_time(sched["end_time"]),
                                exp_h,
                                int(sched.get("break_minutes", 60)),
                                bool(sched.get("is_overnight", False)),
                            )
                        log_row = {
                            "employee_id":       emp_id,
                            "work_date":         str(today),
                            "time_out":          str(now_time.replace(microsecond=0)),
                            "time_out_at":       now_utc.isoformat(),
                            "time_out_method":   "portal",
                            "time_out_lat":      clat,
                            "time_out_lng":      clng,
                            "time_out_distance_m": cdist,
                            "time_out_snapshot_url": snapshot_url,
                        }
                        if result:
                            log_row.update({
                                "gross_hours":        result.gross_hours,
                                "late_minutes":       result.late_minutes,
                                "undertime_minutes":  result.undertime_minutes,
                                "ot_hours":           result.ot_hours,
                                "status":             result.status,
                            })

                    try:
                        _upsert_portal_time_log(log_row)
                        if is_oor:
                            st.warning(
                                f"⚠️ Clocked {'in' if action == 'in' else 'out'} successfully, "
                                f"but you are **{cdist}m** from the nearest office location "
                                f"(allowed: {locations[0]['radius_m']}m). "
                                "HR will be notified."
                            )
                        else:
                            st.success(
                                f"✅ Clocked {'in' if action == 'in' else 'out'} at "
                                f"**{now_time.strftime('%H:%M')}**."
                            )
                        st.session_state.pop(f"dtr_show_clock_{action}", None)
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error saving time log: {ex}")

        st.divider()

    # ── DTR History Table ─────────────────────────────────────────────────────
    st.markdown("#### My Attendance Record")
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input("From", value=today - timedelta(days=30),
                                  key="dtr_portal_from")
    with col2:
        to_date = st.date_input("To", value=today, key="dtr_portal_to")

    logs = _load_own_time_logs(emp_id, from_date, to_date)

    if not logs:
        st.info("No attendance records found for this period.")
        return

    # Headers
    h_cols = [1.2, 1, 1.3, 1.3, 1, 1, 1.8, 1.5]
    hdr = st.columns(h_cols)
    for c, lbl in zip(hdr, ["Date", "Day", "Time In", "Time Out", "Late", "OT", "Status", "Action"]):
        c.markdown(f"**{lbl}**")

    for log in logs:
        d = date.fromisoformat(log["work_date"])
        row = st.columns(h_cols)
        row[0].text(d.strftime("%m/%d/%y"))
        row[1].text(d.strftime("%a"))
        row[2].text(_fmt_time_portal(log.get("time_in")))
        row[3].text(_fmt_time_portal(log.get("time_out")))
        lm = log.get("late_minutes") or 0
        row[4].text(f"{lm}m" if lm else "—")
        ot = float(log.get("ot_hours") or 0)
        row[5].text(f"{ot:.1f}h" if ot else "—")
        row[6].markdown(_dtr_status_badge(log.get("status", "absent")), unsafe_allow_html=True)
        with row[7]:
            if st.button("File Correction", key=f"dtr_corr_{log['id']}",
                         help="Request a correction for this day's record"):
                _correction_dialog(emp_id, log)

    # ── Corrections history ───────────────────────────────────────────────────
    st.divider()
    st.markdown("#### Correction Requests")
    corrections = (
        get_db().table("dtr_corrections")
        .select("*")
        .eq("employee_id", emp_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    ).data or []

    if not corrections:
        st.caption("No correction requests filed yet.")
    else:
        for c in corrections:
            status_color = {
                "pending":  "#92400e",
                "approved": "#15803d",
                "rejected": "#b91c1c",
            }.get(c["status"], "#6b7280")
            st.markdown(
                f'<div style="padding:10px;border-radius:6px;background:var(--gxp-surface2);'
                f'margin-bottom:8px;">'
                f'<b>{c["work_date"]}</b> &nbsp;·&nbsp; '
                f'<span style="color:{status_color};font-weight:600">{c["status"].upper()}</span>'
                f'<br/><small>Requested: In {_fmt_time_portal(c.get("requested_time_in"))} · '
                f'Out {_fmt_time_portal(c.get("requested_time_out"))}</small>'
                f'{"<br/><small>HR note: " + c["admin_notes"] + "</small>" if c.get("admin_notes") else ""}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ============================================================
# Section 5: Documents Tab
# ============================================================

def _render_documents(emp: dict, company: dict):
    st.markdown("##### Available Documents")
    st.caption(
        "Download official HR documents. "
        "These are generated from your current employment record."
    )

    # ── Certificate of Employment ──────────────────────────────────────────────
    st.markdown(
        '<div style="border:1px solid #e5e7eb;border-radius:10px;padding:20px 24px;'
        'margin-bottom:12px;background:#f9fafb;">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start">'
        '<div>'
        '<div style="font-size:15px;font-weight:700;color:#1f2937">📄 Certificate of Employment</div>'
        '<div style="font-size:13px;color:#6b7280;margin-top:4px">'
        'Confirms your current employment status, position, and start date. '
        'Accepted by banks, government agencies, and embassies.'
        '</div>'
        '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    _, btn_col1, btn_col2 = st.columns([2.5, 1, 1])
    from datetime import date as _date
    today_str = _date.today().isoformat()
    with btn_col1:
        try:
            coe_bytes = generate_coe_pdf(company, emp, include_salary=True)
            st.download_button(
                label="⬇ With Salary",
                data=coe_bytes,
                file_name=f"COE_{emp['employee_no']}_{today_str}_with_salary.pdf",
                mime="application/pdf",
                width='stretch',
                key="dl_coe_salary",
                help="Includes your basic salary amount",
            )
        except Exception as ex:
            st.error(f"Could not generate COE: {ex}")
    with btn_col2:
        try:
            coe_bytes = generate_coe_pdf(company, emp, include_salary=False)
            st.download_button(
                label="⬇ Without Salary",
                data=coe_bytes,
                file_name=f"COE_{emp['employee_no']}_{today_str}_no_salary.pdf",
                mime="application/pdf",
                width='stretch',
                key="dl_coe_no_salary",
                help="Does not disclose salary information",
            )
        except Exception as ex:
            st.error(f"Could not generate COE: {ex}")

    # ── BIR Form 2316 ─────────────────────────────────────────────────────────
    st.markdown(
        '<div style="border:1px solid #e5e7eb;border-radius:10px;padding:20px 24px;'
        'margin-bottom:12px;background:#f9fafb;">'
        '<div style="font-size:15px;font-weight:700;color:#1f2937">📋 BIR Form 2316</div>'
        '<div style="font-size:13px;color:#6b7280;margin-top:4px">'
        'Certificate of Compensation Payment / Tax Withheld. '
        'Required for annual income tax return filing.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    year_col, _ = st.columns([2, 5])
    with year_col:
        year_options = [date.today().year - i for i in range(0, 3)]
        sel_year = st.selectbox("Select Year", year_options, key="portal_bir2316_year")

    agg = _load_employee_annual(emp["id"], sel_year)

    if agg is None:
        st.info(f"No finalized payroll data found for {sel_year}.")
    else:
        _, dl_col = st.columns([3, 2])
        with dl_col:
            try:
                pdf_bytes = generate_bir2316_pdf(company, emp, agg, sel_year)
                st.download_button(
                    label=f"⬇ Download BIR 2316 ({sel_year})",
                    data=pdf_bytes,
                    file_name=f"BIR2316_{emp.get('employee_no', emp['id'])}_{sel_year}.pdf",
                    mime="application/pdf",
                    width='stretch',
                    key="dl_bir2316",
                )
            except Exception as ex:
                st.error(f"Could not generate BIR 2316: {ex}")

    st.divider()
    st.caption(
        "Need a document not listed here? Contact your HR department to request it."
    )


# ============================================================
# Main Render
# ============================================================

def render():
    inject_css()

    company = _load_company()
    emp = _get_employee_record()

    if not emp:
        st.error("Could not find your employee record. Please contact HR.")
        return

    _render_hero(emp, company)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    tab_profile, tab_payslips, tab_leave, tab_docs, tab_prefs = st.tabs([
        "My Profile", "My Payslips", "My Time & Leave", "My Documents", "Preferences",
    ])

    with tab_profile:
        profile = _get_profile(emp["id"])
        _render_profile_form(emp, profile)

    with tab_payslips:
        _render_payslips(emp, company)

    with tab_leave:
        _render_time_leave(emp, company)

    with tab_docs:
        _render_documents(emp, company)

    with tab_prefs:
        from app.pages.preferences import render as render_preferences
        render_preferences(standalone=False)
