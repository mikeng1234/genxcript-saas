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
    import time
    for attempt in range(3):
        try:
            db = get_db()
            result = db.table("companies").select("*").eq("id", get_company_id()).execute()
            return result.data[0] if result.data else {}
        except Exception:
            if attempt < 2:
                time.sleep(1)
            else:
                raise


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
            '<div style="font-size:32px;margin-bottom:12px"><span class="mdi mdi-file-document-outline" style="font-size:18px;"></span></div>'
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
        label        = f"{period_start} – {period_end}  ·  Net Pay: ₱{net:,.2f}"
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
                "Disbursement Account No. (HR)",
                value=emp.get("bank_account", "") or "",
                disabled=True,
                help="Bank, GCash, Maya, or other disbursement account. Managed by HR.",
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
        if "perm_copy_cb" not in st.session_state:
            st.session_state["perm_copy_cb"] = bool(p.get("perm_address_same", False))
        perm_same = st.checkbox("Copy from present address", key="perm_copy_cb")

        # When checked, pre-fill with present address values; user can still edit
        _pv_street = present_street if perm_same else (p.get("perm_address_street", "") or "")
        _pv_brgy   = present_barangay if perm_same else (p.get("perm_address_barangay", "") or "")
        _pv_city   = present_city if perm_same else (p.get("perm_address_city", "") or "")
        _pv_zip    = present_zip if perm_same else (p.get("perm_address_zip", "") or "")
        if perm_same:
            _pv_prov_idx = PROVINCES.index(present_province) if present_province in PROVINCES else 0
        else:
            _pv_prov_idx = (
                PROVINCES.index(p["perm_address_province"])
                if p.get("perm_address_province") in PROVINCES else 0
            )

        # Use different keys when checkbox toggles so values refresh properly
        _pk = "_cp" if perm_same else "_ed"
        col1, col2 = st.columns(2)
        with col1:
            perm_street = st.text_input(
                "House No. / Street / Subdivision",
                value=_pv_street,
                key=f"perm_str{_pk}",
            )
        with col2:
            perm_barangay = st.text_input(
                "Barangay",
                value=_pv_brgy,
                key=f"perm_brgy{_pk}",
            )
        col1, col2, col3 = st.columns(3)
        with col1:
            perm_city = st.text_input(
                "City / Municipality",
                value=_pv_city,
                key=f"perm_city{_pk}",
            )
        with col2:
            perm_province = st.selectbox("Province", PROVINCES, index=_pv_prov_idx, key=f"prov_perm{_pk}")
        with col3:
            perm_zip = st.text_input("ZIP Code", value=_pv_zip, key=f"perm_zip{_pk}")

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

# Special leave constants (Philippine statutory)
_SL_TYPE_INFO = {
    "ML":  ("Maternity Leave",   "RA 11210", "#be185d"),
    "PL":  ("Paternity Leave",   "RA 8187",  "#1d4ed8"),
    "SPL": ("Solo Parent Leave", "RA 8972",  "#7c3aed"),
}
_SL_DELIVERY_TYPE_INFO = {
    "normal":                "Normal / Vaginal delivery — 105 days",
    "caesarean":             "Caesarean section — 105 days",
    "miscarriage":           "Miscarriage / Stillbirth — 60 days",
    "emergency_termination": "Emergency termination of pregnancy — 60 days",
}
_SL_MAX_DAYS = {
    "normal": 105, "caesarean": 105, "miscarriage": 60, "emergency_termination": 60,
}


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


def _get_special_leave_requests(employee_id: str) -> list[dict]:
    db = get_db()
    return (
        db.table("special_leave_requests")
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
        "Request type", ["Leave", "Overtime", "Special Leave"],
        horizontal=True, key="portal_req_type", label_visibility="collapsed",
    )

    if req_type == "Leave":
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
                    st.success(f"Leave request filed for {days} day(s). HR will review shortly.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error: {ex}")

    elif req_type == "Overtime":
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
                    st.success(f"OT request filed for {hours:.1f} hour(s). HR will review shortly.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error: {ex}")

    else:  # Special Leave
        # ── Info panel with law reference ─────────────────────────────────────
        st.markdown(
            '<div style="background:#f8f7ff;border:1px solid #ddd6fe;border-radius:8px;'
            'padding:12px 16px;margin-bottom:12px;">'
            '<div style="font-size:13px;font-weight:700;color:#6d28d9;margin-bottom:6px;">'
            '⚖️ Philippine Statutory Special Leaves</div>'
            '<div style="font-size:12px;color:#374151;line-height:1.6;">'
            '<b>ML</b> — Maternity Leave (RA 11210): 105 days paid for normal/caesarean · 60 days for miscarriage<br>'
            '<b>PL</b> — Paternity Leave (RA 8187): 7 days paid · first 4 deliveries of spouse/partner<br>'
            '<b>SPL</b> — Solo Parent Leave (RA 8972): 7 days paid per year · requires DSWD Solo Parent ID'
            '</div></div>',
            unsafe_allow_html=True,
        )

        sl_type_code = st.selectbox(
            "Leave Type",
            options=["ML", "PL", "SPL"],
            format_func=lambda k: {
                "ML":  "ML — Maternity Leave (RA 11210)",
                "PL":  "PL — Paternity Leave (RA 8187)",
                "SPL": "SPL — Solo Parent Leave (RA 8972)",
            }[k],
            key="portal_sl_type_code",
        )

        with st.form("sl_form", clear_on_submit=True):
            # Declare all variables so they're always in scope after the with block
            delivery_type  = None
            delivery_date  = None
            partner_name   = None
            solo_parent_id = None
            sl_start       = today
            sl_end         = today

            if sl_type_code == "ML":
                st.caption("**Maternity Leave** — Submit with supporting medical certificate / birth certificate")
                c1, c2 = st.columns(2)
                delivery_type = c1.selectbox(
                    "Delivery Type *",
                    list(_SL_DELIVERY_TYPE_INFO.keys()),
                    format_func=lambda k: _SL_DELIVERY_TYPE_INFO[k],
                )
                delivery_date = c2.date_input("Expected / Actual Delivery Date")
                max_days = _SL_MAX_DAYS.get(delivery_type, 105)
                st.caption(f"Statutory entitlement: **{max_days} calendar days** paid leave")
                c3, c4 = st.columns(2)
                sl_start = c3.date_input("Leave Start Date", value=today)
                sl_end   = c4.date_input("Leave End Date",   value=today + timedelta(days=max_days - 1))

            elif sl_type_code == "PL":
                st.caption("**Paternity Leave** — Submit with birth certificate of child")
                c1, c2, c3, c4 = st.columns(4)
                partner_name  = c1.text_input("Spouse / Partner Name *")
                delivery_date = c2.date_input("Spouse's Delivery Date")
                sl_start      = c3.date_input("Leave Start Date", value=today)
                sl_end        = c4.date_input("Leave End Date",   value=today + timedelta(days=6))
                st.caption("Statutory entitlement: **7 calendar days** paid leave")

            else:  # SPL
                st.caption("**Solo Parent Leave** — Submit your DSWD-issued Solo Parent ID")
                c1, c2, c3 = st.columns(3)
                solo_parent_id = c1.text_input("Solo Parent ID No. *", placeholder="DSWD-issued card number")
                sl_start       = c2.date_input("Leave Start Date", value=today)
                sl_end         = c3.date_input("Leave End Date",   value=today + timedelta(days=6))
                st.caption("Statutory entitlement: **7 calendar days** paid per calendar year")

            reason    = st.text_area("Notes / Reason", placeholder="Optional notes to HR…")
            docs_note = st.text_input(
                "Supporting Documents",
                placeholder="e.g. Birth certificate submitted to HR on Mar 18, 2026",
            )
            submitted_sl = st.form_submit_button(
                "Submit Special Leave Request", type="primary", width="stretch"
            )

        if submitted_sl:
            days = (sl_end - sl_start).days + 1
            err  = None
            if sl_end < sl_start:
                err = "End date must be on or after the start date."
            elif sl_type_code == "PL"  and not (partner_name  or "").strip():
                err = "Please enter your spouse/partner's name."
            elif sl_type_code == "SPL" and not (solo_parent_id or "").strip():
                err = "Please enter your DSWD Solo Parent ID number."
            if err:
                st.error(err)
            else:
                try:
                    get_db().table("special_leave_requests").insert({
                        "company_id":           company_id,
                        "employee_id":          emp["id"],
                        "leave_type":           sl_type_code,
                        "delivery_type":        delivery_type,
                        "delivery_date":        delivery_date.isoformat() if delivery_date else None,
                        "partner_name":         (partner_name   or "").strip() or None,
                        "solo_parent_id":       (solo_parent_id or "").strip() or None,
                        "start_date":           sl_start.isoformat(),
                        "end_date":             sl_end.isoformat(),
                        "days":                 days,
                        "reason":               reason.strip() or None,
                        "supporting_docs_note": docs_note.strip() or None,
                        "status":               "pending",
                    }).execute()
                    st.success(
                        f"{sl_type_code} request filed for **{days} day(s)**. "
                        "HR will review shortly."
                    )
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error submitting request: {ex}")

    st.divider()

    # ── Request history + Attendance ───────────────────────────────────────────
    st.markdown("##### Request History & Attendance")
    hist_leave, hist_ot, hist_special, hist_dtr = st.tabs([
        "Leave Requests", "Overtime Requests", "Special Leave", "Attendance"
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

    with hist_special:
        sl_reqs = _get_special_leave_requests(emp["id"])
        if not sl_reqs:
            st.caption("No special leave requests filed yet.")
        else:
            for r in sl_reqs:
                lt       = r.get("leave_type", "—")
                lt_label, ra_ref, color = _SL_TYPE_INFO.get(lt, (lt, "", "#6b7280"))
                days_n   = float(r.get("days") or 0)
                days_lbl = f"{days_n:.0f} day{'s' if days_n != 1 else ''}"
                subtitle = f"{r['start_date']} – {r['end_date']}  ({days_lbl})"
                title    = f"{lt} — {lt_label}"

                # Build extra detail line
                extras = []
                if lt == "ML" and r.get("delivery_type"):
                    extras.append(_SL_DELIVERY_TYPE_INFO.get(r["delivery_type"], r["delivery_type"]))
                if lt == "PL" and r.get("partner_name"):
                    extras.append(f"Partner: {r['partner_name']}")
                if lt == "SPL" and r.get("solo_parent_id"):
                    extras.append(f"ID: {r['solo_parent_id']}")
                if r.get("delivery_date"):
                    extras.append(f"Delivery: {r['delivery_date']}")

                note = " · ".join(extras)
                if r.get("reason"):
                    note += ("  ·  " if note else "") + r["reason"]
                if r.get("admin_notes"):
                    note += f"  ·  HR note: {r['admin_notes']}"

                # Render card with colored left border per leave type
                status = r.get("status", "pending")
                s_color = _STATUS_COLOR.get(status, "#94a3b8")
                badge_html = (
                    f'<span style="background:{color};color:#fff;padding:2px 8px;'
                    f'border-radius:4px;font-size:11px;font-weight:700;margin-right:6px">{lt}</span>'
                    f'<span style="background:{s_color};color:#fff;padding:2px 8px;'
                    f'border-radius:4px;font-size:11px;font-weight:700">{status.upper()}</span>'
                )
                note_html = (
                    f'<div style="font-size:12px;color:#6b7280;margin-top:4px">{note}</div>'
                    if note else ""
                )
                st.markdown(
                    f'<div style="padding:12px 16px;border:1px solid #e5e7eb;'
                    f'border-left:4px solid {color};border-radius:8px;'
                    f'margin-bottom:8px;background:#fafafa">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<div><strong style="font-size:14px">{title}</strong>'
                    f'<span style="font-size:13px;color:#6b7280;margin-left:8px">{subtitle}</span></div>'
                    f'<div>{badge_html}</div></div>{note_html}</div>',
                    unsafe_allow_html=True,
                )

    with hist_dtr:
        _render_employee_dtr(emp, company)


# ============================================================
# Section 0: Employee Dashboard
# ============================================================

import calendar as _calendar

def _load_upcoming_holidays(company_id: str, n: int = 5) -> list[dict]:
    """Return next N holidays: national (company_id IS NULL) + company-specific."""
    today = date.today()
    # National holidays have company_id = NULL; company ones match company_id.
    # Use OR filter via PostgREST: `company_id=is.null,company_id=eq.<id>`
    return (
        get_db().table("holidays")
        .select("name, holiday_date, type")
        .or_(f"company_id.is.null,company_id.eq.{company_id}")
        .gte("holiday_date", str(today))
        .order("holiday_date")
        .limit(n)
        .execute()
    ).data or []


def _load_approved_vl_this_month(employee_id: str) -> set[str]:
    """Return set of date strings (YYYY-MM-DD) for approved VL days this month."""
    today = date.today()
    first = today.replace(day=1)
    last  = today.replace(day=_calendar.monthrange(today.year, today.month)[1])
    rows = (
        get_db().table("leave_requests")
        .select("leave_type, start_date, end_date")
        .eq("employee_id", employee_id)
        .eq("status", "approved")
        .gte("start_date", str(first))
        .lte("start_date", str(last))
        .execute()
    ).data or []
    vl_dates: set[str] = set()
    for r in rows:
        s = date.fromisoformat(r["start_date"])
        e = date.fromisoformat(r["end_date"]) if r.get("end_date") else s
        d = s
        while d <= e:
            vl_dates.add(str(d))
            d += timedelta(days=1)
    return vl_dates


def _load_holidays_this_month(company_id: str) -> dict[str, str]:
    """Return {date_str: holiday_name} for holidays this month (national + company)."""
    today = date.today()
    first = today.replace(day=1)
    last  = today.replace(day=_calendar.monthrange(today.year, today.month)[1])
    rows = (
        get_db().table("holidays")
        .select("holiday_date, name, type")
        .or_(f"company_id.is.null,company_id.eq.{company_id}")
        .gte("holiday_date", str(first))
        .lte("holiday_date", str(last))
        .execute()
    ).data or []
    return {r["holiday_date"]: r["name"] for r in rows}


def _mini_calendar_html(year: int, month: int,
                         vl_dates: set[str],
                         holiday_dates: dict[str, str],
                         today: date) -> str:
    """Render a month mini-calendar as HTML. VL = green, Holiday = purple, Today = blue ring."""
    _week_pref = st.session_state.get("gxp_week_start", "Sunday")
    _first_day = 6 if _week_pref == "Sunday" else 0
    cal = _calendar.Calendar(firstweekday=_first_day)
    weeks = cal.monthdatescalendar(year, month)
    month_name = date(year, month, 1).strftime("%B %Y")

    rows = ""
    for week in weeks:
        row = ""
        for d in week:
            ds = str(d)
            is_today    = d == today
            is_vl       = ds in vl_dates
            is_holiday  = ds in holiday_dates
            is_other    = d.month != month

            if is_other:
                cell_bg, cell_color, fw = "transparent", "#d1d5db", "400"
                border = "none"
            elif is_holiday:
                cell_bg, cell_color, fw = "#ede9fe", "#6d28d9", "700"
                border = "2px solid #7c3aed" if is_today else "none"
            elif is_vl:
                cell_bg, cell_color, fw = "#dcfce7", "#15803d", "700"
                border = "2px solid #16a34a" if is_today else "none"
            elif is_today:
                cell_bg, cell_color, fw = "#eff6ff", "#1d4ed8", "700"
                border = "2px solid #3b82f6"
            else:
                cell_bg, cell_color, fw = "transparent", "var(--gx-text)", "400"
                border = "none"

            title = holiday_dates.get(ds, "VL" if is_vl else "")
            row += (
                f'<td title="{title}" style="'
                f'padding:4px 2px;text-align:center;font-size:12px;'
                f'background:{cell_bg};color:{cell_color};font-weight:{fw};'
                f'border-radius:6px;border:{border};cursor:default;">'
                f'{d.day}</td>'
            )
        rows += f"<tr>{row}</tr>"

    legend = (
        '<div style="display:flex;gap:12px;margin-top:8px;font-size:11px;">'
        '<span><span style="display:inline-block;width:10px;height:10px;background:#dcfce7;border-radius:3px;margin-right:3px;border:1px solid #16a34a"></span>VL</span>'
        '<span><span style="display:inline-block;width:10px;height:10px;background:#ede9fe;border-radius:3px;margin-right:3px;border:1px solid #7c3aed"></span>Holiday</span>'
        '<span><span style="display:inline-block;width:10px;height:10px;background:#eff6ff;border-radius:3px;margin-right:3px;border:1px solid #3b82f6"></span>Today</span>'
        '</div>'
    )

    return (
        f'<div style="background:var(--gx-card-bg,#fff);border:1px solid var(--gx-border,#e5e7eb);'
        f'border-radius:12px;padding:14px 16px;">'
        f'<div style="font-weight:700;font-size:13px;margin-bottom:8px;color:var(--gx-text)">{month_name}</div>'
        f'<table style="width:100%;border-collapse:separate;border-spacing:2px 2px;">'
        f'<thead><tr>'
        + "".join(
            f'<th style="font-size:11px;color:#6b7280;font-weight:600;text-align:center;padding-bottom:4px;">{d}</th>'
            for d in (["Su","Mo","Tu","We","Th","Fr","Sa"] if _week_pref == "Sunday" else ["Mo","Tu","We","Th","Fr","Sa","Su"])
        )
        + f'</tr></thead><tbody>{rows}</tbody></table>'
        + legend
        + '</div>'
    )


def _render_clock_widget(
    emp: dict,
    today_log: dict | None,
    locations: list[dict],
    key_prefix: str,
) -> None:
    """
    Reusable Clock In / Clock Out widget.
    Renders a status card + inline camera/geolocation flow.
    key_prefix differentiates session-state keys when the widget
    is placed on both the Dashboard and the Attendance tab.
    """
    today    = date.today()
    emp_id   = emp["id"]
    has_in        = today_log and today_log.get("time_in")
    has_out       = today_log and today_log.get("time_out")
    has_break_out = bool(today_log and today_log.get("break_out"))
    has_break_in  = bool(today_log and today_log.get("break_in"))
    on_break      = has_break_out and not has_break_in

    # ── Status badge ────────────────────────────────────────────
    if has_in and has_out:
        status_html = (
            f'<span style="color:#16a34a;font-weight:600;"><span class="mdi mdi-check-circle" style="font-size:18px;color:#22c55e;"></span> Clocked in '
            f'{_fmt_time_portal(today_log["time_in"])} · '
            f'Out {_fmt_time_portal(today_log["time_out"])}</span>'
        )
        action = None
    elif has_in:
        if on_break:
            status_html = (
                f'<span style="color:#d97706;font-weight:600;">'
                f'<span class="mdi mdi-coffee" style="font-size:18px;color:#d97706;"></span>'
                f' On break since {_fmt_time_portal(today_log["break_out"])}'
                f' (in at {_fmt_time_portal(today_log["time_in"])}) — tap End Break when back!</span>'
            )
        else:
            status_html = (
                f'<span style="color:#2563eb;font-weight:600;">'
                f'<span class="mdi mdi-check-circle" style="font-size:18px;color:#22c55e;"></span> Clocked in at {_fmt_time_portal(today_log["time_in"])} '
                f'— remember to clock out!</span>'
            )
        action = "out"
    else:
        status_html = '<span style="color:#9ca3af;"><span class="mdi mdi-clock-outline" style="font-size:18px;color:#9ca3af;"></span> Not clocked in yet today</span>'
        action = "in"

    # ── Card header ─────────────────────────────────────────────
    st.markdown(
        f'<div style="background:var(--gx-card-bg,#fff);'
        f'border:1px solid var(--gx-border,#e5e7eb);border-radius:12px;'
        f'padding:14px 18px;margin-bottom:4px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<div style="font-size:12px;font-weight:700;color:#6b7280;"><span class="mdi mdi-clock-outline" style="font-size:18px;"></span> TODAY\'S ATTENDANCE</div>'
        f'<div style="font-size:12px;color:#9ca3af;">{today.strftime("%a, %B %d")}</div>'
        f'</div>'
        f'<div style="font-size:13px;margin-top:8px;">{status_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not action:
        return   # both punches done — nothing more to show

    # ── Break tracking (visible when clocked in, not yet clocked out) ────────────
    if action == "out":
        if on_break:
            # Employee is currently on break — show End Break button prominently
            break_since = _fmt_time_portal(today_log.get("break_out"))
            st.info(
                f"☕ You are on break since **{break_since}**. "
                "Tap **End Break** when you return.",
                icon="☕",
            )
            if st.button(
                "☕ End Break",
                type="primary",
                key=f"{key_prefix}_break_in_btn",
                use_container_width=True,
            ):
                _now_utc_brk  = datetime.datetime.now(timezone.utc)
                _now_time_brk = datetime.datetime.now().time().replace(microsecond=0)
                try:
                    _bo_parsed   = _parse_time(today_log["break_out"])
                    _bo_min      = _bo_parsed.hour * 60 + _bo_parsed.minute
                    _bi_min      = _now_time_brk.hour * 60 + _now_time_brk.minute
                    _actual_brk  = max(0, _bi_min - _bo_min)
                    _scheds_brk, _ = _load_employee_schedules(emp)
                    _sched_brk   = resolve_schedule_for_date(emp, _scheds_brk, {}, today)
                    _exp_brk     = int(_sched_brk.get("break_minutes", 60)) if _sched_brk else 60
                    _overbrk     = max(0, _actual_brk - _exp_brk)
                    _upsert_portal_time_log({
                        "employee_id":          emp_id,
                        "work_date":            str(today),
                        "break_in":             str(_now_time_brk),
                        "break_in_at":          _now_utc_brk.isoformat(),
                        "actual_break_minutes": _actual_brk,
                        "overbreak_minutes":    _overbrk,
                    })
                    _brk_msg = f"Break ended at **{_now_time_brk.strftime('%H:%M')}** · {_actual_brk} min"
                    if _overbrk > 0:
                        st.warning(f"{_brk_msg} (**{_overbrk} min overbreak**)")
                    else:
                        st.success(_brk_msg)
                    st.rerun()
                except Exception as _brk_ex:
                    st.error(f"Error saving break end: {_brk_ex}")
            st.markdown("---")
        elif not has_break_out:
            # Not yet on break — offer a one-click Start Break button (secondary)
            if st.button(
                "☕ Start Break",
                key=f"{key_prefix}_break_out_btn",
                use_container_width=True,
            ):
                _now_utc_bo  = datetime.datetime.now(timezone.utc)
                _now_time_bo = datetime.datetime.now().time().replace(microsecond=0)
                try:
                    _upsert_portal_time_log({
                        "employee_id":  emp_id,
                        "work_date":    str(today),
                        "break_out":    str(_now_time_bo),
                        "break_out_at": _now_utc_bo.isoformat(),
                    })
                    st.success(f"Break started at **{_now_time_bo.strftime('%H:%M')}**.")
                    st.rerun()
                except Exception as _bo_ex:
                    st.error(f"Error saving break start: {_bo_ex}")
        else:
            # Break already completed — show summary caption
            _brk_done_min = today_log.get("actual_break_minutes") or 0
            _obk_done_min = today_log.get("overbreak_minutes") or 0
            if _obk_done_min > 0:
                st.caption(f"☕ Break: {_brk_done_min} min · ⚠️ {_obk_done_min} min overbreak")
            else:
                st.caption(f"☕ Break taken: {_brk_done_min} min")
        st.markdown("---")

    # ── Permission notice + button ───────────────────────────────
    st.info(
        "Tap **Clock In/Out** below — you'll be asked to take a photo "
        "and allow location access for on-site verification.",
        icon="ℹ️",
    )

    btn_label = "Clock In" if action == "in" else "Clock Out"
    show_key  = f"{key_prefix}_show_clock_{action}"

    if st.button(btn_label, type="primary", key=f"{key_prefix}_clock_{action}_btn",
                 use_container_width=True):
        st.session_state[show_key] = True

    if not st.session_state.get(show_key):
        return

    # ── Expanded clock flow ──────────────────────────────────────
    st.markdown("---")

    # Photo — use file_uploader instead of camera_input so it works on
    # iOS Chrome over HTTP (st.camera_input requires HTTPS on non-localhost).
    # On mobile, tapping the upload button shows "Take Photo" natively.
    st.markdown("**Step 1 — Take a selfie**")
    st.caption("Tap the button below → choose **Take Photo** (front camera) for verification.")
    snapshot = st.file_uploader(
        "Selfie for verification",
        type=["jpg", "jpeg", "png"],
        key=f"{key_prefix}_cam_{action}",
        label_visibility="collapsed",
        accept_multiple_files=False,
    )

    # ── Persist photo bytes in session_state immediately on upload ───────────
    # st.file_uploader can return None on the rerun triggered by button press,
    # so we cache the raw bytes as soon as the user uploads the photo.
    _img_bytes_key = f"{key_prefix}_img_bytes_{action}"
    if snapshot is not None:
        st.session_state[_img_bytes_key] = snapshot.getvalue()
    _cached_img_bytes = st.session_state.get(_img_bytes_key)

    if _cached_img_bytes:
        st.image(_cached_img_bytes, width=180, caption="Preview")

    # ── Try to extract GPS from photo EXIF (works on HTTP, no browser API) ──
    _exif_key = f"{key_prefix}_exif_gps_{action}"
    if _cached_img_bytes:
        _exif_result = _extract_exif_gps(_cached_img_bytes)
        if _exif_result:
            st.session_state[_exif_key] = _exif_result
        else:
            st.session_state.pop(_exif_key, None)
    elif not st.session_state.get(f"{key_prefix}_show_clock_{action}"):
        st.session_state.pop(_exif_key, None)
        st.session_state.pop(_img_bytes_key, None)

    # ── Location section: EXIF GPS → auto-detect → fallback to manual pick ─
    st.markdown("**Step 2 — Verify your location**")
    company_locations = locations  # office locations for map display

    # Session keys
    _geo_retry_key  = f"{key_prefix}_geo_retry_{action}"
    _manual_loc_key = f"{key_prefix}_manual_loc_{action}"
    if _geo_retry_key not in st.session_state:
        st.session_state[_geo_retry_key] = 0

    # ── Priority 1: GPS from photo EXIF ──────────────────────────
    _exif_gps = st.session_state.get(_exif_key)
    if _exif_gps:
        _lat, _lng = _exif_gps
        st.success(
            f"**Location from photo** — GPS embedded in the image "
            f"({_lat:.6f}, {_lng:.6f})"
        )
        _render_clockin_map(_lat, _lng, company_locations)
        st.caption(
            "Your phone's camera embedded GPS in this photo. "
            "If the pin looks wrong, remove the photo and upload a fresh one taken on-site."
        )
        # EXIF GPS found — skip the rest of the location logic
        loc_data = None
        _geo_ok  = False
    else:
        # ── Priority 2: Browser geolocation (needs HTTPS) ────────
        _geo_comp_key = f"{key_prefix}_geo_{action}_{st.session_state[_geo_retry_key]}"
        loc_data = get_location(key=_geo_comp_key)

        _geo_ok = loc_data is not None and not loc_data.get("error")

        if _geo_ok:
            # Auto-detect succeeded
            _lat, _lng = loc_data["lat"], loc_data["lng"]
            _acc = loc_data.get("accuracy") or 0
            st.success(f"Location captured automatically — accuracy ±{_acc:.0f} m")
            _render_clockin_map(_lat, _lng, company_locations)
            st.session_state.pop(_manual_loc_key, None)

        else:
            # ── Priority 3: Manual location picker ───────────────
            if loc_data is None:
                st.caption("⏳ Fetching location automatically…")
            else:
                st.warning(
                    "**Automatic location blocked by browser.**\n\n"
                    "This happens on local networks (HTTP). Try one of:\n"
                    "- **Enable location in camera app** so the photo contains GPS, or\n"
                    "- **Select your office** below, or\n"
                    "- Use **ngrok / HTTPS** for full GPS capture.",
                )

            col_retry, col_manual = st.columns([1, 1])
            with col_retry:
                if st.button("Retry Auto-detect",
                             key=f"{key_prefix}_geo_retry_btn_{action}",
                             use_container_width=True):
                    st.session_state[_geo_retry_key] += 1
                    st.session_state.pop(_manual_loc_key, None)
                    st.rerun()

            loc_options = {loc["name"]: loc for loc in locations}
            loc_names   = ["— Select office location —"] + list(loc_options.keys())
            with col_manual:
                _sel = st.selectbox(
                    "Select location",
                    loc_names,
                    key=f"{key_prefix}_loc_select_{action}",
                    label_visibility="collapsed",
                )
            if _sel and _sel != "— Select office location —":
                st.session_state[_manual_loc_key] = loc_options[_sel]
                st.info(f"Manual location selected: **{_sel}**")

    if st.button(
        f"Confirm Clock {'In' if action == 'in' else 'Out'}",
        type="primary",
        key=f"{key_prefix}_confirm_{action}",
        use_container_width=True,
    ):
        now_utc  = datetime.datetime.now(timezone.utc)
        now_time = datetime.datetime.now().time().replace(microsecond=0)

        # Upload snapshot using cached bytes (persisted across the button-press rerun)
        snapshot_url = None
        _img_bytes_to_upload = st.session_state.get(_img_bytes_key)
        if _img_bytes_to_upload:
            with st.spinner("Uploading photo…"):
                snapshot_url = _upload_snapshot(
                    get_company_id(), emp_id, today, action, _img_bytes_to_upload
                )
            if snapshot_url is None:
                st.warning(
                    "Photo upload failed — clock-in will save without photo. "
                    "Check that the **dtr-snapshots** storage bucket exists and is set to **Public**."
                )

        # Process location — priority: EXIF GPS → browser auto-detect → manual pick
        clat = clng = cdist = cloc_id = None
        is_oor = False
        _manual_loc  = st.session_state.get(_manual_loc_key)
        _exif_gps_cv = st.session_state.get(_exif_key)   # confirmed EXIF coords

        if _exif_gps_cv:
            # Best: GPS embedded in the uploaded photo
            clat, clng = _exif_gps_cv
            nearest = nearest_location(clat, clng, locations)
            if nearest:
                cdist   = nearest["distance_m"]
                cloc_id = nearest["id"]
                is_oor  = cdist > nearest["radius_m"]
        elif _geo_ok:
            # Good: browser geolocation (requires HTTPS)
            clat, clng = loc_data["lat"], loc_data["lng"]
            nearest = nearest_location(clat, clng, locations)
            if nearest:
                cdist   = nearest["distance_m"]
                cloc_id = nearest["id"]
                is_oor  = cdist > nearest["radius_m"]
        elif _manual_loc:
            # Fallback: employee manually selected their office
            cloc_id = _manual_loc["id"]
            is_oor  = False   # trusted: employee consciously chose their site

        # Resolve schedule
        schedules, overrides = _load_employee_schedules(emp)
        sched = resolve_schedule_for_date(emp, schedules, overrides, today)

        if action == "in":
            log_row: dict = {
                "employee_id":          emp_id,
                "work_date":            str(today),
                "time_in":              str(now_time),
                "time_in_at":           now_utc.isoformat(),
                "time_in_method":       "portal",
                "time_in_lat":          clat,
                "time_in_lng":          clng,
                "time_in_distance_m":   cdist,
                "time_in_location_id":  cloc_id,
                "time_in_snapshot_url": snapshot_url,
                "is_out_of_range":      is_oor,
            }
            if sched:
                log_row.update({
                    "schedule_id":    sched["id"],
                    "expected_start": str(_parse_time(sched["start_time"])),
                    "expected_end":   str(_parse_time(sched["end_time"])),
                    "expected_hours": schedule_expected_hours(sched),
                })
        else:
            result = None
            if today_log and today_log.get("time_in") and sched:
                result = compute_dtr(
                    _parse_time(today_log["time_in"]),
                    now_time,
                    _parse_time(sched["start_time"]),
                    _parse_time(sched["end_time"]),
                    schedule_expected_hours(sched),
                    int(sched.get("break_minutes", 60)),
                    bool(sched.get("is_overnight", False)),
                )
            log_row = {
                "employee_id":           emp_id,
                "work_date":             str(today),
                "time_out":              str(now_time),
                "time_out_at":           now_utc.isoformat(),
                "time_out_method":       "portal",
                "time_out_lat":          clat,
                "time_out_lng":          clng,
                "time_out_distance_m":   cdist,
                "time_out_snapshot_url": snapshot_url,
            }
            if result:
                log_row.update({
                    "gross_hours":       result.gross_hours,
                    "late_minutes":      result.late_minutes,
                    "undertime_minutes": result.undertime_minutes,
                    "ot_hours":          result.ot_hours,
                    "status":            result.status,
                })

        try:
            _upsert_portal_time_log(log_row)
            if is_oor:
                st.warning(
                    f"Clocked {'in' if action == 'in' else 'out'} at "
                    f"**{now_time.strftime('%H:%M')}**, but you are **{cdist}m** "
                    f"from the nearest office (allowed: {locations[0]['radius_m']}m). "
                    "HR will be notified."
                )
            else:
                st.success(
                    f"Clocked {'in' if action == 'in' else 'out'} at "
                    f"**{now_time.strftime('%H:%M')}**."
                )
            st.session_state.pop(show_key, None)
            st.session_state.pop(_img_bytes_key, None)
            st.session_state.pop(_exif_key, None)
            st.rerun()
        except Exception as ex:
            st.error(f"Error saving time log: {ex}")


def _render_dashboard(emp: dict, company: dict):
    """Employee portal landing dashboard."""
    today = date.today()
    greeting_hour = datetime.datetime.now().hour
    greeting = "Good morning" if greeting_hour < 12 else ("Good afternoon" if greeting_hour < 18 else "Good evening")
    first_name = emp.get("first_name", "")

    st.markdown(
        f'<div style="font-size:20px;font-weight:700;margin-bottom:4px;">'
        f'{greeting}, {first_name}! <span class="mdi mdi-hand-wave" style="font-size:18px;"></span></div>'
        f'<div style="font-size:13px;color:#6b7280;margin-bottom:16px;">'
        f'{today.strftime("%A, %B %d, %Y")}</div>',
        unsafe_allow_html=True,
    )

    # ── Clock In / Clock Out widget ────────────────────────────
    _dash_locations = _load_active_locations()
    if _dash_locations:
        _dash_today_log_rows = (
            get_db().table("time_logs")
            .select("*")
            .eq("employee_id", emp["id"])
            .eq("work_date", str(today))
            .execute()
        ).data or []
        _dash_today_log = _dash_today_log_rows[0] if _dash_today_log_rows else None
        _render_clock_widget(emp, _dash_today_log, _dash_locations, key_prefix="dash")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Row 1: Leave balance cards + upcoming holiday ─────────
    col_vl, col_sl, col_cl, col_holiday = st.columns([1, 1, 1, 1.4])

    balance, _ = _get_leave_balance(emp["id"], company, emp)

    def _leave_card(col, leave_type: str, icon: str, bg: str, accent: str):
        b = balance.get(leave_type, {"remaining": 0, "total": 0, "used": 0})
        pct = int((b["used"] / b["total"] * 100)) if b["total"] else 0
        bar_w = max(4, min(100, pct))
        col.markdown(
            f'<div style="background:{bg};border-radius:12px;padding:14px 16px;height:100%;">'
            f'<div style="font-size:20px">{icon}</div>'
            f'<div style="font-size:22px;font-weight:800;color:{accent};margin:4px 0;">'
            f'{b["remaining"]:.0f}<span style="font-size:13px;font-weight:500;color:#6b7280"> / {b["total"]:.0f} days</span></div>'
            f'<div style="font-size:12px;color:#6b7280;font-weight:600;">{leave_type} Balance</div>'
            f'<div style="margin-top:8px;height:4px;background:#e5e7eb;border-radius:4px;">'
            f'<div style="width:{bar_w}%;height:4px;background:{accent};border-radius:4px;opacity:.7;"></div></div>'
            f'<div style="font-size:11px;color:#9ca3af;margin-top:3px;">{pct}% used</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _leave_card(col_vl, "VL", '<span class="mdi mdi-tree" style="font-size:18px;"></span>', "#f0fdf4", "#16a34a")
    _leave_card(col_sl, "SL", '<span class="mdi mdi-hospital-box" style="font-size:18px;"></span>', "#eff6ff", "#2563eb")
    _leave_card(col_cl, "CL", '<span class="mdi mdi-auto-fix" style="font-size:18px;"></span>', "#fdf4ff", "#9333ea")

    # Upcoming holidays card
    upcoming = _load_upcoming_holidays(company["id"], n=4)
    _HTYPE_COLORS = {
        "regular":             ("#fee2e2", "#dc2626"),
        "special_non_working": ("#fef9c3", "#ca8a04"),
        "special_working":     ("#dbeafe", "#2563eb"),
    }
    if upcoming:
        holiday_html = ""
        for h in upcoming:
            hdate = date.fromisoformat(h["holiday_date"])
            days_away = (hdate - today).days
            label = "Today" if days_away == 0 else ("Tomorrow" if days_away == 1 else f"In {days_away}d")
            bg, accent = _HTYPE_COLORS.get(h.get("type", "regular"), ("#f3f4f6", "#374151"))
            holiday_html += (
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
                f'<div style="background:{bg};color:{accent};font-size:10px;font-weight:700;'
                f'padding:2px 6px;border-radius:6px;white-space:nowrap;">{label}</div>'
                f'<div style="font-size:12px;color:var(--gx-text);flex:1;overflow:hidden;'
                f'text-overflow:ellipsis;white-space:nowrap;" title="{h["name"]}">{h["name"]}</div>'
                f'</div>'
            )
        col_holiday.markdown(
            f'<div style="background:var(--gx-card-bg,#fff);border:1px solid var(--gx-border,#e5e7eb);'
            f'border-radius:12px;padding:14px 16px;height:100%;">'
            f'<div style="font-size:12px;font-weight:700;color:#6b7280;margin-bottom:10px;"><span class="mdi mdi-calendar-today" style="font-size:18px;"></span> UPCOMING HOLIDAYS</div>'
            + holiday_html
            + '</div>',
            unsafe_allow_html=True,
        )
    else:
        col_holiday.markdown(
            '<div style="background:var(--gx-card-bg,#fff);border:1px solid var(--gx-border,#e5e7eb);'
            'border-radius:12px;padding:14px 16px;height:100%;">'
            '<div style="font-size:12px;font-weight:700;color:#6b7280;margin-bottom:8px;"><span class="mdi mdi-calendar-today" style="font-size:18px;"></span> UPCOMING HOLIDAYS</div>'
            '<div style="font-size:12px;color:#9ca3af;">No upcoming holidays.</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Row 2: Latest pay breakdown + mini calendar ────────────
    col_pay, col_cal = st.columns([1.3, 1])

    with col_pay:
        payslips = _get_payslips(emp["id"])
        if payslips:
            latest = payslips[0]
            pp = latest.get("pay_periods") or {}
            period_label = f"{pp.get('period_start','')} → {pp.get('period_end','')}"
            gross = _p(latest.get("gross_pay") or 0)
            net   = _p(latest.get("net_pay")   or 0)
            deductions = gross - net

            # Mini bar chart using HTML proportional bars
            items = [
                ("Basic Pay",     _p(latest.get("basic_pay")    or 0), "#3b82f6"),
                ("OT / Other",    _p(latest.get("overtime_pay") or 0) + _p(latest.get("holiday_pay") or 0), "#10b981"),
                ("Deductions",    deductions, "#ef4444"),
                ("Net Pay",       net,        "#8b5cf6"),
            ]
            max_val = max(v for _, v, _ in items) or 1
            bars = ""
            for label, val, color in items:
                if val <= 0:
                    continue
                w = max(4, int(val / max_val * 100))
                bars += (
                    f'<div style="margin-bottom:8px;">'
                    f'<div style="display:flex;justify-content:space-between;font-size:11px;'
                    f'color:#6b7280;margin-bottom:2px;"><span>{label}</span>'
                    f'<span style="font-weight:600;color:var(--gx-text);">₱{val:,.2f}</span></div>'
                    f'<div style="height:8px;background:#f3f4f6;border-radius:4px;">'
                    f'<div style="width:{w}%;height:8px;background:{color};border-radius:4px;"></div>'
                    f'</div></div>'
                )

            st.markdown(
                f'<div style="background:var(--gx-card-bg,#fff);border:1px solid var(--gx-border,#e5e7eb);'
                f'border-radius:12px;padding:16px 18px;">'
                f'<div style="font-size:12px;font-weight:700;color:#6b7280;margin-bottom:4px;"><span class="mdi mdi-cash-multiple" style="font-size:18px;"></span> LATEST PAY BREAKDOWN</div>'
                f'<div style="font-size:11px;color:#9ca3af;margin-bottom:12px;">{period_label}</div>'
                + bars
                + f'<div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--gx-border,#e5e7eb);'
                f'display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="font-size:12px;color:#6b7280;">Net Pay</span>'
                f'<span style="font-size:18px;font-weight:800;color:#16a34a;">₱{net:,.2f}</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:var(--gx-card-bg,#fff);border:1px solid var(--gx-border,#e5e7eb);'
                'border-radius:12px;padding:32px 18px;text-align:center;">'
                '<div style="font-size:24px"><span class="mdi mdi-cash-multiple" style="font-size:18px;"></span></div>'
                '<div style="font-size:13px;color:#6b7280;margin-top:8px;">No payslips yet.</div>'
                '</div>',
                unsafe_allow_html=True,
            )

    with col_cal:
        vl_dates      = _load_approved_vl_this_month(emp["id"])
        holiday_dates = _load_holidays_this_month(company["id"])
        cal_html = _mini_calendar_html(today.year, today.month, vl_dates, holiday_dates, today)
        st.markdown(cal_html, unsafe_allow_html=True)


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


def _render_clockin_map(emp_lat: float, emp_lng: float, office_locations: list[dict]):
    """Render Leaflet map showing employee position + office geofences."""
    import json
    import streamlit.components.v1 as _stc_map

    offices_json = json.dumps([
        {
            "name": loc["name"],
            "lat": float(loc["latitude"]),
            "lng": float(loc["longitude"]),
            "radius": int(loc.get("radius_m", 100)),
        }
        for loc in office_locations
    ])

    # Check if employee is within any geofence
    nearest = None
    min_dist = float("inf")
    for loc in office_locations:
        d = haversine_distance_m(emp_lat, emp_lng, float(loc["latitude"]), float(loc["longitude"]))
        if d < min_dist:
            min_dist = d
            nearest = loc

    in_range = min_dist <= int(nearest.get("radius_m", 100)) if nearest else False
    status_color = "#16a34a" if in_range else "#dc2626"
    status_text = "Inside geofence" if in_range else f"Outside — {min_dist:.0f}m from nearest office"

    _stc_map.html(f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; padding:0; font-family:'Plus Jakarta Sans',system-ui,sans-serif; }}
  #map {{ width:100%; height:100%; border-radius:12px; }}
  .status-badge {{
    position:absolute; bottom:10px; left:10px; z-index:999;
    background:white; padding:6px 12px; border-radius:9999px;
    font-size:11px; font-weight:700; box-shadow:0 2px 8px rgba(0,0,0,0.15);
    display:flex; align-items:center; gap:6px;
  }}
</style>
</head>
<body>
<div id="map"></div>
<script>
var empLat = {emp_lat}, empLng = {emp_lng};
var offices = {offices_json};
var inRange = {'true' if in_range else 'false'};

var map = L.map('map', {{
  center: [empLat, empLng],
  zoom: 16,
  zoomControl: true,
}});

L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '&copy; OSM',
  maxZoom: 19,
}}).addTo(map);

// Employee position — pulsing blue dot
var empIcon = L.divIcon({{
  className: '',
  html: '<div style="width:16px;height:16px;border-radius:50%;background:#005bc1;'
    +'border:3px solid white;box-shadow:0 0 0 3px rgba(0,91,193,0.3),0 0 12px rgba(0,91,193,0.4);'
    +'animation:pulse 2s infinite;"></div>'
    +'<style>@keyframes pulse{{0%,100%{{box-shadow:0 0 0 3px rgba(0,91,193,0.3)}}50%{{box-shadow:0 0 0 8px rgba(0,91,193,0.1)}}}}</style>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
}});
L.marker([empLat, empLng], {{ icon: empIcon }}).addTo(map)
  .bindPopup('<b>Your Location</b><br>' + empLat.toFixed(6) + ', ' + empLng.toFixed(6));

// Office locations + geofence circles
var bounds = [[empLat, empLng]];
offices.forEach(function(loc) {{
  L.circle([loc.lat, loc.lng], {{
    radius: loc.radius,
    color: '#005bc1',
    fillColor: '#005bc1',
    fillOpacity: 0.08,
    weight: 2,
  }}).addTo(map);

  var officeIcon = L.divIcon({{
    className: '',
    html: '<div style="width:10px;height:10px;border-radius:50%;background:#005bc1;'
      +'border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.3);"></div>',
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  }});
  L.marker([loc.lat, loc.lng], {{ icon: officeIcon }}).addTo(map)
    .bindPopup('<b>' + loc.name + '</b><br>Radius: ' + loc.radius + 'm');

  bounds.push([loc.lat, loc.lng]);
}});

if(bounds.length > 1) map.fitBounds(bounds, {{ padding: [30, 30], maxZoom: 17 }});

// Status badge
var badge = L.control({{ position: 'bottomleft' }});
badge.onAdd = function() {{
  var div = L.DomUtil.create('div', 'status-badge');
  var dotColor = inRange ? '#16a34a' : '#dc2626';
  div.innerHTML = '<span style="width:8px;height:8px;border-radius:50%;background:' + dotColor + ';display:inline-block;"></span>'
    + '<span style="color:' + dotColor + ';">{status_text}</span>';
  return div;
}};
badge.addTo(map);
</script>
</body>
</html>""", height=250, scrolling=False)


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


def _extract_exif_gps(img_bytes: bytes) -> tuple[float, float] | None:
    """
    Extract GPS coordinates from JPEG/PNG EXIF metadata.

    Returns (lat, lng) decimal degrees, or None if GPS data is absent.
    Phone cameras embed GPS in EXIF when "Location" is enabled in the camera app.
    This works entirely server-side — no browser geolocation API required.
    """
    try:
        from PIL import Image
        import io as _io

        img = Image.open(_io.BytesIO(img_bytes))
        exif = img.getexif()
        if not exif:
            return None

        gps_ifd = exif.get_ifd(0x8825)   # 0x8825 = GPSInfo IFD tag
        if not gps_ifd:
            return None

        lat_ref = gps_ifd.get(1)   # 'N' or 'S'
        lat_dms = gps_ifd.get(2)   # (degrees, minutes, seconds) — each may be IFDRational or tuple
        lng_ref = gps_ifd.get(3)   # 'E' or 'W'
        lng_dms = gps_ifd.get(4)

        if not (lat_ref and lat_dms and lng_ref and lng_dms):
            return None

        def _rat(val) -> float:
            """Convert IFDRational or (num, den) tuple to float."""
            if hasattr(val, "numerator"):   # IFDRational
                return float(val)
            if isinstance(val, tuple) and len(val) == 2:
                return val[0] / val[1] if val[1] else 0.0
            return float(val)

        def _dms_to_dec(dms, ref: str) -> float:
            d, m, s = _rat(dms[0]), _rat(dms[1]), _rat(dms[2])
            dec = d + m / 60.0 + s / 3600.0
            if ref in ("S", "W"):
                dec = -dec
            return round(dec, 7)

        return _dms_to_dec(lat_dms, lat_ref), _dms_to_dec(lng_dms, lng_ref)
    except Exception:
        return None


def _compress_snapshot(img_bytes: bytes, max_px: int = 640, quality: int = 55) -> bytes:
    """
    Resize + JPEG-compress a snapshot before uploading.

    Phone cameras produce 3–8 MB JPEGs. For DTR verification we only need a
    small face photo — 640 px on the long edge at quality=55 gives ~60–120 KB,
    a 30–60× reduction that keeps Supabase storage well within free-tier limits.

    Returns compressed JPEG bytes, or the original bytes if Pillow fails.
    """
    try:
        import io as _io
        from PIL import Image, ExifTags

        img = Image.open(_io.BytesIO(img_bytes))

        # Honour EXIF orientation so the photo isn't rotated after resize
        try:
            exif = img.getexif()
            orient_tag = next(
                (k for k, v in ExifTags.TAGS.items() if v == "Orientation"), None
            )
            if orient_tag and orient_tag in exif:
                orient = exif[orient_tag]
                _rot = {3: 180, 6: 270, 8: 90}
                if orient in _rot:
                    img = img.rotate(_rot[orient], expand=True)
        except Exception:
            pass

        # Convert palette / RGBA to RGB (JPEG doesn't support alpha)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Resize to fit within max_px × max_px, preserving aspect ratio
        img.thumbnail((max_px, max_px), Image.LANCZOS)

        buf = _io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    except Exception:
        return img_bytes   # fallback: upload as-is if Pillow unavailable


def _upload_snapshot(company_id: str, employee_id: str, work_date: date,
                     suffix: str, img_bytes: bytes) -> str | None:
    """
    Compress then upload a face snapshot to Supabase Storage bucket 'dtr-snapshots'.
    Returns the public URL or None on failure.
    Bucket must be created in Supabase dashboard:
      Storage → New bucket → name: dtr-snapshots → Public = ON
    """
    try:
        # Always upload as JPEG (compressed); ~60–120 KB vs 3–8 MB raw
        compressed = _compress_snapshot(img_bytes)
        path = f"{company_id}/{employee_id}/{work_date}_{suffix}.jpg"

        get_db().storage.from_("dtr-snapshots").upload(
            path=path,
            file=compressed,
            file_options={"content-type": "image/jpeg", "upsert": "true"},
        )
        return get_db().storage.from_("dtr-snapshots").get_public_url(path)
    except Exception as e:
        # Caller checks for None and surfaces the warning
        import sys
        print(f"[dtr] snapshot upload failed: {e}", file=sys.stderr)
        return None


def _fmt_time_portal(t) -> str:
    if t is None:
        return "—"
    if isinstance(t, str):
        return t[:5]
    return t.strftime("%H:%M")


def _dtr_status_badge(status: str) -> str:
    mapping = {
        "present":    ('<span class="mdi mdi-check-circle" style="font-size:18px;"></span> Present',    "#15803d", "#dcfce7"),
        "half_day":   ("½ Half Day",   "#92400e", "#fef3c7"),
        "absent":     ('<span class="mdi mdi-close-circle" style="font-size:18px;"></span> Absent',     "#b91c1c", "#fee2e2"),
        "on_leave":   ('<span class="mdi mdi-beach" style="font-size:18px;"></span> On Leave',  "#1e40af", "#dbeafe"),
        "holiday":    ('<span class="mdi mdi-party-popper" style="font-size:18px;"></span> Holiday',   "#6d28d9", "#ede9fe"),
        "rest_day":   ('<span class="mdi mdi-weather-night" style="font-size:18px;"></span> Rest Day',  "#475569", "#f1f5f9"),
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
        today_log_rows = (
            get_db().table("time_logs")
            .select("*")
            .eq("employee_id", emp_id)
            .eq("work_date", str(today))
            .execute()
        ).data or []
        today_log = today_log_rows[0] if today_log_rows else None
        _render_clock_widget(emp, today_log, locations, key_prefix="dtr")
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

def _render_people_search(emp: dict, company: dict):
    """Employee-facing people directory — search coworkers by name, position, or department."""
    from app.db_helper import get_db, get_company_id

    st.markdown("##### People Directory")
    st.caption("Find colleagues by name, position, or department.")

    db  = get_db()
    cid = get_company_id()

    # Load active employees (includes reports_to for org chart)
    try:
        coworkers = (
            db.table("employees")
            .select("id, employee_no, first_name, last_name, position, email, reports_to")
            .eq("company_id", cid)
            .eq("is_active", True)
            .order("last_name")
            .execute()
            .data or []
        )
        # Load profiles for department + photo
        profiles = (
            db.table("employee_profiles")
            .select("employee_id, department, department_id, photo_url, mobile_no, work_phone")
            .eq("company_id", cid)
            .execute()
            .data or []
        )
        prof_map = {p["employee_id"]: p for p in profiles}

        # Load departments (name + color)
        depts = (
            db.table("departments")
            .select("id, name, color")
            .eq("company_id", cid)
            .execute()
            .data or []
        )
        dept_name_map = {d["id"]: d["name"] for d in depts}
        dept_color_map = {d["id"]: (d.get("color") or "#6366f1") for d in depts}
    except Exception as ex:
        st.error(f"Could not load directory: {ex}")
        return

    if not coworkers:
        st.info("No colleagues found.", icon="\u2139\ufe0f")
        return

    # Enrich employees
    import json as _json
    import streamlit.components.v1 as _stc_people

    emp_ids_set = {cw["id"] for cw in coworkers}
    org_nodes = []
    for cw in coworkers:
        prof = prof_map.get(cw["id"], {})
        dept_id = prof.get("department_id")
        dept = dept_name_map.get(dept_id, "") if dept_id else (prof.get("department") or "")
        color = dept_color_map.get(dept_id, "#6366f1") if dept_id else "#6366f1"
        parent = cw.get("reports_to")
        if parent and parent not in emp_ids_set:
            parent = None
        name = f"{cw['first_name']} {cw['last_name']}"
        initials_v = ((cw["first_name"] or "?")[0] + (cw["last_name"] or "?")[0]).upper()
        org_nodes.append({
            "id": cw["id"],
            "parentId": parent or "",
            "name": name,
            "position": cw.get("position") or "",
            "empNo": cw.get("employee_no") or "",
            "color": color,
            "dept": dept,
            "initials": initials_v,
            "photo": prof.get("photo_url") or "",
            "email": cw.get("email") or "",
            "phone": prof.get("work_phone") or prof.get("mobile_no") or "",
            "isMe": cw["id"] == emp["id"],
        })

    org_data_json = _json.dumps(org_nodes)
    org_height = max(500, min(700, len(coworkers) * 24 + 160))

    # Single iframe with org chart + built-in search (instant, no Streamlit rerun)
    _stc_people.html(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3-org-chart@3.1.1/build/d3-org-chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3-flextree@2.1.2/build/d3-flextree.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{
  background:#f8f9fa;font-family:'Plus Jakarta Sans',system-ui,sans-serif;
  width:100%;height:{org_height}px;margin:0;padding:0;overflow:hidden;
}}
#search-bar{{
  position:absolute;top:8px;left:8px;z-index:10;
  display:flex;gap:6px;align-items:center;
}}
#search-input{{
  font-family:'Plus Jakarta Sans',system-ui,sans-serif;
  font-size:12px;padding:7px 14px;
  border:1.5px solid #c2c6d5;border-radius:9999px;
  outline:none;width:220px;
  background:#fff;color:#191c1d;
  transition:border-color 0.15s;
}}
#search-input:focus{{ border-color:#005bc1; }}
#search-input::placeholder{{ color:#727784; }}
#search-results{{
  position:absolute;top:38px;left:8px;z-index:11;
  background:#fff;border:1px solid #e7e8e9;border-radius:10px;
  box-shadow:0 8px 24px rgba(0,0,0,0.12);
  max-height:220px;overflow-y:auto;
  display:none;min-width:280px;
}}
.sr-item{{
  padding:10px 14px;cursor:pointer;font-size:12px;
  border-bottom:1px solid #f3f4f5;
  transition:background 0.1s;
  display:flex;align-items:center;gap:10px;
}}
.sr-item:hover{{ background:rgba(0,91,193,0.06); }}
.sr-item:last-child{{ border-bottom:none; }}
.sr-av{{
  width:28px;height:28px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  color:#fff;font-size:10px;font-weight:700;flex-shrink:0;
}}
.sr-info{{ flex:1;min-width:0; }}
.sr-name{{ font-weight:700;color:#191c1d;font-size:12px; }}
.sr-pos{{ font-size:10px;color:#727784;margin-top:1px; }}
.sr-me{{
  font-size:8px;font-weight:700;color:#005bc1;
  background:#d8e2ff;padding:1px 5px;border-radius:9999px;
  margin-left:4px;vertical-align:middle;
}}
/* Detail card shown below search when node is clicked */
#detail-card{{
  position:absolute;top:8px;right:8px;z-index:10;
  background:#fff;border:1px solid #e7e8e9;border-radius:12px;
  box-shadow:0 4px 16px rgba(0,0,0,0.08);
  padding:14px 16px;min-width:220px;max-width:280px;
  display:none;font-family:'Plus Jakarta Sans',system-ui,sans-serif;
}}
#chart{{width:100%;height:{org_height}px;}}
.link path{{ stroke-width:2px !important; }}
</style>
</head>
<body>
<div id="search-bar">
  <input id="search-input" type="text" placeholder="Search people..." autocomplete="off">
</div>
<div id="search-results"></div>
<div id="detail-card"></div>
<div id="chart"></div>
<script>
try {{
var DATA = {org_data_json};
var colorMap = {{}};
var nodeMap = {{}};
DATA.forEach(function(d){{ colorMap[d.id] = d.color; nodeMap[d.id] = d; }});

var chartEl = document.getElementById('chart');
chartEl.style.width = '100%';
chartEl.style.height = '{org_height}px';

var chart = new d3.OrgChart()
  .container('#chart')
  .data(DATA)
  .svgHeight({org_height - 10})
  .svgWidth(chartEl.offsetWidth || 800)
  .nodeWidth(function(d){{ return 200; }})
  .nodeHeight(function(d){{ return 94; }})
  .compactMarginBetween(function(d){{ return 30; }})
  .compactMarginPair(function(d){{ return 25; }})
  .neighbourMargin(function(a,b){{ return 25; }})
  .siblingsMargin(function(d){{ return 20; }})
  .childrenMargin(function(d){{ return 40; }})
  .linkUpdate(function(d,i,arr){{
    var c = colorMap[d.data.id] || '#c2c6d5';
    d3.select(this).attr('stroke', c).attr('stroke-width', 2).attr('stroke-opacity', 0.6);
  }})
  .nodeContent(function(d,i,arr,state){{
    var n = d.data;
    var c = n.color || '#6366f1';
    var borderTint = c + '30';
    var bgTint = c + '0d';
    var meBadge = n.isMe ? '<span style="font-size:7px;font-weight:700;color:#005bc1;background:#d8e2ff;padding:1px 4px;border-radius:9999px;margin-left:3px;">YOU</span>' : '';
    var avHtml = n.photo
      ? '<div style="width:36px;height:36px;border-radius:50%;overflow:hidden;flex-shrink:0;border:1.5px solid '+borderTint+';">'
        +'<img src="'+n.photo+'" style="width:100%;height:100%;object-fit:cover;" '
        +'onerror="this.parentElement.innerHTML=\\'<div style=&quot;width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:'+c+';color:#fff;font-size:12px;font-weight:700;&quot;>'+n.initials+'</div>\\'"></div>'
      : '<div style="width:36px;height:36px;border-radius:50%;background:'+c+';display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px;font-weight:700;flex-shrink:0;">'+n.initials+'</div>';
    return '<div style="font-family:Plus Jakarta Sans,system-ui,sans-serif;background:#fff;border:1.5px solid '+borderTint+';border-top:3px solid '+c+';border-radius:10px;padding:10px;width:'+d.width+'px;height:'+d.height+'px;display:flex;align-items:center;gap:10px;box-shadow:0 2px 8px rgba(0,0,0,0.06);cursor:pointer;">'
      +avHtml
      +'<div style="flex:1;min-width:0;overflow:hidden;">'
      +'<div style="font-size:11px;font-weight:700;color:#191c1d;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'+n.name+meBadge+'</div>'
      +'<div style="font-size:9px;color:#424753;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'+n.position+'</div>'
      +'<div style="display:flex;gap:4px;align-items:center;margin-top:3px;">'
      +(n.dept ? '<span style="font-size:7px;font-weight:700;color:'+c+';background:'+bgTint+';padding:1px 5px;border-radius:9999px;text-transform:uppercase;letter-spacing:0.03em;">'+n.dept+'</span>' : '')
      +'<span style="font-size:8px;color:#727784;">'+n.empNo+'</span>'
      +'</div>'
      +'</div></div>';
  }})
  .onNodeClick(function(nodeId){{
    var n = nodeMap[nodeId];
    if(!n) return;
    showDetail(n);
  }})
  .render()
  .fit();

/* ── Detail card on node click ─────────────────────────────── */
var detailCard = document.getElementById('detail-card');
function showDetail(n){{
  var c = n.color || '#6366f1';
  var meBadge = n.isMe ? ' <span style="font-size:8px;font-weight:700;color:#005bc1;background:#d8e2ff;padding:1px 5px;border-radius:9999px;">YOU</span>' : '';
  var avHtml = n.photo
    ? '<img src="'+n.photo+'" style="width:48px;height:48px;border-radius:50%;object-fit:cover;border:2px solid '+c+'30;" onerror="this.outerHTML=\\'<div style=&quot;width:48px;height:48px;border-radius:50%;background:'+c+';display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px;font-weight:700;&quot;>'+n.initials+'</div>\\'">'
    : '<div style="width:48px;height:48px;border-radius:50%;background:'+c+';display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px;font-weight:700;">'+n.initials+'</div>';
  var contactHtml = '';
  if(n.email) contactHtml += '<div style="font-size:10px;color:#005bc1;background:#dbeafe;padding:2px 8px;border-radius:9999px;font-weight:600;display:inline-block;">'+n.email+'</div> ';
  if(n.phone) contactHtml += '<div style="font-size:10px;color:#059669;background:#d1fae5;padding:2px 8px;border-radius:9999px;font-weight:600;display:inline-block;">'+n.phone+'</div>';

  detailCard.innerHTML =
    '<div style="display:flex;gap:12px;align-items:center;margin-bottom:8px;">'
    +avHtml
    +'<div>'
    +'<div style="font-size:14px;font-weight:700;color:#191c1d;">'+n.name+meBadge+'</div>'
    +'<div style="font-size:11px;color:#424753;">'+n.position+'</div>'
    +'</div></div>'
    +'<div style="display:flex;gap:6px;align-items:center;margin-bottom:6px;">'
    +'<span style="font-size:9px;font-weight:700;color:'+c+';background:'+c+'0d;padding:2px 8px;border-radius:9999px;text-transform:uppercase;">'+n.dept+'</span>'
    +'<span style="font-size:10px;color:#727784;">'+n.empNo+'</span>'
    +'</div>'
    +(contactHtml ? '<div style="display:flex;gap:4px;flex-wrap:wrap;">'+contactHtml+'</div>' : '');
  detailCard.style.display = 'block';
}}
/* Close detail card when clicking chart background */
chartEl.addEventListener('click', function(e){{
  if(e.target === chartEl || e.target.tagName === 'svg') detailCard.style.display = 'none';
}});

/* ── Search functionality ─────────────────────────────────── */
var searchInput = document.getElementById('search-input');
var searchResults = document.getElementById('search-results');

searchInput.addEventListener('input', function(){{
  var q = this.value.trim().toLowerCase();
  searchResults.innerHTML = '';
  if(q.length < 1){{ searchResults.style.display='none'; return; }}

  var matches = DATA.filter(function(d){{
    return d.name.toLowerCase().indexOf(q) !== -1
        || d.position.toLowerCase().indexOf(q) !== -1
        || d.dept.toLowerCase().indexOf(q) !== -1
        || d.empNo.toLowerCase().indexOf(q) !== -1;
  }}).slice(0, 10);

  if(!matches.length){{ searchResults.style.display='none'; return; }}

  matches.forEach(function(m){{
    var div = document.createElement('div');
    div.className = 'sr-item';
    var meBadge = m.isMe ? '<span class="sr-me">YOU</span>' : '';
    div.innerHTML =
      '<div class="sr-av" style="background:'+m.color+';">'+m.initials+'</div>'
      +'<div class="sr-info">'
      +'<div class="sr-name">'+m.name+meBadge+'</div>'
      +'<div class="sr-pos">'+m.position+' &middot; '+m.dept+' &middot; '+m.empNo+'</div>'
      +'</div>';
    div.onclick = function(){{
      chart.setCentered(m.id).render();
      setTimeout(function(){{
        chart.setHighlighted(m.id).render();
        setTimeout(function(){{ chart.clearHighlighting(); }}, 5000);
      }}, 400);
      searchResults.style.display='none';
      searchInput.value = m.name;
      showDetail(m);
    }};
    searchResults.appendChild(div);
  }});
  searchResults.style.display='block';
}});

document.addEventListener('click', function(e){{
  if(!searchInput.contains(e.target) && !searchResults.contains(e.target)){{
    searchResults.style.display='none';
  }}
}});

}} catch(e) {{ console.error('People OrgChart error:', e); }}
</script>
</body></html>
""", height=org_height, scrolling=True)


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
        '<div style="font-size:15px;font-weight:700;color:#1f2937">Certificate of Employment</div>'
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
        '<div style="font-size:15px;font-weight:700;color:#1f2937">BIR Form 2316</div>'
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

    tab_dash, tab_profile, tab_payslips, tab_leave, tab_docs, tab_people, tab_prefs = st.tabs([
        "Dashboard", "My Profile", "My Payslips", "My Time & Leave", "My Documents", "People", "Preferences",
    ])

    with tab_dash:
        _render_dashboard(emp, company)

    with tab_profile:
        profile = _get_profile(emp["id"])
        _render_profile_form(emp, profile)

    with tab_payslips:
        _render_payslips(emp, company)

    with tab_leave:
        _render_time_leave(emp, company)

    with tab_docs:
        _render_documents(emp, company)

    with tab_people:
        _render_people_search(emp, company)

    with tab_prefs:
        from app.pages._preferences import render as render_preferences
        render_preferences(standalone=False)
