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

@st.cache_data(ttl=600, show_spinner=False)
def _load_company(_cid: str = "") -> dict:
    """Load the current company record. Cached 10 min."""
    db = get_db()
    result = (
        db.table("companies")
        .select("*")
        .eq("id", _cid or get_company_id())
        .single()
        .execute()
    )
    return result.data or {}


@st.cache_data(ttl=300, show_spinner=False)
def _load_departments_map(_cid: str = "") -> dict:
    """Return {employee_id: department}. Cached 5 min."""
    try:
        db  = get_db()
        cid = _cid or get_company_id()
        emp_ids = [r["id"] for r in db.table("employees").select("id").eq("company_id", cid).execute().data or []]
        if not emp_ids:
            return {}
        rows = db.table("employee_profiles").select("employee_id, department").in_("employee_id", emp_ids).execute().data or []
        return {r["employee_id"]: (r.get("department") or "") for r in rows}
    except Exception:
        return {}


@st.cache_data(ttl=600, show_spinner=False)
def _load_dept_names_from_table(_cid: str = "") -> list[str]:
    """Load structured department names. Cached 10 min."""
    try:
        db = get_db()
        result = (
            db.table("departments")
            .select("name")
            .eq("company_id", _cid or get_company_id())
            .eq("is_active", True)
            .order("name")
            .execute()
        )
        return [r["name"] for r in (result.data or [])]
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def _load_employees(_cid: str = "") -> list[dict]:
    """Load active employees. Cached 5 min."""
    db = get_db()
    result = (
        db.table("employees")
        .select("*")
        .eq("company_id", _cid or get_company_id())
        .eq("is_active", True)
        .order("last_name")
        .execute()
    )
    return result.data


@st.cache_data(ttl=120, show_spinner=False)
def _load_pay_periods(_cid: str = "") -> list[dict]:
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
    # Invalidate related caches
    _load_pay_periods.clear()
    _load_all_period_history.clear()
    _load_all_period_history_detailed.clear()
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

@st.cache_data(ttl=120, show_spinner=False)
def _load_all_period_history(cid: str = "") -> list[dict]:
    """Load aggregate totals for all finalized/paid periods — used for the trend chart.
    Cached for 2 minutes; cid param ensures per-company isolation."""
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
        govt_ee = sum(
            e["sss_employee"] + e["philhealth_employee"] + e["pagibig_employee"]
            for e in entries
        ) / 100
        tax = sum(e["withholding_tax"] for e in entries) / 100
        rows.append({
            "period": p["period_start"],
            "gross_pay":       sum(e["gross_pay"]         for e in entries) / 100,
            "total_deductions":sum(e["total_deductions"]  for e in entries) / 100,
            "net_pay":         sum(e["net_pay"]           for e in entries) / 100,
            "govt_ee":         govt_ee,
            "tax":             tax,
            "employer_cost":   sum(
                e["sss_employer"] + e["philhealth_employer"] + e["pagibig_employer"]
                for e in entries
            ) / 100,
        })
    return rows


@st.cache_data(ttl=120, show_spinner=False)
def _load_all_period_history_detailed(cid: str = "") -> list[dict]:
    """Load per-employee payroll data for all finalized periods — for analytics drill-down.
    Cached for 2 minutes; cid param ensures per-company isolation."""
    cid = cid or get_company_id()
    db = get_db()
    cid = get_company_id()
    periods_result = (
        db.table("pay_periods")
        .select("id, period_start, status")
        .eq("company_id", cid)
        .in_("status", ["finalized", "paid"])
        .order("period_start", desc=False)
        .execute()
    )
    # Load all employees + departments
    emps = (
        db.table("employees").select("id, first_name, last_name, position")
        .eq("company_id", cid).execute().data or []
    )
    emp_map = {e["id"]: f"{e['last_name']}, {e['first_name']}" for e in emps}

    profiles = (
        db.table("employee_profiles").select("employee_id, department_id")
        .eq("company_id", cid).execute().data or []
    )
    dept_by_emp = {p["employee_id"]: p.get("department_id") for p in profiles}

    depts = (
        db.table("departments").select("id, name")
        .eq("company_id", cid).execute().data or []
    )
    dept_name_map = {d["id"]: d["name"] for d in depts}

    # Also map by text department from profiles
    profiles_txt = (
        db.table("employee_profiles").select("employee_id, department")
        .eq("company_id", cid).execute().data or []
    )
    dept_txt_by_emp = {p["employee_id"]: (p.get("department") or "").strip() for p in profiles_txt}

    rows = []
    for p in periods_result.data:
        entries = (
            db.table("payroll_entries").select("*")
            .eq("pay_period_id", p["id"]).execute().data or []
        )
        for e in entries:
            eid = e["employee_id"]
            dept_id = dept_by_emp.get(eid)
            dept_name = dept_name_map.get(dept_id, "") if dept_id else ""
            if not dept_name:
                dept_name = dept_txt_by_emp.get(eid, "Unassigned") or "Unassigned"

            govt_ee = (e["sss_employee"] + e["philhealth_employee"] + e["pagibig_employee"]) / 100
            rows.append({
                "period": p["period_start"],
                "employee_id": eid,
                "employee_name": emp_map.get(eid, "Unknown"),
                "department": dept_name,
                "gross_pay": e["gross_pay"] / 100,
                "net_pay": e["net_pay"] / 100,
                "govt_ee": govt_ee,
                "tax": e["withholding_tax"] / 100,
                "total_deductions": e["total_deductions"] / 100,
                "employer_cost": (e["sss_employer"] + e["philhealth_employer"] + e["pagibig_employer"]) / 100,
            })
    return rows


def _render_pay_period_selector() -> dict | None:
    """Render pay period creation and selection. Returns selected period or None."""
    periods = _load_pay_periods(_cid=get_company_id())

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
        company = _load_company(_cid=get_company_id())
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
                        st.toast(f"📅 Created pay period: {p_start} to {p_end}", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating pay period: {e}")

        st.divider()

    return selected_period


# ============================================================
# Earnings Input & Computation per Employee
# ============================================================

def _pr_avatar_inner(emp_id: str, initials: str, photo_urls: dict | None) -> str:
    """Return inner HTML for avatar — photo if available, else initials."""
    if photo_urls and emp_id in photo_urls:
        url = photo_urls[emp_id]
        return (
            f'<img src="{url}" style="width:100%;height:100%;object-fit:cover;" '
            f'onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';">'
            f'<span style="color:#fff;font-weight:700;font-size:14px;display:none;'
            f'width:100%;height:100%;align-items:center;justify-content:center;">{initials}</span>'
        )
    return f'<span style="color:#fff;font-weight:700;font-size:14px;">{initials}</span>'


@st.cache_data(ttl=300, show_spinner=False)
def _load_pr_photo_urls(_cid: str = "") -> dict:
    """Load photo URLs for all employees. Cached 5 min."""
    try:
        rows = (
            get_db().table("employee_profiles")
            .select("employee_id, photo_url")
            .eq("company_id", get_company_id())
            .not_.is_("photo_url", "null")
            .execute()
            .data or []
        )
        return {r["employee_id"]: r["photo_url"] for r in rows if r.get("photo_url")}
    except Exception:
        return {}


def _render_employee_card_row(
    emp: dict,
    entries: dict,
    photo_urls: dict | None = None,
):
    """Render a compact employee row card for the payroll list."""
    name       = f"{emp['first_name']} {emp['last_name']}"
    is_computed = emp["id"] in entries
    _initials  = (emp['first_name'][:1] + emp['last_name'][:1]).upper()
    _colors    = ["#005bc1","#006e2d","#795900","#ba1a1a","#4b0082","#006064","#37474f","#880e4f"]
    _color     = _colors[hash(emp["id"]) % len(_colors)]
    _pos       = emp.get("position") or "—"
    _dept      = emp.get("department") or "—"
    _salary_lbl = _fmt(emp["basic_salary"])

    if is_computed:
        _badge = (
            '<span style="background:#d4edda;color:#155724;padding:2px 8px;'
            'border-radius:9999px;font-size:10px;font-weight:700;">&#10003; COMPUTED</span>'
        )
        _net_val = entries[emp["id"]].get("net_pay", 0)
        _gross_val = entries[emp["id"]].get("gross_pay", 0)
        _amount_html = (
            f'<div style="text-align:right;">'
            f'<div style="font-size:14px;font-weight:800;color:var(--gxp-accent);">{_fmt(_net_val)}</div>'
            f'<div style="font-size:10px;color:var(--gxp-text3);">Gross {_fmt(_gross_val)}</div>'
            f'</div>'
        )
    else:
        _badge = (
            '<span style="background:#fff3cd;color:#856404;padding:2px 8px;'
            'border-radius:9999px;font-size:10px;font-weight:700;">&#9675; PENDING</span>'
        )
        _amount_html = (
            f'<div style="text-align:right;">'
            f'<div style="font-size:11px;color:var(--gxp-text3);">Basic {_salary_lbl}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="gxp-pr-emp-row" data-pr-emp="{emp["id"]}" style="'
        f'display:flex;align-items:center;gap:12px;padding:10px 14px;'
        f'background:var(--gxp-surface);border-radius:12px;cursor:pointer;'
        f'border:1px solid var(--gxp-border);margin-bottom:4px;'
        f'transition:box-shadow 0.15s,transform 0.15s;">'
        # Avatar
        f'<div style="width:40px;height:40px;border-radius:50%;background:{_color};'
        f'display:flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden;">'
        f'{_pr_avatar_inner(emp["id"], _initials, photo_urls)}</div>'
        # Name + details
        f'<div style="flex:1;min-width:0;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:13px;font-weight:700;color:var(--gxp-text);">{name}</span>'
        f'{_badge}</div>'
        f'<div style="font-size:11px;color:var(--gxp-text3);">{emp.get("employee_no","")}</div>'
        f'<div style="font-size:11px;color:var(--gxp-text3);">{_pos}</div>'
        f'</div>'
        # Amount
        f'{_amount_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_payslip_card(emp, is_done, entries, photo_urls, company, period, select_all):
    """Render a single payslip card matching the payroll processing card style."""
    from reports.payslip_pdf import generate_payslip_pdf

    name = f"{emp['first_name']} {emp['last_name']}"
    _initials = (emp['first_name'][:1] + emp['last_name'][:1]).upper()
    _colors = ["#005bc1", "#006e2d", "#795900", "#ba1a1a", "#4b0082", "#006064", "#37474f", "#880e4f"]
    _color = _colors[hash(emp["id"]) % len(_colors)]
    _pos = emp.get("position") or "—"
    _dept = emp.get("department") or "—"

    if is_done:
        entry = entries[emp["id"]]
        _net_val = entry.get("net_pay", 0)
        _gross_val = entry.get("gross_pay", 0)
        _badge = (
            '<span style="background:#d4edda;color:#155724;padding:2px 8px;'
            'border-radius:9999px;font-size:10px;font-weight:700;">&#10003; READY</span>'
        )
        _amount_html = (
            f'<div style="text-align:right;">'
            f'<div style="font-size:14px;font-weight:800;color:var(--gxp-accent);">{_fmt(_net_val)}</div>'
            f'<div style="font-size:10px;color:var(--gxp-text3);">Gross {_fmt(_gross_val)}</div>'
            f'</div>'
        )
    else:
        _badge = (
            '<span style="background:#fff3cd;color:#856404;padding:2px 8px;'
            'border-radius:9999px;font-size:10px;font-weight:700;">&#9675; PENDING</span>'
        )
        _amount_html = (
            '<div style="text-align:right;">'
            '<div style="font-size:11px;color:var(--gxp-text3);">Not computed</div>'
            '</div>'
        )

    # ── Build swipe action tray (left side, revealed on hover) ──
    if is_done:
        _action_tray = (
            '<div class="ps-swipe-act" style="background:#005bc1;color:#fff;font-size:20px;" '
            f'data-ps-action="dl_{emp["id"]}">&#11015;<br>'
            '<span style="font-size:9px;font-weight:700;">Download</span></div>'
        )
    else:
        _action_tray = (
            '<div class="ps-swipe-act" style="background:#9ca3af;color:#fff;font-size:14px;">'
            '<span style="font-size:9px;font-weight:700;">Pending</span></div>'
        )

    # Card HTML with swipe wrapper
    st.markdown(
        f'<div class="ps-swipe-wrap">'
        f'<div class="ps-swipe-actions">{_action_tray}</div>'
        f'<div class="ps-swipe-card" style="'
        f'display:flex;align-items:center;gap:12px;padding:10px 14px;'
        f'background:var(--gxp-surface);border-radius:12px;'
        f'border:1px solid var(--gxp-border);">'
        # Avatar
        f'<div style="width:40px;height:40px;border-radius:50%;background:{_color};'
        f'display:flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden;">'
        f'{_pr_avatar_inner(emp["id"], _initials, photo_urls)}</div>'
        # Name + details
        f'<div style="flex:1;min-width:0;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:13px;font-weight:700;color:var(--gxp-text);">{name}</span>'
        f'{_badge}</div>'
        f'<div style="font-size:11px;color:var(--gxp-text3);">{emp.get("employee_no","")}</div>'
        f'<div style="font-size:11px;color:var(--gxp-text3);">{_pos}</div>'
        f'</div>'
        # Amount
        f'{_amount_html}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Hidden Streamlit widgets for computed employees (triggered by swipe action JS)
    if is_done:
        entry = entries[emp["id"]]
        pdf_bytes = generate_payslip_pdf(company, emp, period, entry)
        st.download_button(
            label="_",
            data=pdf_bytes,
            file_name=f"payslip_{emp['employee_no']}_{period['period_start']}.pdf",
            mime="application/pdf",
            key=f"ps_dl_{emp['id']}",
        )


@st.dialog("Payroll Computation", width="large")
def _payroll_computation_dialog(
    emp_id: str,
    period_id: str,
    is_finalized: bool,
    period: dict | None = None,
    daily_rate_divisor: int = 26,
):
    """Dialog for computing/viewing payroll for one employee."""
    db = get_db()
    cid = get_company_id()

    # Load employee
    emp_resp = db.table("employees").select("*").eq("id", emp_id).eq("company_id", cid).execute()
    if not emp_resp.data:
        st.error("Employee not found.")
        return
    emp = emp_resp.data[0]

    # Load existing entry
    entry_resp = (
        db.table("payroll_entries")
        .select("*")
        .eq("pay_period_id", period_id)
        .eq("employee_id", emp_id)
        .execute()
    )
    saved = entry_resp.data[0] if entry_resp.data else {}

    name = f"{emp['first_name']} {emp['last_name']}"
    _initials = (emp['first_name'][:1] + emp['last_name'][:1]).upper()
    _colors = ["#005bc1","#006e2d","#795900","#ba1a1a","#4b0082","#006064","#37474f","#880e4f"]
    _color = _colors[hash(emp["id"]) % len(_colors)]
    _pos = emp.get("position") or "—"

    # Header
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;padding-bottom:12px;'
        f'border-bottom:1px solid var(--gxp-border);margin-bottom:16px;">'
        f'<div style="width:48px;height:48px;border-radius:50%;background:{_color};'
        f'display:flex;align-items:center;justify-content:center;">'
        f'<span style="color:#fff;font-weight:700;font-size:16px;">{_initials}</span></div>'
        f'<div><div style="font-size:15px;font-weight:700;">{name}</div>'
        f'<div style="font-size:12px;color:var(--gxp-text3);">'
        f'{_pos} &middot; {emp.get("employee_no","")} &middot; Basic {_fmt(emp["basic_salary"])}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # If finalized, just show summary
    if is_finalized and saved:
        _render_payroll_summary(saved)
        return

    # ── DTR Insights ──────────────────────────────────────────
    if period and not is_finalized:
        _p_start = period.get("period_start", "")
        _p_end   = period.get("period_end", "")
        if _p_start and _p_end:
            _dtr  = _load_dtr_summary_for_period(emp["id"], _p_start, _p_end)
            _appr_ot_h = _load_approved_ot_hours(emp["id"], _p_start, _p_end)
            _hr   = _hourly_rate_centavos(emp, daily_rate_divisor)

            _nsd_sugg   = _hr * _dtr["nsd_hours"] * 0.10
            _ot_sugg    = _hr * _appr_ot_h        * 1.25
            _bs = emp.get("basic_salary") or 0
            _salary_type = (emp.get("salary_type") or "monthly").lower()
            _daily_rate  = _bs if _salary_type == "daily" else int(_bs / daily_rate_divisor)
            _absent_sugg = _daily_rate * _dtr["absent_days"]

            if _dtr["nsd_hours"] > 0 or _appr_ot_h > 0 or _dtr["ot_hours"] > 0 or _dtr["absent_days"] > 0:
                with st.expander("DTR Insights for this period", expanded=_dtr["absent_days"] > 0):
                    _di1, _di2, _di3 = st.columns(3)
                    _di1.metric("NSD Hours", f"{_dtr['nsd_hours']:.2f} h",
                                help="10 PM–6 AM hours per DTR")
                    _di2.metric("Approved OT", f"{_appr_ot_h:.2f} h")
                    _di3.metric("Absent Days", f"{_dtr['absent_days']} day(s)",
                                delta=f"-{_fmt(_absent_sugg)}" if _dtr["absent_days"] > 0 else None,
                                delta_color="inverse")

    # ── Earnings form ─────────────────────────────────────────
    with st.form(key=f"dlg_earn_{period_id}_{emp_id}"):
        st.markdown("**Earnings**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            basic_pay = st.number_input(
                "Basic Pay (₱)", min_value=0.0,
                value=_centavos_to_pesos(saved.get("basic_pay", emp["basic_salary"])),
                step=100.0, format="%.2f",
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
            )
        with col3:
            holiday_pay = st.number_input(
                "Holiday Pay (₱)", min_value=0.0,
                value=_centavos_to_pesos(saved.get("holiday_pay", 0)),
                step=100.0, format="%.2f",
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
            )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            allowances_nt = st.number_input(
                "Non-Taxable Allow. (₱)", min_value=0.0,
                value=_centavos_to_pesos(saved.get("allowances_nontaxable", 0)),
                step=100.0, format="%.2f",
            )
        with col2:
            allowances_t = st.number_input(
                "Taxable Allow. (₱)", min_value=0.0,
                value=_centavos_to_pesos(saved.get("allowances_taxable", 0)),
                step=100.0, format="%.2f",
            )
        with col3:
            commission = st.number_input(
                "Commission (₱)", min_value=0.0,
                value=_centavos_to_pesos(saved.get("commission", 0)),
                step=100.0, format="%.2f",
            )
        with col4:
            thirteenth = st.number_input(
                "13th Month (₱)", min_value=0.0,
                value=_centavos_to_pesos(saved.get("thirteenth_month_accrual", 0)),
                step=100.0, format="%.2f",
            )

        st.markdown("**Other Deductions**")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
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
                "Absent Ded. (₱)", min_value=0.0,
                value=_centavos_to_pesos(_absent_default or 0),
                step=100.0, format="%.2f",
            )
        with col2:
            sss_loan = st.number_input(
                "SSS Loan (₱)", min_value=0.0,
                value=_centavos_to_pesos(saved.get("sss_loan", 0)),
                step=100.0, format="%.2f",
            )
        with col3:
            pagibig_loan = st.number_input(
                "Pag-IBIG Loan (₱)", min_value=0.0,
                value=_centavos_to_pesos(saved.get("pagibig_loan", 0)),
                step=100.0, format="%.2f",
            )
        with col4:
            cash_advance = st.number_input(
                "Cash Advance (₱)", min_value=0.0,
                value=_centavos_to_pesos(saved.get("cash_advance", 0)),
                step=100.0, format="%.2f",
            )
        with col5:
            other_ded = st.number_input(
                "Other Ded. (₱)", min_value=0.0,
                value=_centavos_to_pesos(saved.get("other_deductions", 0)),
                step=100.0, format="%.2f",
            )

        computed = st.form_submit_button("Compute & Save", type="primary", use_container_width=True)

    if computed:
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

        gross = basic_c + ot_c + hol_c + nd_c + ant_c + at_c + comm_c + thirteenth_c - absent_c
        gross = max(gross, 0)

        result = compute_payroll(gross_pay=gross, nontaxable_allowances=ant_c)
        vol_deductions = sssl_c + pil_c + ca_c + other_c

        entry_data = {
            "basic_pay": basic_c, "overtime_pay": ot_c,
            "holiday_pay": hol_c, "night_differential": nd_c,
            "allowances_nontaxable": ant_c, "allowances_taxable": at_c,
            "commission": comm_c, "thirteenth_month_accrual": thirteenth_c,
            "absent_deduction": absent_c, "gross_pay": gross,
            "sss_employee": result.sss_employee,
            "philhealth_employee": result.philhealth_employee,
            "pagibig_employee": result.pagibig_employee,
            "sss_employer": result.sss_employer,
            "philhealth_employer": result.philhealth_employer,
            "pagibig_employer": result.pagibig_employer,
            "withholding_tax": result.withholding_tax,
            "sss_loan": sssl_c, "pagibig_loan": pil_c,
            "cash_advance": ca_c, "other_deductions": other_c,
            "total_deductions": result.total_mandatory_deductions + vol_deductions,
            "net_pay": result.net_pay - vol_deductions,
        }

        try:
            _upsert_payroll_entry(period_id, emp_id, entry_data)
            log_action("updated", "payroll_entries", period_id, f"Entry for {name}", {"net_pay": entry_data["net_pay"]})
            st.toast(f"✅ Saved — Net Pay: {_fmt(entry_data['net_pay'])}", icon="💾")
            st.session_state.pop("_pr_edit_emp", None)
            st.rerun()
        except Exception as e:
            st.error(f"Error saving: {e}")

    # Show summary if already computed
    if saved:
        _render_payroll_summary(saved)


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

def _render_payroll_analytics():
    """Spotfire-style drill-down: Department pie → Department bar → Employee pie."""
    from plotly.subplots import make_subplots

    # ── Load data ─────────────────────────────────────────────
    history_raw = _load_all_period_history_detailed(cid=get_company_id())

    if not history_raw:
        st.info("Analytics will appear once you have at least one finalized pay period.")
        return

    df = pd.DataFrame(history_raw)
    df["period_date"] = pd.to_datetime(df["period"])

    # ── Time range filter ─────────────────────────────────────
    _range_options = {"6 Months": 6, "1 Year": 12, "1.5 Years": 18, "2 Years": 24}
    _, _range_col = st.columns([6, 2])
    with _range_col:
        range_label = st.selectbox(
            "Time Range", list(_range_options.keys()),
            index=1, key="pr_analytics_range", label_visibility="collapsed",
        )
    cutoff = pd.Timestamp.now() - pd.DateOffset(months=_range_options[range_label])
    df = df[df["period_date"] >= cutoff].copy()

    if df.empty:
        st.caption(f"No finalized periods in the last {range_label.lower()}.")
        return

    # ── Filter bar (department + employee grouped by department) ──
    all_depts = sorted(df["department"].unique().tolist())
    all_emps_by_dept = {}
    for d in all_depts:
        emps_in_dept = sorted(df[df["department"] == d]["employee_name"].unique().tolist())
        all_emps_by_dept[d] = emps_in_dept

    # Build grouped employee options: "DEPT | Employee Name"
    grouped_emp_options = []
    for d in all_depts:
        for emp_name in all_emps_by_dept[d]:
            grouped_emp_options.append(f"{d}  ·  {emp_name}")

    _af1, _af2 = st.columns(2)
    with _af1:
        sel_depts = st.multiselect("Department", all_depts, key="pr_an_dept",
                                   placeholder="All departments", label_visibility="collapsed")
    with _af2:
        if sel_depts:
            avail_options = [o for o in grouped_emp_options
                             if any(o.startswith(d + "  ·  ") for d in sel_depts)]
        else:
            avail_options = grouped_emp_options
        sel_emps_raw = st.multiselect("Employee", avail_options, key="pr_an_emp",
                                      placeholder="All employees", label_visibility="collapsed")

    # Apply filters
    if sel_depts:
        df = df[df["department"].isin(sel_depts)]
    if sel_emps_raw:
        # Extract employee names from "DEPT · Name" format
        sel_emp_names = [s.split("  ·  ", 1)[1] for s in sel_emps_raw if "  ·  " in s]
        if sel_emp_names:
            df = df[df["employee_name"].isin(sel_emp_names)]

    if df.empty:
        st.caption("No data matches the current filters.")
        return

    # ── Department aggregation ────────────────────────────────
    dept_agg = (
        df.groupby("department")
        .agg(
            gross=("gross_pay", "sum"),
            net=("net_pay", "sum"),
            govt_ee=("govt_ee", "sum"),
            tax=("tax", "sum"),
            headcount=("employee_id", "nunique"),
        )
        .reset_index()
        .sort_values("gross", ascending=False)
    )

    _DEPT_COLORS = ["#005bc1", "#10b981", "#f59e0b", "#ef4444",
                    "#8b5cf6", "#0891b2", "#db2777", "#6366f1",
                    "#059669", "#d97706"]
    dept_color_map = {d: _DEPT_COLORS[i % len(_DEPT_COLORS)]
                      for i, d in enumerate(dept_agg["department"])}

    # ── Department selection — default to largest ─────────────
    sel_dept = dept_agg["department"].iloc[0]

    # ═══════════════════════════════════════════════════════════
    # ROW 1: Dept Bar (left) + Dept Stacked Bar over time (right)
    # ═══════════════════════════════════════════════════════════
    col_pie, col_bar = st.columns([1, 2])

    with col_pie:
        bar_colors = [dept_color_map[d] for d in dept_agg["department"]]

        fig_dept = go.Figure(go.Bar(
            y=dept_agg["department"],
            x=dept_agg["gross"],
            orientation="h",
            marker=dict(color=bar_colors),
            text=[f"₱{v:,.0f}" for v in dept_agg["gross"]],
            textposition="auto",
            textfont=dict(size=11),
            hovertemplate="<b>%{y}</b><br>Gross: ₱%{x:,.0f}<extra></extra>",
        ))
        fig_dept.update_layout(
            title="Payroll by Department",
            height=max(200, len(dept_agg) * 50 + 80),
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis=dict(title=None, tickprefix="₱", tickformat=","),
            yaxis=dict(title=None, autorange="reversed"),
            plot_bgcolor="#f8f9fa",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, system-ui, sans-serif", size=12),
            bargap=0.25,
        )
        st.plotly_chart(fig_dept, use_container_width=True, key="pr_dept_bar_h")

    # ── Filter to selected department ─────────────────────────
    df_dept = df[df["department"] == sel_dept].copy()

    with col_bar:
        # Aggregate per period for the selected department
        dept_periods = (
            df_dept.groupby("period")
            .agg(gross=("gross_pay", "sum"), net=("net_pay", "sum"),
                 govt_ee=("govt_ee", "sum"), tax=("tax", "sum"))
            .reset_index()
            .sort_values("period")
        )

        fig_bar = make_subplots(specs=[[{"secondary_y": True}]])

        # Stacked bars (Net + Govt + Tax = Gross)
        fig_bar.add_trace(go.Bar(
            name="Net Pay", x=dept_periods["period"], y=dept_periods["net"],
            marker_color="#10b981",
            hovertemplate="Net: ₱%{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig_bar.add_trace(go.Bar(
            name="Gov't (EE)", x=dept_periods["period"], y=dept_periods["govt_ee"],
            marker_color="#3b82f6",
            hovertemplate="Gov't: ₱%{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig_bar.add_trace(go.Bar(
            name="Tax", x=dept_periods["period"], y=dept_periods["tax"],
            marker_color="#ef4444",
            hovertemplate="Tax: ₱%{y:,.0f}<extra></extra>",
        ), secondary_y=False)

        # Line overlay — Gross on secondary axis
        fig_bar.add_trace(go.Scatter(
            name="Gross Pay", x=dept_periods["period"], y=dept_periods["gross"],
            mode="lines+markers",
            line=dict(color="#005bc1", width=3),
            marker=dict(size=7),
            hovertemplate="Gross: ₱%{y:,.0f}<extra></extra>",
        ), secondary_y=True)

        fig_bar.update_layout(
            barmode="stack",
            title=f"{sel_dept} — Payroll Breakdown",
            height=380,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1, font=dict(size=10)),
            margin=dict(l=0, r=0, t=56, b=0),
            plot_bgcolor="#f8f9fa",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, system-ui, sans-serif"),
        )
        fig_bar.update_xaxes(title_text=None)
        fig_bar.update_yaxes(title_text="Components (₱)", secondary_y=False,
                             tickprefix="₱", tickformat=",")
        fig_bar.update_yaxes(title_text="Gross (₱)", secondary_y=True,
                             tickprefix="₱", tickformat=",")

        st.plotly_chart(fig_bar, use_container_width=True, key="pr_dept_bar")

    # ═══════════════════════════════════════════════════════════
    # ROW 2: Detail card + Employee pie for selected period
    # ═══════════════════════════════════════════════════════════
    dept_row = dept_agg[dept_agg["department"] == sel_dept].iloc[0]

    # Detail card
    st.markdown(
        f'<div style="background:#fff;border:1px solid #e7e8e9;border-radius:12px;'
        f'padding:16px 20px;margin:8px 0;box-shadow:0 1px 4px rgba(0,0,0,0.04);">'
        f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">'
        f'<span style="width:12px;height:12px;border-radius:3px;background:{dept_color_map.get(sel_dept, "#005bc1")};'
        f'display:inline-block;flex-shrink:0;"></span>'
        f'<span style="font-size:16px;font-weight:800;color:#191c1d;">{sel_dept}</span>'
        f'<span style="background:#d1fae5;color:#065f46;padding:2px 10px;border-radius:9999px;'
        f'font-size:11px;font-weight:700;">&#8369;{dept_row["gross"]:,.0f} gross</span>'
        f'<span style="background:#dbeafe;color:#1e40af;padding:2px 10px;border-radius:9999px;'
        f'font-size:11px;font-weight:700;">{int(dept_row["headcount"])} employees</span>'
        + f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Employee bar chart for selected department ─────────────
    df_emp = df_dept.copy()
    pie_title = f"{sel_dept} — Employee Gross Pay"

    if df_emp.empty:
        st.caption("No data for this selection.")
        return

    emp_agg = (
        df_emp.groupby("employee_name")
        .agg(gross=("gross_pay", "sum"), net=("net_pay", "sum"))
        .reset_index()
        .sort_values("gross", ascending=False)
    )

    _EMP_COLORS = ["#2563eb", "#ea580c", "#d97706", "#0891b2",
                   "#7c3aed", "#db2777", "#0d9488", "#6366f1",
                   "#059669", "#dc2626", "#4f46e5", "#0284c7"]

    emp_colors = [_EMP_COLORS[i % len(_EMP_COLORS)] for i in range(len(emp_agg))]

    fig_emp_bar = go.Figure(go.Bar(
        y=emp_agg["employee_name"],
        x=emp_agg["gross"],
        orientation="h",
        marker=dict(color=emp_colors),
        text=[f"₱{v:,.0f}" for v in emp_agg["gross"]],
        textposition="auto",
        textfont=dict(size=10),
        hovertemplate="<b>%{y}</b><br>Gross: ₱%{x:,.0f}<extra></extra>",
    ))
    fig_emp_bar.update_layout(
        title=pie_title,
        height=max(250, len(emp_agg) * 32 + 80),
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(title=None, tickprefix="₱", tickformat=","),
        yaxis=dict(title=None, autorange="reversed"),
        plot_bgcolor="#f8f9fa",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, system-ui, sans-serif", size=12),
        bargap=0.2,
    )
    st.plotly_chart(fig_emp_bar, use_container_width=True, key="pr_emp_bar_h")


def _render_payroll_history():
    """Payroll history trend charts with time range filter."""
    from plotly.subplots import make_subplots

    history = _load_all_period_history(cid=get_company_id())
    if not history:
        st.info("Charts will appear once you have at least one finalized pay period.")
        return

    df_hist = pd.DataFrame(history)
    df_hist["period_date"] = pd.to_datetime(df_hist["period"])

    _range_options = {"6 Months": 6, "1 Year": 12, "1.5 Years": 18, "2 Years": 24}
    _, _range_col = st.columns([6, 2])
    with _range_col:
        range_label = st.selectbox(
            "Time Range", list(_range_options.keys()),
            index=1, key="payroll_hist_range", label_visibility="collapsed",
        )
    cutoff = pd.Timestamp.now() - pd.DateOffset(months=_range_options[range_label])
    df_filtered = df_hist[df_hist["period_date"] >= cutoff].copy()

    if df_filtered.empty:
        st.caption(f"No finalized periods in the last {range_label.lower()}.")
        return

    col_left, col_right = st.columns(2)

    with col_left:
        fig_stack = go.Figure()
        fig_stack.add_trace(go.Bar(
            name="Net Pay", x=df_filtered["period"], y=df_filtered["net_pay"],
            marker_color="#10b981",
            hovertemplate="Net Pay: %{y:.1f}%<extra></extra>",
        ))
        fig_stack.add_trace(go.Bar(
            name="Gov't (EE)", x=df_filtered["period"], y=df_filtered["govt_ee"],
            marker_color="#3b82f6",
            hovertemplate="Gov't (EE): %{y:.1f}%<extra></extra>",
        ))
        fig_stack.add_trace(go.Bar(
            name="Tax", x=df_filtered["period"], y=df_filtered["tax"],
            marker_color="#ef4444",
            hovertemplate="Tax: %{y:.1f}%<extra></extra>",
        ))
        fig_stack.update_layout(
            barmode="stack", barnorm="percent",
            title="Gross Pay Composition (%)",
            xaxis_title=None, yaxis_title="% of Gross",
            yaxis=dict(ticksuffix="%", range=[0, 100]), hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
            margin=dict(l=0, r=0, t=56, b=0), height=400,
            plot_bgcolor="#f8f9fa", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, system-ui, sans-serif"),
        )
        st.plotly_chart(fig_stack, use_container_width=True, key="payroll_hist_stack")

    with col_right:
        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        fig_dual.add_trace(go.Scatter(
            name="Gross Pay", x=df_filtered["period"], y=df_filtered["gross_pay"],
            mode="lines+markers", line=dict(color="#005bc1", width=3), marker=dict(size=7),
            fill="tozeroy", fillcolor="rgba(0,91,193,0.08)",
            hovertemplate="Gross: ₱%{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig_dual.add_trace(go.Scatter(
            name="Net Pay", x=df_filtered["period"], y=df_filtered["net_pay"],
            mode="lines+markers", line=dict(color="#10b981", width=2, dash="dot"), marker=dict(size=6),
            hovertemplate="Net: ₱%{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig_dual.add_trace(go.Scatter(
            name="Gov't (EE)", x=df_filtered["period"], y=df_filtered["govt_ee"],
            mode="lines+markers", line=dict(color="#3b82f6", width=2), marker=dict(size=5, symbol="diamond"),
            hovertemplate="Gov't EE: ₱%{y:,.0f}<extra></extra>",
        ), secondary_y=True)
        fig_dual.add_trace(go.Scatter(
            name="Tax", x=df_filtered["period"], y=df_filtered["tax"],
            mode="lines+markers", line=dict(color="#ef4444", width=2), marker=dict(size=5, symbol="square"),
            hovertemplate="Tax: ₱%{y:,.0f}<extra></extra>",
        ), secondary_y=True)
        fig_dual.add_trace(go.Scatter(
            name="Employer Cost", x=df_filtered["period"], y=df_filtered["employer_cost"],
            mode="lines+markers", line=dict(color="#f59e0b", width=2), marker=dict(size=5, symbol="triangle-up"),
            hovertemplate="Employer: ₱%{y:,.0f}<extra></extra>",
        ), secondary_y=True)
        fig_dual.update_layout(
            title="Payroll Trend (dual axis)", hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
            margin=dict(l=0, r=0, t=56, b=0), height=400,
            plot_bgcolor="#f8f9fa", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, system-ui, sans-serif"),
        )
        fig_dual.update_xaxes(title_text=None)
        fig_dual.update_yaxes(title_text="Gross / Net (₱)", secondary_y=False, tickprefix="₱", tickformat=",")
        fig_dual.update_yaxes(title_text="Deductions (₱)", secondary_y=True, tickprefix="₱", tickformat=",")
        st.plotly_chart(fig_dual, use_container_width=True, key="payroll_hist_dual")


def _render_payroll_processing():
    company = _load_company(_cid=get_company_id())
    daily_rate_divisor = int(company.get("daily_rate_divisor") or 26)

    employees = _load_employees(_cid=get_company_id())
    dept_map  = _load_departments_map(_cid=get_company_id())
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
                st.toast("📝 Pay period reopened for editing.", icon="🔓")
                st.rerun()

    # ── Filter bar with cross-filtering ─────────────────────────
    _all_pos_full = sorted({(e.get("position") or "").strip().upper() for e in employees} - {""})
    _all_dept_full = sorted({(e.get("department") or "").strip().upper() for e in employees} - {""})
    _dept_names_structured = _load_dept_names_from_table(_cid=get_company_id())
    if _dept_names_structured:
        _all_dept_full = sorted(set(_all_dept_full) | set(_dept_names_structured))

    _cur_pp_dept = st.session_state.get("pp_f_dept", [])
    _cur_pp_pos  = st.session_state.get("pp_f_pos", [])
    if _cur_pp_dept:
        _pp_avail_pos = sorted({(e.get("position") or "").upper() for e in employees
                                if (e.get("department") or "").upper() in {d.upper() for d in _cur_pp_dept}} - {""})
    else:
        _pp_avail_pos = _all_pos_full
    if _cur_pp_pos:
        _pp_avail_dept = sorted({(e.get("department") or "").upper() for e in employees
                                 if (e.get("position") or "").upper() in {p.upper() for p in _cur_pp_pos}} - {""})
    else:
        _pp_avail_dept = _all_dept_full

    _pf1, _pf2, _pf3 = st.columns([1.5, 1.5, 2])
    with _pf1:
        pp_sel_dept = st.multiselect("Department", _pp_avail_dept, key="pp_f_dept",
                                     placeholder="All departments", label_visibility="collapsed")
    with _pf2:
        pp_sel_pos  = st.multiselect("Position", _pp_avail_pos, key="pp_f_pos",
                                     placeholder="All positions", label_visibility="collapsed")
    with _pf3:
        pp_search   = st.text_input("Employee", placeholder="🔍 Search name or no…",
                                    label_visibility="collapsed", key="pp_search")

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

    # ── Employee card grid grouped by department (4 columns) ──
    _pr_photos = _load_pr_photo_urls(_cid=get_company_id())
    _sorted_emps = sorted(employees, key=lambda e: (e.get("department") or "Unassigned").upper())
    _prev_dept = None
    _col_buf = []  # buffer cards for 4-col grid

    def _flush_cols():
        if not _col_buf:
            return
        gcols = st.columns(4)
        for ci, _emp in enumerate(_col_buf):
            with gcols[ci]:
                _render_employee_card_row(_emp, entries, _pr_photos)
        _col_buf.clear()

    for emp in _sorted_emps:
        _dept = (emp.get("department") or "Unassigned").upper()
        if _dept != _prev_dept:
            _flush_cols()
            _dept_count = sum(1 for e in employees if (e.get("department") or "Unassigned").upper() == _dept)
            _dept_computed = sum(1 for e in employees if (e.get("department") or "Unassigned").upper() == _dept and e["id"] in entries)
            _dc_color = "#155724" if _dept_computed == _dept_count else "#856404"
            st.markdown(
                f"<div style='font-size:11px;font-weight:700;color:#727784;"
                f"text-transform:uppercase;letter-spacing:0.08em;"
                f"padding:8px 0 2px;border-bottom:1px solid #ebeef0;"
                f"margin-bottom:4px;display:flex;justify-content:space-between;'>"
                f"<span>{_dept} ({_dept_count})</span>"
                f"<span style='color:{_dc_color};'>"
                f"{_dept_computed}/{_dept_count} computed</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            _prev_dept = _dept
        _col_buf.append(emp)
        if len(_col_buf) == 4:
            _flush_cols()
    _flush_cols()  # remaining cards

    # ── Wire card row clicks to open dialog via JS ──
    import streamlit.components.v1 as _pr_components
    _pr_components.html("""
    <script>
    (function(){
        const pd = window.parent.document;
        pd.querySelectorAll('.gxp-pr-emp-row').forEach(r => {
            if (r.dataset.gxpWired) return;
            r.dataset.gxpWired = '1';
            r.addEventListener('click', () => {
                const eid = r.dataset.prEmp;
                const btn = pd.querySelector('[class*="st-key-_pr_open_' + eid + '"] button');
                if (btn) btn.click();
            });
            r.addEventListener('mouseenter', () => {
                r.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
                r.style.transform = 'translateY(-1px)';
            });
            r.addEventListener('mouseleave', () => {
                r.style.boxShadow = '';
                r.style.transform = '';
            });
        });
    })();
    </script>
    """, height=0)

    # Hidden buttons per employee (triggered by JS clicks)
    for emp in employees:
        def _on_pr_open(_eid=emp["id"]):
            st.session_state["_pr_edit_emp"] = _eid
        st.button("\u200b", key=f"_pr_open_{emp['id']}", on_click=_on_pr_open)

    # Open dialog if employee selected
    _pr_emp_id = st.session_state.get("_pr_edit_emp")
    if _pr_emp_id:
        _payroll_computation_dialog(
            _pr_emp_id, period["id"], is_locked, period, daily_rate_divisor
        )

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
                st.toast("📋 Pay period submitted for review.", icon="✅")
                st.rerun()

        if not all_computed:
            st.caption("Compute all employees before submitting for review.")

    elif period["status"] == "reviewed":
        st.divider()

        # Build reviewer options from active employees
        _reviewer_options = [
            f"{e.get('employee_no', '')} · {e.get('last_name', '')}, {e.get('first_name', '')}"
            for e in sorted(employees, key=lambda x: (x.get("last_name", ""), x.get("first_name", "")))
            if e.get("is_active", True)
        ]

        _rev_search = st.text_input(
            "Reviewer", placeholder="Type name or employee number…",
            key="_pr_rev_search",
        )

        # Filter options based on search
        _rev_filtered = _reviewer_options
        if _rev_search and _rev_search.strip():
            _q = _rev_search.strip().lower()
            _rev_filtered = [o for o in _reviewer_options if _q in o.lower()]

        _rev_selected = st.session_state.get("_pr_reviewer_selected", "")

        if _rev_search and _rev_search.strip() and not _rev_selected:
            if _rev_filtered:
                # Show matching suggestions as radio buttons
                _pick = st.radio(
                    "Select reviewer:", _rev_filtered,
                    label_visibility="collapsed", key="_pr_rev_pick",
                )
                if st.button("Confirm Reviewer", key="_pr_rev_confirm"):
                    st.session_state["_pr_reviewer_selected"] = _pick
                    st.rerun()
            else:
                st.error("⛔ Unauthorized — no matching employee found. Only registered employees can review payroll.")

        reviewer_name = ""
        if _rev_selected:
            reviewer_name = _rev_selected
            st.success(f"✓ Reviewer: **{reviewer_name}**")
            if st.button("Change Reviewer", key="_pr_rev_clear", type="tertiary"):
                st.session_state.pop("_pr_reviewer_selected", None)
                st.session_state.pop("_pr_rev_search", None)
                st.rerun()

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
                st.toast(f"✅ Approved by {reviewer_name.strip()}. Pay period finalized!", icon="🎉")
                st.session_state.pop("_pr_reviewer_selected", None)
                st.session_state.pop("_pr_rev_search", None)
                st.rerun()

        if not reviewer_name.strip():
            st.caption("Type a name or employee number to search for the reviewer.")

    elif period["status"] == "finalized":
        st.divider()
        col1, col2, col3 = st.columns([2, 1, 1])
        with col3:
            if st.button("Mark as Paid", width="stretch"):
                _update_pay_period(period["id"], {"status": "paid"})
                log_action("paid", "pay_period", period["id"], f"{period['period_start']} to {period['period_end']}")
                st.toast("💰 Pay period marked as paid!", icon="✅")
                st.rerun()


def _render_payslips_tab():
    """Payslip selection, filtering, and PDF download — embedded in Payroll Run."""
    from reports.payslip_pdf import generate_payslip_pdf, generate_all_payslips_pdf

    # ── Period selector ────────────────────────────────────────────────────
    all_periods = _load_pay_periods(_cid=get_company_id())

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
    company      = _load_company(_cid=get_company_id())
    all_employees = _load_employees(_cid=get_company_id())
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
    dept_map_ps = _load_departments_map(_cid=get_company_id())
    for emp in all_employees:
        emp["department"] = dept_map_ps.get(emp["id"], "")

    all_depts_ps = sorted({e.get("department") or "" for e in all_employees} - {""})
    _dept_names_structured = _load_dept_names_from_table(_cid=get_company_id())
    if _dept_names_structured:
        all_depts_ps = _dept_names_structured
    all_pos_ps   = sorted({e.get("position") or "" for e in all_employees} - {""})

    _fc1, _fc2, _fc3, _fc4 = st.columns([1.5, 1.5, 1.5, 1])
    with _fc1:
        f_dept = st.multiselect("Department", all_depts_ps, key="ps_f_dept", placeholder="All",
                                label_visibility="collapsed")
    with _fc2:
        if f_dept:
            _ps_avail_pos = sorted({(e.get("position") or "") for e in all_employees
                                    if (e.get("department") or "") in f_dept} - {""})
        else:
            _ps_avail_pos = all_pos_ps
        f_pos = st.multiselect("Position", _ps_avail_pos, key="ps_f_pos", placeholder="All positions",
                               label_visibility="collapsed")
    with _fc3:
        f_name = st.text_input("Employee", placeholder="🔍 Search name or no…",
                               key="ps_f_name", label_visibility="collapsed")
    with _fc4:
        sort_by = st.selectbox(
            "Sort by",
            ["A-Z", "Z-A", "Net ↓", "Net ↑", "Dept"],
            key="ps_sort", label_visibility="collapsed",
        )
        # Map short labels back to full names for sorting logic
        _sort_map = {"A-Z": "Name (A-Z)", "Z-A": "Name (Z-A)", "Net ↓": "Net Pay (High-Low)",
                     "Net ↑": "Net Pay (Low-High)", "Dept": "Department"}
        sort_by = _sort_map.get(sort_by, sort_by)

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

    # ── Generate Payslips (based on current filter) ─────────────────────
    select_all = False  # no longer used, kept for compatibility
    _filter_label = f" ({len(done_filtered)})" if (f_name or f_dept or f_pos) else f" — All ({len(done_filtered)})"
    if done_filtered:
        _gen_pdf_bytes = generate_all_payslips_pdf(company, done_filtered, period, entries)
        st.download_button(
            label=f"📄 Generate Payslips{_filter_label}",
            data=_gen_pdf_bytes,
            file_name=f"payslips_{period['period_start']}_to_{period['period_end']}.pdf",
            mime="application/pdf",
            type="primary",
            key="ps_dl_all",
        )
    else:
        st.info("No computed payslips to generate. Complete payroll processing first.")

    st.divider()

    # ── Progress header (same style as Payroll Processing) ────────────────
    _pct_ps = int(len(done_filtered) / len(done_filtered + pending_filtered) * 100) if (done_filtered or pending_filtered) else 0
    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin:0.5rem 0 0.5rem;">'
        f'<div>'
        f'<span class="gxp-page-label" style="margin:0;">PAYSLIPS</span>'
        f'<span style="font-size:0.8125rem;color:var(--gxp-text3);margin-left:0.5rem;">'
        f'{len(done_filtered)} of {len(done_filtered) + len(pending_filtered)} ready</span>'
        f'</div>'
        f'<span style="font-size:0.8125rem;font-weight:700;color:var(--gxp-accent);">{_pct_ps}%</span>'
        f'</div>'
        f'<div style="height:4px;background:var(--gxp-border);border-radius:9999px;margin-bottom:0.75rem;">'
        f'<div style="height:4px;width:{_pct_ps}%;background:var(--gxp-accent);border-radius:9999px;'
        f'transition:width 0.3s ease;"></div></div>',
        unsafe_allow_html=True,
    )

    # ── Photo URLs ────────────────────────────────────────────────────────
    _ps_photos = _load_pr_photo_urls(_cid=get_company_id())

    # ── Card grid grouped by department (4 columns) ───────────────────────
    all_filtered = done_filtered + pending_filtered
    all_filtered = sorted(all_filtered, key=lambda e: (e.get("department") or "Unassigned").upper())
    _prev_dept_ps = None
    _col_buf_ps: list = []

    def _flush_ps_cols():
        if not _col_buf_ps:
            return
        gcols = st.columns(4)
        for ci, (_emp, _is_done) in enumerate(_col_buf_ps):
            with gcols[ci]:
                _render_payslip_card(_emp, _is_done, entries, _ps_photos, company, period, select_all)
        _col_buf_ps.clear()

    for emp in all_filtered:
        _dept = (emp.get("department") or "Unassigned").upper()
        if _dept != _prev_dept_ps:
            _flush_ps_cols()
            _dept_total = sum(1 for e in all_filtered if (e.get("department") or "Unassigned").upper() == _dept)
            _dept_done = sum(1 for e in all_filtered if (e.get("department") or "Unassigned").upper() == _dept and e["id"] in entries)
            st.markdown(
                f"<div style='font-size:11px;font-weight:700;color:#727784;"
                f"text-transform:uppercase;letter-spacing:0.08em;"
                f"padding:8px 0 2px;border-bottom:1px solid #ebeef0;"
                f"margin-bottom:4px;display:flex;justify-content:space-between;'>"
                f"<span>{_dept} ({_dept_total})</span>"
                f"<span style='color:{'#155724' if _dept_done == _dept_total else '#856404'};'>"
                f"{_dept_done}/{_dept_total} ready</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            _prev_dept_ps = _dept
        _is_done = emp["id"] in entries
        _col_buf_ps.append((emp, _is_done))
        if len(_col_buf_ps) == 4:
            _flush_ps_cols()
    _flush_ps_cols()

    # ── Wire swipe action clicks to hidden Streamlit widgets ─────────────
    import streamlit.components.v1 as _ps_components
    _ps_components.html("""
    <script>
    (function(){
        const pd = window.parent.document;
        pd.querySelectorAll('.ps-swipe-act[data-ps-action]').forEach(el => {
            if (el.dataset.gxpWired) return;
            el.dataset.gxpWired = '1';
            el.addEventListener('click', e => {
                e.stopPropagation();
                const action = el.dataset.psAction;
                if (action.startsWith('dl_')) {
                    const btn = pd.querySelector('[class*="st-key-ps_dl_' + action.slice(3) + '"] button');
                    if (btn) btn.click();
                }
            });
        });
    })();
    </script>
    """, height=0)



def render():
    inject_css()
    st.title("Payroll Run")

    tab_run, tab_analytics, tab_history, tab_payslips = st.tabs([
        "📋 Payroll Processing", "📊 Analytics", "📈 History", "🧾 Payslips",
    ])

    with tab_run:
        _render_payroll_processing()

    with tab_analytics:
        _render_payroll_analytics()

    with tab_history:
        _render_payroll_history()

    with tab_payslips:
        _render_payslips_tab()


