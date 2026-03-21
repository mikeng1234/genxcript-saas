"""
Payroll Run — Streamlit page.

The main working screen:
1. Create or select a pay period
2. Input additional earnings per employee (OT, holiday, allowances, etc.)
3. Auto-compute government contributions + withholding tax
4. Review breakdown and finalize
"""

import streamlit as st
from datetime import date, timedelta
import calendar
from backend.payroll import compute_payroll
from app.db_helper import get_db, get_company_id, log_action
from app.styles import (
    inject_css, status_badge, info_bar, fin_table, remit_card,
    progress_bar, GOV_COLORS,
)
import plotly.graph_objects as go
import pandas as pd


# ============================================================
# Helpers
# ============================================================

def _centavos_to_pesos(centavos: int) -> float:
    return centavos / 100


def _compute_period_end(start: date, pay_frequency: str) -> date:
    """
    Given a period start date and the company's pay frequency,
    return the estimated period end date.

    - semi-monthly : start on 1–15 → end on the 15th;
                     start on 16–31 → end on last day of the month
    - monthly      : last day of the start date's month
    - weekly       : start + 6 days (Mon–Sun)
    """
    if pay_frequency == "semi-monthly":
        if start.day <= 15:
            return start.replace(day=15)
        else:
            last_day = calendar.monthrange(start.year, start.month)[1]
            return start.replace(day=last_day)

    elif pay_frequency == "monthly":
        last_day = calendar.monthrange(start.year, start.month)[1]
        return start.replace(day=last_day)

    elif pay_frequency == "weekly":
        return start + timedelta(days=6)

    # Fallback — treat as semi-monthly
    if start.day <= 15:
        return start.replace(day=15)
    last_day = calendar.monthrange(start.year, start.month)[1]
    return start.replace(day=last_day)


def _pesos_to_centavos(pesos: float) -> int:
    return int(round(pesos * 100))


def _fmt(centavos: int) -> str:
    """Format centavos as peso string: ₱12,345.67"""
    return f"₱{_centavos_to_pesos(centavos):,.2f}"


# ============================================================
# Database operations
# ============================================================

def _load_company() -> dict:
    """Load the current company record (for pay_frequency etc.)."""
    db = get_db()
    result = (
        db.table("companies")
        .select("*")
        .eq("id", get_company_id())
        .single()
        .execute()
    )
    return result.data or {}


def _load_departments_map() -> dict:
    """Return {employee_id: department} for this company's active employees."""
    try:
        db  = get_db()
        cid = get_company_id()
        emp_ids = [r["id"] for r in db.table("employees").select("id").eq("company_id", cid).execute().data or []]
        if not emp_ids:
            return {}
        rows = db.table("employee_profiles").select("employee_id, department").in_("employee_id", emp_ids).execute().data or []
        return {r["employee_id"]: (r.get("department") or "") for r in rows}
    except Exception:
        return {}


def _load_dept_names_from_table() -> list[str]:
    """Load structured department names for filter dropdowns."""
    try:
        db = get_db()
        result = (
            db.table("departments")
            .select("name")
            .eq("company_id", get_company_id())
            .eq("is_active", True)
            .order("name")
            .execute()
        )
        return [r["name"] for r in (result.data or [])]
    except Exception:
        return []


def _load_employees() -> list[dict]:
    """Load active employees from Supabase."""
    db = get_db()
    result = (
        db.table("employees")
        .select("*")
        .eq("company_id", get_company_id())
        .eq("is_active", True)
        .order("last_name")
        .execute()
    )
    return result.data


def _load_pay_periods() -> list[dict]:
    """Load all pay periods from Supabase."""
    db = get_db()
    result = (
        db.table("pay_periods")
        .select("*")
        .eq("company_id", get_company_id())
        .order("period_start", desc=True)
        .execute()
    )
    return result.data


def _create_pay_period(data: dict) -> dict:
    """Insert a new pay period."""
    db = get_db()
    data["company_id"] = get_company_id()
    result = db.table("pay_periods").insert(data).execute()
    return result.data[0]


def _update_pay_period(period_id: str, data: dict) -> dict:
    """Update a pay period (e.g. status change)."""
    db = get_db()
    result = db.table("pay_periods").update(data).eq("id", period_id).execute()
    return result.data[0]


def _load_payroll_entries(pay_period_id: str) -> dict:
    """Load all payroll entries for a pay period, keyed by employee_id."""
    db = get_db()
    result = (
        db.table("payroll_entries")
        .select("*")
        .eq("pay_period_id", pay_period_id)
        .execute()
    )
    return {row["employee_id"]: row for row in result.data}


def _upsert_payroll_entry(pay_period_id: str, employee_id: str, data: dict) -> dict:
    """Insert or update a payroll entry for an employee in a pay period."""
    db = get_db()
    data["pay_period_id"] = pay_period_id
    data["employee_id"] = employee_id

    # Check if entry exists
    existing = (
        db.table("payroll_entries")
        .select("id")
        .eq("pay_period_id", pay_period_id)
        .eq("employee_id", employee_id)
        .execute()
    )

    if existing.data:
        # Update existing
        result = (
            db.table("payroll_entries")
            .update(data)
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        # Insert new
        result = db.table("payroll_entries").insert(data).execute()

    return result.data[0]


def _load_dtr_summary_for_period(emp_id: str, p_start: str, p_end: str) -> dict:
    """Sum nsd_hours, ot_hours, and absent_days from time_logs for an employee within a pay period."""
    try:
        rows = (
            get_db().table("time_logs")
            .select("nsd_hours,ot_hours,status")
            .eq("employee_id", emp_id)
            .gte("work_date", p_start)
            .lte("work_date", p_end)
            .execute()
        ).data or []
        return {
            "nsd_hours":   round(sum(float(r.get("nsd_hours") or 0) for r in rows), 2),
            "ot_hours":    round(sum(float(r.get("ot_hours")  or 0) for r in rows), 2),
            "absent_days": sum(1 for r in rows if r.get("status") == "absent"),
        }
    except Exception:
        return {"nsd_hours": 0.0, "ot_hours": 0.0, "absent_days": 0}


def _load_approved_ot_hours(emp_id: str, p_start: str, p_end: str) -> float:
    """Sum approved OT hours from overtime_requests for an employee within a pay period."""
    try:
        rows = (
            get_db().table("overtime_requests")
            .select("hours")
            .eq("employee_id", emp_id)
            .eq("status", "approved")
            .gte("ot_date", p_start)
            .lte("ot_date", p_end)
            .execute()
        ).data or []
        return round(sum(float(r.get("hours") or 0) for r in rows), 2)
    except Exception:
        return 0.0


def _hourly_rate_centavos(emp: dict, divisor: int = 26) -> float:
    """Compute the per-hour rate in centavos from the employee's basic_salary."""
    bs = emp.get("basic_salary") or 0
    salary_type = (emp.get("salary_type") or "monthly").lower()
    if salary_type == "daily":
        return bs / 8.0
    return bs / (divisor * 8)    # monthly → company divisor × 8 hours


# ============================================================
# Pay Period Management
# ============================================================

def _load_all_period_history() -> list[dict]:
    """Load aggregate totals for all finalized/paid periods — used for the trend chart."""
    db = get_db()
    periods_result = (
        db.table("pay_periods")
        .select("*")
        .eq("company_id", get_company_id())
        .in_("status", ["finalized", "paid"])
        .order("period_start", desc=False)
        .execute()
    )
    rows = []
    for p in periods_result.data:
        entries_result = (
            db.table("payroll_entries")
            .select("*")
            .eq("pay_period_id", p["id"])
            .execute()
        )
        entries = entries_result.data
        if not entries:
            continue
        rows.append({
            "period": p["period_start"],
            "gross_pay":       sum(e["gross_pay"]         for e in entries) / 100,
            "total_deductions":sum(e["total_deductions"]  for e in entries) / 100,
            "net_pay":         sum(e["net_pay"]           for e in entries) / 100,
            "employer_cost":   sum(
                e["sss_employer"] + e["philhealth_employer"] + e["pagibig_employer"]
                for e in entries
            ) / 100,
        })
    return rows


def _render_pay_period_selector() -> dict | None:
    """Render pay period creation and selection. Returns selected period or None."""
    periods = _load_pay_periods()

    col_select, col_new = st.columns([3, 1])

    with col_new:
        st.write("")  # spacer
        st.write("")
        if st.button("+ New Pay Period", type="primary", width="stretch"):
            st.session_state.show_new_period = True
            # Clear stale date state so defaults are recomputed fresh
            for k in ("np_start", "np_end", "np_pay", "np_start_prev"):
                st.session_state.pop(k, None)

    with col_select:
        if not periods:
            st.info("No pay periods yet. Create one to start.")
            selected_period = None
        else:
            period_labels = {
                p["id"]: f"{p['period_start']} to {p['period_end']}  [{p['status'].upper()}]"
                for p in periods
            }
            selected_id = st.selectbox(
                "Select Pay Period",
                options=[p["id"] for p in periods],
                format_func=lambda x: period_labels[x],
                index=0,  # latest first (sorted desc)
            )
            selected_period = next(p for p in periods if p["id"] == selected_id)

    # ── New period creation ──────────────────────────────────────────────────
    if st.session_state.get("show_new_period"):
        st.subheader("Create Pay Period")

        # Load company settings once
        company = _load_company()
        pay_frequency = company.get("pay_frequency", "semi-monthly")
        daily_rate_divisor = int(company.get("daily_rate_divisor") or 26)

        # Compute sensible default start date based on frequency
        today = date.today()
        if pay_frequency == "weekly":
            # Start of the current week (Monday)
            default_start = today - timedelta(days=today.weekday())
        elif pay_frequency == "monthly":
            default_start = today.replace(day=1)
        else:  # semi-monthly
            default_start = today.replace(day=1) if today.day <= 15 else today.replace(day=16)

        # ── Seed session state on first render ───────────────────────────────
        if "np_start" not in st.session_state:
            st.session_state.np_start = default_start
            st.session_state.np_end   = _compute_period_end(default_start, pay_frequency)
            st.session_state.np_pay   = st.session_state.np_end + timedelta(days=5)
            st.session_state.np_start_prev = default_start

        # ── Auto-update end/payment dates when start changes ─────────────────
        # Compare current widget value to previous; update end only if start moved.
        current_start = st.session_state.np_start
        if current_start != st.session_state.get("np_start_prev"):
            new_end = _compute_period_end(current_start, pay_frequency)
            st.session_state.np_end  = new_end
            st.session_state.np_pay  = new_end + timedelta(days=5)
            st.session_state.np_start_prev = current_start

        # ── Date inputs (outside form so changes trigger reruns) ─────────────
        col1, col2, col3 = st.columns(3)
        with col1:
            st.date_input(
                "Period Start",
                key="np_start",
                help=f"Pay frequency: {pay_frequency}. Period End auto-fills based on this.",
            )
        with col2:
            st.date_input(
                "Period End",
                key="np_end",
                help="Auto-filled from Period Start. You can adjust if needed.",
            )
        with col3:
            st.date_input(
                "Payment Date",
                key="np_pay",
                help="Default is 5 days after Period End.",
            )

        # ── Submit button ────────────────────────────────────────────────────
        col_cancel, col_create = st.columns([1, 1])
        with col_cancel:
            if st.button("Cancel", width="stretch"):
                st.session_state.show_new_period = False
                for k in ("np_start", "np_end", "np_pay", "np_start_prev"):
                    st.session_state.pop(k, None)
                st.rerun()
        with col_create:
            if st.button("Create Period", type="primary", width="stretch"):
                p_start = st.session_state.np_start
                p_end   = st.session_state.np_end
                p_pay   = st.session_state.np_pay
                if p_end <= p_start:
                    st.error("Period End must be after Period Start.")
                else:
                    try:
                        new_period = _create_pay_period({
                            "period_start": p_start.isoformat(),
                            "period_end":   p_end.isoformat(),
                            "payment_date": p_pay.isoformat(),
                            "status": "draft",
                        })
                        log_action("created", "pay_period", new_period["id"], f"{p_start} to {p_end}")
                        st.session_state.show_new_period = False
                        for k in ("np_start", "np_end", "np_pay", "np_start_prev"):
                            st.session_state.pop(k, None)
                        st.success(f"Created pay period: {p_start} to {p_end}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating pay period: {e}")

        st.divider()

    return selected_period


# ============================================================
# Earnings Input & Computation per Employee
# ============================================================

def _render_employee_payroll(
    emp: dict,
    period_id: str,
    is_finalized: bool,
    entries: dict,
    period: dict | None = None,
    daily_rate_divisor: int = 26,
):
    """Render earnings input and computation for one employee."""
    saved = entries.get(emp["id"], {})

    name       = f"{emp['first_name']} {emp['last_name']}"
    is_computed = emp["id"] in entries
    dept        = emp.get("department") or emp.get("position") or ""
    gross_str   = f"₱{entries[emp['id']]['gross_pay']/100:,.0f} gross" if is_computed else "Not yet computed"
    status_dot  = "✓" if is_computed else "○"
    exp_label   = f"{status_dot}  {name}  ·  {dept}  ·  {gross_str}"

    with st.expander(exp_label, expanded=False):
        # M3 mini-header inside expander
        _initials  = (emp['first_name'][:1] + emp['last_name'][:1]).upper()
        _colors    = ["#005bc1","#006e2d","#795900","#ba1a1a","#4b0082","#006064","#37474f","#880e4f"]
        _color     = _colors[hash(emp["id"]) % len(_colors)]
        _pos       = emp.get("position") or "—"
        _salary_lbl = _fmt(emp["basic_salary"])
        _badge_html = (
            f'<span style="display:inline-flex;align-items:center;gap:0.25rem;'
            f'background:var(--gxp-success-bg);color:var(--gxp-success-fg);'
            f'padding:0.15rem 0.6rem;border-radius:9999px;font-size:0.6875rem;font-weight:700;">'
            f'✓ COMPUTED</span>'
            if is_computed else
            f'<span style="display:inline-flex;align-items:center;gap:0.25rem;'
            f'background:var(--gxp-warning-bg);color:var(--gxp-warning-fg);'
            f'padding:0.15rem 0.6rem;border-radius:9999px;font-size:0.6875rem;font-weight:700;">'
            f'○ PENDING</span>'
        )
        _net_html = ""
        if is_computed:
            _net_val = entries[emp["id"]].get("net_pay", 0)
            _net_html = (
                f'<div style="font-size:0.75rem;color:var(--gxp-text3);margin-top:0.125rem;">'
                f'Net Pay <span style="font-size:1rem;font-weight:800;color:var(--gxp-accent);">'
                f'{_fmt(_net_val)}</span></div>'
            )
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:1rem;padding:0.5rem 0 1.25rem;'
            f'border-bottom:1px solid var(--gxp-border);margin-bottom:1.25rem;">'
            f'<div style="width:48px;height:48px;border-radius:50%;background:{_color};'
            f'display:flex;align-items:center;justify-content:center;flex-shrink:0;">'
            f'<span style="color:#fff;font-weight:700;font-size:1.125rem;">{_initials}</span></div>'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-size:1rem;font-weight:700;color:var(--gxp-text);">{name}</div>'
            f'<div style="font-size:0.8125rem;color:var(--gxp-text2);">'
            f'{_pos} · {emp["employee_no"]} · Basic {_salary_lbl}</div>'
            f'</div>'
            f'<div style="text-align:right;flex-shrink:0;">'
            f'{_badge_html}{_net_html}'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        if is_finalized:
            _render_payroll_summary(saved)
            return

        # ── DTR Insights ─────────────────────────────────────────────────────────
        if period and not is_finalized:
            _p_start = period.get("period_start", "")
            _p_end   = period.get("period_end", "")
            if _p_start and _p_end:
                _dtr  = _load_dtr_summary_for_period(emp["id"], _p_start, _p_end)
                _appr_ot_h = _load_approved_ot_hours(emp["id"], _p_start, _p_end)
                _hr   = _hourly_rate_centavos(emp, daily_rate_divisor)

                _nsd_sugg   = _hr * _dtr["nsd_hours"] * 0.10
                _ot_sugg    = _hr * _appr_ot_h        * 1.25
                # Daily rate = basic_salary / company divisor (monthly) or as-is (daily)
                _bs = emp.get("basic_salary") or 0
                _salary_type = (emp.get("salary_type") or "monthly").lower()
                _daily_rate  = _bs if _salary_type == "daily" else int(_bs / daily_rate_divisor)
                _absent_sugg = _daily_rate * _dtr["absent_days"]

                if _dtr["nsd_hours"] > 0 or _appr_ot_h > 0 or _dtr["ot_hours"] > 0 or _dtr["absent_days"] > 0:
                    with st.expander("📊 DTR Insights for this period", expanded=_dtr["absent_days"] > 0):
                        _di1, _di2, _di3, _di4, _di5, _di6 = st.columns(6)
                        _di1.metric("NSD Hours (DTR)", f"{_dtr['nsd_hours']:.2f} h",
                                    help="Total hours worked 10 PM–6 AM in this period per DTR.")
                        _di2.metric("NSD Suggested Pay",
                                    f"₱{_nsd_sugg/100:,.2f}",
                                    help="NSD hrs × hourly rate × 10% (DOLE Art. 86)")
                        _di3.metric("Approved OT Hours", f"{_appr_ot_h:.2f} h",
                                    help="Sum of approved overtime requests in this period.")
                        _di4.metric("OT Suggested Pay",
                                    f"₱{_ot_sugg/100:,.2f}",
                                    help="Approved OT hrs × hourly rate × 125%")
                        _di5.metric("Absent Days (DTR)", f"{_dtr['absent_days']} day(s)",
                                    help="Days with status='absent' in DTR for this period.")
                        _di6.metric("Absent Deduction",
                                    f"₱{_absent_sugg/100:,.2f}",
                                    delta=f"-₱{_absent_sugg/100:,.2f}" if _dtr["absent_days"] > 0 else None,
                                    delta_color="inverse",
                                    help="Daily rate × absent days. Auto-filled in deductions below.")
                        if _dtr["ot_hours"] != _appr_ot_h:
                            st.caption(
                                f"ℹ️ DTR-computed OT: **{_dtr['ot_hours']:.2f} h** "
                                f"vs. Approved OT: **{_appr_ot_h:.2f} h**. "
                                "Payroll uses **approved** OT only."
                            )
                        if _dtr["absent_days"] > 0:
                            st.caption(
                                f"ℹ️ {_dtr['absent_days']} absent day(s) × "
                                f"₱{_daily_rate/100:,.2f} daily rate = "
                                f"**₱{_absent_sugg/100:,.2f}** auto-filled in Absent Deduction below."
                            )

        # --- Earnings input form ---
        with st.form(key=f"earnings_{period_id}_{emp['id']}"):

            st.markdown("**Earnings**")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                basic_pay = st.number_input(
                    "Basic Pay (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("basic_pay", emp["basic_salary"])),
                    step=100.0, format="%.2f",
                    key=f"basic_{period_id}_{emp['id']}",
                )
            with col2:
                _ot_default = saved.get("overtime_pay")
                if _ot_default is None and period:
                    _p_s = period.get("period_start", "")
                    _p_e = period.get("period_end", "")
                    if _p_s and _p_e:
                        _appr_h = _load_approved_ot_hours(emp["id"], _p_s, _p_e)
                        _ot_default = int(_hourly_rate_centavos(emp, daily_rate_divisor) * _appr_h * 1.25)
                overtime_pay = st.number_input(
                    "Overtime (₱)", min_value=0.0,
                    value=_centavos_to_pesos(_ot_default or 0),
                    step=100.0, format="%.2f",
                    key=f"ot_{period_id}_{emp['id']}",
                    help="Auto-suggested from approved OT requests × 125% rate.",
                )
            with col3:
                holiday_pay = st.number_input(
                    "Holiday Pay (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("holiday_pay", 0)),
                    step=100.0, format="%.2f",
                    key=f"hol_{period_id}_{emp['id']}",
                )
            with col4:
                _nd_default = saved.get("night_differential")
                if _nd_default is None and period:
                    _p_s2 = period.get("period_start", "")
                    _p_e2 = period.get("period_end", "")
                    if _p_s2 and _p_e2:
                        _dtr2 = _load_dtr_summary_for_period(emp["id"], _p_s2, _p_e2)
                        _nd_default = int(_hourly_rate_centavos(emp, daily_rate_divisor) * _dtr2["nsd_hours"] * 0.10)
                night_diff = st.number_input(
                    "Night Diff (₱)", min_value=0.0,
                    value=_centavos_to_pesos(_nd_default or 0),
                    step=100.0, format="%.2f",
                    key=f"nd_{period_id}_{emp['id']}",
                    help="Auto-suggested from DTR night-shift hours × 10% premium.",
                )

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                allowances_nt = st.number_input(
                    "Non-Taxable Allowances (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("allowances_nontaxable", 0)),
                    step=100.0, format="%.2f",
                    key=f"ant_{period_id}_{emp['id']}",
                    help="Meal, rice, clothing allowances within de minimis limits",
                )
            with col2:
                allowances_t = st.number_input(
                    "Taxable Allowances (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("allowances_taxable", 0)),
                    step=100.0, format="%.2f",
                    key=f"at_{period_id}_{emp['id']}",
                )
            with col3:
                commission = st.number_input(
                    "Commission (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("commission", 0)),
                    step=100.0, format="%.2f",
                    key=f"comm_{period_id}_{emp['id']}",
                )
            with col4:
                thirteenth = st.number_input(
                    "13th Month Accrual (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("thirteenth_month_accrual", 0)),
                    step=100.0, format="%.2f",
                    key=f"13th_{period_id}_{emp['id']}",
                )

            # --- Other deductions ---
            st.markdown("**Other Deductions**")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                # Auto-suggest absent deduction from DTR if not yet saved
                _absent_default = saved.get("absent_deduction")
                if _absent_default is None and period and not is_finalized:
                    _p_s3 = period.get("period_start", "")
                    _p_e3 = period.get("period_end", "")
                    if _p_s3 and _p_e3:
                        _dtr3 = _load_dtr_summary_for_period(emp["id"], _p_s3, _p_e3)
                        _bs3 = emp.get("basic_salary") or 0
                        _st3 = (emp.get("salary_type") or "monthly").lower()
                        _dr3 = _bs3 if _st3 == "daily" else int(_bs3 / daily_rate_divisor)
                        _absent_default = _dr3 * _dtr3["absent_days"]
                absent_ded = st.number_input(
                    "Absent Deduction (₱)", min_value=0.0,
                    value=_centavos_to_pesos(_absent_default or 0),
                    step=100.0, format="%.2f",
                    key=f"absent_{period_id}_{emp['id']}",
                    help="Auto-computed: daily rate × absent days from DTR. Editable.",
                )
            with col2:
                sss_loan = st.number_input(
                    "SSS Loan (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("sss_loan", 0)),
                    step=100.0, format="%.2f",
                    key=f"sssl_{period_id}_{emp['id']}",
                )
            with col3:
                pagibig_loan = st.number_input(
                    "Pag-IBIG Loan (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("pagibig_loan", 0)),
                    step=100.0, format="%.2f",
                    key=f"pil_{period_id}_{emp['id']}",
                )
            with col4:
                cash_advance = st.number_input(
                    "Cash Advance (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("cash_advance", 0)),
                    step=100.0, format="%.2f",
                    key=f"ca_{period_id}_{emp['id']}",
                )
            with col5:
                other_ded = st.number_input(
                    "Other Deductions (₱)", min_value=0.0,
                    value=_centavos_to_pesos(saved.get("other_deductions", 0)),
                    step=100.0, format="%.2f",
                    key=f"other_{period_id}_{emp['id']}",
                )

            computed = st.form_submit_button("Compute & Save", type="primary", width="stretch")

        if computed:
            # Convert all inputs to centavos
            basic_c = _pesos_to_centavos(basic_pay)
            ot_c = _pesos_to_centavos(overtime_pay)
            hol_c = _pesos_to_centavos(holiday_pay)
            nd_c = _pesos_to_centavos(night_diff)
            ant_c = _pesos_to_centavos(allowances_nt)
            at_c = _pesos_to_centavos(allowances_t)
            comm_c = _pesos_to_centavos(commission)
            thirteenth_c = _pesos_to_centavos(thirteenth)
            absent_c = _pesos_to_centavos(absent_ded)
            sssl_c = _pesos_to_centavos(sss_loan)
            pil_c = _pesos_to_centavos(pagibig_loan)
            ca_c = _pesos_to_centavos(cash_advance)
            other_c = _pesos_to_centavos(other_ded)

            # Gross pay = earnings - absent deduction (before contributions)
            gross = basic_c + ot_c + hol_c + nd_c + ant_c + at_c + comm_c + thirteenth_c - absent_c
            gross = max(gross, 0)

            # Run computation engine
            result = compute_payroll(
                gross_pay=gross,
                nontaxable_allowances=ant_c,
            )

            # Total voluntary deductions (loans, advances, other)
            vol_deductions = sssl_c + pil_c + ca_c + other_c

            # Save to database
            entry_data = {
                "basic_pay": basic_c,
                "overtime_pay": ot_c,
                "holiday_pay": hol_c,
                "night_differential": nd_c,
                "allowances_nontaxable": ant_c,
                "allowances_taxable": at_c,
                "commission": comm_c,
                "thirteenth_month_accrual": thirteenth_c,
                "absent_deduction": absent_c,
                "gross_pay": gross,
                "sss_employee": result.sss_employee,
                "philhealth_employee": result.philhealth_employee,
                "pagibig_employee": result.pagibig_employee,
                "sss_employer": result.sss_employer,
                "philhealth_employer": result.philhealth_employer,
                "pagibig_employer": result.pagibig_employer,
                "withholding_tax": result.withholding_tax,
                "sss_loan": sssl_c,
                "pagibig_loan": pil_c,
                "cash_advance": ca_c,
                "other_deductions": other_c,
                "total_deductions": result.total_mandatory_deductions + vol_deductions,
                "net_pay": result.net_pay - vol_deductions,
            }

            try:
                saved_entry = _upsert_payroll_entry(period_id, emp["id"], entry_data)
                entries[emp["id"]] = saved_entry
                log_action("updated", "payroll_entries", period_id, f"Entry for {name}", {"net_pay": entry_data["net_pay"]})
                st.success(f"Computed: {name} — Net Pay: {_fmt(entry_data['net_pay'])}")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving: {e}")

        # Show last computed result if available
        if emp["id"] in entries:
            _render_payroll_summary(entries[emp["id"]])


def _render_payroll_summary(entry: dict):
    """Show the computation breakdown for an employee — M3 3-column grid."""
    if not entry:
        st.caption("Not yet computed. Fill in earnings and click 'Compute & Save'.")
        return

    gross   = entry.get("gross_pay", 0)
    net     = entry.get("net_pay", 0)
    tot_ded = entry.get("total_deductions", 0)
    er_tot  = (entry.get("sss_employer", 0)
               + entry.get("philhealth_employer", 0)
               + entry.get("pagibig_employer", 0))

    def _row(label, val, color="var(--gxp-text)", label_color="var(--gxp-text2)"):
        return (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:0.35rem 0;border-bottom:1px solid var(--gxp-border);">'
            f'<span style="font-size:0.8125rem;color:{label_color};">{label}</span>'
            f'<span style="font-size:0.8125rem;font-weight:600;color:{color};">{val}</span>'
            f'</div>'
        )

    earnings_rows = "".join([
        _row("Basic Pay",          _fmt(entry.get("basic_pay", 0))),
        _row("Overtime",           _fmt(entry.get("overtime_pay", 0))),
        _row("Holiday Pay",        _fmt(entry.get("holiday_pay", 0))),
        _row("Night Differential", _fmt(entry.get("night_differential", 0))),
        _row("Allowances (NT)",    _fmt(entry.get("allowances_nontaxable", 0))),
        _row("Allowances (Tax)",   _fmt(entry.get("allowances_taxable", 0))),
        _row("Commission",         _fmt(entry.get("commission", 0))),
        _row("13th Month",         _fmt(entry.get("thirteenth_month_accrual", 0))),
        _row("Absent Deduction",   f'-{_fmt(entry.get("absent_deduction", 0))}',
             color="var(--gxp-danger)"),
    ])

    deductions_rows = "".join([
        _row("SSS (Employee)",        _fmt(entry.get("sss_employee", 0))),
        _row("PhilHealth (Employee)", _fmt(entry.get("philhealth_employee", 0))),
        _row("Pag-IBIG (Employee)",   _fmt(entry.get("pagibig_employee", 0))),
        _row("Withholding Tax",       _fmt(entry.get("withholding_tax", 0)),
             color="var(--gxp-danger)", label_color="var(--gxp-danger)"),
        _row("SSS Loan",              _fmt(entry.get("sss_loan", 0))),
        _row("Pag-IBIG Loan",         _fmt(entry.get("pagibig_loan", 0))),
        _row("Cash Advance",          _fmt(entry.get("cash_advance", 0))),
        _row("Other Deductions",      _fmt(entry.get("other_deductions", 0))),
    ])

    employer_rows = "".join([
        _row("SSS (Employer)",        _fmt(entry.get("sss_employer", 0))),
        _row("PhilHealth (Employer)", _fmt(entry.get("philhealth_employer", 0))),
        _row("Pag-IBIG (Employer)",   _fmt(entry.get("pagibig_employer", 0))),
        _row("Employer Total",        _fmt(er_tot),
             color="var(--gxp-text)", label_color="var(--gxp-text3)"),
    ])

    col_h = (
        'style="font-size:0.6875rem;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.1em;color:var(--gxp-text3);margin-bottom:0.75rem;"'
    )

    st.markdown(
        f'<div style="background:var(--gxp-surface);border-radius:1rem;padding:1.5rem;'
        f'margin-top:1rem;display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.5rem;">'

        # ── Earnings column
        f'<div>'
        f'<div {col_h}>Earnings</div>'
        f'{earnings_rows}'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:0.5rem 0;margin-top:0.25rem;">'
        f'<span style="font-size:0.8125rem;font-weight:700;color:var(--gxp-text);">Gross Pay</span>'
        f'<span style="font-size:0.9375rem;font-weight:800;color:var(--gxp-text);">{_fmt(gross)}</span>'
        f'</div>'
        f'</div>'

        # ── Deductions column
        f'<div>'
        f'<div {col_h}>Deductions</div>'
        f'{deductions_rows}'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:0.5rem 0;margin-top:0.25rem;">'
        f'<span style="font-size:0.8125rem;font-weight:700;color:var(--gxp-danger);">Total Deductions</span>'
        f'<span style="font-size:0.9375rem;font-weight:800;color:var(--gxp-danger);">{_fmt(tot_ded)}</span>'
        f'</div>'
        f'</div>'

        # ── Summary column
        f'<div style="display:flex;flex-direction:column;justify-content:space-between;">'
        f'<div>'
        f'<div {col_h}>Employer Contributions</div>'
        f'{employer_rows}'
        f'</div>'
        f'<div style="margin-top:1.5rem;">'
        f'<div style="font-size:0.6875rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.1em;color:var(--gxp-text3);">NET PAY</div>'
        f'<div style="font-size:2.25rem;font-weight:800;color:var(--gxp-accent);'
        f'line-height:1.1;margin-top:0.25rem;">{_fmt(net)}</div>'
        f'</div>'
        f'</div>'

        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# Payroll Summary Totals
# ============================================================

def _render_period_totals(entries: dict, employees: list[dict]):
    """Show totals across all employees for this pay period."""
    computed = [entries[e["id"]] for e in employees if e["id"] in entries]

    if not computed:
        return

    st.markdown('<p class="gxp-page-label" style="margin-top:1.5rem;">PAY PERIOD TOTALS</p>', unsafe_allow_html=True)

    total_gross = sum(e["gross_pay"] for e in computed)
    total_sss_ee = sum(e["sss_employee"] for e in computed)
    total_ph_ee = sum(e["philhealth_employee"] for e in computed)
    total_pi_ee = sum(e["pagibig_employee"] for e in computed)
    total_wht = sum(e["withholding_tax"] for e in computed)
    total_sss_er = sum(e["sss_employer"] for e in computed)
    total_ph_er = sum(e["philhealth_employer"] for e in computed)
    total_pi_er = sum(e["pagibig_employer"] for e in computed)
    total_deductions = sum(e["total_deductions"] for e in computed)
    total_net = sum(e["net_pay"] for e in computed)
    total_er = total_sss_er + total_ph_er + total_pi_er

    st.markdown(
        f'<div style="background:var(--gxp-surface);border-radius:1rem;padding:1.25rem 2rem;'
        f'box-shadow:var(--gxp-m3-ambient-shadow);display:flex;align-items:center;gap:2.5rem;'
        f'margin:1.25rem 0;">'
        f'<div><div style="font-size:0.6875rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.1em;color:var(--gxp-text3);">Total Gross</div>'
        f'<div style="font-size:1.375rem;font-weight:800;color:var(--gxp-text);">{_fmt(total_gross)}</div></div>'
        f'<div style="width:1px;height:2.5rem;background:var(--gxp-border);"></div>'
        f'<div><div style="font-size:0.6875rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.1em;color:var(--gxp-text3);">Total Deductions</div>'
        f'<div style="font-size:1.375rem;font-weight:800;color:var(--gxp-danger);">{_fmt(total_deductions)}</div></div>'
        f'<div style="width:1px;height:2.5rem;background:var(--gxp-border);"></div>'
        f'<div><div style="font-size:0.6875rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.1em;color:var(--gxp-accent);">Net Payroll</div>'
        f'<div style="font-size:1.75rem;font-weight:800;color:var(--gxp-accent);">{_fmt(total_net)}</div></div>'
        f'<div style="width:1px;height:2.5rem;background:var(--gxp-border);"></div>'
        f'<div><div style="font-size:0.6875rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.1em;color:var(--gxp-text3);">Employer Cost</div>'
        f'<div style="font-size:1.375rem;font-weight:800;color:var(--gxp-text);">{_fmt(total_er)}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("**Government Remittances Due:**")
    rem_cols = st.columns(4)
    with rem_cols[0]:
        st.markdown(remit_card(
            "SSS", GOV_COLORS["SSS"],
            [("Employee", _fmt(total_sss_ee)), ("Employer", _fmt(total_sss_er))],
            ("Total", _fmt(total_sss_ee + total_sss_er)),
        ), unsafe_allow_html=True)
    with rem_cols[1]:
        st.markdown(remit_card(
            "PhilHealth", GOV_COLORS["PhilHealth"],
            [("Employee", _fmt(total_ph_ee)), ("Employer", _fmt(total_ph_er))],
            ("Total", _fmt(total_ph_ee + total_ph_er)),
        ), unsafe_allow_html=True)
    with rem_cols[2]:
        st.markdown(remit_card(
            "Pag-IBIG", GOV_COLORS["Pag-IBIG"],
            [("Employee", _fmt(total_pi_ee)), ("Employer", _fmt(total_pi_er))],
            ("Total", _fmt(total_pi_ee + total_pi_er)),
        ), unsafe_allow_html=True)
    with rem_cols[3]:
        st.markdown(remit_card(
            "BIR Withholding", GOV_COLORS["BIR"],
            [("Withholding Tax", _fmt(total_wht))],
            ("Total", _fmt(total_wht)),
        ), unsafe_allow_html=True)

    computed_count = len(computed)
    total_count = len(employees)
    if computed_count < total_count:
        st.warning(f"Only {computed_count} of {total_count} employees computed. Compute all before finalizing.")


# ============================================================
# Main Page Render
# ============================================================

def _render_payroll_processing():
    # ---- Payroll History Combination Chart ----
    st.subheader("Payroll History")

    history = _load_all_period_history()

    if not history:
        st.info("Chart will appear once you have at least one finalized pay period.")
    else:
        df_hist = pd.DataFrame(history)

        fig = go.Figure()

        # Grouped bars: Net Pay, Total Deductions, Employer Cost
        fig.add_trace(go.Bar(
            name="Net Pay",
            x=df_hist["period"],
            y=df_hist["net_pay"],
            marker_color="#2ca02c",
            offsetgroup=0,
        ))
        fig.add_trace(go.Bar(
            name="Total Deductions",
            x=df_hist["period"],
            y=df_hist["total_deductions"],
            marker_color="#d62728",
            offsetgroup=1,
        ))
        fig.add_trace(go.Bar(
            name="Employer Cost",
            x=df_hist["period"],
            y=df_hist["employer_cost"],
            marker_color="#ff7f0e",
            offsetgroup=2,
        ))

        # Line overlay: Total Gross Pay
        fig.add_trace(go.Scatter(
            name="Gross Pay",
            x=df_hist["period"],
            y=df_hist["gross_pay"],
            mode="lines+markers",
            line=dict(color="#1f77b4", width=3),
            marker=dict(size=8),
        ))

        fig.update_layout(
            barmode="group",
            title="Payroll Breakdown by Period",
            xaxis_title="Pay Period Start",
            yaxis_title="Amount (₱)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=56, b=0),
        )

        st.plotly_chart(fig, width="stretch")

    company = _load_company()
    daily_rate_divisor = int(company.get("daily_rate_divisor") or 26)

    employees = _load_employees()
    dept_map  = _load_departments_map()
    for emp in employees:
        emp["department"] = dept_map.get(emp["id"], "")

    if not employees:
        st.warning("No active employees. Add employees first in the Employee Master File.")
        return

    # --- Pay Period Selection ---
    period = _render_pay_period_selector()

    if period is None:
        return

    is_locked = period["status"] in ("reviewed", "finalized", "paid")

    # ── M3 Status bar ─────────────────────────────────────────────────────
    _status = period["status"]
    _status_colors = {
        "draft":     ("var(--gxp-text2)",  "var(--gxp-m3-surface-container)"),
        "reviewed":  ("var(--gxp-warning-fg)", "var(--gxp-warning-bg)"),
        "finalized": ("var(--gxp-accent-fg)", "var(--gxp-accent-bg)"),
        "paid":      ("var(--gxp-success-fg)", "var(--gxp-success-bg)"),
    }
    _sc, _sbg = _status_colors.get(_status, ("var(--gxp-text2)", "var(--gxp-m3-surface-container)"))
    _reviewer_str = ""
    if period.get("reviewed_by"):
        _rat = period["reviewed_at"][:16].replace("T", " ") if period.get("reviewed_at") else ""
        _reviewer_str = f'<span style="color:var(--gxp-text3);font-size:0.75rem;"> · Reviewed by {period["reviewed_by"]} ({_rat})</span>'

    st.markdown(
        f'<div style="background:var(--gxp-surface);border-radius:1rem;padding:1rem 1.5rem;'
        f'display:flex;align-items:center;justify-content:space-between;'
        f'box-shadow:var(--gxp-m3-ambient-shadow);margin-bottom:1rem;">'
        f'<div style="display:flex;align-items:center;gap:2rem;">'
        f'<div><div style="font-size:0.6875rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.1em;color:var(--gxp-text3);">Period</div>'
        f'<div style="font-size:0.875rem;font-weight:600;">{period["period_start"]} – {period["period_end"]}</div></div>'
        f'<div style="width:1px;height:2rem;background:var(--gxp-border);"></div>'
        f'<div><div style="font-size:0.6875rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.1em;color:var(--gxp-text3);">Status</div>'
        f'<div style="display:inline-block;background:{_sbg};color:{_sc};'
        f'padding:0.15rem 0.75rem;border-radius:9999px;font-size:0.75rem;font-weight:700;">'
        f'{_status.upper()}</div>{_reviewer_str}</div>'
        f'<div style="width:1px;height:2rem;background:var(--gxp-border);"></div>'
        f'<div><div style="font-size:0.6875rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.1em;color:var(--gxp-text3);">Headcount</div>'
        f'<div style="font-size:0.875rem;font-weight:600;">{len(employees)} employees</div></div>'
        f'<div style="width:1px;height:2rem;background:var(--gxp-border);"></div>'
        f'<div><div style="font-size:0.6875rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.1em;color:var(--gxp-text3);">Payment Date</div>'
        f'<div style="font-size:0.875rem;font-weight:600;">{period["payment_date"]}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    if is_locked:
        col_msg, col_btn = st.columns([4, 1])
        with col_msg:
            if period["status"] == "reviewed":
                st.info("This pay period is under review. Earnings are read-only.")
            else:
                st.info("This pay period is finalized. Earnings are read-only.")
        with col_btn:
            st.write("")  # spacer
            if st.button("Reopen for Editing", width="stretch"):
                _update_pay_period(period["id"], {"status": "draft", "reviewed_by": None, "reviewed_at": None})
                log_action("updated", "pay_period", period["id"], f"{period['period_start']} to {period['period_end']}", {"status": "draft (reopened)"})
                st.rerun()

    # ── Filter bar ────────────────────────────────────────────
    all_positions = sorted({(e.get("position") or "").strip() for e in employees} - {""})
    all_depts     = sorted({(e.get("department") or "").strip() for e in employees} - {""})
    _dept_names_structured = _load_dept_names_from_table()
    if _dept_names_structured:
        all_depts = _dept_names_structured
    pp_s, pp_p, pp_d = st.columns([2, 1.5, 1.5])
    with pp_s:
        pp_search   = st.text_input("Search employees", placeholder="Name or employee no…",
                                    label_visibility="collapsed", key="pp_search")
    with pp_p:
        pp_sel_pos  = st.multiselect("Position",   all_positions, key="pp_f_pos",  placeholder="All positions")
    with pp_d:
        pp_sel_dept = st.multiselect("Department", all_depts,     key="pp_f_dept", placeholder="All departments")

    def _pp_match(emp):
        if pp_search:
            q = pp_search.lower()
            name = f"{emp['last_name']} {emp['first_name']}".lower()
            if q not in name and q not in (emp.get("employee_no") or "").lower():
                return False
        if pp_sel_pos  and (emp.get("position") or "") not in pp_sel_pos:
            return False
        if pp_sel_dept and (emp.get("department") or "") not in pp_sel_dept:
            return False
        return True

    employees = [e for e in employees if _pp_match(e)]

    # --- Load payroll entries for this period ---
    entries = _load_payroll_entries(period["id"])

    # --- Employee payroll entries with M3 progress header ---
    computed_count = sum(1 for e in employees if e["id"] in entries)
    _pct = int(computed_count / len(employees) * 100) if employees else 0
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin:1.25rem 0 0.75rem;">'
        f'<div>'
        f'<span class="gxp-page-label" style="margin:0;">EMPLOYEES</span>'
        f'<span style="font-size:0.8125rem;color:var(--gxp-text3);margin-left:0.5rem;">'
        f'{computed_count} of {len(employees)} computed</span>'
        f'</div>'
        f'<span style="font-size:0.8125rem;font-weight:700;color:var(--gxp-accent);">{_pct}%</span>'
        f'</div>'
        f'<div style="height:4px;background:var(--gxp-border);border-radius:9999px;margin-bottom:1rem;">'
        f'<div style="height:4px;width:{_pct}%;background:var(--gxp-accent);border-radius:9999px;'
        f'transition:width 0.3s ease;"></div></div>',
        unsafe_allow_html=True,
    )

    for emp in employees:
        _render_employee_payroll(emp, period["id"], is_locked, entries, period, daily_rate_divisor)

    # --- Period totals ---
    _render_period_totals(entries, employees)

    # --- Workflow buttons ---
    if period["status"] == "draft":
        st.divider()
        all_computed = all(e["id"] in entries for e in employees)

        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            if st.button(
                "Submit for Review",
                type="primary",
                disabled=not all_computed,
                width="stretch",
            ):
                _update_pay_period(period["id"], {"status": "reviewed"})
                log_action("reviewed", "pay_period", period["id"], f"{period['period_start']} to {period['period_end']}")
                st.success("Pay period submitted for review.")
                st.rerun()

        if not all_computed:
            st.caption("Compute all employees before submitting for review.")

    elif period["status"] == "reviewed":
        st.divider()
        reviewer_name = st.text_input("Reviewer Name", placeholder="e.g. Juan dela Cruz")
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            if st.button(
                "Approve & Finalize",
                type="primary",
                disabled=not reviewer_name.strip(),
                width="stretch",
            ):
                from datetime import datetime
                _update_pay_period(period["id"], {
                    "status": "finalized",
                    "reviewed_by": reviewer_name.strip(),
                    "reviewed_at": datetime.now().isoformat(),
                })
                log_action("finalized", "pay_period", period["id"], f"{period['period_start']} to {period['period_end']}", {"reviewed_by": reviewer_name.strip()})
                st.success(f"Approved by {reviewer_name.strip()}. Pay period finalized!")
                st.rerun()

        if not reviewer_name.strip():
            st.caption("Enter reviewer name to approve and finalize.")

    elif period["status"] == "finalized":
        st.divider()
        col1, col2, col3 = st.columns([2, 1, 1])
        with col3:
            if st.button("Mark as Paid", width="stretch"):
                _update_pay_period(period["id"], {"status": "paid"})
                log_action("paid", "pay_period", period["id"], f"{period['period_start']} to {period['period_end']}")
                st.rerun()


def _render_payslips_tab():
    """Payslip selection, filtering, and PDF download — embedded in Payroll Run."""
    from reports.payslip_pdf import generate_payslip_pdf, generate_all_payslips_pdf

    # ── Period selector ────────────────────────────────────────────────────
    all_periods = _load_pay_periods()

    if not all_periods:
        st.info("No pay periods found. Create one in Payroll Processing first.")
        return

    col_sel, col_new_btn = st.columns([4, 1])
    with col_sel:
        period_labels = {
            p["id"]: f"{p['period_start']} to {p['period_end']}  [{p['status'].upper()}]"
            for p in all_periods
        }
        selected_id = st.selectbox(
            "Select Pay Period",
            options=[p["id"] for p in all_periods],
            format_func=lambda x: period_labels[x],
            index=0,
            key="payslip_period_select",
        )
    period = next(p for p in all_periods if p["id"] == selected_id)

    if period["status"] == "draft":
        st.warning("This pay period is still a draft. Finalize it in Payroll Processing before generating payslips.")
        return

    # ── Load data ──────────────────────────────────────────────────────────
    company      = _load_company()
    all_employees = _load_employees()
    entries      = _load_payroll_entries(period["id"])

    done_emps    = [e for e in all_employees if e["id"] in entries]
    pending_emps = [e for e in all_employees if e["id"] not in entries]

    st.markdown(
        f'<div style="display:flex;gap:16px;align-items:center;margin:8px 0 12px;">'
        f'<span style="font-size:13px;color:var(--gxp-text2);">'
        f'<strong style="color:var(--gxp-text);">{len(done_emps)}</strong> computed &nbsp;·&nbsp; '
        f'<strong style="color:var(--gxp-warning);">{len(pending_emps)}</strong> pending</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Filters & Sort ────────────────────────────────────────────────────
    dept_map_ps = _load_departments_map()
    for emp in all_employees:
        emp["department"] = dept_map_ps.get(emp["id"], "")

    all_depts_ps = sorted({e.get("department") or "" for e in all_employees} - {""})
    _dept_names_structured = _load_dept_names_from_table()
    if _dept_names_structured:
        all_depts_ps = _dept_names_structured
    all_pos_ps   = sorted({e.get("position") or "" for e in all_employees} - {""})

    ps_s, ps_p, ps_d = st.columns([2, 1.5, 1.5])
    with ps_s:
        f_name = st.text_input("Search", placeholder="Name or employee no…",
                               label_visibility="collapsed", key="ps_f_name")
    with ps_p:
        f_pos  = st.multiselect("Position",   all_pos_ps,   key="ps_f_pos",  placeholder="All positions")
    with ps_d:
        f_dept = st.multiselect("Department", all_depts_ps, key="ps_f_dept", placeholder="All departments")

    ps_sort_col, _ = st.columns([2, 3])
    with ps_sort_col:
        sort_by = st.selectbox(
            "Sort by",
            ["Name (A-Z)", "Name (Z-A)", "Net Pay (High-Low)", "Net Pay (Low-High)", "Department"],
            key="ps_sort",
        )

    def _apply_filters(emp_list):
        result = emp_list
        if f_name:
            q = f_name.lower()
            result = [e for e in result if q in f"{e.get('last_name','')} {e.get('first_name','')}".lower()
                      or q in (e.get("employee_no") or "").lower()]
        if f_dept:
            result = [e for e in result if (e.get("department") or "") in f_dept]
        if f_pos:
            result = [e for e in result if (e.get("position") or "") in f_pos]
        # Sort
        if sort_by == "Name (A-Z)":
            result = sorted(result, key=lambda e: f"{e.get('last_name','')} {e.get('first_name','')}".lower())
        elif sort_by == "Name (Z-A)":
            result = sorted(result, key=lambda e: f"{e.get('last_name','')} {e.get('first_name','')}".lower(), reverse=True)
        elif sort_by == "Net Pay (High-Low)":
            result = sorted(result, key=lambda e: entries.get(e["id"], {}).get("net_pay", 0), reverse=True)
        elif sort_by == "Net Pay (Low-High)":
            result = sorted(result, key=lambda e: entries.get(e["id"], {}).get("net_pay", 0))
        elif sort_by == "Department":
            result = sorted(result, key=lambda e: (e.get("department") or "").lower())
        return result

    done_filtered    = _apply_filters(done_emps)
    pending_filtered = _apply_filters(pending_emps)

    # ── Select All + Generate Selected ────────────────────────────────────
    col_sel_all, col_gen_sel, col_gen_all = st.columns([1, 2, 2])
    with col_sel_all:
        select_all = st.checkbox("Select All", key="ps_select_all")
    with col_gen_sel:
        gen_selected = st.button(
            "Generate Selected Payslips",
            type="primary",
            use_container_width=True,
            icon="⬇️",
            key="ps_gen_selected",
        )
    with col_gen_all:
        if done_emps:
            all_pdf_bytes = generate_all_payslips_pdf(company, done_emps, period, entries)
            st.download_button(
                label="Download All Payslips (PDF)",
                data=all_pdf_bytes,
                file_name=f"payslips_{period['period_start']}_to_{period['period_end']}.pdf",
                mime="application/pdf",
                use_container_width=True,
                icon="📄",
                key="ps_dl_all",
            )

    st.divider()

    # ── Track selections ─────────────────────────────────────────────────
    selected_ids: list[str] = []

    # ── Done column ───────────────────────────────────────────────────────
    col_done, col_pending = st.columns(2)

    with col_done:
        st.markdown(
            '<div style="background:var(--gxp-success-bg);color:var(--gxp-success-fg);'
            'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;'
            'padding:4px 10px;border-radius:4px;margin-bottom:8px;display:inline-block;">'
            f'Done ({len(done_filtered)})</div>',
            unsafe_allow_html=True,
        )
        for emp in done_filtered:
            entry = entries[emp["id"]]
            emp_key = f"ps_chk_{emp['id']}"
            # Pre-set state before widget instantiation to avoid the
            # "default value + Session State API" conflict warning.
            if select_all:
                st.session_state[emp_key] = True

            row_c1, row_c2, row_c3 = st.columns([0.4, 3, 2])
            with row_c1:
                is_checked = st.checkbox("", key=emp_key, label_visibility="collapsed")
            with row_c2:
                emp_no   = emp.get("employee_no") or ""
                name     = f"{emp.get('last_name', '')}, {emp.get('first_name', '')}"
                position = emp.get("position") or ""
                dept     = emp.get("department") or ""
                sub_line = " · ".join(filter(None, [position, dept]))
                st.markdown(
                    f'<div style="padding:2px 0;">'
                    f'<div style="font-size:10px;color:var(--gxp-text2);">{emp_no}</div>'
                    f'<div style="font-size:13px;font-weight:600;color:var(--gxp-text);">{name}</div>'
                    f'<div style="font-size:11px;color:var(--gxp-text2);">{sub_line}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with row_c3:
                net = entry.get("net_pay", 0)
                st.markdown(
                    f'<div style="text-align:right;padding:2px 0;">'
                    f'<div style="font-size:13px;font-weight:600;color:var(--gxp-success);">'
                    f'₱{net/100:,.2f}</div>'
                    f'<div style="font-size:11px;color:var(--gxp-text2);">Net Pay</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            if is_checked:
                selected_ids.append(emp["id"])

            # Individual download
            pdf_bytes = generate_payslip_pdf(company, emp, period, entry)
            st.download_button(
                label="Download",
                data=pdf_bytes,
                file_name=f"payslip_{emp['employee_no']}_{period['period_start']}.pdf",
                mime="application/pdf",
                key=f"ps_dl_{emp['id']}",
                use_container_width=True,
                icon="⬇️",
            )
            st.markdown("<hr style='border:none;border-top:1px solid var(--gxp-border);margin:4px 0;'>", unsafe_allow_html=True)

    with col_pending:
        if pending_filtered:
            st.markdown(
                '<div style="background:var(--gxp-warning-bg);color:var(--gxp-warning-fg);'
                'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;'
                'padding:4px 10px;border-radius:4px;margin-bottom:8px;display:inline-block;">'
                f'Pending ({len(pending_filtered)})</div>',
                unsafe_allow_html=True,
            )
            for emp in pending_filtered:
                name = f"{emp.get('last_name', '')}, {emp.get('first_name', '')}"
                dept = emp.get("department") or ""
                st.markdown(
                    f'<div style="padding:6px 0;border-bottom:1px solid var(--gxp-border);">'
                    f'<div style="font-size:13px;color:var(--gxp-text2);">{name}</div>'
                    f'<div style="font-size:11px;color:var(--gxp-text3);">{dept} — Not yet computed</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div style="color:var(--gxp-text3);font-size:13px;text-align:center;'
                'padding:24px 0;">All employees computed</div>',
                unsafe_allow_html=True,
            )

    # ── Generate Selected ─────────────────────────────────────────────────
    if gen_selected:
        if not selected_ids:
            st.warning("No employees selected. Check the boxes on the left.")
        else:
            sel_emps = [e for e in done_emps if e["id"] in selected_ids]
            pdf_bytes = generate_all_payslips_pdf(company, sel_emps, period, entries)
            st.download_button(
                label=f"Download {len(sel_emps)} Payslip(s) (PDF)",
                data=pdf_bytes,
                file_name=f"payslips_selected_{period['period_start']}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                key="ps_dl_selected_result",
            )


def render():
    inject_css()
    st.markdown(
        '<p class="gxp-page-label">PAYROLL RUN</p>'
        '<h1 style="font-size:2.75rem;font-weight:300;letter-spacing:-0.02em;'
        'margin:0 0 1.5rem;line-height:1.1;">Payroll Run</h1>',
        unsafe_allow_html=True,
    )

    tab_run, tab_payslips = st.tabs(["📋 Payroll Processing", "🧾 Payslips"])

    with tab_run:
        _render_payroll_processing()

    with tab_payslips:
        _render_payslips_tab()

