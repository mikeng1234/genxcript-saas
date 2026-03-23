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
def _load_payroll_history(_cid: str = "") -> list[dict]:
    """Load all finalized/paid periods with aggregate totals for charts.

    Uses a single batch query to avoid N+1 round-trips.
    Cached for 2 minutes to avoid repeated heavy queries.
    """
    db  = get_db()
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


def _count_pending_requests() -> tuple[int, int]:
    """Return (pending_leave_count, pending_ot_count) for this company."""
    try:
        db  = get_db()
        cid = get_company_id()
        lr  = db.table("leave_requests").select("id", count="exact").eq("company_id", cid).eq("status", "pending").execute()
        otr = db.table("overtime_requests").select("id", count="exact").eq("company_id", cid).eq("status", "pending").execute()
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
# Phase D: Bento Grid Hero
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
_CARD  = "background:#ffffff;border-radius:16px;padding:28px;box-shadow:0 20px 40px rgba(45,51,53,0.06);"
_LABEL = "font-size:10px;font-weight:700;color:#004494;text-transform:uppercase;letter-spacing:.2em;margin-bottom:14px;font-family:'Plus Jakarta Sans',system-ui,sans-serif;"
_MLBL  = "font-size:10px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:.2em;margin-bottom:14px;font-family:'Plus Jakarta Sans',system-ui,sans-serif;"
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
            f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="{_CARD}min-height:150px;">'
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
        card_html = (
            f'<div class="gxp-bento-hero-card gxp-bento-clickable" style="background:#febf0d;border-radius:16px;padding:24px;min-height:150px;display:flex;flex-direction:column;justify-content:space-between;">'
            f'  <div class="gxp-count" data-to="{active_count}" style="font-size:36px;font-weight:900;color:#000;line-height:1;font-family:\'Plus Jakarta Sans\',system-ui,sans-serif;">0</div>'
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


def _render_bento_row2(latest_period, history, cal_events):
    """Row 2: Calendar | Payroll Expenditure."""
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
        if latest_period and bar_vals:
            latest_gross = bar_vals[-1]
            prev_gross   = bar_vals[-2] if len(bar_vals) >= 2 else 0
            gross_fmt    = _fmt(latest_gross)
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

            period_lbl = f"{latest_period['period_start']} \u2192 {latest_period['period_end']}"
            st.markdown(
                f'<div class="gxp-bento-hero-card" style="{_CARD}">'
                f'  <div style="{_MLBL}">Payroll Expenditure</div>'
                f'  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
                f'    <span class="gxp-count-money" data-to="{latest_gross}" style="font-size:1.6rem;font-weight:800;color:#191c1d;letter-spacing:-1px">&#8369;0</span>'
                f'    {trend_s}'
                f'  </div>'
                f'  <div style="font-size:10px;color:#9ca3af;margin-top:4px">{period_lbl}</div>'
                f'  <div style="display:flex;align-items:flex-end;gap:5px;height:60px;margin-top:14px">{bars_html}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="gxp-bento-hero-card" style="{_CARD}">'
                f'  <div style="{_MLBL}">Payroll Expenditure</div>'
                f'  <div style="color:#9ca3af;font-size:12px;margin-top:8px">No finalized pay periods yet.<br>Run your first payroll to see trends.</div>'
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
            html = (
                f'<div class="gxp-stat-card">'
                f'<div class="gxp-stat-icon" style="background:{card["icon_bg"]};color:{card["icon_color"]}">'
                f'{card["svg"]}</div>'
                f'<div class="gxp-stat-label">{card["label"]}</div>'
                f'<div class="gxp-stat-value">{card["value"]}</div>'
                f'<div class="gxp-stat-trend-row">{trend_content}</div>'
                f'<div class="gxp-stat-sub">{card["sub"]}</div>'
                f'</div>'
            )
            st.markdown(html, unsafe_allow_html=True)
            # Pill button — label fades in on hover, glows with card accent color
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
                color = "#e53935" if "regular" in htype.lower() else "#ff9800"
                events[d.isoformat()].append({"label": h["name"], "color": color})
    except Exception:
        pass

    # 2. Pay period key dates (start, end, payment_date)
    for p in (periods or []):
        for field, label, color in [
            ("start_date", "Pay period start", "#2196f3"),
            ("end_date",   "Pay period end",   "#2196f3"),
            ("payment_date", f"Pay day ({p.get('status','')})", "#4caf50"),
        ]:
            val = p.get(field)
            if val:
                d = date.fromisoformat(val) if isinstance(val, str) else val
                if d.month == month and d.year == year:
                    events[d.isoformat()].append({"label": label, "color": color})

    # 3. Government deadlines
    for dl in (deadlines or []):
        d = dl.get("date") or dl.get("deadline")
        if d:
            d = date.fromisoformat(d) if isinstance(d, str) else d
            if d.month == month and d.year == year:
                events[d.isoformat()].append({
                    "label": dl.get("label", dl.get("agency", "Deadline")),
                    "color": "#ff6f00",
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
    cal_sun = _cal.Calendar(firstweekday=6)  # Sunday first
    weeks = cal_sun.monthdayscalendar(year, month)

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
        <span>Su</span><span>Mo</span><span>Tu</span><span>We</span>
        <span>Th</span><span>Fr</span><span>Sa</span>
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
            var dots = document.createElement('div');
            dots.className = 'cal-dots';
            // Show max 3 dots
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
    _stc.html(html, height=240, scrolling=False)


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

    # ── Show greeting immediately (before data loads) ──
    import datetime as _dt
    _hour = _dt.datetime.now().hour
    _greeting = "Good morning" if _hour < 12 else ("Good afternoon" if _hour < 18 else "Good evening")
    _display_name = st.session_state.get("display_name", "Admin")
    _first_name = _display_name.split()[0] if _display_name else "Admin"
    _now = _dt.datetime.now()
    _date_str = _now.strftime("%B %d, %Y")
    _time_str = _now.strftime("%I:%M %p").lstrip("0")

    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        st.markdown(
            f'<h2 class="gxp-editorial-heading" style="margin-top:0">{_greeting}, {_first_name}.</h2>'
            f'<p class="gxp-editorial-sub">Everything is ready for your next pay cycle.</p>',
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

    # ── Skeleton placeholders (show instantly while data loads) ──
    _skel_placeholder = st.empty()
    _SKEL_CARD = (
        '<div class="gxp-skeleton" style="min-height:150px;margin-bottom:8px;"></div>'
    )
    _SKEL_SMALL = (
        '<div class="gxp-skeleton" style="height:60px;margin-bottom:6px;"></div>'
    )
    with _skel_placeholder.container():
        sk_main, sk_side = st.columns([3, 1], gap="medium")
        with sk_main:
            sk1, sk2, sk3 = st.columns(3, gap="medium")
            sk1.markdown(_SKEL_CARD, unsafe_allow_html=True)
            sk2.markdown(_SKEL_CARD, unsafe_allow_html=True)
            sk3.markdown(_SKEL_CARD, unsafe_allow_html=True)
            sk4, sk5 = st.columns(2, gap="medium")
            sk4.markdown(_SKEL_CARD, unsafe_allow_html=True)
            sk5.markdown(_SKEL_CARD, unsafe_allow_html=True)
        with sk_side:
            st.markdown(_SKEL_SMALL, unsafe_allow_html=True)
            st.markdown(_SKEL_SMALL, unsafe_allow_html=True)
            st.markdown(_SKEL_SMALL, unsafe_allow_html=True)

    # ── Load all data ─────────────────────────────────
    company             = _load_company()
    active_count, total_count = _load_employee_counts()
    periods             = _load_pay_periods()
    history             = _load_payroll_history(_cid=get_company_id())
    remittance_status   = _load_current_remittance_status()
    deadlines           = _get_deadlines(remittance_status)
    pending_leave, pending_ot = _count_pending_requests()

    next_period    = _find_next_period(periods)
    latest_period  = _find_latest_finalized(periods)
    latest_entries = _load_payroll_entries(latest_period["id"]) if latest_period else []

    total_gross = sum(e["gross_pay"] for e in latest_entries) if latest_entries else 0
    total_net   = sum(e["net_pay"]   for e in latest_entries) if latest_entries else 0
    total_er    = sum(
        e["sss_employer"] + e["philhealth_employer"] + e["pagibig_employer"]
        for e in latest_entries
    ) if latest_entries else 0
    total_cost  = total_gross + total_er

    headcount = len(latest_entries)

    # Build calendar events from loaded data
    _cal_events = _build_calendar_events(periods, deadlines)

    # ── Clear skeletons, render real content ───────────
    _skel_placeholder.empty()

    # ── Bento grid ─────────────────────────────────────────────
    # Outer 2-column: left (3/4) for content rows, right (1/4) for Reminders + Alerts
    col_main, col_side = st.columns([3, 1], gap="medium")

    with col_main:
        # Row 1: Upcoming Milestone | Active Employees | Recent Activity
        _render_bento_row1(next_period, active_count, total_count)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        # Row 2: Calendar | Payroll Expenditure
        _render_bento_row2(latest_period, history, _cal_events)

    with col_side:
        st.markdown('<span class="gxp-bento-hero-card" style="display:none"></span>', unsafe_allow_html=True)
        _render_reminders(pending_leave, pending_ot)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        _render_alerts(deadlines, periods)

    # Wire bento card clicks + ripple + reminder swipe action buttons (pure JS)
    _stc.html("""<script>
    (function(){
      var pd=window.parent.document;

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

      /* ── Counting number animation ─────────────────────────── */
      function animateCounts(){
        /* Integer counts */
        pd.querySelectorAll('.gxp-count[data-to]').forEach(function(el){
          if(el._counted) return;
          el._counted = true;
          var target = parseInt(el.getAttribute('data-to')) || 0;
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
          if(el._counted) return;
          el._counted = true;
          var target = parseInt(el.getAttribute('data-to')) || 0;
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

    # ── 3. KPI Stat Cards ────────────────────────────
    _render_stat_cards(active_count, total_count, total_gross, total_net, total_cost,
                       latest_period, history,
                       latest_entries=latest_entries, headcount=headcount)
