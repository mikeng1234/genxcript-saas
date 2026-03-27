"""
Dashboard — ADP-inspired Streamlit page.

Action-oriented layout: what needs attention NOW at the top,
analytics and history below. Designed after ADP's payroll dashboard
pattern: CTA → Alerts → Stats → Summary → Trends.
"""

import streamlit as st
import streamlit.components.v1 as _stc
from datetime import date
from app.db_helper import get_db, get_company_id
from app.styles import (
    inject_css, status_badge, remit_card, GOV_COLORS,
)
from app.auth import is_supervisor, get_supervisor_employee_ids, get_role_label
from backend.deadlines import get_remittance_deadlines, load_holiday_set
import plotly.express as px
import pandas as pd


# ============================================================
# Data Helpers
# ============================================================

def _fmt(centavos: int) -> str:
    return f"\u20b1{centavos / 100:,.2f}"


def _fmt_short(centavos: int) -> str:
    """Compact peso format for stat cards."""
    pesos = centavos / 100
    if pesos >= 1_000_000:
        return f"\u20b1{pesos / 1_000_000:,.1f}M"
    if pesos >= 1_000:
        return f"\u20b1{pesos / 1_000:,.1f}K"
    return f"\u20b1{pesos:,.0f}"


def _load_company() -> dict:
    db = get_db()
    result = db.table("companies").select("*").eq("id", get_company_id()).execute()
    return result.data[0] if result.data else {}


def _load_employee_counts() -> tuple[int, int]:
    """Return (active_count, total_count) in a single query."""
    db = get_db()
    result = (
        db.table("employees")
        .select("id, is_active")
        .eq("company_id", get_company_id())
        .execute()
    )
    total = len(result.data)
    active = sum(1 for e in result.data if e.get("is_active", True))
    return active, total


def _load_pay_periods() -> list[dict]:
    db = get_db()
    result = (
        db.table("pay_periods")
        .select("*")
        .eq("company_id", get_company_id())
        .order("period_start", desc=True)
        .limit(10)
        .execute()
    )
    return result.data


def _load_payroll_entries(pay_period_id: str) -> list[dict]:
    db = get_db()
    result = (
        db.table("payroll_entries")
        .select("*")
        .eq("pay_period_id", pay_period_id)
        .execute()
    )
    return result.data


def _load_employee_names(employee_ids: list[str]) -> dict[str, str]:
    """Return {employee_id: "First Last"} for the given IDs."""
    if not employee_ids:
        return {}
    db = get_db()
    result = (
        db.table("employees")
        .select("id, first_name, last_name")
        .in_("id", employee_ids)
        .execute()
    )
    return {r["id"]: f"{r['first_name']} {r['last_name']}" for r in result.data}


@st.cache_data(ttl=120, show_spinner=False)
def _load_payroll_history(cid: str = "") -> list[dict]:
    """Load all finalized/paid periods with aggregate totals for charts.

    Uses a single batch query to avoid N+1 round-trips.
    Cached for 2 minutes keyed by company_id.
    """
    db  = get_db()
    if not cid:
        cid = get_company_id()

    # Single query: get all entries for finalized/paid periods, grouped
    try:
        periods_result = (
            db.table("pay_periods")
            .select("id, period_start, status")
            .eq("company_id", cid)
            .in_("status", ["finalized", "paid"])
            .order("period_start", desc=False)
            .execute()
        )
        if not periods_result.data:
            return []

        pp_ids = [p["id"] for p in periods_result.data]
        pp_start_map = {p["id"]: p["period_start"] for p in periods_result.data}

        # Batch load ALL entries for all finalized periods in ONE query
        all_entries = (
            db.table("payroll_entries")
            .select("pay_period_id, gross_pay, net_pay, sss_employee, sss_employer, "
                     "philhealth_employee, philhealth_employer, pagibig_employee, "
                     "pagibig_employer, withholding_tax")
            .in_("pay_period_id", pp_ids)
            .execute()
        ).data

        # Group by period
        from collections import defaultdict
        grouped = defaultdict(list)
        for e in all_entries:
            grouped[e["pay_period_id"]].append(e)

        rows = []
        for pp_id in pp_ids:
            entries = grouped.get(pp_id, [])
            if not entries:
                continue
            rows.append({
                "period":     pp_start_map[pp_id],
                "gross_pay":  sum(e["gross_pay"] for e in entries) / 100,
                "net_pay":    sum(e["net_pay"]   for e in entries) / 100,
                "headcount":  len(entries),
                "sss":        sum(e["sss_employee"]       + e["sss_employer"]       for e in entries) / 100,
                "philhealth": sum(e["philhealth_employee"] + e["philhealth_employer"] for e in entries) / 100,
                "pagibig":    sum(e["pagibig_employee"]   + e["pagibig_employer"]   for e in entries) / 100,
                "bir":        sum(e["withholding_tax"]    for e in entries) / 100,
            })
        return rows
    except Exception:
        return []


def _load_current_remittance_status() -> dict[str, dict | None]:
    """Return {agency: remittance_record_or_None} for the current reference month.

    The reference month mirrors the logic in ``backend/deadlines.py``:
    - day ≤ 20 → current calendar month
    - day > 20 → next calendar month
    """
    from datetime import timedelta
    today = date.today()
    if today.day <= 20:
        ref = today.replace(day=1)
    else:
        nxt = today.replace(day=28) + timedelta(days=4)
        ref = nxt.replace(day=1)

    result_map: dict[str, dict | None] = {
        "SSS": None, "PhilHealth": None, "Pag-IBIG": None, "BIR": None,
    }
    try:
        db = get_db()
        rows = (
            db.table("remittance_records")
            .select("*")
            .eq("company_id", get_company_id())
            .eq("period_year",  ref.year)
            .eq("period_month", ref.month)
            .execute()
        ).data
        for row in rows:
            result_map[row["agency"]] = row
    except Exception:
        pass
    return result_map


def _get_deadlines(remittance_status: dict[str, dict | None] | None = None) -> list[dict]:
    db = get_db()
    today = date.today()
    holidays = load_holiday_set(db, year=today.year, company_id=get_company_id())
    remitted_set: set[tuple[str, int, int]] = set()
    if remittance_status:
        for agency, row in remittance_status.items():
            if row:
                remitted_set.add((agency, row["period_year"], row["period_month"]))
    return get_remittance_deadlines(today, holidays, remitted_set)


def _count_pending_requests(team_ids: list | None = None) -> tuple[int, int]:
    """Return (pending_leave_count, pending_ot_count). If team_ids given, scope to those employees."""
    try:
        db  = get_db()
        cid = get_company_id()
        lr_q  = db.table("leave_requests").select("id", count="exact").eq("company_id", cid).eq("status", "pending")
        otr_q = db.table("overtime_requests").select("id", count="exact").eq("company_id", cid).eq("status", "pending")
        if team_ids:
            str_ids = [str(tid) for tid in team_ids]
            lr_q  = lr_q.in_("employee_id", str_ids)
            otr_q = otr_q.in_("employee_id", str_ids)
        lr  = lr_q.execute()
        otr = otr_q.execute()
        return (lr.count or 0), (otr.count or 0)
    except Exception:
        return 0, 0


def _find_next_period(periods: list[dict]) -> dict | None:
    """Find the most recent draft/reviewed period (next to run)."""
    for p in periods:
        if p["status"] in ("draft", "reviewed"):
            return p
    return None


def _find_latest_finalized(periods: list[dict]) -> dict | None:
    """Find the most recent finalized/paid period."""
    for p in periods:
        if p["status"] in ("finalized", "paid"):
            return p
    return None


def _trend_html(current: int, previous: int) -> str:
    """Return a coloured trend indicator comparing current vs previous value."""
    if not previous or previous == 0:
        return '<span class="gxp-stat-trend gxp-stat-trend-neutral">— new</span>'
    pct = (current - previous) / previous * 100
    if pct > 0.5:
        return f'<span class="gxp-stat-trend gxp-stat-trend-up">▲ {pct:.1f}%</span>'
    if pct < -0.5:
        return f'<span class="gxp-stat-trend gxp-stat-trend-down">▼ {abs(pct):.1f}%</span>'
    return '<span class="gxp-stat-trend gxp-stat-trend-neutral">— flat</span>'


# Inline SVG icons — stroke-based, single icon set (Heroicons-style)
_SVG = {
    "employees": (
        '<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">'
        '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/>'
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
        '</svg>'
    ),
    "gross": (
        '<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">'
        '<line x1="12" y1="1" x2="12" y2="23"/>'
        '<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'
        '</svg>'
    ),
    "net": (
        '<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">'
        '<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>'
        '<line x1="1" y1="10" x2="23" y2="10"/>'
        '</svg>'
    ),
    "cost": (
        '<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">'
        '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
        '</svg>'
    ),
    "ytd": (
        '<svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">'
        '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'
        '</svg>'
    ),
}


# ============================================================
# Dashboard v2 — 6-Panel Bento Grid
# ============================================================

@st.cache_data(ttl=120, show_spinner=False)
def _load_department_breakdown(_cid: str) -> list[dict]:
    """Return [{department, count, pct}] for donut chart."""
    try:
        db = get_db()
        rows = (
            db.table("employee_profiles")
            .select("employee_id, department")
            .execute()
        ).data or []
        # Filter to active employees in this company
        emp_rows = (
            db.table("employees")
            .select("id")
            .eq("company_id", _cid)
            .eq("is_active", True)
            .execute()
        ).data or []
        active_ids = {e["id"] for e in emp_rows}
        dept_counts: dict[str, int] = {}
        for r in rows:
            if r["employee_id"] in active_ids:
                dept = r.get("department") or "Unassigned"
                dept_counts[dept] = dept_counts.get(dept, 0) + 1
        total = sum(dept_counts.values()) or 1
        result = [
            {"department": d, "count": c, "pct": round(c / total * 100)}
            for d, c in sorted(dept_counts.items(), key=lambda x: -x[1])
        ]
        return result
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def _load_employee_dept_map(_cid: str) -> dict[str, str]:
    """Return {employee_id: department} for all employees in the company."""
    try:
        db = get_db()
        profiles = (
            db.table("employee_profiles")
            .select("employee_id, department")
            .execute()
        ).data or []
        emp_rows = (
            db.table("employees")
            .select("id")
            .eq("company_id", _cid)
            .execute()
        ).data or []
        company_ids = {e["id"] for e in emp_rows}
        return {
            r["employee_id"]: r.get("department") or "Unassigned"
            for r in profiles if r["employee_id"] in company_ids
        }
    except Exception:
        return {}


@st.cache_data(ttl=60, show_spinner=False)
def _load_today_attendance(_cid: str) -> list[dict]:
    """Return today's time log entries for the Attendance Detail panel."""
    try:
        db = get_db()
        today_str = date.today().isoformat()
        rows = (
            db.table("time_logs")
            .select("employee_id, clock_in, clock_out, status")
            .eq("company_id", _cid)
            .eq("log_date", today_str)
            .order("clock_in", desc=False)
            .limit(20)
            .execute()
        ).data or []
        return rows
    except Exception:
        return []


@st.cache_data(ttl=120, show_spinner=False)
def _load_attendance_monthly(_cid: str) -> list[dict]:
    """Return monthly attendance rates for bar chart (last 6 months)."""
    try:
        db = get_db()
        from datetime import timedelta
        today = date.today()
        six_months_ago = (today.replace(day=1) - timedelta(days=180)).replace(day=1)
        rows = (
            db.table("time_logs")
            .select("log_date, status")
            .eq("company_id", _cid)
            .gte("log_date", six_months_ago.isoformat())
            .execute()
        ).data or []
        if not rows:
            return []
        from collections import defaultdict
        monthly: dict[str, dict] = defaultdict(lambda: {"total": 0, "present": 0})
        for r in rows:
            ym = r["log_date"][:7]  # "2026-03"
            monthly[ym]["total"] += 1
            if r.get("status") in ("present", "on_time", None, ""):
                monthly[ym]["present"] += 1
        result = []
        for ym in sorted(monthly.keys())[-6:]:
            d = monthly[ym]
            pct = round(d["present"] / d["total"] * 100) if d["total"] else 0
            # Abbreviated month name
            try:
                from datetime import datetime as _dt3
                lbl = _dt3.strptime(ym, "%Y-%m").strftime("%b")
            except Exception:
                lbl = ym
            result.append({"month": lbl, "pct": pct})
        return result
    except Exception:
        return []


@st.cache_data(ttl=60, show_spinner=False)
def _load_pending_request_details(_cid: str, team_ids: list | None = None) -> list[dict]:
    """Load pending leave/OT request details for the Pending Requests panel."""
    try:
        db = get_db()
        requests = []
        # Leave requests
        lq = (
            db.table("leave_requests")
            .select("id, employee_id, leave_type, start_date, end_date, created_at")
            .eq("company_id", _cid)
            .eq("status", "pending")
            .order("created_at", desc=True)
            .limit(6)
        )
        if team_ids:
            lq = lq.in_("employee_id", [str(t) for t in team_ids])
        lr = lq.execute().data or []
        for r in lr:
            requests.append({
                "id": r["id"], "employee_id": r["employee_id"],
                "type": "Leave", "detail": f"{r.get('leave_type', 'Leave')} — {r.get('start_date', '')} to {r.get('end_date', '')}",
                "created_at": r.get("created_at", ""),
            })
        # OT requests
        oq = (
            db.table("overtime_requests")
            .select("id, employee_id, ot_date, hours, created_at")
            .eq("company_id", _cid)
            .eq("status", "pending")
            .order("created_at", desc=True)
            .limit(6)
        )
        if team_ids:
            oq = oq.in_("employee_id", [str(t) for t in team_ids])
        otr = oq.execute().data or []
        for r in otr:
            requests.append({
                "id": r["id"], "employee_id": r["employee_id"],
                "type": "Overtime", "detail": f"{r.get('hours', 0)}hrs on {r.get('ot_date', '')}",
                "created_at": r.get("created_at", ""),
            })
        # Sort by created_at desc
        requests.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return requests[:8]
    except Exception:
        return []


# Department color palette for donut chart
_DEPT_COLORS = [
    "#005bc1", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444",
    "#06b6d4", "#ec4899", "#9ca3af",
]


def _render_panel_payroll_overview(latest_period, history, latest_entries,
                                   total_gross, total_net, total_cost, headcount,
                                   dept_map: dict | None = None):
    """Panel 1: Payroll Overview — headline + stacked bars by dept + click → Payroll Run."""
    from collections import defaultdict

    # Trend
    bar_vals = [int(r["gross_pay"] * 100) for r in history[-6:]] if history else []
    max_val = max(bar_vals) if bar_vals else 1
    bar_labels = []
    for r in history[-6:]:
        try:
            from datetime import datetime as _dt4
            dt = _dt4.strptime(str(r["period"])[:10], "%Y-%m-%d")
            day = dt.day
            mon = dt.strftime("%b")
            # Show "Jan₁" / "Jan₂" for semi-monthly, plain "Jan" for monthly
            if day <= 1:
                lbl = mon
            elif day >= 15:
                lbl = f"{mon}₂"
            else:
                lbl = f"{mon}₁"
        except Exception:
            lbl = str(r["period"])[:3]
        bar_labels.append(lbl)

    if len(bar_vals) >= 2:
        pct = (bar_vals[-1] - bar_vals[-2]) / bar_vals[-2] * 100 if bar_vals[-2] else 0
        if pct > 0.5:
            trend_html = f'<span style="color:#059669;font-size:11px;font-weight:700;">▲ {pct:.1f}%</span> <span style="color:#9ca3af;font-size:9px;">vs last period</span>'
        elif pct < -0.5:
            trend_html = f'<span style="color:#93000a;font-size:11px;font-weight:700;">▼ {abs(pct):.1f}%</span> <span style="color:#9ca3af;font-size:9px;">vs last period</span>'
        else:
            trend_html = '<span style="color:#9ca3af;font-size:11px;">— flat vs last period</span>'
    else:
        trend_html = '<span style="color:#9ca3af;font-size:10px;">First pay run</span>'

    # Build stacked bars by department for latest period
    # Each bar = one period; segments stacked by department gross totals
    dept_map = dept_map or {}
    # Get unique depts sorted by total (for consistent color assignment)
    dept_totals: dict[str, int] = defaultdict(int)
    if latest_entries and dept_map:
        for e in latest_entries:
            dept = dept_map.get(e.get("employee_id", ""), "Other")
            dept_totals[dept] += e.get("gross_pay", 0)
    sorted_depts = sorted(dept_totals.keys(), key=lambda d: -dept_totals[d])
    dept_color_map = {d: _DEPT_COLORS[i % len(_DEPT_COLORS)] for i, d in enumerate(sorted_depts)}

    # For historical bars, we don't have per-dept breakdown, so show solid color
    # For the latest bar, show stacked segments
    _BAR_MAX_PX = 80  # max bar height in pixels
    bars_html = ""
    for i, v in enumerate(bar_vals):
        h_px = max(int((v / max_val) * _BAR_MAX_PX), 12) if max_val else 12
        lbl = bar_labels[i] if i < len(bar_labels) else ""
        is_latest = (i == len(bar_vals) - 1)

        if is_latest and dept_totals and v > 0:
            # Stacked bar — segments proportional to h_px, no min inflation
            dept_total_sum = sum(dept_totals.values()) or 1
            segments_html = ""
            for dept in reversed(sorted_depts):
                seg_frac = dept_totals[dept] / dept_total_sum
                seg_px = max(round(seg_frac * h_px), 2)
                color = dept_color_map.get(dept, "#005bc1")
                segments_html += (
                    f'<div style="width:100%;height:{seg_px}px;background:{color};'
                    f'transition:height 0.4s ease;" title="{dept}: {_fmt_short(dept_totals[dept])}"></div>'
                )
            bars_html += (
                f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;">'
                f'  <div style="width:100%;border-radius:4px 4px 0 0;display:flex;flex-direction:column;justify-content:flex-end;overflow:hidden;height:{h_px}px;">'
                f'    {segments_html}'
                f'  </div>'
                f'  <span style="font-size:7px;color:#005bc1;font-weight:700;">{lbl}</span>'
                f'</div>'
            )
        else:
            bg = "#d8e2ff"
            bars_html += (
                f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;">'
                f'  <div style="width:100%;border-radius:4px 4px 0 0;background:{bg};height:{h_px}px;"></div>'
                f'  <span style="font-size:7px;color:#9ca3af;font-weight:600;">{lbl}</span>'
                f'</div>'
            )

    # Dept legend (compact, single line under the chart)
    dept_legend = ""
    for dept in sorted_depts[:4]:
        color = dept_color_map[dept]
        short = dept[:6] if len(dept) > 6 else dept
        dept_legend += (
            f'<span style="display:inline-flex;align-items:center;gap:3px;margin-right:8px;">'
            f'<span style="width:6px;height:6px;border-radius:2px;background:{color};display:inline-block;"></span>'
            f'<span style="font-size:7px;font-weight:600;color:#9ca3af;">{short}</span>'
            f'</span>'
        )

    st.markdown(
        f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="{_CARD}cursor:pointer;max-height:280px;overflow:hidden;">'
        f'  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">'
        f'    <div style="{_MLBL}margin-bottom:0;">Payroll Overview</div>'
        f'    <div style="width:28px;height:28px;border-radius:8px;background:rgba(0,91,193,0.08);display:flex;align-items:center;justify-content:center;">'
        f'      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#005bc1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>'
        f'    </div>'
        f'  </div>'
        f'  <div style="font-size:24px;font-weight:900;color:#191c1d;letter-spacing:-1.5px;line-height:1;margin-bottom:4px;font-family:\'Plus Jakarta Sans\',system-ui,sans-serif;">₱{total_gross / 100:,.2f}</div>'
        f'  <div style="margin-bottom:10px;">{trend_html}</div>'
        f'  <div style="display:flex;align-items:flex-end;gap:4px;margin-bottom:4px;">{bars_html}</div>'
        f'  <div style="margin-bottom:8px;">{dept_legend}</div>'
        f'  <div style="display:flex;gap:12px;padding-top:8px;border-top:1px solid #f3f4f6;">'
        f'    <div><div style="font-size:7px;color:#9ca3af;font-weight:600;">Net Pay</div><div style="font-size:9px;font-weight:800;color:#191c1d;">{_fmt_short(total_net)}</div></div>'
        f'    <div><div style="font-size:7px;color:#9ca3af;font-weight:600;">Employer Cost</div><div style="font-size:9px;font-weight:800;color:#191c1d;">{_fmt_short(total_cost)}</div></div>'
        f'    <div><div style="font-size:7px;color:#9ca3af;font-weight:600;">Headcount</div><div style="font-size:9px;font-weight:800;color:#191c1d;">{headcount}</div></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    # Hidden button — JS wires click on the card to this → opens expanded dialog
    if st.button("Payroll Overview →", key="bento_payroll_overview", use_container_width=True):
        _dlg_payroll_overview()


@st.dialog("Payroll Overview", width="large")
def _dlg_payroll_overview():
    """Expanded payroll overview dialog — bigger chart + tables."""
    from collections import defaultdict

    cid = get_company_id()
    history = _load_payroll_history(cid=cid)
    periods = _load_pay_periods()
    latest_period = _find_latest_finalized(periods)
    latest_entries = _load_payroll_entries(latest_period["id"]) if latest_period else []
    dept_map = _load_employee_dept_map(cid)
    name_map = _load_employee_names(
        [e["employee_id"] for e in latest_entries if e.get("employee_id")]
    ) if latest_entries else {}

    total_gross = sum(e["gross_pay"] for e in latest_entries) if latest_entries else 0
    total_net = sum(e["net_pay"] for e in latest_entries) if latest_entries else 0
    total_er = sum(
        e["sss_employer"] + e["philhealth_employer"] + e["pagibig_employer"]
        for e in latest_entries
    ) if latest_entries else 0

    # ── Header stats ──
    st.markdown(
        f'<div style="display:flex;gap:24px;margin-bottom:20px;flex-wrap:wrap;">'
        f'  <div><div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;">Gross Pay</div>'
        f'  <div style="font-size:28px;font-weight:900;color:#191c1d;letter-spacing:-1px;">₱{total_gross / 100:,.2f}</div></div>'
        f'  <div><div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;">Net Pay</div>'
        f'  <div style="font-size:20px;font-weight:800;color:#191c1d;">₱{total_net / 100:,.2f}</div></div>'
        f'  <div><div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;">Employer Cost</div>'
        f'  <div style="font-size:20px;font-weight:800;color:#191c1d;">₱{(total_gross + total_er) / 100:,.2f}</div></div>'
        f'  <div><div style="font-size:10px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;">Headcount</div>'
        f'  <div style="font-size:20px;font-weight:800;color:#191c1d;">{len(latest_entries)}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if latest_period:
        st.caption(f"Latest period: {latest_period['period_start']} → {latest_period['period_end']} · Status: {latest_period['status'].upper()}")

    # ── Expanded bar chart — last 12 periods ──
    st.markdown("#### Payroll History")
    history = history[-12:]
    bar_vals = [int(r["gross_pay"] * 100) for r in history] if history else []
    max_val = max(bar_vals) if bar_vals else 1

    bars_html = ""
    for i, r in enumerate(history):
        v = int(r["gross_pay"] * 100)
        h_px = max(int((v / max_val) * 160), 10) if max_val else 10
        is_latest = (i == len(history) - 1)
        bg = "#005bc1" if is_latest else "#d8e2ff"
        try:
            from datetime import datetime as _dtx
            dt = _dtx.strptime(str(r["period"])[:10], "%Y-%m-%d")
            day = dt.day
            mon = dt.strftime("%b")
            if day <= 1:
                lbl = mon
            elif day >= 15:
                lbl = f"{mon}₂"
            else:
                lbl = f"{mon}₁"
        except Exception:
            lbl = str(r["period"])[:3]

        amt_lbl = f"₱{v / 100:,.0f}"
        bars_html += (
            f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;min-width:36px;">'
            f'  <div style="font-size:8px;color:#727784;font-weight:600;white-space:nowrap;">{amt_lbl}</div>'
            f'  <div style="width:100%;border-radius:4px 4px 0 0;background:{bg};height:{h_px}px;"></div>'
            f'  <span style="font-size:8px;color:{"#005bc1" if is_latest else "#9ca3af"};font-weight:{"700" if is_latest else "600"};">{lbl}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div style="display:flex;align-items:flex-end;gap:4px;padding:8px 0;overflow-x:auto;">{bars_html}</div>',
        unsafe_allow_html=True,
    )

    # ── Department breakdown ──
    if latest_entries and dept_map:
        st.markdown("#### Department Breakdown")
        dept_totals: dict[str, dict] = defaultdict(lambda: {"gross": 0, "net": 0, "count": 0})
        for e in latest_entries:
            dept = dept_map.get(e.get("employee_id", ""), "Other")
            dept_totals[dept]["gross"] += e.get("gross_pay", 0)
            dept_totals[dept]["net"] += e.get("net_pay", 0)
            dept_totals[dept]["count"] += 1

        sorted_depts = sorted(dept_totals.items(), key=lambda x: -x[1]["gross"])

        rows_html = ""
        for i, (dept, vals) in enumerate(sorted_depts):
            color = _DEPT_COLORS[i % len(_DEPT_COLORS)]
            pct = round(vals["gross"] / total_gross * 100, 1) if total_gross else 0
            bar_w = max(pct, 2)
            rows_html += (
                f'<div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #f3f4f6;">'
                f'  <div style="width:10px;height:10px;border-radius:3px;background:{color};flex-shrink:0;"></div>'
                f'  <div style="min-width:120px;font-size:12px;font-weight:700;color:#191c1d;white-space:nowrap;">{dept}</div>'
                f'  <div style="flex:1;display:flex;align-items:center;gap:8px;">'
                f'    <div style="flex:1;height:8px;background:#f3f4f6;border-radius:4px;overflow:hidden;">'
                f'      <div style="width:{bar_w}%;height:100%;background:{color};border-radius:4px;"></div>'
                f'    </div>'
                f'    <span style="font-size:10px;font-weight:700;color:#191c1d;min-width:32px;text-align:right;">{pct}%</span>'
                f'  </div>'
                f'  <div style="font-size:12px;font-weight:800;color:#191c1d;min-width:80px;text-align:right;">₱{vals["gross"] / 100:,.0f}</div>'
                f'  <div style="font-size:10px;color:#9ca3af;min-width:28px;text-align:right;">{vals["count"]}emp</div>'
                f'</div>'
            )
        st.markdown(f'<div>{rows_html}</div>', unsafe_allow_html=True)

    # ── Per-employee table ──
    if latest_entries and name_map:
        st.markdown("#### Employee Breakdown")
        sorted_entries = sorted(latest_entries, key=lambda e: e.get("gross_pay", 0), reverse=True)

        tbl_rows = ""
        for e in sorted_entries:
            eid = e.get("employee_id", "")
            name = name_map.get(eid, "Unknown")
            dept = dept_map.get(eid, "—")
            gross = e.get("gross_pay", 0)
            net = e.get("net_pay", 0)
            tbl_rows += (
                f'<tr style="border-bottom:1px solid #f3f4f6;">'
                f'  <td style="padding:6px 8px;font-size:11px;font-weight:700;color:#191c1d;">{name}</td>'
                f'  <td style="padding:6px 8px;font-size:10px;color:#727784;">{dept}</td>'
                f'  <td style="padding:6px 8px;font-size:11px;font-weight:700;color:#191c1d;text-align:right;">₱{gross / 100:,.2f}</td>'
                f'  <td style="padding:6px 8px;font-size:11px;color:#727784;text-align:right;">₱{net / 100:,.2f}</td>'
                f'</tr>'
            )
        st.markdown(
            f'<div style="max-height:300px;overflow-y:auto;">'
            f'<table style="width:100%;border-collapse:collapse;">'
            f'  <thead><tr style="border-bottom:2px solid #e5e7eb;">'
            f'    <th style="padding:6px 8px;font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;text-align:left;">Employee</th>'
            f'    <th style="padding:6px 8px;font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;text-align:left;">Department</th>'
            f'    <th style="padding:6px 8px;font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;text-align:right;">Gross</th>'
            f'    <th style="padding:6px 8px;font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;text-align:right;">Net</th>'
            f'  </tr></thead>'
            f'  <tbody>{tbl_rows}</tbody>'
            f'</table></div>',
            unsafe_allow_html=True,
        )

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Go to Payroll Run →", use_container_width=True, type="primary"):
            st.session_state["_nav_redirect"] = "Payroll Run"
            st.rerun()
    with c2:
        if st.button("Close", use_container_width=True):
            st.rerun()


def _render_panel_recent_payroll(latest_entries, name_map, latest_period):
    """Panel 2: Recent Payroll — top employees by gross pay."""
    top = sorted(latest_entries, key=lambda e: e.get("gross_pay", 0), reverse=True)[:6]

    _INITIALS_COLORS = [
        ("#dbeafe", "#005bc1"), ("#d1fae5", "#059669"), ("#fef3c7", "#d97706"),
        ("#ede9fe", "#7c3aed"), ("#fce7f3", "#db2777"), ("#e0f2fe", "#0284c7"),
    ]

    rows_html = ""
    for idx, ent in enumerate(top):
        eid = ent.get("employee_id", "")
        name = name_map.get(eid, "Unknown")
        initials = "".join(w[0] for w in name.split()[:2]).upper() if name != "Unknown" else "?"
        gross = ent.get("gross_pay", 0)
        ibg, ifg = _INITIALS_COLORS[idx % len(_INITIALS_COLORS)]
        status = latest_period.get("status", "draft") if latest_period else "draft"
        if status in ("finalized", "paid"):
            s_bg, s_fg, s_txt = "#d1fae5", "#059669", "Paid"
        elif status == "reviewed":
            s_bg, s_fg, s_txt = "#fef3c7", "#d97706", "Reviewed"
        else:
            s_bg, s_fg, s_txt = "#f3f4f6", "#6b7280", "Draft"

        border = 'border-bottom:1px solid #f3f4f6;' if idx < len(top) - 1 else ''
        rows_html += (
            f'<div style="display:flex;align-items:center;justify-content:space-between;padding:7px 2px;{border}border-radius:6px;">'
            f'  <div style="display:flex;align-items:center;gap:8px;">'
            f'    <div style="width:30px;height:30px;border-radius:50%;background:{ibg};display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:800;color:{ifg};flex-shrink:0;">{initials}</div>'
            f'    <div>'
            f'      <div style="font-size:11px;font-weight:700;color:#191c1d;">{name}</div>'
            f'      <div style="font-size:8px;color:#9ca3af;margin-top:1px;">EMP-{eid[:6]}</div>'
            f'    </div>'
            f'  </div>'
            f'  <div style="text-align:right;">'
            f'    <div style="font-size:11px;font-weight:800;color:#005bc1;">₱{gross / 100:,.0f}</div>'
            f'    <span style="font-size:7px;font-weight:700;padding:2px 6px;border-radius:9999px;background:{s_bg};color:{s_fg};text-transform:uppercase;">{s_txt}</span>'
            f'  </div>'
            f'</div>'
        )

    if not top:
        rows_html = '<div style="color:#9ca3af;font-size:12px;padding:20px 0;text-align:center;">No payroll data yet.</div>'

    st.markdown(
        f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="{_CARD}overflow:hidden;">'
        f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
        f'    <div style="{_MLBL}margin-bottom:0;">Recent Payroll</div>'
        f'    <span style="font-size:10px;font-weight:700;color:#005bc1;cursor:pointer;">View All</span>'
        f'  </div>'
        f'  <div style="max-height:220px;overflow-y:auto;">{rows_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("View All →", key="bento_recent_payroll", use_container_width=True):
        st.session_state["_nav_redirect"] = "Payroll Run"
        st.rerun()


def _render_panel_mini_calendar(cal_events: dict):
    """Panel 3: Mini calendar inside a bento card — pure HTML, no iframe."""
    import calendar as _cal

    today = date.today()
    year, month = today.year, today.month
    month_name = today.strftime("%B %Y")
    today_iso = today.isoformat()

    _week_pref = st.session_state.get("gxp_week_start", "Sunday")
    _first_day = 6 if _week_pref == "Sunday" else 0
    cal_obj = _cal.Calendar(firstweekday=_first_day)
    weeks = cal_obj.monthdayscalendar(year, month)

    if _week_pref == "Sunday":
        hdr = "".join(f'<span style="font-size:8px;font-weight:700;color:#727784;text-transform:uppercase;text-align:center;">{d}</span>' for d in ["SU","MO","TU","WE","TH","FR","SA"])
    else:
        hdr = "".join(f'<span style="font-size:8px;font-weight:700;color:#727784;text-transform:uppercase;text-align:center;">{d}</span>' for d in ["MO","TU","WE","TH","FR","SA","SU"])

    cells = ""
    for week in weeks:
        for day in week:
            if day == 0:
                cells += '<div style="min-height:24px;"></div>'
                continue
            iso = f"{year}-{month:02d}-{day:02d}"
            is_today = iso == today_iso
            evts = cal_events.get(iso, [])

            # Style
            if is_today:
                style = "font-size:12px;font-weight:800;color:#005bc1;"
            elif evts:
                prio_colors = {"holiday": "#e53935", "payday": "#4caf50", "deadline": "#ff6f00", "special": "#ff9800"}
                clr = "#424753"
                for e in evts:
                    if e.get("type") in prio_colors:
                        clr = prio_colors[e["type"]]
                        break
                style = f"font-size:10px;font-weight:700;color:{clr};"
            else:
                style = "font-size:10px;font-weight:500;color:#424753;"

            # Dots
            dots = ""
            if evts:
                dot_spans = "".join(
                    f'<span style="width:3px;height:3px;border-radius:50%;background:{e.get("color","#9ca3af")};display:inline-block;"></span>'
                    for e in evts[:3]
                )
                dots = f'<div style="display:flex;gap:1px;justify-content:center;margin-top:1px;">{dot_spans}</div>'

            cells += (
                f'<div style="text-align:center;padding:2px 0;border-radius:4px;min-height:24px;'
                f'display:flex;flex-direction:column;align-items:center;justify-content:center;{style}">'
                f'{day}{dots}</div>'
            )

    st.markdown(
        f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="{_CARD}cursor:pointer;">'
        f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        f'    <div style="{_MLBL}margin-bottom:0;">{month_name}</div>'
        f'  </div>'
        f'  <div style="display:grid;grid-template-columns:repeat(7,1fr);text-align:center;margin-bottom:3px;">{hdr}</div>'
        f'  <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:1px;">{cells}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Calendar →", key="bento_mini_cal", use_container_width=True):
        st.session_state["_nav_redirect"] = "Calendar"
        st.rerun()


def _render_panel_attendance_rate(monthly_data):
    """Panel 3: Attendance Rate — headline % + monthly bar chart."""
    if not monthly_data:
        st.markdown(
            f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="{_CARD}cursor:pointer;">'
            f'  <div style="{_MLBL}">Attendance Rate</div>'
            f'  <div style="color:#9ca3af;font-size:12px;padding:32px 0;text-align:center;">No attendance data available.<br>Enable the Attendance module to track.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("Attendance →", key="bento_attendance_rate_empty", use_container_width=True):
            st.session_state["_nav_redirect"] = "Attendance"
            st.rerun()
        return

    latest_pct = monthly_data[-1]["pct"] if monthly_data else 0
    prev_pct = monthly_data[-2]["pct"] if len(monthly_data) >= 2 else 0

    if prev_pct and latest_pct > prev_pct:
        trend_html = f'<span style="color:#059669;font-size:11px;font-weight:700;">▲ {latest_pct - prev_pct}% better than last month</span>'
    elif prev_pct and latest_pct < prev_pct:
        trend_html = f'<span style="color:#93000a;font-size:11px;font-weight:700;">▼ {prev_pct - latest_pct}% from last month</span>'
    else:
        trend_html = '<span style="color:#9ca3af;font-size:11px;">Stable</span>'

    bars_html = ""
    max_pct = max(d["pct"] for d in monthly_data) if monthly_data else 100
    for i, d in enumerate(monthly_data):
        h = max(int((d["pct"] / max_pct) * 100), 8) if max_pct else 8
        is_last = i == len(monthly_data) - 1
        bg = "#10b981" if is_last else "#e5e7eb"
        bars_html += (
            f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;">'
            f'  <div style="width:100%;border-radius:4px 4px 0 0;background:{bg};height:{h}%;min-height:4px;transition:height 0.6s ease;"></div>'
            f'  <span style="font-size:8px;color:#9ca3af;font-weight:600;">{d["month"]}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="{_CARD}cursor:pointer;">'
        f'  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">'
        f'    <div style="{_MLBL}margin-bottom:0;">Attendance Rate</div>'
        f'    <span style="font-size:9px;font-weight:700;padding:3px 10px;border-radius:9999px;background:#d1fae5;color:#059669;text-transform:uppercase;">Monthly</span>'
        f'  </div>'
        f'  <div style="font-size:38px;font-weight:900;color:#191c1d;line-height:1;margin-bottom:4px;font-family:\'Plus Jakarta Sans\',system-ui,sans-serif;">{latest_pct}%</div>'
        f'  <div style="margin-bottom:14px;">{trend_html}</div>'
        f'  <div style="display:flex;align-items:flex-end;gap:5px;height:56px;">{bars_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Attendance →", key="bento_attendance_rate", use_container_width=True):
        st.session_state["_nav_redirect"] = "Attendance"
        st.rerun()


def _render_panel_workforce(dept_data, active_count):
    """Panel 4: Workforce Breakdown — SVG donut with dept name, count, % on each segment."""
    import math

    if not dept_data:
        st.markdown(
            f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="{_CARD}cursor:pointer;">'
            f'  <div style="{_MLBL}">Total Employees</div>'
            f'  <div style="font-size:38px;font-weight:900;color:#191c1d;text-align:center;padding:16px 0;">{active_count}</div>'
            f'  <div style="color:#9ca3af;font-size:11px;text-align:center;">No department data</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("Employees →", key="bento_workforce_empty", use_container_width=True):
            st.session_state["_nav_redirect"] = "Employees"
            st.rerun()
        return

    cx, cy = 60, 60
    outer_r = 55
    inner_r = 32
    gap_deg = 2.5
    total_gap = gap_deg * len(dept_data)
    available_deg = 360 - total_gap
    vb = "0 0 120 120"

    def p2c(r, angle_deg):
        a = math.radians(angle_deg - 90)
        return cx + r * math.cos(a), cy + r * math.sin(a)

    segments_svg = ""
    labels_svg = ""
    angle = 0

    for i, d in enumerate(dept_data):
        seg_deg = d["pct"] / 100 * available_deg
        if seg_deg < 0.5:
            angle += seg_deg + gap_deg
            continue
        start = angle
        end = angle + seg_deg
        large = 1 if seg_deg > 180 else 0
        color = _DEPT_COLORS[i % len(_DEPT_COLORS)]

        ox1, oy1 = p2c(outer_r, start)
        ox2, oy2 = p2c(outer_r, end)
        ix1, iy1 = p2c(inner_r, start)
        ix2, iy2 = p2c(inner_r, end)

        path = (
            f'M {ox1:.2f} {oy1:.2f} '
            f'A {outer_r} {outer_r} 0 {large} 1 {ox2:.2f} {oy2:.2f} '
            f'L {ix2:.2f} {iy2:.2f} '
            f'A {inner_r} {inner_r} 0 {large} 0 {ix1:.2f} {iy1:.2f} Z'
        )
        segments_svg += f'<path d="{path}" fill="{color}" />'

        # Label — positioned outside the ring with a tiny connector line
        mid_angle = start + seg_deg / 2
        ring_r = (outer_r + inner_r) / 2
        rx, ry = p2c(ring_r, mid_angle)

        # For segments big enough, put % + count ON the ring
        if seg_deg >= 30:
            labels_svg += (
                f'<text x="{rx:.1f}" y="{ry:.1f}" text-anchor="middle" '
                f'dominant-baseline="central" fill="#fff" '
                f'style="font-family:\'Plus Jakarta Sans\',system-ui,sans-serif;pointer-events:none;">'
                f'<tspan style="font-size:5px;font-weight:800;">{d["pct"]}%</tspan>'
                f'<tspan x="{rx:.1f}" dy="5.5" style="font-size:3.5px;font-weight:600;opacity:0.9;">{d["count"]} emp</tspan>'
                f'</text>'
            )

        # External label with dept name — connector line from outer edge
        label_anchor_r = outer_r + 3
        lx, ly = p2c(label_anchor_r, mid_angle)
        # Determine text anchor based on which side
        is_right = lx >= cx
        txt_anchor = "start" if is_right else "end"
        txt_x = lx + 2 if is_right else lx - 2
        # Connector line end
        line_end_x = lx + 8 if is_right else lx - 8

        dept_name = d["department"]
        if len(dept_name) > 10:
            dept_name = dept_name[:9] + "…"

        # Connector line
        labels_svg += (
            f'<line x1="{lx:.1f}" y1="{ly:.1f}" x2="{line_end_x:.1f}" y2="{ly:.1f}" '
            f'stroke="{color}" stroke-width="0.4" opacity="0.5" />'
        )
        # Dept name
        labels_svg += (
            f'<text x="{line_end_x + (1.5 if is_right else -1.5):.1f}" y="{ly:.1f}" '
            f'text-anchor="{txt_anchor}" dominant-baseline="central" '
            f'fill="#191c1d" style="font-family:\'Plus Jakarta Sans\',system-ui,sans-serif;'
            f'font-size:3.6px;font-weight:700;">{dept_name}</text>'
        )
        # Small count + % below dept name (for segments too small to have ring label)
        if seg_deg < 30:
            labels_svg += (
                f'<text x="{line_end_x + (1.5 if is_right else -1.5):.1f}" y="{ly + 4.5:.1f}" '
                f'text-anchor="{txt_anchor}" dominant-baseline="central" '
                f'fill="#9ca3af" style="font-family:\'Plus Jakarta Sans\',system-ui,sans-serif;'
                f'font-size:3px;font-weight:600;">{d["count"]} · {d["pct"]}%</text>'
            )

        angle = end + gap_deg

    st.markdown(
        f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="{_CARD}padding:16px 8px;cursor:pointer;">'
        f'  <div style="{_MLBL}padding-left:12px;">Total Employees</div>'
        f'  <div style="position:relative;width:100%;max-width:260px;margin:0 auto;">'
        f'    <svg viewBox="{vb}" style="width:100%;height:auto;overflow:visible;">'
        f'      {segments_svg}'
        f'      {labels_svg}'
        f'    </svg>'
        f'    <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;pointer-events:none;">'
        f'      <div style="font-size:22px;font-weight:900;color:#191c1d;line-height:1;">{active_count}</div>'
        f'      <div style="font-size:7px;font-weight:700;color:#9ca3af;text-transform:uppercase;margin-top:2px;">Active</div>'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Employees →", key="bento_workforce", use_container_width=True):
        st.session_state["_nav_redirect"] = "Employees"
        st.rerun()


def _render_panel_attendance_detail(today_logs, name_map_all):
    """Panel 5: Attendance Detail — today's time logs table."""
    if not today_logs:
        st.markdown(
            f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="{_CARD}cursor:pointer;">'
            f'  <div style="{_MLBL}">Attendance Detail</div>'
            f'  <div style="color:#9ca3af;font-size:12px;padding:24px 0;text-align:center;">No attendance logs for today.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("Attendance →", key="bento_attendance_detail_empty", use_container_width=True):
            st.session_state["_nav_redirect"] = "Attendance"
            st.rerun()
        return

    _STATUS_PILLS = {
        "present":  ("#d1fae5", "#059669", "Present"),
        "on_time":  ("#d1fae5", "#059669", "On Time"),
        "late":     ("#fee2e2", "#93000a", "Late"),
        "absent":   ("#f3f4f6", "#6b7280", "Absent"),
        "overtime": ("#dbeafe", "#005bc1", "Overtime"),
    }

    _ROW_COLORS = [
        ("#dbeafe", "#005bc1"), ("#fce7f3", "#db2777"), ("#d1fae5", "#059669"),
        ("#fef3c7", "#d97706"), ("#ede9fe", "#7c3aed"), ("#e0f2fe", "#0284c7"),
    ]

    rows_html = ""
    for idx, log in enumerate(today_logs[:8]):
        eid = log.get("employee_id", "")
        name = name_map_all.get(eid, "Employee")
        initials = "".join(w[0] for w in name.split()[:2]).upper()
        ibg, ifg = _ROW_COLORS[idx % len(_ROW_COLORS)]

        clock_in = log.get("clock_in", "—")
        clock_out = log.get("clock_out") or "—"
        if clock_in and clock_in != "—":
            try:
                clock_in = clock_in[11:19] if len(clock_in) > 11 else clock_in
            except Exception:
                pass
        if clock_out and clock_out != "—":
            try:
                clock_out = clock_out[11:19] if len(clock_out) > 11 else clock_out
            except Exception:
                pass

        raw_status = (log.get("status") or "present").lower().replace(" ", "_")
        s_bg, s_fg, s_txt = _STATUS_PILLS.get(raw_status, ("#f3f4f6", "#6b7280", raw_status.title()))
        bg_row = "#fafbfc" if idx % 2 else "transparent"

        rows_html += (
            f'<tr style="background:{bg_row};">'
            f'  <td style="padding:10px 8px;">'
            f'    <div style="display:flex;align-items:center;gap:8px;">'
            f'      <div style="width:28px;height:28px;border-radius:50%;background:{ibg};display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:800;color:{ifg};flex-shrink:0;">{initials}</div>'
            f'      <span style="font-size:12px;font-weight:700;color:#191c1d;">{name}</span>'
            f'    </div>'
            f'  </td>'
            f'  <td style="padding:10px 8px;font-size:12px;color:#191c1d;font-family:monospace;">{clock_in}</td>'
            f'  <td style="padding:10px 8px;font-size:12px;color:#191c1d;font-family:monospace;">{clock_out}</td>'
            f'  <td style="padding:10px 8px;">'
            f'    <span style="font-size:9px;font-weight:700;padding:3px 10px;border-radius:9999px;background:{s_bg};color:{s_fg};text-transform:uppercase;">{s_txt}</span>'
            f'  </td>'
            f'</tr>'
        )

    st.markdown(
        f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="{_CARD}cursor:pointer;">'
        f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">'
        f'    <div style="{_MLBL}margin-bottom:0;">Attendance Detail</div>'
        f'    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="cursor:pointer;"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>'
        f'  </div>'
        f'  <div style="overflow-x:auto;max-height:240px;overflow-y:auto;">'
        f'    <table style="width:100%;border-collapse:collapse;text-align:left;">'
        f'      <thead>'
        f'        <tr style="border-bottom:2px solid #f3f4f6;">'
        f'          <th style="padding:8px;font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.1em;">Employee</th>'
        f'          <th style="padding:8px;font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.1em;">Time In</th>'
        f'          <th style="padding:8px;font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.1em;">Time Out</th>'
        f'          <th style="padding:8px;font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.1em;">Status</th>'
        f'        </tr>'
        f'      </thead>'
        f'      <tbody>{rows_html}</tbody>'
        f'    </table>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Attendance →", key="bento_attendance_detail", use_container_width=True):
        st.session_state["_nav_redirect"] = "Attendance"
        st.rerun()


def _render_panel_pending_requests(pending_details, name_map_all, pending_leave, pending_ot):
    """Panel 6: Pending Requests — leave/OT cards with approve/reject."""
    total_pending = pending_leave + pending_ot

    if not pending_details and total_pending == 0:
        st.markdown(
            f'<div class="gxp-bento-hero-card" style="{_CARD}">'
            f'  <div style="{_MLBL}">Pending Requests</div>'
            f'  <div style="text-align:center;padding:24px 0;">'
            f'    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
            f'    <div style="font-size:13px;font-weight:700;color:#10b981;margin-top:8px;">All caught up!</div>'
            f'    <div style="font-size:11px;color:#9ca3af;margin-top:4px;">No pending requests</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    _TYPE_STYLE = {
        "Leave":    ("#fef3c7", "#d97706"),
        "Overtime": ("#dbeafe", "#005bc1"),
    }

    cards_html = ""
    for req in pending_details[:3]:
        eid = req.get("employee_id", "")
        name = name_map_all.get(eid, "Employee")
        rtype = req.get("type", "Leave")
        detail = req.get("detail", "")
        tbg, tfg = _TYPE_STYLE.get(rtype, ("#f3f4f6", "#6b7280"))

        # Time ago (simple)
        ts = req.get("created_at", "")
        try:
            from datetime import datetime as _dt5, timezone as _tz5, timedelta as _td5
            dt = _dt5.fromisoformat(ts.replace("Z", "+00:00"))
            diff = _dt5.now(_tz5.utc) - dt
            if diff.days > 0:
                ago = f"{diff.days}d ago"
            elif diff.seconds > 3600:
                ago = f"{diff.seconds // 3600}h ago"
            else:
                ago = f"{diff.seconds // 60}m ago"
        except Exception:
            ago = ""

        cards_html += (
            f'<div style="background:#f8f9fa;padding:12px;border-radius:10px;border:1px solid transparent;">'
            f'  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">'
            f'    <span style="font-size:8px;font-weight:700;padding:2px 8px;border-radius:5px;background:{tbg};color:{tfg};">{rtype}</span>'
            f'    <span style="font-size:8px;color:#9ca3af;">{ago}</span>'
            f'  </div>'
            f'  <div style="font-size:11px;font-weight:700;color:#191c1d;margin-bottom:2px;">{name}</div>'
            f'  <div style="font-size:9px;color:#727784;margin-bottom:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{detail}</div>'
            f'  <div style="display:flex;gap:5px;">'
            f'    <div style="flex:1;padding:5px 0;background:#005bc1;color:#fff;font-size:9px;font-weight:700;border-radius:6px;text-align:center;cursor:pointer;">Approve</div>'
            f'    <div style="flex:1;padding:5px 0;background:#e5e7eb;color:#191c1d;font-size:9px;font-weight:700;border-radius:6px;text-align:center;cursor:pointer;">Decline</div>'
            f'  </div>'
            f'</div>'
        )

    # Summary card
    summary_card = (
        f'<div style="background:linear-gradient(135deg,#005bc1,#004494);padding:12px;border-radius:10px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:#fff;">'
        f'  <div style="font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;opacity:0.8;margin-bottom:3px;">Total Pending</div>'
        f'  <div style="font-size:28px;font-weight:900;line-height:1;margin-bottom:3px;">{total_pending}</div>'
        f'  <div style="font-size:8px;opacity:0.7;">{pending_leave} leave · {pending_ot} overtime</div>'
        f'</div>'
    )

    st.markdown(
        f'<div class="gxp-bento-hero-card" style="{_CARD}">'
        f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">'
        f'    <div>'
        f'      <div style="{_MLBL}margin-bottom:2px;">Action Required</div>'
        f'      <div style="font-size:13px;font-weight:800;color:#191c1d;">Pending Requests</div>'
        f'    </div>'
        f'    <div style="width:24px;height:24px;border-radius:50%;background:#dbeafe;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:#005bc1;">{total_pending}</div>'
        f'  </div>'
        f'  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;">'
        f'    {cards_html}'
        f'    {summary_card}'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# Phase D: Bento Grid Hero (legacy — kept for supervisor portal)
# ============================================================

_ENTITY_LABELS = {
    "employee":         "Employee",
    "pay_period":       "Pay Period",
    "payroll_entries":  "Payroll",
    "leave_request":    "Leave Request",
    "overtime_request": "OT Request",
    "company":          "Company",
    "leave_template":   "Leave Template",
    "holiday":          "Holiday",
}


def _load_recent_activity(n: int = 4) -> list[dict]:
    """Fetch last n audit_log entries for the Recent Activity card."""
    from datetime import timezone, timedelta
    _PH_TZ = timezone(timedelta(hours=8))
    try:
        db     = get_db()
        result = (
            db.table("audit_logs")
            .select("action,entity_type,entity_label,user_email,created_at")
            .eq("company_id", get_company_id())
            .order("created_at", desc=True)
            .limit(n)
            .execute()
        )
        rows = result.data or []
        entries = []
        for r in rows:
            action  = (r.get("action") or "updated").capitalize()
            etype   = _ENTITY_LABELS.get(r.get("entity_type", ""), r.get("entity_type", "").replace("_", " ").title())
            elabel  = r.get("entity_label") or ""
            actor   = (r.get("user_email") or "System").split("@")[0]
            ts_raw  = r.get("created_at", "")
            try:
                from datetime import datetime as _dt2
                dt  = _dt2.fromisoformat(ts_raw.replace("Z", "+00:00")).astimezone(_PH_TZ)
                ts  = dt.strftime("%b %d")
            except Exception:
                ts = ts_raw[:10]
            title = f"{action}: {elabel}" if elabel else f"{action} {etype}"
            entries.append({"title": title[:52], "sub": actor, "date": ts})
        return entries
    except Exception:
        return []


_MS = "font-family:'Material Symbols Outlined';font-variation-settings:'FILL' 1,'wght' 400,'GRAD' 0,'opsz' 24;"
_CARD  = "background:#ffffff;border-radius:14px;padding:20px;box-shadow:0 16px 32px rgba(45,51,53,0.05);"
_LABEL = "font-size:9px;font-weight:700;color:#004494;text-transform:uppercase;letter-spacing:.18em;margin-bottom:10px;font-family:'Plus Jakarta Sans',system-ui,sans-serif;"
_MLBL  = "font-size:9px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.18em;margin-bottom:10px;font-family:'Plus Jakarta Sans',system-ui,sans-serif;"
_BADGE = "display:inline-flex;align-items:center;padding:4px 14px;border-radius:9999px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;"
_BADGE_COLORS = {
    "green":  "background:#89fa9b;color:#005320;",
    "yellow": "background:#ffdea0;color:#5c4300;",
    "red":    "background:#ffdad6;color:#93000a;",
    "blue":   "background:#d8e2ff;color:#001a41;",
}


def _render_bento_row1(next_period, active_count, total_count):
    """Row 1: Upcoming Milestone | Active Employees | Recent Activity."""
    from datetime import date as _date
    today = _date.today()

    if next_period:
        end = next_period["period_end"]
        try:
            end_dt    = _date.fromisoformat(str(end))
            days_left = (end_dt - today).days
            date_disp = end_dt.strftime("%b %d").upper()
            if days_left < 0:
                b_col, b_txt = "red",    f"OVERDUE {abs(days_left)}D"
            elif days_left == 0:
                b_col, b_txt = "yellow", "DUE TODAY"
            elif days_left <= 7:
                b_col, b_txt = "yellow", f"IN {days_left} DAYS"
            else:
                b_col, b_txt = "green",  f"IN {days_left} DAYS"
        except Exception:
            date_disp, b_col, b_txt = str(end)[:6].upper(), "blue", "UPCOMING"
        status_txt  = next_period.get("status", "draft").upper()
        period_sub  = f"{next_period.get('period_start','')} \u2192 {next_period.get('period_end','')}"
    else:
        date_disp   = "\u2014"
        b_col, b_txt = "blue", "NOT SCHEDULED"
        status_txt, period_sub = "DRAFT", "No pay period created yet"

    badge_style = _BADGE + _BADGE_COLORS[b_col]

    col_next, col_emp, col_act = st.columns(3, gap="medium")

    def _nav(page):
        st.session_state["_nav_redirect"] = page

    with col_next:
        card_html = (
            f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="{_CARD}">'
            f'  <div style="{_LABEL}">Upcoming Milestone</div>'
            f'  <div style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:10px">'
            f'    <span style="font-size:44px;font-weight:800;color:#005bc1;line-height:1;letter-spacing:-2px;font-family:\'Plus Jakarta Sans\',system-ui,sans-serif;">{date_disp}</span>'
            f'    <span style="{badge_style}">{b_txt}</span>'
            f'  </div>'
            f'  <div style="font-size:11px;color:#6b7280;">{period_sub}</div>'
            f'  <div style="font-size:10px;color:#9ca3af;font-weight:600;margin-top:8px">Status: {status_txt}</div>'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)
        if st.button("Review Cycle \u2192", key="bento_review", use_container_width=True):
            _nav("Payroll Run"); st.rerun()

    with col_emp:
        inactive = total_count - active_count
        sub_txt  = f"{inactive} inactive" if inactive else "All active"
        _cid_tag = get_company_id()[:8]  # force DOM refresh on company switch
        card_html = (
            f'<div class="gxp-bento-hero-card gxp-bento-clickable" data-cid="{_cid_tag}" style="background:#febf0d;border-radius:16px;padding:28px;justify-content:space-between;">'
            f'  <div class="gxp-count" data-to="{active_count}" style="font-size:36px;font-weight:900;color:#000;line-height:1;font-family:\'Plus Jakarta Sans\',system-ui,sans-serif;">{active_count}</div>'
            f'  <div>'
            f'    <div style="font-size:1rem;font-weight:700;color:#000;">Active Employees</div>'
            f'    <div style="font-size:12px;font-weight:500;color:rgba(0,0,0,.55);margin-top:4px">{sub_txt}</div>'
            f'  </div>'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)
        if st.button("View Employees \u2192", key="bento_emp", use_container_width=True):
            _nav("Employees"); st.rerun()

    with col_act:
        activities = _load_recent_activity(4)
        _ACT_COLORS = [
            ("#d1fae5", "#059669"), ("#dbeafe", "#2563eb"),
            ("#fef3c7", "#d97706"), ("#fce7f3", "#db2777"),
        ]
        items_html = ""
        if activities:
            for idx, act in enumerate(activities):
                bg, fg = _ACT_COLORS[idx % len(_ACT_COLORS)]
                dot = f'<div style="width:8px;height:8px;border-radius:50%;background:{fg};flex-shrink:0"></div>'
                items_html += (
                    f'<div style="display:flex;align-items:flex-start;gap:10px;padding:6px 4px;border-radius:10px;">'
                    f'  <div style="width:28px;height:28px;border-radius:50%;background:{bg};display:flex;align-items:center;justify-content:center;flex-shrink:0">'
                    f'    {dot}'
                    f'  </div>'
                    f'  <div style="flex:1;min-width:0">'
                    f'    <div style="font-size:11px;font-weight:700;color:#191c1d;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{act["title"]}</div>'
                    f'    <div style="font-size:9px;color:#9ca3af;margin-top:1px">{act["sub"]} \u00b7 {act["date"]}</div>'
                    f'  </div>'
                    f'</div>'
                )
        else:
            items_html = '<div style="color:#9ca3af;font-size:12px;padding:12px">No recent activity.</div>'

        st.markdown(
            f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="{_CARD}">'
            f'  <div style="{_MLBL}margin-bottom:8px;">Recent Activity</div>'
            f'  <div>{items_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


@st.cache_data(ttl=120, show_spinner=False)
def _load_team_cache(_team_ids_tuple: tuple, company_id: str) -> dict:
    """Load ALL subordinate data in bulk — cached for 2 min.
    Returns a dict with employees, profiles, and a name_map for quick lookup.
    Called once per session refresh; all supervisor tabs read from this cache.
    """
    db = get_db()
    str_ids = [str(tid) for tid in _team_ids_tuple]

    # 1. Full employee records
    emp_resp = (
        db.table("employees")
        .select("id,first_name,last_name,employee_no,position,employment_type,"
                "date_hired,email,sss_no,philhealth_no,pagibig_no,bir_tin,"
                "basic_salary,salary_type,is_active")
        .in_("id", str_ids)
        .eq("is_active", True)
        .order("last_name")
        .execute()
    )
    employees = emp_resp.data or []

    # 2. Full profiles
    prof_resp = (
        db.table("employee_profiles")
        .select("employee_id,department,mobile_no,emergency_name,emergency_relationship,"
                "emergency_phone,date_of_birth,sex,civil_status,present_address_city,"
                "present_address_province,education_degree,education_school,photo_url")
        .in_("employee_id", str_ids)
        .execute()
    )
    profiles = {p["employee_id"]: p for p in (prof_resp.data or [])}

    # 3. Name map (used everywhere)
    name_map = {e["id"]: f'{e["first_name"]} {e["last_name"]}' for e in employees}

    # 4. Department map
    dept_map = {eid: p.get("department") or "" for eid, p in profiles.items()}

    return {
        "employees": employees,
        "profiles": profiles,
        "name_map": name_map,
        "dept_map": dept_map,
        "str_ids": str_ids,
    }


_SV_AVATAR_COLORS = [
    ("#dbeafe", "#2563eb"), ("#fef3c7", "#d97706"), ("#d1fae5", "#059669"),
    ("#ede9fe", "#7c3aed"), ("#f1f5f9", "#475569"), ("#fce7f3", "#be185d"),
    ("#e0e7ff", "#4338ca"), ("#fef9c3", "#a16207"),
]


def _build_201_modals_html(team_cache: dict, company_id: str) -> str:
    """Pre-render all employee 201 modals as hidden HTML divs.
    Shown/hidden with JS — zero Streamlit reruns for instant popup.
    """
    if not team_cache:
        return ""
    employees = team_cache["employees"]
    profiles = team_cache["profiles"]
    dept_map = team_cache["dept_map"]
    str_ids = team_cache["str_ids"]

    modals_html = ""
    for idx, emp in enumerate(employees):
        eid = emp.get("id", "")
        name = f'{emp.get("first_name", "")} {emp.get("last_name", "")}'
        initials = (emp.get("first_name", "?")[0] + emp.get("last_name", "?")[0]).upper()
        emp_no = emp.get("employee_no", "")
        pos = emp.get("position", "")
        dept = dept_map.get(eid, "")
        prof = profiles.get(eid, {})

        # Photo URL
        photo_url = (
            f"https://dduxctbrjggqkqdlhwpz.supabase.co/storage/v1/object/public/"
            f"employee-photos/{company_id}/{eid}.jpg"
        ) if company_id else ""
        bg_img = f"background-image:url({photo_url});" if photo_url else ""

        # Avatar color
        bg, fg = _SV_AVATAR_COLORS[idx % len(_SV_AVATAR_COLORS)]

        # Employment type badge
        emp_type = emp.get("employment_type", "")
        et_bg = {"regular": "#d4edda", "probationary": "#fef3c7", "contractual": "#dbeafe"}.get(
            (emp_type or "").lower(), "#f1f5f9")
        et_fg = {"regular": "#155724", "probationary": "#92400e", "contractual": "#1e40af"}.get(
            (emp_type or "").lower(), "#475569")
        et_label = (emp_type or "").capitalize()

        # Personal details
        city = prof.get("present_address_city") or ""
        prov = prof.get("present_address_province") or ""
        loc = f"{city}, {prov}".strip(", ") or "\u2014"

        dash = "\u2014"

        modals_html += (
            f'<div id="gxp201_{eid}" class="gxp-201-content" style="display:none;">'
            # Header
            f'<div class="gxp-201-hdr">'
            f'<div class="gxp-201-avatar" style="background:{bg};{bg_img}">'
            f'<span style="color:{fg};">{initials}</span></div>'
            f'<div>'
            f'<div class="gxp-201-name">{name}</div>'
            f'<div class="gxp-201-sub">{emp_no} &middot; {dept} &middot; {pos}</div>'
            f'<span class="gxp-201-badge" style="background:{et_bg};color:{et_fg};">{et_label}</span>'
            f'</div></div>'
            # Divider
            f'<div class="gxp-201-divider"></div>'
            # Detail grid
            f'<div class="gxp-201-grid">'
            # Employment column
            f'<div>'
            f'<div class="gxp-201-section-title">Employment</div>'
            f'<div class="gxp-201-field">Date Hired: <b>{emp.get("date_hired") or dash}</b></div>'
            f'<div class="gxp-201-field">Email: <b>{emp.get("email") or dash}</b></div>'
            f'<div class="gxp-201-field">Mobile: <b>{prof.get("mobile_no") or dash}</b></div>'
            f'<div class="gxp-201-field">Salary Type: <b>{emp.get("salary_type") or dash}</b></div>'
            f'</div>'
            # Personal column
            f'<div>'
            f'<div class="gxp-201-section-title">Personal</div>'
            f'<div class="gxp-201-field">Date of Birth: <b>{prof.get("date_of_birth") or dash}</b></div>'
            f'<div class="gxp-201-field">Sex: <b>{prof.get("sex") or dash}</b> &middot; Civil Status: <b>{prof.get("civil_status") or dash}</b></div>'
            f'<div class="gxp-201-field">Location: <b>{loc}</b></div>'
            f'<div class="gxp-201-field">Education: <b>{prof.get("education_degree") or dash}</b></div>'
            f'</div>'
            # Emergency column
            f'<div>'
            f'<div class="gxp-201-section-title">Emergency Contact</div>'
            f'<div class="gxp-201-field">Name: <b>{prof.get("emergency_name") or dash}</b></div>'
            f'<div class="gxp-201-field">Relationship: <b>{prof.get("emergency_relationship") or dash}</b></div>'
            f'<div class="gxp-201-field">Phone: <b>{prof.get("emergency_phone") or dash}</b></div>'
            f'</div>'
            f'</div>'
            # Divider
            f'<div class="gxp-201-divider"></div>'
            # Government IDs
            f'<div class="gxp-201-section-title">Government IDs</div>'
            f'<div class="gxp-201-gov-grid">'
            f'<div class="gxp-201-field">SSS: <b>{emp.get("sss_no") or dash}</b></div>'
            f'<div class="gxp-201-field">PhilHealth: <b>{emp.get("philhealth_no") or dash}</b></div>'
            f'<div class="gxp-201-field">Pag-IBIG: <b>{emp.get("pagibig_no") or dash}</b></div>'
            f'<div class="gxp-201-field">BIR TIN: <b>{emp.get("bir_tin") or dash}</b></div>'
            f'</div>'
            f'</div>'
        )

    # Overlay container with modal shell + close button
    html = (
        f'<div id="gxp201-overlay" class="gxp-201-overlay">'
        f'<div class="gxp-201-modal" style="position:relative;">'
        f'<button class="gxp-201-close" id="gxp201-close">&times;</button>'
        f'<div id="gxp201-body">{modals_html}</div>'
        f'</div></div>'
    )
    return html


def _build_201_modal_js() -> str:
    """JS to open/close the pure HTML 201 modal. No Streamlit rerun."""
    return """
    <script>
    (function(){
        const pd = window.parent.document;

        // ── Open / Close functions (on parent window so tiles can call them) ──
        window.parent._gxpOpen201 = function(eid) {
            pd.querySelectorAll('.gxp-201-content').forEach(d => d.style.display = 'none');
            var target = pd.getElementById('gxp201_' + eid);
            if (target) target.style.display = 'block';
            var ov = pd.getElementById('gxp201-overlay');
            if (ov) ov.classList.add('gxp-201-open');
        };
        window.parent._gxpClose201 = function() {
            var ov = pd.getElementById('gxp201-overlay');
            if (ov) ov.classList.remove('gxp-201-open');
        };

        // ── Close button ──
        var closeBtn = pd.getElementById('gxp201-close');
        if (closeBtn) {
            closeBtn.onclick = function(e) { e.stopPropagation(); window.parent._gxpClose201(); };
        }
        // Click overlay background to close
        var ov = pd.getElementById('gxp201-overlay');
        if (ov) {
            ov.addEventListener('click', function(e) {
                if (e.target === ov) window.parent._gxpClose201();
            });
        }
        // ESC key to close
        pd.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && window.parent._gxpClose201) window.parent._gxpClose201();
        });

        // ── Wire clickable elements ──
        function wireAll() {
            // Team tiles (Your Team grid)
            pd.querySelectorAll('.gxp-team-tile[data-emp-id]').forEach(el => {
                if (el.dataset.gxp201) return;
                el.dataset.gxp201 = '1';
                el.style.cursor = 'pointer';
                el.addEventListener('click', () => {
                    window.parent._gxpOpen201(el.dataset.empId);
                });
            });

            // Swipe action clicks (201 cards)
            pd.querySelectorAll('.ps-swipe-act[data-ps-action]').forEach(el => {
                if (el.dataset.gxp201) return;
                el.dataset.gxp201 = '1';
                var action = el.getAttribute('data-ps-action');
                if (action && action.startsWith('view201_')) {
                    el.addEventListener('click', function(e) {
                        e.stopPropagation();
                        window.parent._gxpOpen201(action.slice(8));
                    });
                }
            });

            // Hide old hidden buttons (tile201_ and sv201_) if any remain
            pd.querySelectorAll('[class*="st-key-tile201_"],[class*="st-key-sv201_"]').forEach(el => {
                el.style.position = 'absolute';
                el.style.opacity = '0';
                el.style.pointerEvents = 'none';
                el.style.height = '0';
                el.style.overflow = 'hidden';
            });
        }

        // Wire immediately, then re-wire after DOM settles (race condition fix)
        wireAll();
        setTimeout(wireAll, 300);
        setTimeout(wireAll, 800);

        // Also watch for new tiles added dynamically
        var obs = new MutationObserver(function() { wireAll(); });
        var main = pd.querySelector('[data-testid="stMain"]');
        if (main) obs.observe(main, {childList: true, subtree: true});
        // Auto-disconnect after 10s to avoid perf drag
        setTimeout(function() { obs.disconnect(); }, 10000);
    })();
    </script>
    """


def _render_supervisor_row1(team_ids, pending_leave, pending_ot, team_cache: dict | None = None):
    """Supervisor Row 1: Expanded Team Grid (7/12) | Pending Approvals + mini alerts (5/12)."""

    team_count = len(team_ids)

    col_team, col_right = st.columns([7, 5], gap="medium")

    def _nav(page):
        st.session_state["_nav_redirect"] = page

    with col_team:
        _tiles_html = ""
        try:
            # Use cached data if available
            if team_cache:
                _team_emps = team_cache["employees"]
                dept_map = team_cache["dept_map"]
            else:
                db = get_db()
                str_ids = [str(tid) for tid in team_ids]
                team_data = (
                    db.table("employees")
                    .select("id,first_name,last_name")
                    .in_("id", str_ids)
                    .eq("is_active", True)
                    .order("last_name")
                    .execute()
                )
                _team_emps = team_data.data or []
                dept_map = {}
                if str_ids:
                    prof_result = (
                        db.table("employee_profiles")
                        .select("employee_id,department")
                        .in_("employee_id", str_ids)
                        .execute()
                    )
                    for p in (prof_result.data or []):
                        dept_map[p["employee_id"]] = p.get("department") or ""
            _team_tile_ids = []
            for idx, m in enumerate(_team_emps):
                _mid = m.get("id", "")
                _team_tile_ids.append(_mid)
                initials = (m.get("first_name", "?")[0] + m.get("last_name", "?")[0]).upper()
                first = m.get("first_name", "?")
                dept = dept_map.get(_mid, "")
                bg, fg = _SV_AVATAR_COLORS[idx % len(_SV_AVATAR_COLORS)]
                _color_idx = idx % len(_SV_AVATAR_COLORS)
                _tiles_html += (
                    f'<div class="gxp-team-tile gxp-tile-c{_color_idx}" data-emp-id="{_mid}" style="aspect-ratio:1;background:#f8f9fa;border-radius:16px;display:flex;flex-direction:column;'
                    f'align-items:center;justify-content:center;padding:8px;text-align:center;cursor:pointer;">'
                    f'  <div style="width:40px;height:40px;border-radius:50%;background:{bg};color:{fg};'
                    f'font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;margin-bottom:6px;">{initials}</div>'
                    f'  <div style="font-size:10px;font-weight:700;color:#191c1d;line-height:1.2;">{first}</div>'
                    f'  <div style="font-size:8px;color:#9ca3af;margin-top:2px;">{dept}</div>'
                    f'</div>'
                )
            # (Add New tile removed — supervisors manage team via Team Records)
        except Exception:
            _tiles_html = '<div style="color:#9ca3af;font-size:11px;grid-column:span 6;">Could not load team.</div>'

        st.markdown(
            f'<div class="gxp-bento-hero-card" style="{_CARD}min-height:180px;padding:24px;">'
            f'  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">'
            f'    <div style="{_LABEL}margin-bottom:0;">Your Team</div>'
            f'    <span style="font-size:10px;font-weight:700;color:#2563eb;background:#eff6ff;'
            f'padding:4px 12px;border-radius:9999px;">{team_count} Members Total</span>'
            f'  </div>'
            f'  <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px;">{_tiles_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_right:
        # Pending Approvals + Reminders/Alerts in a single flex column
        total_pending = pending_leave + pending_ot
        if total_pending > 0:
            items_html = ""
            if pending_leave:
                items_html += (
                    f'<div style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:12px;background:#f3f4f5;cursor:pointer;">'
                    f'  <span style="font-size:16px">🏖</span>'
                    f'  <div>'
                    f'    <div style="font-size:10px;font-weight:700;color:#191c1d">{pending_leave} Leave{"s" if pending_leave > 1 else ""}</div>'
                    f'    <div style="font-size:8px;color:#9ca3af">Awaiting approval</div>'
                    f'  </div>'
                    f'</div>'
                )
            if pending_ot:
                items_html += (
                    f'<div style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:12px;background:#f3f4f5;cursor:pointer;">'
                    f'  <span style="font-size:16px">⏰</span>'
                    f'  <div>'
                    f'    <div style="font-size:10px;font-weight:700;color:#191c1d">{pending_ot} OT Req</div>'
                    f'    <div style="font-size:8px;color:#9ca3af">Awaiting approval</div>'
                    f'  </div>'
                    f'</div>'
                )
            approvals_html = (
                f'<div style="{_CARD}flex:1;display:flex;flex-direction:column;justify-content:space-between;">'
                f'  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">'
                f'    <div style="{_LABEL}margin-bottom:0;">Pending Approvals</div>'
                f'    <span style="background:#febf0d;color:#000;font-size:10px;font-weight:900;'
                f'padding:2px 8px;border-radius:9999px;">{total_pending}</span>'
                f'  </div>'
                f'  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">{items_html}</div>'
                f'</div>'
            )
        else:
            approvals_html = (
                f'<div style="{_CARD}flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;">'
                f'  <div style="{_LABEL}align-self:flex-start;">Pending Approvals</div>'
                f'  <div style="font-size:28px;margin-bottom:4px">✅</div>'
                f'  <div style="font-size:12px;font-weight:700;color:#191c1d">All Clear</div>'
                f'  <div style="font-size:10px;color:#9ca3af;margin-top:2px">No pending requests</div>'
                f'</div>'
            )

        alerts_html = (
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;flex:1;">'
            '  <div style="background:#f3f4f5;padding:12px 16px;border-radius:16px;position:relative;overflow:hidden;'
            'display:flex;align-items:center;gap:10px;">'
            '    <div style="position:absolute;top:0;right:0;width:3px;height:100%;background:#89fa9b;border-radius:0 4px 4px 0;"></div>'
            '    <span class="material-symbols-outlined" style="font-size:18px;color:#059669;">task_alt</span>'
            '    <div>'
            '      <div style="font-size:10px;font-weight:700;color:#191c1d">Reminders</div>'
            '      <div style="font-size:8px;color:#727784;margin-top:1px">All caught up</div>'
            '    </div>'
            '  </div>'
            '  <div style="background:#f3f4f5;padding:12px 16px;border-radius:16px;position:relative;overflow:hidden;'
            'display:flex;align-items:center;gap:10px;">'
            '    <div style="position:absolute;top:0;right:0;width:3px;height:100%;background:#ba1a1a;border-radius:0 4px 4px 0;"></div>'
            '    <span class="material-symbols-outlined" style="font-size:18px;color:#ba1a1a;">notification_important</span>'
            '    <div>'
            '      <div style="font-size:10px;font-weight:700;color:#191c1d">Alerts</div>'
            '      <div style="font-size:8px;color:#727784;margin-top:1px">No issues</div>'
            '    </div>'
            '  </div>'
            '</div>'
        )

        st.markdown(
            f'<div style="display:flex;flex-direction:column;gap:10px;height:100%;">'
            f'  {approvals_html}'
            f'  {alerts_html}'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_bento_row2(latest_period, history, cal_events,
                       latest_entries: list | None = None,
                       name_map: dict | None = None,
                       team_scope: bool = False):
    """Row 2: Calendar | Payroll Expenditure.
    When team_scope=True, derive headline amount from latest_entries (team only)
    instead of company-wide history.
    """
    bar_vals = [int(r["gross_pay"] * 100) for r in history[-6:]] if history else []
    max_val  = max(bar_vals) if bar_vals else 1

    col_cal, col_exp = st.columns(2, gap="medium")

    with col_cal:
        st.markdown('<span class="gxp-bento-hero-card gxp-bento-clickable" style="display:none"></span>', unsafe_allow_html=True)
        _render_mini_calendar(cal_events or {})
        if st.button("Calendar \u2192", key="bento_cal", use_container_width=True):
            st.session_state["_nav_redirect"] = "Calendar"
            st.rerun()

    with col_exp:
        # When team_scope, derive headline from latest_entries (subordinates only)
        _has_data = False
        if team_scope and latest_entries:
            latest_gross = sum(e.get("gross_pay", 0) for e in latest_entries)
            _has_data = bool(latest_period and latest_gross)
            # No trend comparison for team scope (no historical per-team data)
            trend_s = f'<span style="color:#6b7280;font-size:12px">{len(latest_entries)} team member{"s" if len(latest_entries) != 1 else ""}</span>'
            # Build mini bars from entries (per-employee share)
            _sorted_for_bars = sorted(latest_entries, key=lambda e: e.get("gross_pay", 0))
            _bar_max = max(e.get("gross_pay", 0) for e in latest_entries) if latest_entries else 1
            bars_html = ""
            for i, ent in enumerate(_sorted_for_bars):
                _g = ent.get("gross_pay", 0)
                h = max(int((_g / _bar_max) * 100), 8) if _bar_max else 8
                bg = "#005bc1" if i == len(_sorted_for_bars) - 1 else "#e5e7eb"
                bars_html += f'<div style="flex:1;border-radius:4px 4px 0 0;background:{bg};height:{h}%;min-height:4px"></div>'
        elif latest_period and bar_vals:
            latest_gross = bar_vals[-1]
            _has_data = True
            prev_gross = bar_vals[-2] if len(bar_vals) >= 2 else 0
            if prev_gross:
                pct = (latest_gross - prev_gross) / prev_gross * 100
                if pct > 0.5:
                    trend_s = f'<span style="color:#005320;font-weight:700;font-size:12px">\u25b2 {pct:.1f}%</span>'
                elif pct < -0.5:
                    trend_s = f'<span style="color:#93000a;font-weight:700;font-size:12px">\u25bc {abs(pct):.1f}%</span>'
                else:
                    trend_s = '<span style="color:#6b7280;font-size:12px">\u2014 flat</span>'
            else:
                trend_s = '<span style="color:#6b7280;font-size:12px">First pay run</span>'
            bars_html = ""
            for i, v in enumerate(bar_vals):
                h   = max(int((v / max_val) * 100), 4)
                bg  = "#005bc1" if i == len(bar_vals) - 1 else "#e5e7eb"
                bars_html += f'<div style="flex:1;border-radius:4px 4px 0 0;background:{bg};height:{h}%;min-height:4px"></div>'
        else:
            latest_gross = 0
            trend_s = ""
            bars_html = ""

        if _has_data:
            period_lbl = f"{latest_period['period_start']} \u2192 {latest_period['period_end']}"
            _scope_label = "Team Payroll" if team_scope else "Payroll Expenditure"

            # Hint text for clickable card
            _click_hint = ""
            if latest_entries:
                _click_hint = (
                    '<div style="font-size:9px;color:#2563eb;margin-top:8px;font-weight:600;'
                    'cursor:pointer;letter-spacing:0.02em;" id="gxp-exp-hint">'
                    'Click to view breakdown per employee →</div>'
                )

            st.markdown(
                f'<div class="gxp-bento-hero-card gxp-exp-clickable" style="{_CARD}cursor:pointer;" id="gxp-exp-card">'
                f'  <div style="{_MLBL}">{_scope_label}</div>'
                f'  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
                f'    <span class="gxp-count-money" data-to="{latest_gross}" data-cid="{get_company_id()[:8]}" style="font-size:1.6rem;font-weight:800;color:#191c1d;letter-spacing:-1px">&#8369;{latest_gross / 100:,.2f}</span>'
                f'    {trend_s}'
                f'  </div>'
                f'  <div style="font-size:10px;color:#9ca3af;margin-top:4px">{period_lbl}</div>'
                f'  <div style="display:flex;align-items:flex-end;gap:5px;height:60px;margin-top:14px">{bars_html}</div>'
                f'  {_click_hint}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # ── Build per-employee breakdown modal (pure HTML/JS — instant) ──
            if latest_entries and name_map:
                _sorted_entries = sorted(latest_entries, key=lambda e: e.get("gross_pay", 0), reverse=True)
                _total_gross = sum(e.get("gross_pay", 0) for e in _sorted_entries)
                _total_net = sum(e.get("net_pay", 0) for e in _sorted_entries)
                _total_deductions = _total_gross - _total_net

                _rows_html = ""
                for idx, ent in enumerate(_sorted_entries):
                    _eid = ent.get("employee_id", "")
                    _ename = name_map.get(_eid, "Unknown")
                    _gross = ent.get("gross_pay", 0)
                    _net = ent.get("net_pay", 0)
                    _ded = _gross - _net
                    _pct = (_gross / _total_gross * 100) if _total_gross else 0
                    _bar_w = max(int(_pct), 2)
                    _bg_row = "#f8fafc" if idx % 2 == 0 else "#fff"
                    _rows_html += (
                        f'<tr style="background:{_bg_row};">'
                        f'<td style="padding:10px 14px;font-size:13px;font-weight:600;color:#191c1d;white-space:nowrap;">{_ename}</td>'
                        f'<td style="padding:10px 14px;font-size:13px;color:#191c1d;text-align:right;font-weight:700;">₱{_gross/100:,.2f}</td>'
                        f'<td style="padding:10px 14px;font-size:13px;color:#727784;text-align:right;">₱{_ded/100:,.2f}</td>'
                        f'<td style="padding:10px 14px;font-size:13px;color:#059669;text-align:right;font-weight:700;">₱{_net/100:,.2f}</td>'
                        f'<td style="padding:10px 14px;width:120px;">'
                        f'  <div style="background:#e5e7eb;border-radius:4px;height:8px;overflow:hidden;">'
                        f'    <div style="background:#2563eb;height:100%;width:{_bar_w}%;border-radius:4px;"></div>'
                        f'  </div>'
                        f'  <div style="font-size:9px;color:#9ca3af;margin-top:2px;text-align:right;">{_pct:.1f}%</div>'
                        f'</td>'
                        f'</tr>'
                    )

                _breakdown_html = (
                    f'<div id="gxp-exp-overlay" class="gxp-201-overlay">'
                    f'<div class="gxp-201-modal" style="position:relative;max-width:1000px;">'
                    f'<button class="gxp-201-close" id="gxp-exp-close">&times;</button>'
                    f'<div style="margin-bottom:20px;">'
                    f'  <div style="font-size:20px;font-weight:800;color:#191c1d;">Payroll Expenditure Breakdown</div>'
                    f'  <div style="font-size:12px;color:#727784;margin-top:4px;">{period_lbl} · {len(_sorted_entries)} employees</div>'
                    f'</div>'
                    # Summary cards
                    f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px;">'
                    f'  <div style="background:#eff6ff;border-radius:12px;padding:14px 18px;">'
                    f'    <div style="font-size:10px;font-weight:700;color:#2563eb;text-transform:uppercase;letter-spacing:0.04em;">Total Gross</div>'
                    f'    <div style="font-size:20px;font-weight:800;color:#191c1d;margin-top:4px;">₱{_total_gross/100:,.2f}</div>'
                    f'  </div>'
                    f'  <div style="background:#fef3c7;border-radius:12px;padding:14px 18px;">'
                    f'    <div style="font-size:10px;font-weight:700;color:#92400e;text-transform:uppercase;letter-spacing:0.04em;">Total Deductions</div>'
                    f'    <div style="font-size:20px;font-weight:800;color:#191c1d;margin-top:4px;">₱{_total_deductions/100:,.2f}</div>'
                    f'  </div>'
                    f'  <div style="background:#d1fae5;border-radius:12px;padding:14px 18px;">'
                    f'    <div style="font-size:10px;font-weight:700;color:#059669;text-transform:uppercase;letter-spacing:0.04em;">Total Net Pay</div>'
                    f'    <div style="font-size:20px;font-weight:800;color:#191c1d;margin-top:4px;">₱{_total_net/100:,.2f}</div>'
                    f'  </div>'
                    f'</div>'
                    # Table
                    f'<div style="overflow-x:auto;border-radius:12px;border:1px solid #e5e7eb;">'
                    f'<table style="width:100%;border-collapse:collapse;">'
                    f'<thead><tr style="background:#f1f5f9;">'
                    f'  <th style="padding:10px 14px;font-size:11px;font-weight:800;color:#475569;text-align:left;text-transform:uppercase;letter-spacing:0.04em;">Employee</th>'
                    f'  <th style="padding:10px 14px;font-size:11px;font-weight:800;color:#475569;text-align:right;text-transform:uppercase;letter-spacing:0.04em;">Gross</th>'
                    f'  <th style="padding:10px 14px;font-size:11px;font-weight:800;color:#475569;text-align:right;text-transform:uppercase;letter-spacing:0.04em;">Deductions</th>'
                    f'  <th style="padding:10px 14px;font-size:11px;font-weight:800;color:#475569;text-align:right;text-transform:uppercase;letter-spacing:0.04em;">Net Pay</th>'
                    f'  <th style="padding:10px 14px;font-size:11px;font-weight:800;color:#475569;text-align:right;text-transform:uppercase;letter-spacing:0.04em;">Share</th>'
                    f'</tr></thead>'
                    f'<tbody>{_rows_html}</tbody>'
                    f'<tfoot><tr style="background:#f1f5f9;border-top:2px solid #e5e7eb;">'
                    f'  <td style="padding:10px 14px;font-size:13px;font-weight:800;color:#191c1d;">Total</td>'
                    f'  <td style="padding:10px 14px;font-size:13px;font-weight:800;color:#191c1d;text-align:right;">₱{_total_gross/100:,.2f}</td>'
                    f'  <td style="padding:10px 14px;font-size:13px;font-weight:800;color:#727784;text-align:right;">₱{_total_deductions/100:,.2f}</td>'
                    f'  <td style="padding:10px 14px;font-size:13px;font-weight:800;color:#059669;text-align:right;">₱{_total_net/100:,.2f}</td>'
                    f'  <td style="padding:10px 14px;font-size:13px;font-weight:800;color:#191c1d;text-align:right;">100%</td>'
                    f'</tr></tfoot>'
                    f'</table></div>'
                    f'</div></div>'
                )
                st.markdown(_breakdown_html, unsafe_allow_html=True)

                # JS to wire click open/close
                _stc.html("""<script>
                (function(){
                    var pd=window.parent.document;
                    var card=pd.querySelector('.gxp-exp-clickable');
                    var ov=pd.getElementById('gxp-exp-overlay');
                    var closeBtn=pd.getElementById('gxp-exp-close');
                    if(card&&ov){
                        card.addEventListener('click',function(){ov.classList.add('gxp-201-open');});
                        if(closeBtn) closeBtn.onclick=function(e){e.stopPropagation();ov.classList.remove('gxp-201-open');};
                        ov.addEventListener('click',function(e){if(e.target===ov)ov.classList.remove('gxp-201-open');});
                        pd.addEventListener('keydown',function(e){if(e.key==='Escape')ov.classList.remove('gxp-201-open');});
                    }
                })();
                </script>""", height=0)

        else:
            _no_data_label = "Team Payroll" if team_scope else "Payroll Expenditure"
            _no_data_msg = ("No payroll data for your team yet." if team_scope
                            else "No finalized pay periods yet.<br>Run your first payroll to see trends.")
            st.markdown(
                f'<div class="gxp-bento-hero-card" style="{_CARD}">'
                f'  <div style="{_MLBL}">{_no_data_label}</div>'
                f'  <div style="color:#9ca3af;font-size:12px;margin-top:8px">{_no_data_msg}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _render_quick_actions_m3():
    """6-icon quick action cards — M3 style with emoji fallback icons."""
    _QA_ICONS = {
        "Add Employee":  "👤",
        "Run Payroll":   "▶",
        "Attendance":    "🕐",
        "Gov. Reports":  "🏛",
        "Calendar":      "📅",
        "Settings":      "⚙",
    }
    actions = [
        {"label": "Add Employee",  "nav": "Employees"},
        {"label": "Run Payroll",   "nav": "Payroll Run"},
        {"label": "Attendance",    "nav": "Attendance"},
        {"label": "Gov. Reports",  "nav": "Government Reports"},
        {"label": "Calendar",      "nav": "Calendar"},
        {"label": "Settings",      "nav": "Company Setup"},
    ]
    cols = st.columns(6, gap="small")
    for col, act in zip(cols, actions):
        with col:
            icon = _QA_ICONS[act["label"]]
            st.markdown(
                f'<div class="gxp-qa-card" style="background:#fff;border-radius:14px;padding:18px 8px 12px;'
                f'text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.04);margin-bottom:4px">'
                f'  <div style="width:44px;height:44px;border-radius:12px;background:#edeeef;'
                f'display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-size:20px">'
                f'    {icon}'
                f'  </div>'
                f'  <div style="font-size:10px;font-weight:700;color:#191c1d">{act["label"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(act["label"], key=f"qa_m3_{act['nav']}", use_container_width=True):
                st.session_state["_nav_redirect"] = act["nav"]
                st.rerun()


# ============================================================
# Section 1: Action Bar (ADP Hero)
# ============================================================

def _render_action_bar(company: dict, next_period: dict | None):
    company_name = company.get("name", "Your Company")
    today = date.today()
    today_str = today.strftime("%A, %B %d, %Y")

    # Reduce top padding above company name
    st.markdown(
        "<style>.stMainBlockContainer { padding-top: 0.5rem !important; }</style>",
        unsafe_allow_html=True,
    )
    # Company name as native Streamlit heading (h1 with anchor link on hover)
    st.title(company_name)

    # Next payroll info block
    if next_period:
        next_date = next_period["period_end"]
        badge = status_badge(next_period["status"])
        next_html = (
            '<div class="gxp-action-bar-next">'
            '<div class="gxp-action-bar-next-label">Next Payroll</div>'
            f'<div class="gxp-action-bar-next-date">{next_date}</div>'
            f'<div style="margin-top:6px">{badge}</div>'
            '</div>'
        )
    else:
        next_html = (
            '<div class="gxp-action-bar-next">'
            '<div class="gxp-action-bar-next-label">Next Payroll</div>'
            '<div class="gxp-action-bar-next-date" style="color:#94a3b8">Not scheduled</div>'
            '<div style="margin-top:6px;font-size:11px;color:#64748b">Create a pay period to begin</div>'
            '</div>'
        )

    st.markdown(
        '<div class="gxp-action-bar">'
        '<div class="gxp-action-bar-left">'
        '<div style="text-align:left;">'
        f'<div class="gxp-action-bar-next-label">Today</div>'
        f'<div class="gxp-action-bar-next-date">{today_str}</div>'
        '</div>'
        '</div>'
        '<div class="gxp-action-bar-right">'
        f'{next_html}'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Quick action buttons — flush below the hero bar
    st.markdown('<div class="gxp-quick-actions">', unsafe_allow_html=True)
    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1:
        if st.button("Run Payroll", width='stretch', type="primary", key="qa_run"):
            st.session_state["_nav_redirect"] = "Payroll Run"
            st.rerun()
    with qa2:
        if st.button("Add Employee", width='stretch', key="qa_add"):
            st.session_state["_nav_redirect"] = "Employees"
            st.rerun()
    with qa3:
        if st.button("Gov. Reports", width='stretch', key="qa_gov"):
            st.session_state["_nav_redirect"] = "Government Reports"
            st.rerun()
    with qa4:
        if st.button("Company Setup", width='stretch', key="qa_setup"):
            st.session_state["_nav_redirect"] = "Company Setup"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# Section 2: Alerts / To-Do
# ============================================================

def _render_alerts(deadlines: list[dict], periods: list[dict]):
    alerts = []

    # Check for overdue / due-soon deadlines — skip if already remitted
    for i, d in enumerate(deadlines):
        if d.get("remitted"):
            continue  # HR has already marked this as paid — suppress alert
        if d["days_until"] < 0:
            alerts.append({
                "type":     "overdue",
                "icon":     "\u26a0",
                "title":    f"{d['agency']} ({d['form']}) — OVERDUE",
                "desc":     f"Due {d['deadline'].strftime('%b %d')} \u2022 {abs(d['days_until'])} days overdue",
                "nav_page": "Government Reports",
                "btn_key":  f"dash_gov_overdue_{i}",
            })
        elif d["days_until"] <= 3:
            alerts.append({
                "type":     "warning",
                "icon":     "\u23f0",
                "title":    f"{d['agency']} ({d['form']}) — Due Soon",
                "desc":     f"Due {d['deadline'].strftime('%b %d')} \u2022 {d['days_until']} day{'s' if d['days_until'] != 1 else ''} left",
                "nav_page": "Government Reports",
                "btn_key":  f"dash_gov_soon_{i}",
            })

    # Check for draft periods needing review
    for i, p in enumerate(periods[:3]):
        if p["status"] == "draft":
            alerts.append({
                "type":     "info",
                "icon":     "\u270e",
                "title":    f"Payroll Draft — {p['period_start']} to {p['period_end']}",
                "desc":     "Payroll entries need review and finalization",
                "nav_page": "Payroll Run",
                "btn_key":  f"dash_payroll_draft_{i}",
            })
        elif p["status"] == "reviewed":
            alerts.append({
                "type":     "info",
                "icon":     "\u2713",
                "title":    f"Ready to Finalize — {p['period_start']} to {p['period_end']}",
                "desc":     "Payroll reviewed and ready for finalization",
                "nav_page": "Payroll Run",
                "btn_key":  f"dash_payroll_reviewed_{i}",
            })

    # ── Visual config per severity type ───────────────────────────────────
    _CFG = {
        "overdue": {
            "border":      "#e11d48",
            "badge_bg":    "#fecdd3", "badge_fg": "#be123c",
            "badge":       "OVERDUE",
            "title_color": "#be123c", "desc_color": "#9f1239",
            "icon_bg":     "#fecdd3", "icon_fg":   "#be123c",
        },
        "warning": {
            "border":      "#f59e0b",
            "badge_bg":    "#fde68a", "badge_fg": "#92400e",
            "badge":       "ACTION NEEDED",
            "title_color": "#92400e", "desc_color": "#78350f",
            "icon_bg":     "#fde68a", "icon_fg":   "#92400e",
        },
        "info": {
            "border":      "#3b82f6",
            "badge_bg":    "#bfdbfe", "badge_fg": "#1d4ed8",
            "badge":       "PENDING",
            "title_color": "#1d4ed8", "desc_color": "#1e40af",
            "icon_bg":     "#bfdbfe", "icon_fg":   "#1d4ed8",
        },
    }

    def _alert_card_html(a: dict) -> str:
        c = _CFG.get(a["type"], _CFG["info"])
        nav_page = a.get("nav_page", "Government Reports")
        is_gov = nav_page == "Government Reports"

        # Build action buttons based on alert type
        if is_gov:
            # Government: two nav buttons — Gov't Reports + Calendar
            actions_html = (
                f'<div class="gxp-remind-action-btn gxp-alert-nav-btn" '
                f'data-nav="Government Reports" style="'
                f'background:{c["border"]};color:#fff;border:none;">'
                f"Gov't Reports</div>"
                f'<div class="gxp-remind-action-btn gxp-alert-nav-btn" '
                f'data-nav="Calendar" style="'
                f'background:transparent;color:{c["desc_color"]};'
                f'border:1px solid {c["border"]};">Calendar</div>'
            )
        else:
            # Payroll: Payroll Run + Dismiss
            actions_html = (
                f'<div class="gxp-remind-action-btn gxp-alert-nav-btn" '
                f'data-nav="Payroll Run" style="'
                f'background:{c["border"]};color:#fff;border:none;">Payroll Run</div>'
                f'<div class="gxp-remind-action-btn gxp-alert-dismiss" style="'
                f'background:transparent;color:{c["desc_color"]};'
                f'border:1px solid {c["border"]};">Dismiss</div>'
            )

        return (
            f'<div class="gxp-remind-swipe gxp-alert-swipe-card">'

            # ── Action panel (behind the card) ──
            f'<div class="gxp-remind-actions" style="'
            f'background:linear-gradient(135deg,{c["icon_bg"]},{c["badge_bg"]});">'
            f'{actions_html}'
            f'</div>'

            # ── Card (slides left on hover) ──
            f'<div class="gxp-remind-card-inner" style="'
            f'background:var(--gxp-surface);'
            f'border:1px solid var(--gxp-border);'
            f'border-top:3px solid {c["border"]};'
            f'border-radius:10px;'
            f'padding:12px 12px 10px;">'
            f'<div style="display:flex;align-items:center;'
            f'justify-content:space-between;margin-bottom:8px;">'
            f'<div style="width:30px;height:30px;border-radius:50%;'
            f'background:{c["icon_bg"]};color:{c["icon_fg"]};flex-shrink:0;'
            f'display:flex;align-items:center;justify-content:center;font-size:14px;">'
            f'{a["icon"]}</div>'
            f'<span style="font-size:9px;font-weight:800;letter-spacing:.5px;'
            f'text-transform:uppercase;background:{c["badge_bg"]};color:{c["badge_fg"]};'
            f'padding:2px 6px;border-radius:4px;">{c["badge"]}</span>'
            f'</div>'
            f'<div style="font-size:11.5px;font-weight:700;color:{c["title_color"]};'
            f'line-height:1.35;margin-bottom:3px;">{a["title"]}</div>'
            f'<div style="font-size:10.5px;color:{c["desc_color"]};opacity:.85;">'
            f'{a["desc"]}</div>'
            f'</div>'

            f'</div>'
        )

    # Wrap in container so hover is scoped to alerts section only
    with st.container():
        st.markdown(
            '<span class="gxp-alert-section" style="display:none"></span>'
            '<span class="gxp-alert-gov-marker" style="display:none"></span>'
            '<div class="gxp-panel-title" style="margin-bottom:10px">Alerts</div>',
            unsafe_allow_html=True,
        )

        if not alerts:
            st.markdown(
                '<div style="background:var(--gxp-surface);border:1px solid var(--gxp-border);'
                'border-top:3px solid #16a34a;border-radius:10px;padding:14px 12px;">'
                '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
                '<div style="width:30px;height:30px;border-radius:50%;background:#dcfce7;'
                'color:#16a34a;display:flex;align-items:center;justify-content:center;'
                'font-size:14px;"><span class="mdi mdi-check-circle" style="font-size:16px;font-variation-settings:\'FILL\' 1;"></span></div>'
                '<span style="font-size:9px;font-weight:800;letter-spacing:.5px;'
                'text-transform:uppercase;background:#dcfce7;color:#166534;'
                'padding:2px 6px;border-radius:4px;">ALL CLEAR</span></div>'
                '<div style="font-size:11.5px;font-weight:700;color:#166534;">All caught up</div>'
                '<div style="font-size:10.5px;color:#166534;opacity:.75;">No overdue items or pending tasks.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            _PRIORITY = {"overdue": 0, "warning": 1, "info": 2}
            top3 = sorted(alerts, key=lambda a: _PRIORITY.get(a["type"], 3))[:3]
            for a in top3:
                st.markdown(_alert_card_html(a), unsafe_allow_html=True)
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        # Hidden nav buttons for swipe "View" actions
        _alert_nav_slot = st.empty()
        with _alert_nav_slot:
            if st.button("\u200b", key="alert_nav_gov"):
                st.session_state["_nav_redirect"] = "Government Reports"
                st.rerun()
        _alert_nav_payroll_slot = st.empty()
        with _alert_nav_payroll_slot:
            if st.button("\u200b", key="alert_nav_payroll"):
                st.session_state["_nav_redirect"] = "Payroll Run"
                st.rerun()


# ============================================================
# Section 2B: Reminders — Supervisory Approvals
# ============================================================

def _render_reminders(pending_leave: int, pending_ot: int):
    """Approval reminder cards — wrapped in st.container() for scoped hover."""
    with st.container():
        st.markdown(
            '<span class="gxp-remind-section" style="display:none"></span>'
            '<div class="gxp-panel-title" style="margin-bottom:10px">Reminders</div>',
            unsafe_allow_html=True,
        )

        # ── Visual config per reminder type ─────────────────────────────
        _CFG_REMIND = {
            "leave": {
                "border":      "#7c3aed",
                "badge_bg":    "#ede9fe", "badge_fg": "#5b21b6",
                "icon_bg":     "#ede9fe", "icon_fg":  "#7c3aed",
                "title_color": "#5b21b6", "desc_color": "#6d28d9",
                "badge":       "NEEDS APPROVAL",
                "icon":        '<span class="mdi mdi-beach" style="font-size:18px;"></span>',
            },
            "ot": {
                "border":      "#0284c7",
                "badge_bg":    "#bae6fd", "badge_fg": "#0c4a6e",
                "icon_bg":     "#e0f2fe", "icon_fg":  "#0284c7",
                "title_color": "#0c4a6e", "desc_color": "#075985",
                "badge":       "NEEDS APPROVAL",
                "icon":        "\u23f1",
            },
        }

        def _remind_card_html(kind: str, count: int) -> str:
            c = _CFG_REMIND[kind]
            word = "Leave" if kind == "leave" else "Overtime"
            plural = "s" if count != 1 else ""
            req = "request" + plural
            title = f"{count} {word} {req.capitalize()} Pending"
            desc  = f"{count} {req} awaiting your approval"
            # Swipe-reveal card: action buttons sit behind, card slides left on hover
            # All positioning handled by CSS classes in styles.py
            return (
                f'<div class="gxp-remind-swipe gxp-remind-{kind}">'

                # ── Action panel (behind the card) ──
                f'<div class="gxp-remind-actions" style="'
                f'background:linear-gradient(135deg,{c["icon_bg"]},{c["badge_bg"]});">'
                f'<div class="gxp-remind-action-btn gxp-remind-approve" style="'
                f'background:{c["border"]};color:#fff;border:none;">Approvals</div>'
                f'<div class="gxp-remind-action-btn gxp-remind-dismiss" style="'
                f'background:transparent;color:{c["desc_color"]};'
                f'border:1px solid {c["border"]};">Dismiss</div>'
                f'</div>'

                # ── Card (slides left on hover) ──
                f'<div class="gxp-remind-card-inner" style="'
                f'background:var(--gxp-surface);'
                f'border:1px solid var(--gxp-border);'
                f'border-top:3px solid {c["border"]};'
                f'border-radius:10px;'
                f'padding:12px 12px 10px;">'
                f'<div style="display:flex;align-items:center;'
                f'justify-content:space-between;margin-bottom:8px;">'
                f'<div style="width:30px;height:30px;border-radius:50%;'
                f'background:{c["icon_bg"]};color:{c["icon_fg"]};flex-shrink:0;'
                f'display:flex;align-items:center;justify-content:center;font-size:14px;">'
                f'{c["icon"]}</div>'
                f'<span style="font-size:9px;font-weight:800;letter-spacing:.5px;'
                f'text-transform:uppercase;background:{c["badge_bg"]};color:{c["badge_fg"]};'
                f'padding:2px 6px;border-radius:4px;">{c["badge"]}</span>'
                f'</div>'
                f'<div style="font-size:11.5px;font-weight:700;color:{c["title_color"]};'
                f'line-height:1.35;margin-bottom:3px;">{title}</div>'
                f'<div style="font-size:10.5px;color:{c["desc_color"]};opacity:.85;">'
                f'{desc}</div>'
                f'</div>'

                f'</div>'
            )

        def _remind_empty_html(kind: str) -> str:
            cfg = _CFG_REMIND[kind]
            label = "No pending leave requests" if kind == "leave" else "No pending OT requests"
            return (
                f'<div style="background:var(--gxp-surface);border:1px solid var(--gxp-border);'
                f'border-top:3px solid #d1d5db;border-radius:10px;padding:12px 12px 10px;opacity:.5;">'
                f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">'
                f'<div style="width:30px;height:30px;border-radius:50%;background:#f3f4f6;'
                f'color:#9ca3af;display:flex;align-items:center;justify-content:center;font-size:14px;">'
                f'{cfg["icon"]}</div>'
                f'<span style="font-size:9px;font-weight:800;letter-spacing:.5px;'
                f'text-transform:uppercase;background:#f3f4f6;color:#9ca3af;'
                f'padding:2px 6px;border-radius:4px;">ALL CLEAR</span></div>'
                f'<div style="font-size:11px;color:#9ca3af;">{label}</div>'
                f'</div>'
            )

        any_pending = pending_leave > 0 or pending_ot > 0

        if not any_pending:
            st.markdown(
                '<div style="background:var(--gxp-surface);border:1px solid var(--gxp-border);'
                'border-top:3px solid #16a34a;border-radius:10px;padding:12px 12px 10px;">'
                '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">'
                '<div style="width:30px;height:30px;border-radius:50%;background:#dcfce7;'
                'color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:14px;"><span class="mdi mdi-check" style="font-size:18px;"></span></div>'
                '<span style="font-size:9px;font-weight:800;letter-spacing:.5px;'
                'text-transform:uppercase;background:#dcfce7;color:#166534;'
                'padding:2px 6px;border-radius:4px;">ALL CLEAR</span></div>'
                '<div style="font-size:11.5px;font-weight:700;color:#166534;">No Pending Approvals</div>'
                '<div style="font-size:10.5px;color:#166534;opacity:.75;">All leave and OT requests are handled.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            if pending_leave > 0:
                st.markdown(_remind_card_html("leave", pending_leave), unsafe_allow_html=True)
            else:
                st.markdown(_remind_empty_html("leave"), unsafe_allow_html=True)

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            if pending_ot > 0:
                st.markdown(_remind_card_html("ot", pending_ot), unsafe_allow_html=True)
            else:
                st.markdown(_remind_empty_html("ot"), unsafe_allow_html=True)

    # Hidden button for swipe Approvals — use st.empty so no visible space
    _approve_slot = st.empty()
    with _approve_slot:
        if st.button("\u200b", key="remind_approvals_pill"):
            st.session_state["_nav_redirect"] = "Employees"
            st.session_state["_emp_tab_redirect"] = "Leave & OT Approvals"
            st.rerun()


# ============================================================
# Stat Card Popup Dialogs
# ============================================================

@st.dialog("Government Reports", width="large")
def _dlg_gov_reports() -> None:
    """Embed the full Government Reports page inside a dialog."""
    from app.pages._government_reports import render as _gov_render
    _gov_render(show_title=False)


@st.dialog("Employees", width="large")
def _dlg_employees() -> None:
    """Full Employees page embedded in a dialog (all 3 tabs)."""
    # If Edit was clicked inside this dialog, we can't nest another dialog.
    # Instead: show a brief redirect, then use JS to navigate to the Employees page.
    if st.session_state.get("editing_id"):
        _eid = st.session_state["editing_id"]
        st.info("Opening employee edit form...")
        import streamlit.components.v1 as _dlg_stc
        _dlg_stc.html("""<script>
        (function(){
            var pd = window.parent.document;
            // Close this dialog by pressing ESC
            pd.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape',code:'Escape',bubbles:true}));
            // Click the Employees nav button after a short delay
            setTimeout(function(){
                var sb = pd.querySelector('[data-testid="stSidebar"]');
                if (!sb) return;
                var btns = sb.querySelectorAll('[data-testid="stButton"] button');
                for (var i = 0; i < btns.length; i++) {
                    if (btns[i].textContent.indexOf('Employees') !== -1) {
                        btns[i].click();
                        return;
                    }
                }
            }, 200);
        })();
        </script>""", height=0)
        return

    from app.pages._employees import (
        _render_employees_tab,
        _render_approvals_tab,
        _render_leave_balances_tab,
        _count_pending_admin,
    )

    pending_lr, pending_ot = _count_pending_admin()
    pending_total = pending_lr + pending_ot
    pending_label = f" ({pending_total})" if pending_total else ""

    tab_emp, tab_approvals, tab_balances = st.tabs([
        "Employees",
        f"Leave & OT Approvals{pending_label}",
        "Leave Balances",
    ])
    with tab_emp:
        _render_employees_tab(show_salary_toggle=False)
    with tab_approvals:
        _render_approvals_tab()
    with tab_balances:
        _render_leave_balances_tab()


@st.dialog("Leave Requests", width="large")
def _dlg_leave_approvals() -> None:
    """Embed the Leave & OT Approvals tab (filtered to leave) inside a dialog."""
    from app.pages._employees import _render_approvals_tab
    _render_approvals_tab()


@st.dialog("OT Requests", width="large")
def _dlg_ot_approvals() -> None:
    """Embed the Leave & OT Approvals tab inside a dialog (OT focus)."""
    from app.pages._employees import _render_approvals_tab
    _render_approvals_tab()


@st.dialog("Payroll Detail", width="large")
def _dlg_payroll_detail(entries: list[dict], period: dict | None) -> None:
    if not entries or not period:
        st.info("No payroll data available for this period.")
        return

    label = f"{period['period_start']} → {period['period_end']}"
    st.caption(f"Pay period: {label}")

    emp_names = _load_employee_names([e["employee_id"] for e in entries])

    rows = []
    for e in sorted(entries, key=lambda x: emp_names.get(x["employee_id"], "").lower()):
        deductions = (
            e["sss_employee"] + e["philhealth_employee"]
            + e["pagibig_employee"] + e["withholding_tax"]
        )
        rows.append({
            "Employee":   emp_names.get(e["employee_id"], "—"),
            "Gross Pay":  e["gross_pay"]  / 100,
            "Deductions": deductions      / 100,
            "Net Pay":    e["net_pay"]    / 100,
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df.style.format({"Gross Pay": "₱{:,.2f}", "Deductions": "₱{:,.2f}", "Net Pay": "₱{:,.2f}"}),
        use_container_width=True,
        hide_index=True,
    )
    st.markdown(
        f"**{len(rows)} employees · "
        f"Gross ₱{df['Gross Pay'].sum():,.2f} · "
        f"Deductions ₱{df['Deductions'].sum():,.2f} · "
        f"Net ₱{df['Net Pay'].sum():,.2f}**"
    )


@st.dialog("Employer Cost Breakdown", width="large")
def _dlg_employer_cost(entries: list[dict], period: dict | None) -> None:
    if not entries or not period:
        st.info("No payroll data available for this period.")
        return

    label = f"{period['period_start']} → {period['period_end']}"
    st.caption(f"Pay period: {label}")

    emp_names = _load_employee_names([e["employee_id"] for e in entries])

    rows = []
    for e in sorted(entries, key=lambda x: emp_names.get(x["employee_id"], "").lower()):
        total_er = e["sss_employer"] + e["philhealth_employer"] + e["pagibig_employer"]
        rows.append({
            "Employee":       emp_names.get(e["employee_id"], "—"),
            "SSS (ER)":       e["sss_employer"]        / 100,
            "PhilHealth (ER)": e["philhealth_employer"] / 100,
            "Pag-IBIG (ER)":  e["pagibig_employer"]    / 100,
            "Total ER":       total_er                  / 100,
        })

    df = pd.DataFrame(rows)
    fmt = {"SSS (ER)": "₱{:,.2f}", "PhilHealth (ER)": "₱{:,.2f}",
           "Pag-IBIG (ER)": "₱{:,.2f}", "Total ER": "₱{:,.2f}"}
    st.dataframe(df.style.format(fmt), use_container_width=True, hide_index=True)
    st.markdown(
        f"**Total employer contributions: "
        f"SSS ₱{df['SSS (ER)'].sum():,.2f} · "
        f"PhilHealth ₱{df['PhilHealth (ER)'].sum():,.2f} · "
        f"Pag-IBIG ₱{df['Pag-IBIG (ER)'].sum():,.2f} · "
        f"Total ₱{df['Total ER'].sum():,.2f}**"
    )


@st.dialog("YTD Payroll Summary", width="large")
def _dlg_ytd_summary(history: list[dict], current_year: int) -> None:
    ytd = [r for r in history if str(r["period"]).startswith(str(current_year))]
    if not ytd:
        st.info(f"No finalized payroll runs found for {current_year}.")
        return

    st.caption(f"{len(ytd)} pay run(s) in {current_year}")

    # Bar chart
    df_chart = pd.DataFrame(ytd)
    fig = px.bar(
        df_chart, x="period", y=["gross_pay", "net_pay"],
        labels={"value": "Amount (₱)", "period": "Pay Period", "variable": ""},
        color_discrete_map={"gross_pay": "#bfdbfe", "net_pay": "#2563eb"},
        barmode="overlay", height=220,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=8, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_traces(selector={"name": "gross_pay"}, name="Gross Pay")
    fig.update_traces(selector={"name": "net_pay"},   name="Net Pay")
    st.plotly_chart(fig, use_container_width=True)

    # Summary table
    df_tbl = pd.DataFrame([{
        "Period":     r["period"],
        "Employees":  r["headcount"],
        "Gross Pay":  r["gross_pay"],
        "Net Pay":    r["net_pay"],
    } for r in ytd])
    st.dataframe(
        df_tbl.style.format({"Gross Pay": "₱{:,.2f}", "Net Pay": "₱{:,.2f}"}),
        use_container_width=True, hide_index=True,
    )
    st.markdown(
        f"**YTD total: Gross ₱{df_tbl['Gross Pay'].sum():,.2f} · "
        f"Net ₱{df_tbl['Net Pay'].sum():,.2f}**"
    )


# ============================================================
# Section 3: Quick Stat Cards
# ============================================================

def _render_stat_cards(active_count: int, total_count: int,
                       total_gross: int, total_net: int, total_cost: int,
                       latest_period: dict | None, history: list[dict],
                       latest_entries: list[dict] | None = None,
                       headcount: int = 0):
    period_label = (
        f"{latest_period['period_start']} → {latest_period['period_end']}"
        if latest_period else "No data yet"
    )

    # Compute previous period values for trend indicators
    prev_gross = int(history[-2]["gross_pay"] * 100) if len(history) >= 2 else 0
    prev_net   = int(history[-2]["net_pay"]   * 100) if len(history) >= 2 else 0

    # YTD payroll cost (current calendar year)
    from datetime import date as _date
    current_year = _date.today().year
    ytd_cost = int(sum(
        row["gross_pay"] for row in history
        if str(row["period"]).startswith(str(current_year))
    ) * 100)

    entries = latest_entries or []

    cards = [
        {
            "svg":      _SVG["employees"],
            "icon_bg":  "#dbeafe", "icon_color": "#2563eb", "accent": "#2563eb",
            "label":    "Employees Paid",
            "value":    f"{headcount} / {active_count}" if latest_period else f"— / {active_count}",
            "sub":      period_label,
            "trend":    "",
            "dialog":   "employees",
            "pill_lbl": "Employees →",
        },
        {
            "svg":      _SVG["gross"],
            "icon_bg":  "#d1fae5", "icon_color": "#059669", "accent": "#059669",
            "label":    "Gross Pay",
            "value":    _fmt_short(total_gross),
            "sub":      period_label,
            "trend":    _trend_html(total_gross, prev_gross),
            "dialog":   "payroll",
            "pill_lbl": "Gross Pay →",
        },
        {
            "svg":      _SVG["net"],
            "icon_bg":  "#ede9fe", "icon_color": "#7c3aed", "accent": "#7c3aed",
            "label":    "Net Pay",
            "value":    _fmt_short(total_net),
            "sub":      period_label,
            "trend":    _trend_html(total_net, prev_net),
            "dialog":   "payroll",
            "pill_lbl": "Net Pay →",
        },
        {
            "svg":      _SVG["cost"],
            "icon_bg":  "#fef3c7", "icon_color": "#d97706", "accent": "#d97706",
            "label":    "Employer Cost",
            "value":    _fmt_short(total_cost),
            "sub":      "Gross + employer contributions",
            "trend":    "",
            "dialog":   "employer",
            "pill_lbl": "Emp. Cost →",
        },
        {
            "svg":      _SVG["ytd"],
            "icon_bg":  "#fce7f3", "icon_color": "#db2777", "accent": "#db2777",
            "label":    f"YTD Payroll ({current_year})",
            "value":    _fmt_short(ytd_cost) if ytd_cost else "—",
            "sub":      f"{len([r for r in history if str(r['period']).startswith(str(current_year))])} pay runs this year",
            "trend":    "",
            "dialog":   "ytd",
            "pill_lbl": "YTD →",
        },
    ]

    cols = st.columns(5)
    for i, (col, card) in enumerate(zip(cols, cards)):
        with col:
            trend_content = card["trend"] if card["trend"] else "&nbsp;"
            _accent = card.get("accent", "#005bc1")
            html = (
                f'<div class="gxp-stat-swipe">'
                # Action tray (behind card, at bottom)
                f'<div class="gxp-stat-actions" style="background:linear-gradient(135deg,{card["icon_bg"]},{card["icon_bg"]});">'
                f'<div class="gxp-stat-action-btn" data-stat-action="stat_card_{i}" '
                f'style="background:{_accent};color:#fff;border:none;">{card["pill_lbl"]}</div>'
                f'</div>'
                # Card (slides up on hover)
                f'<div class="gxp-stat-card gxp-stat-card-inner">'
                f'<div class="gxp-stat-icon" style="background:{card["icon_bg"]};color:{card["icon_color"]}">'
                f'{card["svg"]}</div>'
                f'<div class="gxp-stat-label">{card["label"]}</div>'
                f'<div class="gxp-stat-value">{card["value"]}</div>'
                f'<div class="gxp-stat-trend-row">{trend_content}</div>'
                f'<div class="gxp-stat-sub">{card["sub"]}</div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(html, unsafe_allow_html=True)
            # Hidden button (wired via JS)
            if st.button(card["pill_lbl"], key=f"stat_card_{i}", use_container_width=True):
                dlg = card["dialog"]
                if dlg == "employees":
                    _dlg_employees()
                elif dlg == "payroll":
                    _dlg_payroll_detail(entries, latest_period)
                elif dlg == "employer":
                    _dlg_employer_cost(entries, latest_period)
                elif dlg == "ytd":
                    _dlg_ytd_summary(history, current_year)


# ============================================================
# Section 4: Last Payroll Summary
# ============================================================

def _render_last_payroll_summary(latest_period: dict | None, latest_entries: list[dict]):
    if not latest_period or not latest_entries:
        st.markdown("""
        <div class="gxp-summary-card">
            <div class="gxp-summary-header">
                <div class="gxp-summary-title">Last Payroll Run</div>
            </div>
            <div style="text-align:center;padding:24px 0;color:#9ca3af;font-size:13px">
                No finalized payroll yet. Run your first payroll to see the summary here.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    headcount = len(latest_entries)
    gross = sum(e["gross_pay"] for e in latest_entries)
    net = sum(e["net_pay"] for e in latest_entries)
    total_deductions = gross - net
    badge = status_badge(latest_period["status"])

    st.markdown(f"""
    <div class="gxp-summary-card">
        <div class="gxp-summary-header">
            <div class="gxp-summary-title">Last Payroll Run</div>
            <div>{badge} &nbsp; <span style="font-size:12px;color:#6b7280">{latest_period['period_start']} to {latest_period['period_end']}</span></div>
        </div>
        <div class="gxp-summary-grid">
            <div class="gxp-summary-item">
                <div class="gxp-summary-item-label">Employees Paid</div>
                <div class="gxp-summary-item-value">{headcount}</div>
            </div>
            <div class="gxp-summary-item">
                <div class="gxp-summary-item-label">Total Gross</div>
                <div class="gxp-summary-item-value">{_fmt(gross)}</div>
            </div>
            <div class="gxp-summary-item">
                <div class="gxp-summary-item-label">Total Net</div>
                <div class="gxp-summary-item-value" style="color:#059669">{_fmt(net)}</div>
            </div>
            <div class="gxp-summary-item">
                <div class="gxp-summary-item-label">Total Deductions</div>
                <div class="gxp-summary-item-value" style="color:#dc2626">{_fmt(total_deductions)}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# Section 5A: Pending Approvals — compact panel (right column)
# ============================================================

def _render_pending_approvals_panel(pending_leave: int, pending_ot: int):
    total = pending_leave + pending_ot
    if total == 0:
        icon, bg, color, title, desc = '<span class="mdi mdi-check" style="font-size:18px;"></span>', "#f0fdf4", "#16a34a", "All caught up", "No pending leave or OT requests."
    else:
        icon, bg, color = '<span class="mdi mdi-clipboard-text" style="font-size:18px;"></span>', "#fffbeb", "#d97706"
        parts = []
        if pending_leave: parts.append(f"{pending_leave} leave")
        if pending_ot:    parts.append(f"{pending_ot} OT")
        title = f"{total} Request{'s' if total != 1 else ''} Pending"
        desc  = " · ".join(parts) + " awaiting approval"

    st.markdown(f"""
    <div class="gxp-panel" style="margin-bottom:12px">
        <div class="gxp-panel-header" style="padding-bottom:8px">
            <div class="gxp-panel-title">Pending Approvals</div>
        </div>
        <div style="display:flex;align-items:center;gap:12px;padding:10px 0">
            <div style="width:36px;height:36px;border-radius:8px;background:{bg};color:{color};
                        display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0">
                {icon}
            </div>
            <div>
                <div style="font-size:13px;font-weight:600;color:#1f2937">{title}</div>
                <div style="font-size:11px;color:#6b7280;margin-top:2px">{desc}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if total > 0:
        if st.button(f"Review {total} Request{'s' if total != 1 else ''}", key="dash_pending_panel", width="stretch"):
            st.session_state["_nav_redirect"] = "Employees"
            st.rerun()


# ============================================================
# Section 5B: Upcoming Deadlines — compact panel (right column)
# ============================================================

def _render_deadlines_panel(deadlines: list[dict]):
    st.markdown('<div class="gxp-panel">', unsafe_allow_html=True)
    st.markdown('<div class="gxp-panel-header" style="padding-bottom:8px"><div class="gxp-panel-title">Filing Deadlines</div></div>', unsafe_allow_html=True)

    for d in deadlines:
        days = d["days_until"]
        deadline_str = d["deadline"].strftime("%b %d, %Y")
        if d["deadline"] != d["raw_deadline"]:
            deadline_str += " (adj.)"

        if days < 0:
            tag = f'<span style="background:#fef2f2;color:#dc2626;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:700">OVERDUE</span>'
        elif days <= 3:
            tag = f'<span style="background:#fffbeb;color:#d97706;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:700">{days}d left</span>'
        elif days <= 7:
            tag = f'<span style="background:#dbeafe;color:#2563eb;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:700">{days}d left</span>'
        else:
            tag = f'<span style="background:#f0fdf4;color:#16a34a;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:700">{days}d</span>'

        st.markdown(f"""
        <div style="display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid #f3f4f6">
            <div>
                <div style="font-size:12px;font-weight:600;color:#1f2937">{d['agency']}
                    <span style="font-weight:400;color:#6b7280;font-size:11px">({d['form']})</span>
                </div>
                <div style="font-size:10px;color:#9ca3af;margin-top:1px">{deadline_str}</div>
            </div>
            <div>{tag}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# Section 5C: Government Remittance — full width below
# ============================================================

def _render_remittance(
    latest_entries: list[dict],
    remittance_status: dict[str, dict | None] | None = None,
):
    _status = remittance_status or {}

    # Plain section title — no panel wrapper (no white card behind the heading)
    st.markdown(
        '<div class="gxp-panel-title" style="margin-bottom:10px">Government Remittance</div>',
        unsafe_allow_html=True,
    )

    if not latest_entries:
        st.caption("Remittance data will appear after the first finalized payroll.")
        return

    total_sss_ee = sum(e["sss_employee"]        for e in latest_entries)
    total_sss_er = sum(e["sss_employer"]        for e in latest_entries)
    total_ph_ee  = sum(e["philhealth_employee"] for e in latest_entries)
    total_ph_er  = sum(e["philhealth_employer"] for e in latest_entries)
    total_pi_ee  = sum(e["pagibig_employee"]    for e in latest_entries)
    total_pi_er  = sum(e["pagibig_employer"]    for e in latest_entries)
    total_wht    = sum(e["withholding_tax"]     for e in latest_entries)
    all_gov      = (
        total_sss_ee + total_sss_er + total_ph_ee + total_ph_er
        + total_pi_ee + total_pi_er + total_wht
    )

    # Render all 4 cards in a single HTML block so equal-height CSS works
    # (no intermediate Streamlit widget calls that would break flex context)
    sss_html  = remit_card("SSS",          GOV_COLORS["SSS"],
                           [("Employee", _fmt(total_sss_ee)), ("Employer", _fmt(total_sss_er))],
                           ("Total", _fmt(total_sss_ee + total_sss_er)),
                           remitted=bool(_status.get("SSS")))
    ph_html   = remit_card("PhilHealth",   GOV_COLORS["PhilHealth"],
                           [("Employee", _fmt(total_ph_ee)), ("Employer", _fmt(total_ph_er))],
                           ("Total", _fmt(total_ph_ee + total_ph_er)),
                           remitted=bool(_status.get("PhilHealth")))
    pi_html   = remit_card("Pag-IBIG",    GOV_COLORS["Pag-IBIG"],
                           [("Employee", _fmt(total_pi_ee)), ("Employer", _fmt(total_pi_er))],
                           ("Total", _fmt(total_pi_ee + total_pi_er)),
                           remitted=bool(_status.get("Pag-IBIG")))
    bir_html  = remit_card("BIR Withholding", GOV_COLORS["BIR"],
                           [("Withholding Tax", _fmt(total_wht))],
                           ("All Gov Total", _fmt(all_gov)),
                           remitted=bool(_status.get("BIR")))

    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'
        f'{sss_html}{ph_html}{pi_html}{bir_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# Section 6: Analytics — compact (top-row right column)
# ============================================================

def _render_analytics_compact(history: list[dict]):
    """Overlay bar chart + deductions donut with amounts, for 1/3-width column."""
    if len(history) < 2:
        st.markdown(
            '<div class="gxp-panel" style="padding:16px">'
            '<div style="color:#9ca3af;font-size:12px;text-align:center;padding:24px 0">'
            'Analytics appear once you have 2+ finalized pay periods.'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    df = pd.DataFrame(history)

    # ── Overlay bar chart: Gross behind, Net in front ─
    fig_bar = px.bar(
        df,
        x="period",
        y=["gross_pay", "net_pay"],
        labels={"value": "₱", "period": "", "variable": ""},
        color_discrete_map={"gross_pay": "#bfdbfe", "net_pay": "#2563eb"},
        barmode="overlay",
    )
    fig_bar.for_each_trace(
        lambda t: t.update(name={"gross_pay": "Gross", "net_pay": "Net"}[t.name])
    )
    fig_bar.update_layout(
        title="Cost Trend",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font_size=10),
        margin=dict(l=0, r=0, t=40, b=0),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=210,
    )
    fig_bar.update_xaxes(showgrid=False, tickfont_size=9)
    fig_bar.update_yaxes(gridcolor="#f3f4f6", tickfont_size=9)
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Deductions donut — percent + ₱ amount ─────────
    latest = history[-1]
    sss, ph, pi, bir = latest["sss"], latest["philhealth"], latest["pagibig"], latest["bir"]
    amounts_fmt = [f"₱{v:,.0f}" for v in [sss, ph, pi, bir]]

    fig_donut = px.pie(
        names=["SSS", "PhilHealth", "Pag-IBIG", "BIR"],
        values=[sss, ph, pi, bir],
        title=f"Deductions — {latest['period'][:7]}",
        color_discrete_sequence=["#7c3aed", "#0891b2", "#059669", "#dc2626"],
        hole=0.42,
    )
    fig_donut.update_traces(
        text=amounts_fmt,
        textinfo="percent+text",
        texttemplate="%{percent:.0%}<br><b>%{text}</b>",
        textposition="inside",
        textfont_size=9,
    )
    fig_donut.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.05, font_size=9),
        margin=dict(l=0, r=0, t=40, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=230,
    )
    st.plotly_chart(fig_donut, use_container_width=True)


# ============================================================
# Mini Calendar Widget
# ============================================================

def _build_calendar_events(periods: list[dict], deadlines: list[dict]) -> dict:
    """
    Build a dict mapping ISO date strings to lists of {label, color} event markers.
    Merges holidays, pay period dates, and government deadlines for current month.
    """
    import calendar as _cal
    from collections import defaultdict

    today = date.today()
    year, month = today.year, today.month
    events: dict[str, list[dict]] = defaultdict(list)

    # 1. Holidays — load from calendar_view helper
    try:
        from app.pages._calendar_view import _load_holidays
        holidays = _load_holidays(year)
        for h in holidays:
            d = h.get("observed_date") or h.get("holiday_date")
            if d and d.month == month and d.year == year:
                htype = h.get("type", "regular")
                is_regular = "regular" in htype.lower()
                color = "#e53935" if is_regular else "#ff9800"
                etype = "holiday" if is_regular else "special"
                events[d.isoformat()].append({"label": h["name"], "color": color, "type": etype})
    except Exception:
        pass

    # 2. Pay period key dates (start, end, payment_date)
    for p in (periods or []):
        for field, label, color, etype in [
            ("start_date", "Pay period start", "#2196f3", "period"),
            ("end_date",   "Pay period end",   "#2196f3", "period"),
            ("payment_date", f"Pay day ({p.get('status','')})", "#4caf50", "payday"),
        ]:
            val = p.get(field)
            if val:
                d = date.fromisoformat(val) if isinstance(val, str) else val
                if d.month == month and d.year == year:
                    events[d.isoformat()].append({"label": label, "color": color, "type": etype})

    # 3. Government deadlines
    for dl in (deadlines or []):
        d = dl.get("date") or dl.get("deadline")
        if d:
            d = date.fromisoformat(d) if isinstance(d, str) else d
            if d.month == month and d.year == year:
                events[d.isoformat()].append({
                    "label": dl.get("label", dl.get("agency", "Deadline")),
                    "color": "#ff6f00",
                    "type": "deadline",
                })

    return dict(events)


def _render_mini_calendar(events: dict):
    """Render a compact month calendar with event dots + hover tooltips via components.html."""
    import calendar as _cal
    import json

    today = date.today()
    year, month = today.year, today.month
    month_name = today.strftime("%B %Y")

    # Build grid: list of weeks, each week = list of (day_number_or_0)
    _week_pref = st.session_state.get("gxp_week_start", "Sunday")
    _first_day = 6 if _week_pref == "Sunday" else 0
    cal_obj = _cal.Calendar(firstweekday=_first_day)
    weeks = cal_obj.monthdayscalendar(year, month)

    events_json = json.dumps(events)
    today_iso = today.isoformat()

    weeks_json = json.dumps(weeks)

    html = f"""
    <style>
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      body {{ background:transparent; font-family:'Plus Jakarta Sans',system-ui,sans-serif; }}
      .cal-wrap {{ padding:12px 8px 8px; }}
      .cal-header {{
        display:flex; justify-content:space-between; align-items:center;
        margin-bottom:10px; padding:0 2px;
      }}
      .cal-month {{ font-size:13px; font-weight:700; color:#191c1d; }}
      .cal-weekdays {{
        display:grid; grid-template-columns:repeat(7,1fr);
        text-align:center; margin-bottom:4px;
      }}
      .cal-weekdays span {{
        font-size:9px; font-weight:600; color:#727784;
        text-transform:uppercase; letter-spacing:0.05em;
      }}
      .cal-grid {{ display:grid; grid-template-columns:repeat(7,1fr); gap:1px; }}
      .cal-day {{
        position:relative; text-align:center; padding:4px 0;
        font-size:11px; font-weight:500; color:#424753; cursor:default;
        border-radius:6px; transition:background 0.15s;
        min-height:28px; display:flex; flex-direction:column;
        align-items:center; justify-content:center;
      }}
      .cal-day:hover {{ background:rgba(0,91,193,0.06); }}
      .cal-day.today {{
        color:#005bc1; font-weight:800; font-size:15px;
        text-shadow:0 0 8px rgba(0,91,193,0.45), 0 0 16px rgba(0,91,193,0.2);
      }}
      .cal-day.evt-holiday {{ color:#e53935; font-weight:700; font-size:12px; }}
      .cal-day.evt-special {{ color:#ff9800; font-weight:700; font-size:12px; }}
      .cal-day.evt-payday  {{ color:#4caf50; font-weight:700; font-size:12px; }}
      .cal-day.evt-deadline {{ color:#ff6f00; font-weight:700; font-size:12px; }}
      .cal-day.evt-period  {{ color:#2196f3; font-weight:600; }}
      .cal-day.today.evt-holiday {{ color:#e53935; font-size:15px; }}
      .cal-day.today.evt-payday  {{ color:#4caf50; font-size:15px; }}
      .cal-day.today.evt-special {{ color:#ff9800; font-size:15px; }}
      .cal-day.today.evt-deadline {{ color:#ff6f00; font-size:15px; }}
      .cal-day.empty {{ pointer-events:none; }}
      .cal-dots {{
        display:flex; gap:2px; justify-content:center;
        position:absolute; bottom:1px; left:50%;
        transform:translateX(-50%);
      }}
      .cal-dot {{
        width:4px; height:4px; border-radius:50%;
      }}
      /* Tooltip */
      .cal-tip {{
        display:none; position:absolute; bottom:calc(100% + 6px); left:50%;
        transform:translateX(-50%); background:#1e293b; color:#fff;
        font-size:10px; font-weight:500; padding:5px 8px; border-radius:6px;
        white-space:nowrap; z-index:999; pointer-events:none;
        box-shadow:0 4px 12px rgba(0,0,0,0.15);
        line-height:1.4;
      }}
      .cal-tip::after {{
        content:''; position:absolute; top:100%; left:50%;
        transform:translateX(-50%);
        border:4px solid transparent; border-top-color:#1e293b;
      }}
      .cal-day:hover .cal-tip {{ display:block; }}
    </style>
    <div class="cal-wrap">
      <div class="cal-header">
        <span class="cal-month">{month_name}</span>
      </div>
      <div class="cal-weekdays">
        {"<span>Su</span><span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span>" if _week_pref == "Sunday" else "<span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span><span>Su</span>"}
      </div>
      <div class="cal-grid" id="calGrid"></div>
    </div>
    <script>
    (function(){{
      var weeks  = {weeks_json};
      var events = {events_json};
      var todayISO = "{today_iso}";
      var year = {year}, month = {month};
      var grid = document.getElementById('calGrid');

      weeks.forEach(function(week){{
        week.forEach(function(day){{
          var cell = document.createElement('div');
          cell.className = 'cal-day';
          if (day === 0) {{
            cell.classList.add('empty');
            grid.appendChild(cell);
            return;
          }}
          var iso = year + '-' + String(month).padStart(2,'0') + '-' + String(day).padStart(2,'0');
          if (iso === todayISO) cell.classList.add('today');
          cell.textContent = day;

          var dayEvents = events[iso];
          if (dayEvents && dayEvents.length > 0) {{
            // Apply color class by priority: holiday > payday > deadline > special > period
            var prio = ['holiday','payday','deadline','special','period'];
            var types = dayEvents.map(function(e){{ return e.type || ''; }});
            for (var p=0; p<prio.length; p++) {{
              if (types.indexOf(prio[p]) !== -1) {{
                cell.classList.add('evt-' + prio[p]);
                break;
              }}
            }}
            var dots = document.createElement('div');
            dots.className = 'cal-dots';
            dayEvents.slice(0,3).forEach(function(ev){{
              var dot = document.createElement('span');
              dot.className = 'cal-dot';
              dot.style.backgroundColor = ev.color;
              dots.appendChild(dot);
            }});
            cell.appendChild(dots);

            // Tooltip
            var tip = document.createElement('div');
            tip.className = 'cal-tip';
            tip.innerHTML = dayEvents.map(function(ev){{
              return '<span style="color:'+ev.color+';margin-right:3px">●</span>' + ev.label;
            }}).join('<br>');
            cell.appendChild(tip);
          }}
          grid.appendChild(cell);
        }});
      }});
    }})();
    </script>
    """
    _stc.html(html, height=216, scrolling=False)


# ============================================================
# Supervisor Dashboard Sections (ADP Manager Tool)
# ============================================================

_COMING_SOON_CSS = (
    "background:linear-gradient(135deg,#f8fafc,#f1f5f9);border:1px dashed #cbd5e1;"
    "border-radius:16px;padding:24px;min-height:140px;display:flex;flex-direction:column;"
    "align-items:center;justify-content:center;text-align:center;opacity:.75;"
)


def _sv_load_dtr_exceptions(team_ids: list, team_cache: dict | None = None) -> list[dict]:
    """Load team members with missing time-in/out for today or recent workdays."""
    from datetime import date as _d, timedelta
    try:
        db = get_db()
        cid = get_company_id()
        today = _d.today()
        check_dates = []
        d = today
        for _ in range(5):
            if d.weekday() < 6:
                check_dates.append(str(d))
            d -= timedelta(days=1)
            if len(check_dates) >= 3:
                break

        str_ids = [str(tid) for tid in team_ids]
        logs = (
            db.table("time_logs")
            .select("employee_id,work_date,time_in,time_out,status,late_minutes,nsd_hours")
            .eq("company_id", cid)
            .in_("employee_id", str_ids)
            .in_("work_date", check_dates)
            .execute()
        )
        # Use cache for employee names if available
        if team_cache:
            emp_map = {e["id"]: e for e in team_cache["employees"]}
        else:
            emps = (
                db.table("employees")
                .select("id,first_name,last_name,position")
                .in_("id", str_ids)
                .eq("is_active", True)
                .execute()
            )
            emp_map = {e["id"]: e for e in (emps.data or [])}

        exceptions = []
        for log in (logs.data or []):
            issues = []
            if not log.get("time_in"):
                issues.append("No Time In")
            if not log.get("time_out") and log.get("time_in"):
                issues.append("No Time Out")
            if (log.get("late_minutes") or 0) >= 15:
                issues.append(f"Late {log['late_minutes']}min")
            if (log.get("nsd_hours") or 0) > 0:
                issues.append(f"NSD {log['nsd_hours']:.1f}h")
            if issues:
                emp = emp_map.get(log["employee_id"], {})
                exceptions.append({
                    "name": f'{emp.get("first_name", "?")} {emp.get("last_name", "")}',
                    "position": emp.get("position", ""),
                    "date": log["work_date"],
                    "issues": issues,
                    "status": log.get("status", ""),
                })
        # Sort by date desc, then name
        exceptions.sort(key=lambda x: (x["date"], x["name"]), reverse=True)
        return exceptions[:12]
    except Exception:
        return []


def _sv_load_holiday_workers(team_ids: list, team_cache: dict | None = None) -> list[dict]:
    """Load team members who worked on recent holidays."""
    from datetime import date as _d, timedelta
    try:
        db = get_db()
        cid = get_company_id()
        today = _d.today()
        month_ago = today - timedelta(days=30)

        # Get recent holidays
        holidays = (
            db.table("holidays")
            .select("date,observed_date,name,type")
            .gte("date", str(month_ago))
            .lte("date", str(today))
            .execute()
        )
        if not holidays.data:
            return []

        hol_dates = {}
        for h in holidays.data:
            d = h.get("observed_date") or h["date"]
            hol_dates[d] = {"name": h["name"], "type": h["type"]}

        if not hol_dates:
            return []

        str_ids = [str(tid) for tid in team_ids]
        logs = (
            db.table("time_logs")
            .select("employee_id,work_date,gross_hours,ot_hours")
            .eq("company_id", cid)
            .in_("employee_id", str_ids)
            .in_("work_date", list(hol_dates.keys()))
            .not_.is_("time_in", "null")
            .execute()
        )
        if not logs.data:
            return []

        if team_cache:
            emp_map = {e["id"]: e for e in team_cache["employees"]}
        else:
            emps = (
                db.table("employees")
                .select("id,first_name,last_name")
                .in_("id", str_ids)
                .execute()
            )
            emp_map = {e["id"]: e for e in (emps.data or [])}

        result = []
        for log in logs.data:
            hol = hol_dates.get(log["work_date"], {})
            emp = emp_map.get(log["employee_id"], {})
            result.append({
                "name": f'{emp.get("first_name", "?")} {emp.get("last_name", "")}',
                "date": log["work_date"],
                "holiday": hol.get("name", ""),
                "type": hol.get("type", ""),
                "hours": log.get("gross_hours", 0),
            })
        return result
    except Exception:
        return []


def _sv_load_ot_requests(team_ids: list, team_cache: dict | None = None) -> list[dict]:
    """Load pending + recent OT requests from team."""
    try:
        db = get_db()
        cid = get_company_id()
        str_ids = [str(tid) for tid in team_ids]
        result = (
            db.table("overtime_requests")
            .select("id,employee_id,ot_date,start_time,end_time,hours,reason,status,created_at")
            .eq("company_id", cid)
            .in_("employee_id", str_ids)
            .order("created_at", desc=True)
            .limit(15)
            .execute()
        )
        if team_cache:
            emp_map = {e["id"]: e for e in team_cache["employees"]}
        else:
            emps = (
                db.table("employees")
                .select("id,first_name,last_name")
                .in_("id", str_ids)
                .execute()
            )
            emp_map = {e["id"]: e for e in (emps.data or [])}
        rows = []
        for r in (result.data or []):
            emp = emp_map.get(r["employee_id"], {})
            rows.append({
                **r,
                "name": f'{emp.get("first_name", "?")} {emp.get("last_name", "")}',
            })
        return rows
    except Exception:
        return []


def _sv_load_leave_overview(team_ids: list, team_cache: dict | None = None) -> list[dict]:
    """Load team leave balances and pending requests."""
    from datetime import date as _d
    try:
        db = get_db()
        cid = get_company_id()
        year = _d.today().year
        str_ids = [str(tid) for tid in team_ids]

        # Get leave balances
        balances = (
            db.table("leave_balance")
            .select("employee_id,leave_type,opening_balance")
            .eq("company_id", cid)
            .eq("year", year)
            .in_("employee_id", str_ids)
            .execute()
        )
        # Get approved leave days this year
        approved = (
            db.table("leave_requests")
            .select("employee_id,leave_type,days")
            .eq("company_id", cid)
            .eq("status", "approved")
            .in_("employee_id", str_ids)
            .gte("start_date", f"{year}-01-01")
            .execute()
        )
        # Get pending leave requests
        pending = (
            db.table("leave_requests")
            .select("id,employee_id,leave_type,start_date,end_date,days,reason,status,created_at")
            .eq("company_id", cid)
            .eq("status", "pending")
            .in_("employee_id", str_ids)
            .order("created_at", desc=True)
            .execute()
        )
        # Get special leaves
        special = (
            db.table("special_leave_requests")
            .select("employee_id,leave_type,days,status,start_date,end_date")
            .eq("company_id", cid)
            .in_("employee_id", str_ids)
            .gte("start_date", f"{year}-01-01")
            .execute()
        )

        if team_cache:
            emp_map = {e["id"]: e for e in team_cache["employees"]}
        else:
            emps = (
                db.table("employees")
                .select("id,first_name,last_name")
                .in_("id", str_ids)
                .eq("is_active", True)
                .execute()
            )
            emp_map = {e["id"]: e for e in (emps.data or [])}

        # Build per-employee balance summary
        bal_map = {}  # emp_id -> {VL: {opening, used}, SL: ...}
        for b in (balances.data or []):
            eid = b["employee_id"]
            lt = b["leave_type"]
            bal_map.setdefault(eid, {}).setdefault(lt, {"opening": 0, "used": 0})
            bal_map[eid][lt]["opening"] = float(b.get("opening_balance") or 0)
        for a in (approved.data or []):
            eid = a["employee_id"]
            lt = a["leave_type"]
            bal_map.setdefault(eid, {}).setdefault(lt, {"opening": 0, "used": 0})
            bal_map[eid][lt]["used"] += float(a.get("days") or 0)

        return {
            "balances": bal_map,
            "emp_map": emp_map,
            "pending": pending.data or [],
            "special": special.data or [],
        }
    except Exception:
        return {"balances": {}, "emp_map": {}, "pending": [], "special": []}


def _sv_load_statutory_overview(team_ids: list, team_cache: dict | None = None) -> list[dict]:
    """Load latest payroll statutory deductions for team (read-only)."""
    try:
        db = get_db()
        cid = get_company_id()
        str_ids = [str(tid) for tid in team_ids]

        periods = (
            db.table("pay_periods")
            .select("id,period_start,period_end,status")
            .eq("company_id", cid)
            .in_("status", ["finalized", "paid"])
            .order("period_end", desc=True)
            .limit(1)
            .execute()
        )
        if not periods.data:
            return {"entries": [], "period": None}

        period = periods.data[0]
        entries = (
            db.table("payroll_entries")
            .select("employee_id,basic_pay,sss_employee,sss_employer,philhealth_employee,philhealth_employer,pagibig_employee,pagibig_employer,withholding_tax")
            .eq("pay_period_id", period["id"])
            .in_("employee_id", str_ids)
            .execute()
        )
        if team_cache:
            emp_map = {e["id"]: e for e in team_cache["employees"]}
        else:
            emps = (
                db.table("employees")
                .select("id,first_name,last_name")
                .in_("id", str_ids)
                .execute()
            )
            emp_map = {e["id"]: e for e in (emps.data or [])}

        result = []
        for e in (entries.data or []):
            emp = emp_map.get(e["employee_id"], {})
            result.append({
                "name": f'{emp.get("first_name", "?")} {emp.get("last_name", "")}',
                "sss_ee": e.get("sss_employee", 0),
                "sss_er": e.get("sss_employer", 0),
                "ph_ee": e.get("philhealth_employee", 0),
                "ph_er": e.get("philhealth_employer", 0),
                "pi_ee": e.get("pagibig_employee", 0),
                "pi_er": e.get("pagibig_employer", 0),
                "tax": e.get("withholding_tax", 0),
            })
        result.sort(key=lambda x: x["name"])
        return {"entries": result, "period": period}
    except Exception:
        return {"entries": [], "period": None}


def _render_supervisor_sections(team_ids: list, pending_leave: int = 0, pending_ot: int = 0,
                                team_cache: dict | None = None,
                                latest_period: dict | None = None,
                                history: list | None = None,
                                cal_events: dict | None = None,
                                latest_entries: list | None = None,
                                name_map: dict | None = None):
    """Render the full ADP-style supervisor management tool below the bento grid.
    Design patterned after fromstitch/12_supervisor_dashboard.html (Tactile Sanctuary).
    """
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Shadow-soft card style (no 1px borders — Stitch rule) ──
    _SV_CARD = ("background:#ffffff;border-radius:16px;padding:20px;"
                "box-shadow:0 20px 40px rgba(45,51,53,0.06);")
    _SV_CARD_FLUSH = ("background:#ffffff;border-radius:16px;overflow:hidden;"
                      "box-shadow:0 20px 40px rgba(45,51,53,0.06);")

    # ── Tab bar (5 tabs — Dashboard first, then Stitch v2 layout) ──
    tabs = st.tabs([
        "📊 Dashboard",
        "🕐 Timekeeping",
        "📁 Team Records",
        "🏖 Benefits",
        "🔜 More",
    ])

    # ────────────────────────────────────────────────
    # TAB 0: Dashboard (bento: Your Team + Pending Approvals + Alerts + Row 2)
    # ────────────────────────────────────────────────
    with tabs[0]:
        _render_supervisor_row1(team_ids, pending_leave, pending_ot, team_cache=team_cache)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        _render_bento_row2(latest_period, history or [], cal_events or {},
                           latest_entries=latest_entries, name_map=name_map,
                           team_scope=True)

    # ────────────────────────────────────────────────
    # TAB 1: Timekeeping & DTR (Stitch pattern)
    # ────────────────────────────────────────────────
    with tabs[1]:
        col_dtr, col_ot = st.columns(2, gap="large")

        with col_dtr:
            # DTR Exceptions — shadow-soft cards with initials avatars
            st.markdown(
                '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;">'
                '  <div style="font-size:14px;font-weight:700;color:#191c1d;">DTR Exceptions</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            exceptions = _sv_load_dtr_exceptions(team_ids, team_cache=team_cache)
            if exceptions:
                for idx, exc in enumerate(exceptions):
                    initials = "".join(w[0] for w in exc["name"].split()[:2]).upper()
                    bg, fg = _SV_AVATAR_COLORS[idx % len(_SV_AVATAR_COLORS)]
                    issue_pills = " ".join(
                        f'<span style="background:{"#ffdad6" if "No" in i else ("#d8e2ff" if "NSD" in i else "#ebeef0")};'
                        f'color:{"#93000a" if "No" in i else ("#004494" if "NSD" in i else "#424753")};'
                        f'font-size:9px;font-weight:700;padding:3px 10px;border-radius:9999px;text-transform:uppercase;">{i}</span>'
                        for i in exc["issues"]
                    )
                    st.markdown(
                        f'<div style="{_SV_CARD}margin-bottom:8px;padding:16px 20px;">'
                        f'  <div style="display:flex;align-items:center;justify-content:space-between;">'
                        f'    <div style="display:flex;align-items:center;gap:14px;">'
                        f'      <div style="width:40px;height:40px;border-radius:50%;background:{bg};color:{fg};'
                        f'font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0">{initials}</div>'
                        f'      <div>'
                        f'        <div style="font-size:12px;font-weight:700;color:#191c1d">{exc["name"]}</div>'
                        f'        <div style="font-size:10px;color:#727784;margin-top:1px">{exc["date"]}</div>'
                        f'      </div>'
                        f'    </div>'
                        f'    <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;">{issue_pills}</div>'
                        f'  </div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    f'<div style="{_SV_CARD}text-align:center;padding:28px;">'
                    '  <div style="font-size:24px;margin-bottom:6px">✅</div>'
                    '  <div style="font-size:12px;font-weight:700;color:#005320">No DTR Exceptions</div>'
                    '  <div style="font-size:10px;color:#727784;margin-top:2px">All team members have complete logs</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

        with col_ot:
            # OT Authorization — amber-tinted featured card (Stitch pattern)
            ot_requests = _sv_load_ot_requests(team_ids, team_cache=team_cache)
            pending_ots = [r for r in ot_requests if r["status"] == "pending"]
            recent_ots = [r for r in ot_requests if r["status"] != "pending"][:6]

            st.markdown(
                f'<div style="background:rgba(251,188,5,0.08);border-radius:16px;padding:24px;position:relative;overflow:hidden;margin-bottom:16px;">'
                f'  <div style="position:absolute;right:16px;top:16px;opacity:0.15;font-size:3rem;">⏰</div>'
                f'  <div style="font-size:10px;font-weight:900;color:#000;text-transform:uppercase;letter-spacing:.1em;margin-bottom:14px;">OT Authorization</div>'
                f'  <div style="display:flex;align-items:center;gap:24px;">'
                f'    <div>'
                f'      <div style="font-size:2rem;font-weight:900;color:#000;line-height:1;">{len(pending_ots)}</div>'
                f'      <div style="font-size:10px;font-weight:700;color:rgba(0,0,0,.55);text-transform:uppercase;margin-top:2px;">Pending Review</div>'
                f'    </div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if pending_ots:
                for ot in pending_ots:
                    st.markdown(
                        f'<div style="{_SV_CARD}margin-bottom:8px;padding:14px 20px;">'
                        f'  <div style="display:flex;justify-content:space-between;align-items:center;">'
                        f'    <span style="font-size:12px;font-weight:700;color:#191c1d">{ot["name"]}</span>'
                        f'    <span style="font-size:11px;font-weight:800;color:#d97706">{ot.get("hours", 0):.1f}h</span>'
                        f'  </div>'
                        f'  <div style="font-size:10px;color:#727784;margin-top:3px">'
                        f'    {ot["ot_date"]} \u2022 {ot.get("start_time", "")[:5]}\u2013{ot.get("end_time", "")[:5]}'
                        f'  </div>'
                        f'  <div style="font-size:10px;color:#9ca3af;margin-top:2px;font-style:italic">{ot.get("reason", "")[:60]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Holiday Pay Validator — rate reference cards (Stitch pattern)
            st.markdown(
                '<div style="background:#f3f4f5;border-radius:16px;padding:20px;margin-top:16px;">'
                '  <div style="font-size:10px;font-weight:900;color:#191c1d;text-transform:uppercase;letter-spacing:.1em;margin-bottom:14px;">Holiday Pay Validator</div>'
                '  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">',
                unsafe_allow_html=True,
            )
            hol_workers = _sv_load_holiday_workers(team_ids, team_cache=team_cache)
            _hw_count_reg = sum(1 for h in hol_workers if "regular" in h.get("type", "").lower())
            _hw_count_sp = len(hol_workers) - _hw_count_reg
            st.markdown(
                f'    <div style="background:#fff;padding:14px;border-radius:12px;">'
                f'      <div style="font-size:10px;color:#727784;font-weight:700;text-transform:uppercase;">Regular Holiday</div>'
                f'      <div style="font-size:1.3rem;font-weight:800;color:#004494;margin-top:6px;">200%</div>'
                f'      <div style="font-size:9px;color:#9ca3af;margin-top:2px;">{_hw_count_reg} team member{"s" if _hw_count_reg != 1 else ""} worked</div>'
                f'    </div>'
                f'    <div style="background:#fff;padding:14px;border-radius:12px;">'
                f'      <div style="font-size:10px;color:#727784;font-weight:700;text-transform:uppercase;">Special Non-Working</div>'
                f'      <div style="font-size:1.3rem;font-weight:800;color:#d97706;margin-top:6px;">130%</div>'
                f'      <div style="font-size:9px;color:#9ca3af;margin-top:2px;">{_hw_count_sp} team member{"s" if _hw_count_sp != 1 else ""} worked</div>'
                f'    </div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ────────────────────────────────────────────────
    # TAB 3: Benefits (Leave & Benefits)
    # ────────────────────────────────────────────────
    with tabs[3]:
        leave_data = _sv_load_leave_overview(team_ids, team_cache=team_cache)
        balances = leave_data["balances"]
        emp_map = leave_data["emp_map"]
        pending_leaves = leave_data["pending"]
        special_leaves = leave_data["special"]

        col_bal, col_pending = st.columns([3, 2], gap="medium")

        with col_bal:
            st.markdown(
                '<div style="font-size:14px;font-weight:700;color:#191c1d;margin-bottom:12px;">'
                'Team Leave Balances</div>',
                unsafe_allow_html=True,
            )
            if balances:
                # Proper HTML table — Stitch pattern: divide-y, no borders, shadow-soft
                rows_html = ""
                for eid, types in balances.items():
                    emp = emp_map.get(eid, {})
                    name = f'{emp.get("first_name", "?")} {emp.get("last_name", "")}'
                    cells = ""
                    for lt in ["VL", "SL", "CL"]:
                        info = types.get(lt, {"opening": 0, "used": 0})
                        remaining = info["opening"] - info["used"]
                        color = "#059669" if remaining > 3 else ("#d97706" if remaining > 0 else "#dc2626")
                        cells += (
                            f'<td style="text-align:center;padding:10px 8px;">'
                            f'<span style="font-size:14px;font-weight:700;color:{color}">{remaining:.0f}</span>'
                            f'<span style="font-size:9px;color:#94a3b8;margin-left:2px">/{info["opening"]:.0f}</span>'
                            f'</td>'
                        )
                    idx = list(balances.keys()).index(eid)
                    av_bg, av_fg = _SV_AVATAR_COLORS[idx % len(_SV_AVATAR_COLORS)]
                    initials = (emp.get("first_name", "?")[0] + emp.get("last_name", " ")[0]).upper()
                    rows_html += (
                        f'<tr style="border-bottom:1px solid #f1f5f9;">'
                        f'<td style="padding:10px 8px;">'
                        f'<div style="display:flex;align-items:center;gap:8px;">'
                        f'<div style="width:28px;height:28px;border-radius:50%;background:{av_bg};color:{av_fg};'
                        f'display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;flex-shrink:0;">{initials}</div>'
                        f'<span style="font-size:12px;font-weight:600;color:#191c1d">{name}</span>'
                        f'</div></td>{cells}</tr>'
                    )
                st.markdown(
                    '<div style="background:#fff;border-radius:16px;box-shadow:0px 20px 40px rgba(45,51,53,0.06);overflow:hidden;">'
                    '<table style="width:100%;border-collapse:collapse;text-align:left;font-size:11px;">'
                    '<thead><tr style="border-bottom:1px solid #e2e8f0;">'
                    '<th style="padding:10px 8px;font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Employee</th>'
                    '<th style="padding:10px 8px;text-align:center;font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">VL</th>'
                    '<th style="padding:10px 8px;text-align:center;font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">SL</th>'
                    '<th style="padding:10px 8px;text-align:center;font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">CL</th>'
                    '</tr></thead>'
                    f'<tbody>{rows_html}</tbody></table></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="background:#fff;border-radius:16px;box-shadow:0px 20px 40px rgba(45,51,53,0.06);'
                    'padding:24px;text-align:center;">'
                    '<div style="font-size:20px;margin-bottom:4px">📋</div>'
                    '<div style="font-size:12px;font-weight:600;color:#64748b">No leave balances set up for this year.</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

            # Special leaves — shadow-soft card, no borders
            if special_leaves:
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                st.markdown(
                    '<div style="font-size:14px;font-weight:700;color:#191c1d;margin-bottom:8px;">'
                    'Special Leaves (Statutory)</div>',
                    unsafe_allow_html=True,
                )
                _SL_LABELS = {"ML": "Maternity (105d)", "PL": "Paternity (7d)", "SPL": "Solo Parent (7d)"}
                for sl in special_leaves:
                    emp = emp_map.get(sl["employee_id"], {})
                    name = f'{emp.get("first_name", "?")} {emp.get("last_name", "")}'
                    s = sl.get("status", "pending")
                    s_bg = {"approved": "#d1fae5", "rejected": "#fecaca"}.get(s, "#fef3c7")
                    s_fg = {"approved": "#065f46", "rejected": "#991b1b"}.get(s, "#92400e")
                    st.markdown(
                        f'<div style="background:#fff;border-radius:12px;box-shadow:0px 20px 40px rgba(45,51,53,0.06);'
                        f'padding:12px 14px;margin-bottom:6px;">'
                        f'  <div style="display:flex;justify-content:space-between;align-items:center;">'
                        f'    <div>'
                        f'      <span style="font-size:12px;font-weight:600;color:#191c1d">{name}</span>'
                        f'      <span style="font-size:10px;color:#64748b;margin-left:6px">'
                        f'{_SL_LABELS.get(sl["leave_type"], sl["leave_type"])}</span>'
                        f'    </div>'
                        f'    <span style="background:{s_bg};color:{s_fg};font-size:9px;font-weight:700;'
                        f'padding:3px 10px;border-radius:9999px;">{s.upper()}</span>'
                        f'  </div>'
                        f'  <div style="font-size:10px;color:#94a3b8;margin-top:3px">{sl.get("start_date", "")} → {sl.get("end_date", "")}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        with col_pending:
            st.markdown(
                '<div style="font-size:14px;font-weight:700;color:#191c1d;margin-bottom:12px;">'
                'Pending Leave Requests</div>',
                unsafe_allow_html=True,
            )
            if pending_leaves:
                for lv in pending_leaves:
                    emp = emp_map.get(lv["employee_id"], {})
                    name = f'{emp.get("first_name", "?")} {emp.get("last_name", "")}'
                    lt_colors = {"VL": ("#dbeafe", "#1d4ed8"), "SL": ("#fce7f3", "#be185d"), "CL": ("#e0e7ff", "#4338ca")}
                    bg, fg = lt_colors.get(lv["leave_type"], ("#f3f4f6", "#374151"))
                    st.markdown(
                        f'<div style="background:#fffbeb;border-radius:12px;box-shadow:0px 20px 40px rgba(45,51,53,0.06);'
                        f'padding:12px 14px;margin-bottom:8px;">'
                        f'  <div style="display:flex;justify-content:space-between;align-items:center;">'
                        f'    <span style="font-size:12px;font-weight:600;color:#191c1d">{name}</span>'
                        f'    <span style="background:{bg};color:{fg};font-size:9px;font-weight:700;'
                        f'padding:3px 10px;border-radius:9999px;">{lv["leave_type"]} · {lv.get("days", 0):.0f}d</span>'
                        f'  </div>'
                        f'  <div style="font-size:10px;color:#64748b;margin-top:3px">{lv.get("start_date", "")} → {lv.get("end_date", "")}</div>'
                        f'  <div style="font-size:10px;color:#94a3b8;margin-top:2px;font-style:italic">{lv.get("reason", "")[:80]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<div style="background:#f0fdf4;border-radius:12px;box-shadow:0px 20px 40px rgba(45,51,53,0.06);'
                    'padding:20px;text-align:center;">'
                    '  <div style="font-size:20px;margin-bottom:4px">✅</div>'
                    '  <div style="font-size:12px;font-weight:600;color:#166534">No Pending Leaves</div>'
                    '  <div style="font-size:10px;color:#94a3b8;margin-top:2px">All leave requests have been processed</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

    # ────────────────────────────────────────────────
    # TAB 2: Team Records (Stitch v2 — 2-column: Statutory + 201 Cards)
    # ────────────────────────────────────────────────
    with tabs[2]:
        col_stat, col_201 = st.columns(2, gap="large")

        # ── Left: Statutory Summary ──
        with col_stat:
            st.markdown(
                '<div style="font-size:12px;font-weight:700;color:#191c1d;text-transform:uppercase;'
                'letter-spacing:.05em;margin-bottom:12px;">Statutory Summary</div>',
                unsafe_allow_html=True,
            )
            stat_data = _sv_load_statutory_overview(team_ids, team_cache=team_cache)
            stat_entries = stat_data["entries"]
            stat_period = stat_data["period"]

            if stat_entries:
                _f = lambda c: f"\u20b1{c / 100:,.2f}" if c else "\u20b10.00"

                # Summary metric cards — 2-column grid (Stitch v2)
                tot_sss = sum(e["sss_ee"] + e["sss_er"] for e in stat_entries)
                tot_ph = sum(e["ph_ee"] + e["ph_er"] for e in stat_entries)

                st.markdown(
                    f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">'
                    f'  <div style="{_SV_CARD}background:#f8f9fa;">'
                    f'    <div style="font-size:8px;font-weight:900;color:#9ca3af;text-transform:uppercase;">SSS Contribution</div>'
                    f'    <div style="font-size:14px;font-weight:700;color:#191c1d;margin-top:6px">{_f(tot_sss)}</div>'
                    f'  </div>'
                    f'  <div style="{_SV_CARD}background:#f8f9fa;">'
                    f'    <div style="font-size:8px;font-weight:900;color:#9ca3af;text-transform:uppercase;">PhilHealth</div>'
                    f'    <div style="font-size:14px;font-weight:700;color:#191c1d;margin-top:6px">{_f(tot_ph)}</div>'
                    f'  </div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Detail table — EE/ER breakdown
                rows_html = ""
                for e in stat_entries:
                    rows_html += (
                        f'<tr style="border-top:1px solid #f1f5f9;">'
                        f'  <td style="padding:8px 16px;font-weight:700;font-size:10px;color:#191c1d;">{e["name"]}</td>'
                        f'  <td style="padding:8px 16px;font-size:10px;">{_f(e["sss_ee"])}</td>'
                        f'  <td style="padding:8px 16px;font-size:10px;color:#9ca3af;">{_f(e["sss_er"])}</td>'
                        f'</tr>'
                    )
                st.markdown(
                    f'<div style="{_SV_CARD_FLUSH}">'
                    f'<table style="width:100%;text-align:left;border-collapse:collapse;">'
                    f'  <thead><tr style="background:#f3f4f5;">'
                    f'    <th style="padding:8px 16px;font-size:8px;font-weight:900;color:#94a3b8;text-transform:uppercase;">Employee</th>'
                    f'    <th style="padding:8px 16px;font-size:8px;font-weight:900;color:#94a3b8;text-transform:uppercase;">EE Share</th>'
                    f'    <th style="padding:8px 16px;font-size:8px;font-weight:900;color:#94a3b8;text-transform:uppercase;">ER Share</th>'
                    f'  </tr></thead>'
                    f'  <tbody>{rows_html}</tbody>'
                    f'</table></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.info("No finalized payroll data available for your team yet.", icon="💰")

        # ── Right: Digital 201 Cards ──
        with col_201:
            st.markdown(
                '<div style="font-size:12px;font-weight:700;color:#191c1d;text-transform:uppercase;'
                'letter-spacing:.05em;margin-bottom:12px;">Digital 201 Cards</div>',
                unsafe_allow_html=True,
            )
            try:
                # Use cache for employees + profiles (no DB hit)
                if team_cache:
                    _tc_emps = team_cache["employees"]
                    dept_map = team_cache["dept_map"]
                    prof_map = team_cache["profiles"]
                    str_ids = team_cache["str_ids"]
                else:
                    db = get_db()
                    str_ids = [str(tid) for tid in team_ids]
                    _tc_resp = (
                        db.table("employees")
                        .select("id,first_name,last_name,employee_no,position,employment_type,date_hired,"
                                "email,sss_no,philhealth_no,pagibig_no,bir_tin,basic_salary,salary_type")
                        .in_("id", str_ids)
                        .eq("is_active", True)
                        .order("last_name")
                        .execute()
                    )
                    _tc_emps = _tc_resp.data or []
                    dept_map = {}
                    prof_map = {}
                    prof_result = (
                        db.table("employee_profiles")
                        .select("employee_id,department,mobile_no,emergency_name,emergency_relationship,"
                                "emergency_phone,date_of_birth,sex,civil_status,present_address_city,"
                                "present_address_province,education_degree,education_school")
                        .in_("employee_id", str_ids)
                        .execute()
                    )
                    for p in (prof_result.data or []):
                        dept_map[p["employee_id"]] = p.get("department") or ""
                        prof_map[p["employee_id"]] = p

                # Load photo URLs
                _photo_urls_201 = {}
                cid = get_company_id()
                if str_ids and cid:
                    for _eid in str_ids:
                        _photo_urls_201[_eid] = (
                            f"https://dduxctbrjggqkqdlhwpz.supabase.co/storage/v1/object/public/"
                            f"employee-photos/{cid}/{_eid}.jpg"
                        )

                for idx, emp in enumerate(_tc_emps):
                    initials = (emp.get("first_name", "?")[0] + emp.get("last_name", "?")[0]).upper()
                    name = f'{emp.get("first_name", "")} {emp.get("last_name", "")}'
                    bg, fg = _SV_AVATAR_COLORS[idx % len(_SV_AVATAR_COLORS)]
                    emp_no = emp.get("employee_no", "")
                    dept = dept_map.get(emp.get("id", ""), "")
                    pos = emp.get("position", "")
                    eid = emp.get("id", "")
                    prof = prof_map.get(eid, {})

                    # Gov ID dots
                    gov_dots = ""
                    for gid, label in [
                        ("sss_no", "SSS"), ("philhealth_no", "PH"),
                        ("pagibig_no", "PI"), ("bir_tin", "TIN"),
                    ]:
                        dot_color = "#059669" if emp.get(gid) else "#d97706"
                        gov_dots += (
                            f'<div style="display:inline-flex;align-items:center;gap:3px;margin-right:8px;">'
                            f'<div style="width:4px;height:4px;border-radius:50%;background:{dot_color};"></div>'
                            f'<span style="font-size:8px;font-weight:700;color:#9ca3af;">{label}</span>'
                            f'</div>'
                        )

                    # Employment type badge
                    emp_type = emp.get("employment_type", "")
                    et_bg = {"regular": "#d4edda", "probationary": "#fef3c7", "contractual": "#dbeafe"}.get(
                        (emp_type or "").lower(), "#f1f5f9")
                    et_fg = {"regular": "#155724", "probationary": "#92400e", "contractual": "#1e40af"}.get(
                        (emp_type or "").lower(), "#475569")
                    et_label = (emp_type or "").upper()

                    # Avatar — CSS background-image for photo, initials always visible as fallback
                    _photo_url = _photo_urls_201.get(eid, "")
                    _bg_img = f"background-image:url({_photo_url});background-size:cover;background-position:center;" if _photo_url else ""
                    _avatar_inner = (
                        f'<span style="color:{fg};font-weight:700;font-size:14px;">{initials}</span>'
                    )

                    # Swipe card (same pattern as payroll run)
                    _action_tray = (
                        f'<div class="ps-swipe-act" '
                        f'data-ps-action="view201_{eid}" '
                        f'style="background:#2563eb;color:#fff;font-size:20px;">'
                        f'&#128065;<br><span style="font-size:9px;font-weight:700;">View</span></div>'
                    )

                    st.markdown(
                        f'<div class="ps-swipe-wrap">'
                        f'<div class="ps-swipe-actions">{_action_tray}</div>'
                        f'<div class="ps-swipe-card" style="'
                        f'display:flex;align-items:center;gap:12px;padding:10px 14px;'
                        f'background:var(--gxp-surface);border-radius:12px;'
                        f'border:1px solid var(--gxp-border);">'
                        # Avatar — bg-image for photo, initials show if no photo
                        f'<div style="width:40px;height:40px;border-radius:50%;background:{bg};{_bg_img}'
                        f'display:flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden;">'
                        f'{_avatar_inner}</div>'
                        # Name + details
                        f'<div style="flex:1;min-width:0;">'
                        f'<div style="display:flex;align-items:center;gap:8px;">'
                        f'<span style="font-size:13px;font-weight:700;color:var(--gxp-text);">{name}</span>'
                        f'<span style="background:{et_bg};color:{et_fg};padding:2px 8px;border-radius:9999px;'
                        f'font-size:10px;font-weight:700;">{et_label}</span></div>'
                        f'<div style="font-size:11px;color:var(--gxp-text3);">{emp_no}</div>'
                        f'<div style="font-size:11px;color:var(--gxp-text3);">{dept} · {pos}</div>'
                        f'</div>'
                        # Gov ID dots (right side)
                        f'<div style="display:flex;flex-wrap:wrap;gap:2px;">{gov_dots}</div>'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            except Exception:
                st.error("Could not load team records.")

    # ────────────────────────────────────────────────
    # TAB 4: More (Platform Roadmap — Stitch v2 minimal)
    # ────────────────────────────────────────────────
    with tabs[4]:
        st.markdown(
            '<div style="font-size:12px;font-weight:700;color:#191c1d;display:flex;align-items:center;gap:8px;margin-bottom:16px;">'
            '  <span class="material-symbols-outlined" style="font-size:16px;color:#d97706;">auto_awesome</span>'
            '  Platform Roadmap'
            '</div>',
            unsafe_allow_html=True,
        )
        _coming = [
            ("gavel", "Disciplinary Hub"),
            ("payments", "Loan Portal"),
            ("draw", "Digital Sign-off"),
            ("analytics", "AI Analytics"),
        ]
        cols = st.columns(4, gap="medium")
        for i, col in enumerate(cols):
            ms_icon, title = _coming[i]
            with col:
                st.markdown(
                    f'<div style="background:#f3f4f5;border-radius:16px;padding:20px;'
                    f'opacity:0.6;cursor:not-allowed;">'
                    f'  <div style="color:#9ca3af;margin-bottom:8px;">'
                    f'    <span class="material-symbols-outlined" style="font-size:18px;">{ms_icon}</span>'
                    f'  </div>'
                    f'  <div style="font-size:10px;font-weight:700;color:#191c1d;">{title}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ────────────────────────────────────────────────
    # 201 Modal (pure HTML/JS — instant, no Streamlit rerun)
    # ────────────────────────────────────────────────
    if team_cache:
        cid = get_company_id()
        _modal_html = _build_201_modals_html(team_cache, cid or "")
        st.markdown(_modal_html, unsafe_allow_html=True)
        import streamlit.components.v1 as _modal_stc
        _modal_stc.html(_build_201_modal_js(), height=0)


# ============================================================
# Main Page Render
# ============================================================

def render():
    # If editing_id was set inside the Employees dialog, redirect immediately
    # to the Employees page where the edit dialog can open properly (no nesting).
    if st.session_state.get("editing_id"):
        st.session_state["_nav_redirect"] = "Employees"
        st.rerun()

    inject_css()

    # ── Role-based scoping (must be before title/greeting) ──
    _is_supervisor = is_supervisor()
    _team_ids = get_supervisor_employee_ids() if _is_supervisor else []

    # ── Show greeting immediately (before data loads) ──
    import datetime as _dt
    _hour = _dt.datetime.now().hour
    _greeting = "Good morning" if _hour < 12 else ("Good afternoon" if _hour < 18 else "Good evening")
    _display_name = st.session_state.get("display_name") or ""
    if not _display_name:
        # Fallback: derive from email
        _email = st.session_state.get("user_email", "")
        _display_name = _email.split("@")[0].replace(".", " ").title() if _email else "there"
    _first_name = _display_name.split()[0] if _display_name else "there"
    _now = _dt.datetime.now()
    _date_str = _now.strftime("%B %d, %Y")
    _time_str = _now.strftime("%I:%M %p").lstrip("0")

    st.title("Supervisor Portal" if _is_supervisor else "Dashboard")

    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        _sub_msg = (
            f"You have <strong>{len(_team_ids)} team member(s)</strong> reporting to you."
            if _is_supervisor and _team_ids
            else "Everything is ready for your next pay cycle."
        )
        st.markdown(
            f'<p style="font-size:16px;font-weight:600;color:#191c1d;margin:0;">{_greeting}, {_first_name}.</p>'
            f'<p style="font-size:13px;color:#727784;margin:4px 0 0;">{_sub_msg}</p>',
            unsafe_allow_html=True,
        )
    with hdr_r:
        st.markdown(
            f'<div style="text-align:right;padding-top:8px">'
            f'  <div style="font-size:14px;font-weight:700;color:var(--gxp-text)">{_date_str}</div>'
            f'  <div style="font-size:12px;color:var(--gxp-text2);margin-top:2px">{_time_str}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # (Skeleton placeholders removed — Streamlit's native stale/fade state
    #  provides sufficient loading feedback.)

    # ── Load all data ─────────────────────────────────
    company             = _load_company()
    if _is_supervisor and _team_ids:
        # Supervisor sees only their team
        active_count = sum(1 for _ in _team_ids)  # approximate — all team members
        total_count = len(_team_ids)
    else:
        active_count, total_count = _load_employee_counts()
    pending_leave, pending_ot = _count_pending_requests(_team_ids if _is_supervisor else None)

    # ── Build team cache for supervisors (single bulk load, cached 2 min) ──
    _team_cache = None
    if _is_supervisor and _team_ids:
        _cid = get_company_id()
        _team_cache = _load_team_cache(tuple(_team_ids), _cid)

    # ── Load payroll & calendar data (shared by admin + supervisor) ──
    periods             = _load_pay_periods()
    history             = _load_payroll_history(cid=get_company_id())
    remittance_status   = _load_current_remittance_status()
    deadlines           = _get_deadlines(remittance_status)

    next_period    = _find_next_period(periods)
    latest_period  = _find_latest_finalized(periods)
    latest_entries = _load_payroll_entries(latest_period["id"]) if latest_period else []

    _cal_events = _build_calendar_events(periods, deadlines)

    if not _is_supervisor:
        total_gross = sum(e["gross_pay"] for e in latest_entries) if latest_entries else 0
        total_net   = sum(e["net_pay"]   for e in latest_entries) if latest_entries else 0
        total_er    = sum(
            e["sss_employer"] + e["philhealth_employer"] + e["pagibig_employer"]
            for e in latest_entries
        ) if latest_entries else 0
        total_cost  = total_gross + total_er
        headcount = len(latest_entries)

    # ── Bento grid ─────────────────────────────────────────────
    if _is_supervisor:
        # Supervisor: bento grid is inside the tabbed sections (Dashboard tab)
        col_main = None  # skip side column
        col_side = None
    else:
        # ── NEW 6-panel dashboard layout ──
        _admin_name_map = _load_employee_names(
            [e["employee_id"] for e in latest_entries if e.get("employee_id")]
        ) if latest_entries else {}

        # Load additional data for new panels
        _cid = get_company_id()
        _dept_data = _load_department_breakdown(_cid)
        _emp_dept_map = _load_employee_dept_map(_cid)
        _today_logs = _load_today_attendance(_cid)
        _monthly_att = _load_attendance_monthly(_cid)
        _pending_details = _load_pending_request_details(_cid)

        # Name map for all employees (for attendance + pending panels)
        _all_emp_ids = list(set(
            [log.get("employee_id", "") for log in _today_logs] +
            [req.get("employee_id", "") for req in _pending_details]
        ))
        _all_name_map = {**_admin_name_map}
        if _all_emp_ids:
            _extra_names = _load_employee_names([eid for eid in _all_emp_ids if eid and eid not in _all_name_map])
            _all_name_map.update(_extra_names)

        # Outer layout: main content (3/4) + sidebar (1/4)
        col_main, col_side = st.columns([3, 1], gap="medium")

        with col_main:
            # Row 1: Payroll Overview | Recent Payroll | Attendance Rate
            r1c1, r1c2, r1c3 = st.columns(3, gap="medium")
            with r1c1:
                _render_panel_payroll_overview(
                    latest_period, history, latest_entries,
                    total_gross, total_net, total_cost, headcount,
                    dept_map=_emp_dept_map,
                )
            with r1c2:
                _render_panel_recent_payroll(latest_entries, _admin_name_map, latest_period)
            with r1c3:
                _render_panel_mini_calendar(_cal_events or {})

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            # Row 2: Workforce Breakdown | Attendance Detail (wider)
            r2c1, r2c2 = st.columns([1, 2], gap="medium")
            with r2c1:
                _render_panel_workforce(_dept_data, active_count)
            with r2c2:
                _render_panel_attendance_detail(_today_logs, _all_name_map)

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            # Row 3: Pending Requests
            _render_panel_pending_requests(_pending_details, _all_name_map, pending_leave, pending_ot)

        with col_side:
            _render_reminders(pending_leave, pending_ot)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            _render_alerts(deadlines, periods)

    # Wire bento card clicks + ripple + equal-height cards (pure JS)
    _stc.html("""<script>
    (function(){
      var pd=window.parent.document;

      // ── Equal-height cards per row (not across outer columns) ──
      function equalizeBento(){
        // Find inner stHorizontalBlock rows that contain bento cards
        pd.querySelectorAll('[data-testid="stHorizontalBlock"]').forEach(function(row){
          var cards=row.querySelectorAll(':scope > [data-testid="stColumn"] .gxp-bento-hero-card');
          if(cards.length<2) return;
          // Skip the outer [3,1] split (it has col_side with reminders, no bento card directly)
          // Only equalize rows where ALL columns have a bento card
          var cols=row.querySelectorAll(':scope > [data-testid="stColumn"]');
          var bentoColCount=0;
          cols.forEach(function(c){if(c.querySelector('.gxp-bento-hero-card'))bentoColCount++;});
          if(bentoColCount<cols.length) return;
          // Reset then measure
          cards.forEach(function(c){c.style.minHeight='';});
          var maxH=0;
          cards.forEach(function(c){var h=c.getBoundingClientRect().height;if(h>maxH)maxH=h;});
          if(maxH>40) cards.forEach(function(c){c.style.minHeight=maxH+'px';});
        });
      }
      setTimeout(equalizeBento,400);
      setTimeout(equalizeBento,900);
      setTimeout(equalizeBento,1800);

      // ── Ripple effect helper ──
      function addRipple(el,e){
        var rect=el.getBoundingClientRect();
        var size=Math.max(rect.width,rect.height);
        var x=(e.clientX||rect.left+rect.width/2)-rect.left-size/2;
        var y=(e.clientY||rect.top+rect.height/2)-rect.top-size/2;
        var isDark=el.style.background&&el.style.background.indexOf('#febf0d')!==-1;
        var span=pd.createElement('span');
        span.className='gxp-ripple'+(isDark?' gxp-ripple-dark':'');
        span.style.cssText='width:'+size+'px;height:'+size+'px;left:'+x+'px;top:'+y+'px;';
        el.appendChild(span);
        setTimeout(function(){span.remove();},600);
      }

      // ── Bento clickable cards → hidden Streamlit buttons + ripple ──
      function wireBento(){
        var cards=pd.querySelectorAll('.gxp-bento-clickable');
        if(!cards.length){setTimeout(wireBento,80);return;}
        cards.forEach(function(card){
          if(card.dataset.gxpWired) return;
          card.dataset.gxpWired='1';
          card.addEventListener('click',function(e){
            addRipple(card,e);
            var col=card.closest('[data-testid="stColumn"]');
            if(!col) return;
            var btn=col.querySelector('[data-testid="stButton"] button');
            if(btn) setTimeout(function(){btn.click();},150);
          });
        });
      }
      wireBento();

      // ── Reminder swipe action buttons ──
      function wireRemind(){
        var approves=pd.querySelectorAll('.gxp-remind-approve');
        var dismisses=pd.querySelectorAll('.gxp-remind-dismiss');
        if(!approves.length && !dismisses.length){setTimeout(wireRemind,80);return;}
        approves.forEach(function(btn){
          if(btn.dataset.gxpWired) return;
          btn.dataset.gxpWired='1';
          btn.addEventListener('click',function(e){
            e.stopPropagation();
            addRipple(btn,e);
            // Find the hidden Approvals button by its key and click it
            var allBtns=pd.querySelectorAll('[data-testid="stBaseButton-secondary"]');
            for(var i=0;i<allBtns.length;i++){
              if(allBtns[i].textContent.trim()==='\u200b' || allBtns[i].textContent.trim()===''){
                allBtns[i].click();
                break;
              }
            }
          });
        });
        dismisses.forEach(function(btn){
          if(btn.dataset.gxpWired) return;
          btn.dataset.gxpWired='1';
          btn.addEventListener('click',function(e){
            e.stopPropagation();
            addRipple(btn,e);
            var swipe=btn.closest('.gxp-remind-swipe');
            if(swipe){
              // Replace card with a dismissed message
              swipe.style.overflow='hidden';
              swipe.innerHTML=
                '<div style="background:var(--gxp-surface);border:1px solid var(--gxp-border);'+
                'border-radius:10px;padding:10px 12px;opacity:.6;'+
                'display:flex;align-items:center;gap:8px;">'+
                '<span class="mdi mdi-check" style="font-size:16px;color:#9ca3af;"></span>'+
                '<span style="font-size:11px;color:#9ca3af;">'+
                'Dismissed \u2014 go to Approvals to review</span></div>';
            }
          });
        });
      }
      wireRemind();

      // ── Alert swipe action buttons ──
      function wireAlerts(){
        var navBtns=pd.querySelectorAll('.gxp-alert-nav-btn');
        var dismisses2=pd.querySelectorAll('.gxp-alert-dismiss');
        if(!navBtns.length && !dismisses2.length){setTimeout(wireAlerts,80);return;}
        navBtns.forEach(function(btn){
          if(btn.dataset.gxpWired) return;
          btn.dataset.gxpWired='1';
          btn.addEventListener('click',function(e){
            e.stopPropagation();
            addRipple(btn,e);
            var nav=btn.getAttribute('data-nav')||'';
            // Use same approach as main.py clickNav() — find sidebar buttons by text
            var sb=pd.querySelector('[data-testid="stSidebar"]');
            if(!sb) return;
            var sBtns=sb.querySelectorAll('[data-testid="stButton"] button');
            for(var i=0;i<sBtns.length;i++){
              if(sBtns[i].textContent.indexOf(nav)!==-1){
                sBtns[i].click();
                return;
              }
            }
          });
        });
        dismisses2.forEach(function(btn){
          if(btn.dataset.gxpWired) return;
          btn.dataset.gxpWired='1';
          btn.addEventListener('click',function(e){
            e.stopPropagation();
            addRipple(btn,e);
            var swipe=btn.closest('.gxp-remind-swipe');
            if(swipe){
              swipe.innerHTML=
                '<div style="background:var(--gxp-surface);border:1px solid var(--gxp-border);'+
                'border-radius:10px;padding:10px 12px;opacity:.6;'+
                'display:flex;align-items:center;gap:8px;">'+
                '<span class="mdi mdi-check" style="font-size:16px;color:#9ca3af;"></span>'+
                '<span style="font-size:11px;color:#9ca3af;">'+
                'Dismissed</span></div>';
            }
          });
        });
      }
      wireAlerts();

      // ── Stat card swipe-up action buttons ──
      function wireStatActions(){
        pd.querySelectorAll('.gxp-stat-action-btn[data-stat-action]').forEach(function(el){
          if(el.dataset.gxpWired) return;
          el.dataset.gxpWired='1';
          el.addEventListener('click',function(e){
            e.stopPropagation();
            var key=el.getAttribute('data-stat-action');
            if(!key) return;
            var btn=pd.querySelector('div[class*="st-key-'+key+'"] button');
            if(btn) btn.click();
          });
        });
      }
      wireStatActions();
      setTimeout(wireStatActions,500);
      setTimeout(wireStatActions,1500);

      /* ── Counting number animation ─────────────────────────── */
      function animateCounts(){
        /* Integer counts */
        pd.querySelectorAll('.gxp-count[data-to]').forEach(function(el){
          var target = parseInt(el.getAttribute('data-to')) || 0;
          var current = parseInt(el.textContent.replace(/,/g,'')) || 0;
          /* Skip if already correct, or animate from 0 on first load */
          if(current === target) return;
          if(target === 0){ el.textContent = '0'; return; }
          var dur = 800, start = performance.now();
          (function step(now){
            var t = Math.min((now - start) / dur, 1);
            var ease = 1 - Math.pow(1 - t, 3);
            el.textContent = Math.round(ease * target).toLocaleString();
            if(t < 1) requestAnimationFrame(step);
          })(performance.now());
        });
        /* Money counts (centavos → formatted peso) */
        pd.querySelectorAll('.gxp-count-money[data-to]').forEach(function(el){
          var target = parseInt(el.getAttribute('data-to')) || 0;
          var curText = el.textContent.replace(/[^\d]/g,'') || '0';
          var current = parseInt(curText) || 0;
          if(current === target) return;
          if(target === 0){ el.innerHTML = '&#8369;0.00'; return; }
          var dur = 1000, start = performance.now();
          (function step(now){
            var t = Math.min((now - start) / dur, 1);
            var ease = 1 - Math.pow(1 - t, 3);
            var val = Math.round(ease * target);
            var pesos = (val / 100).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
            el.innerHTML = '&#8369;' + pesos;
            if(t < 1) requestAnimationFrame(step);
          })(performance.now());
        });
      }
      animateCounts();
      setTimeout(animateCounts, 300);
      setTimeout(animateCounts, 800);
    })();
    </script>""", height=0)

    # ── 3. KPI Stat Cards — now embedded in Payroll Overview panel ──
    # (Kept for supervisor portal; hidden for admin since v2 panels cover this)
    # if not _is_supervisor:
    #     _render_stat_cards(active_count, total_count, total_gross, total_net, total_cost,
    #                        latest_period, history,
    #                        latest_entries=latest_entries, headcount=headcount)

    # ── 4. Supervisor Management Sections ──────────
    if _is_supervisor and _team_ids:
        # Filter payroll entries to subordinates only
        _team_id_set = set(str(tid) for tid in _team_ids)
        _sv_entries = [
            e for e in (latest_entries or [])
            if str(e.get("employee_id", "")) in _team_id_set
        ]

        # Build name map for payroll breakdown (use cache if available, else load)
        _exp_name_map = {}
        if _team_cache:
            _exp_name_map = _team_cache.get("name_map", {})
        if _sv_entries and not _exp_name_map:
            _entry_ids = [e["employee_id"] for e in _sv_entries if e.get("employee_id")]
            _exp_name_map = _load_employee_names(_entry_ids)

        _render_supervisor_sections(
            _team_ids, pending_leave, pending_ot, team_cache=_team_cache,
            latest_period=latest_period, history=history, cal_events=_cal_events,
            latest_entries=_sv_entries, name_map=_exp_name_map,
        )
