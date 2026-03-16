"""
Dashboard — ADP-inspired Streamlit page.

Action-oriented layout: what needs attention NOW at the top,
analytics and history below. Designed after ADP's payroll dashboard
pattern: CTA → Alerts → Stats → Summary → Trends.
"""

import streamlit as st
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


def _load_active_employee_count() -> int:
    db = get_db()
    result = (
        db.table("employees")
        .select("id", count="exact")
        .eq("company_id", get_company_id())
        .eq("is_active", True)
        .execute()
    )
    return result.count or 0


def _load_all_employee_count() -> int:
    db = get_db()
    result = (
        db.table("employees")
        .select("id", count="exact")
        .eq("company_id", get_company_id())
        .execute()
    )
    return result.count or 0


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


def _load_payroll_history() -> list[dict]:
    """Load all finalized/paid periods with aggregate totals for charts."""
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
        entries = _load_payroll_entries(p["id"])
        if not entries:
            continue
        rows.append({
            "period":     p["period_start"],
            "gross_pay":  sum(e["gross_pay"] for e in entries) / 100,
            "net_pay":    sum(e["net_pay"]   for e in entries) / 100,
            "headcount":  len(entries),
            "sss":        sum(e["sss_employee"]       + e["sss_employer"]       for e in entries) / 100,
            "philhealth": sum(e["philhealth_employee"] + e["philhealth_employer"] for e in entries) / 100,
            "pagibig":    sum(e["pagibig_employee"]   + e["pagibig_employer"]   for e in entries) / 100,
            "bir":        sum(e["withholding_tax"]    for e in entries) / 100,
        })
    return rows


def _get_deadlines() -> list[dict]:
    db = get_db()
    today = date.today()
    holidays = load_holiday_set(db, year=today.year)
    return get_remittance_deadlines(today, holidays)


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
# Section 1: Action Bar (ADP Hero)
# ============================================================

def _render_action_bar(company: dict, next_period: dict | None):
    company_name = company.get("name", "Your Company")
    today = date.today()
    today_str = today.strftime("%A, %B %d, %Y")

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
        f'<div class="gxp-action-bar-greeting">{company_name}</div>'
        f'<div class="gxp-action-bar-sub">Today is <strong>{today_str}</strong></div>'
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
        if st.button("▶  Run Payroll", use_container_width=True, type="primary", key="qa_run"):
            st.session_state["_nav_redirect"] = "Payroll Run"
            st.rerun()
    with qa2:
        if st.button("＋  Add Employee", use_container_width=True, key="qa_add"):
            st.session_state["_nav_redirect"] = "Employees"
            st.rerun()
    with qa3:
        if st.button("⬡  Government Reports", use_container_width=True, key="qa_gov"):
            st.session_state["_nav_redirect"] = "Government Reports"
            st.rerun()
    with qa4:
        if st.button("⚙  Company Setup", use_container_width=True, key="qa_setup"):
            st.session_state["_nav_redirect"] = "Company Setup"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# Section 2: Alerts / To-Do
# ============================================================

def _render_alerts(deadlines: list[dict], periods: list[dict],
                   pending_leave: int = 0, pending_ot: int = 0):
    alerts = []

    # ── Pending Leave / OT approval reminder ──────────────────────────────────
    pending_total = pending_leave + pending_ot
    if pending_total > 0:
        leave_part = f"{pending_leave} leave request{'s' if pending_leave != 1 else ''}" if pending_leave else ""
        ot_part    = f"{pending_ot} overtime request{'s' if pending_ot != 1 else ''}"    if pending_ot    else ""
        desc_parts = [p for p in [leave_part, ot_part] if p]
        alerts.append({
            "type":     "warning",
            "icon":     "📋",
            "title":    f"{pending_total} Leave/OT Request{'s' if pending_total != 1 else ''} Awaiting Approval",
            "desc":     " · ".join(desc_parts),
            "action":   f"{pending_total} pending",
            "nav_page": "Employees",
            "btn_label": f"📋  Review {pending_total} Request{'s' if pending_total != 1 else ''}",
            "btn_key":   "dash_review_leave",
        })

    # Check for overdue deadlines
    for i, d in enumerate(deadlines):
        if d["days_until"] < 0:
            alerts.append({
                "type":     "overdue",
                "icon":     "\u26a0",
                "title":    f"{d['agency']} ({d['form']}) — OVERDUE",
                "desc":     f"Due {d['deadline'].strftime('%b %d')} \u2022 {abs(d['days_until'])} days overdue",
                "action":   "Remit now",
                "nav_page": "Government Reports",
                "btn_label": f"⬡  Open Government Reports",
                "btn_key":   f"dash_gov_overdue_{i}",
            })
        elif d["days_until"] <= 3:
            alerts.append({
                "type":     "warning",
                "icon":     "\u23f0",
                "title":    f"{d['agency']} ({d['form']}) — Due Soon",
                "desc":     f"Due {d['deadline'].strftime('%b %d')} \u2022 {d['days_until']} day{'s' if d['days_until'] != 1 else ''} left",
                "action":   f"Due in {d['days_until']}d",
                "nav_page": "Government Reports",
                "btn_label": "⬡  Open Government Reports",
                "btn_key":   f"dash_gov_soon_{i}",
            })

    # Check for draft periods needing review
    for i, p in enumerate(periods[:3]):
        if p["status"] == "draft":
            alerts.append({
                "type":     "info",
                "icon":     "\u270e",
                "title":    f"Payroll Draft — {p['period_start']} to {p['period_end']}",
                "desc":     "Payroll entries need review and finalization",
                "action":   "Review",
                "nav_page": "Payroll Run",
                "btn_label": "▶  Open Payroll Run",
                "btn_key":   f"dash_payroll_draft_{i}",
            })
        elif p["status"] == "reviewed":
            alerts.append({
                "type":     "info",
                "icon":     "\u2713",
                "title":    f"Ready to Finalize — {p['period_start']} to {p['period_end']}",
                "desc":     "Payroll reviewed and ready for finalization",
                "action":   "Finalize",
                "nav_page": "Payroll Run",
                "btn_label": "▶  Open Payroll Run",
                "btn_key":   f"dash_payroll_reviewed_{i}",
            })

    if not alerts:
        st.markdown("""
        <div class="gxp-alert-card gxp-alert-info" style="border-color:#16a34a;background:#f0fdf4">
            <div class="gxp-alert-icon" style="background:#dcfce7;color:#16a34a">\u2713</div>
            <div class="gxp-alert-body">
                <div class="gxp-alert-title" style="color:#166534">All caught up</div>
                <div class="gxp-alert-desc">No overdue items or pending tasks. You're in good shape.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    for a in alerts:
        card_col, btn_col = st.columns([5, 1.6], vertical_alignment="center")
        with card_col:
            st.markdown(f"""
            <div class="gxp-alert-card gxp-alert-{a['type']}">
                <div class="gxp-alert-icon">{a['icon']}</div>
                <div class="gxp-alert-body">
                    <div class="gxp-alert-title">{a['title']}</div>
                    <div class="gxp-alert-desc">{a['desc']}</div>
                </div>
                <div class="gxp-alert-action">{a['action']}</div>
            </div>
            """, unsafe_allow_html=True)
        with btn_col:
            if a.get("nav_page"):
                st.markdown('<div class="gxp-alert-nav-btn">', unsafe_allow_html=True)
                if st.button(a["btn_label"], key=a["btn_key"], use_container_width=True):
                    st.session_state["_nav_redirect"] = a["nav_page"]
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# Section 3: Quick Stat Cards
# ============================================================

def _render_stat_cards(active_count: int, total_count: int,
                       total_gross: int, total_net: int, total_cost: int,
                       latest_period: dict | None, history: list[dict]):
    inactive = total_count - active_count
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

    cards = [
        {
            "svg":    _SVG["employees"],
            "icon_bg": "#dbeafe", "icon_color": "#2563eb", "accent": "#2563eb",
            "label":  "Active Employees",
            "value":  str(active_count),
            "sub":    f"{inactive} inactive" if inactive else "All employees active",
            "trend":  "",
        },
        {
            "svg":    _SVG["gross"],
            "icon_bg": "#d1fae5", "icon_color": "#059669", "accent": "#059669",
            "label":  "Gross Pay",
            "value":  _fmt_short(total_gross),
            "sub":    period_label,
            "trend":  _trend_html(total_gross, prev_gross),
        },
        {
            "svg":    _SVG["net"],
            "icon_bg": "#ede9fe", "icon_color": "#7c3aed", "accent": "#7c3aed",
            "label":  "Net Pay",
            "value":  _fmt_short(total_net),
            "sub":    period_label,
            "trend":  _trend_html(total_net, prev_net),
        },
        {
            "svg":    _SVG["cost"],
            "icon_bg": "#fef3c7", "icon_color": "#d97706", "accent": "#d97706",
            "label":  "Employer Cost",
            "value":  _fmt_short(total_cost),
            "sub":    "Gross + employer contributions",
            "trend":  "",
        },
        {
            "svg":    _SVG["ytd"],
            "icon_bg": "#fce7f3", "icon_color": "#db2777", "accent": "#db2777",
            "label":  f"YTD Payroll ({current_year})",
            "value":  _fmt_short(ytd_cost) if ytd_cost else "—",
            "sub":    f"{len([r for r in history if str(r['period']).startswith(str(current_year))])} pay runs this year",
            "trend":  "",
        },
    ]

    cols = st.columns(5)
    for col, card in zip(cols, cards):
        with col:
            # Always render trend row div — empty trend leaves a blank line that
            # breaks Streamlit's markdown parser, causing subsequent divs to render as literal text.
            trend_content = card["trend"] if card["trend"] else "&nbsp;"
            html = (
                f'<div class="gxp-stat-card" style="border-top:3px solid {card["accent"]}">'
                f'<div class="gxp-stat-icon" style="background:{card["icon_bg"]};color:{card["icon_color"]}">'
                f'{card["svg"]}</div>'
                f'<div class="gxp-stat-label">{card["label"]}</div>'
                f'<div class="gxp-stat-value">{card["value"]}</div>'
                f'<div class="gxp-stat-trend-row">{trend_content}</div>'
                f'<div class="gxp-stat-sub">{card["sub"]}</div>'
                f'</div>'
            )
            st.markdown(html, unsafe_allow_html=True)


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
# Section 5: Government Remittance + Upcoming Deadlines
# ============================================================

def _render_remittance_and_deadlines(latest_entries: list[dict], latest_period: dict | None,
                                      deadlines: list[dict]):
    col_remit, col_deadlines = st.columns([3, 2])

    with col_remit:
        st.markdown('<div class="gxp-panel">', unsafe_allow_html=True)
        st.markdown('<div class="gxp-panel-header"><div class="gxp-panel-title">Government Remittance</div></div>', unsafe_allow_html=True)

        if not latest_entries:
            st.caption("Remittance data will appear after the first finalized payroll.")
        else:
            total_sss_ee = sum(e["sss_employee"]        for e in latest_entries)
            total_sss_er = sum(e["sss_employer"]        for e in latest_entries)
            total_ph_ee  = sum(e["philhealth_employee"] for e in latest_entries)
            total_ph_er  = sum(e["philhealth_employer"] for e in latest_entries)
            total_pi_ee  = sum(e["pagibig_employee"]    for e in latest_entries)
            total_pi_er  = sum(e["pagibig_employer"]    for e in latest_entries)
            total_wht    = sum(e["withholding_tax"]     for e in latest_entries)

            r1, r2 = st.columns(2)
            with r1:
                st.markdown(remit_card(
                    "SSS", GOV_COLORS["SSS"],
                    [("Employee", _fmt(total_sss_ee)), ("Employer", _fmt(total_sss_er))],
                    ("Total", _fmt(total_sss_ee + total_sss_er)),
                ), unsafe_allow_html=True)
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                st.markdown(remit_card(
                    "Pag-IBIG", GOV_COLORS["Pag-IBIG"],
                    [("Employee", _fmt(total_pi_ee)), ("Employer", _fmt(total_pi_er))],
                    ("Total", _fmt(total_pi_ee + total_pi_er)),
                ), unsafe_allow_html=True)
            with r2:
                st.markdown(remit_card(
                    "PhilHealth", GOV_COLORS["PhilHealth"],
                    [("Employee", _fmt(total_ph_ee)), ("Employer", _fmt(total_ph_er))],
                    ("Total", _fmt(total_ph_ee + total_ph_er)),
                ), unsafe_allow_html=True)
                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
                all_gov = (
                    total_sss_ee + total_sss_er + total_ph_ee + total_ph_er
                    + total_pi_ee + total_pi_er + total_wht
                )
                st.markdown(remit_card(
                    "BIR Withholding", GOV_COLORS["BIR"],
                    [("Withholding Tax", _fmt(total_wht))],
                    ("All Gov Total", _fmt(all_gov)),
                ), unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with col_deadlines:
        st.markdown('<div class="gxp-panel">', unsafe_allow_html=True)
        st.markdown('<div class="gxp-panel-header"><div class="gxp-panel-title">Upcoming Deadlines</div></div>', unsafe_allow_html=True)

        for d in deadlines:
            days = d["days_until"]
            deadline_str = d["deadline"].strftime("%b %d, %Y")
            if d["deadline"] != d["raw_deadline"]:
                deadline_str += " (adj.)"

            if days < 0:
                color = "#dc2626"
                tag = f'<span style="background:#fef2f2;color:#dc2626;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700">OVERDUE</span>'
            elif days <= 3:
                color = "#d97706"
                tag = f'<span style="background:#fffbeb;color:#d97706;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700">{days}d left</span>'
            elif days <= 7:
                color = "#2563eb"
                tag = f'<span style="background:#dbeafe;color:#2563eb;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700">{days}d left</span>'
            else:
                color = "#16a34a"
                tag = f'<span style="background:#f0fdf4;color:#16a34a;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700">{days}d</span>'

            st.markdown(f"""
            <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f3f4f6">
                <div>
                    <div style="font-size:13px;font-weight:600;color:#1f2937">{d['agency']}
                        <span style="font-weight:400;color:#6b7280;font-size:12px">({d['form']})</span>
                    </div>
                    <div style="font-size:11px;color:#9ca3af;margin-top:2px">{deadline_str}</div>
                </div>
                <div>{tag}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# Section 6: Analytics (Trends — Secondary)
# ============================================================

def _render_analytics(history: list[dict]):
    st.markdown('<div class="gxp-panel">', unsafe_allow_html=True)
    st.markdown("""
    <div class="gxp-panel-header">
        <div class="gxp-panel-title">Payroll Analytics</div>
        <div class="gxp-panel-subtitle">Trends across finalized pay periods</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if len(history) < 2:
        st.info("Analytics will appear once you have 2+ finalized pay periods.")
        return

    df = pd.DataFrame(history)

    col_trend, col_breakdown = st.columns([3, 2])

    with col_trend:
        fig_trend = px.area(
            df,
            x="period",
            y=["gross_pay", "net_pay"],
            labels={"value": "Amount (\u20b1)", "period": "Period", "variable": ""},
            color_discrete_map={"gross_pay": "#2563eb", "net_pay": "#059669"},
        )
        fig_trend.for_each_trace(
            lambda t: t.update(
                name={"gross_pay": "Gross Pay", "net_pay": "Net Pay"}[t.name]
            )
        )
        fig_trend.update_layout(
            title="Payroll Cost Trend",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=48, b=0),
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig_trend.update_xaxes(showgrid=False)
        fig_trend.update_yaxes(gridcolor="#f3f4f6")
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_breakdown:
        latest = history[-1]
        fig_donut = px.pie(
            names=["SSS", "PhilHealth", "Pag-IBIG", "BIR"],
            values=[latest["sss"], latest["philhealth"], latest["pagibig"], latest["bir"]],
            title=f"Deductions ({latest['period'][:7]})",
            color_discrete_sequence=["#7c3aed", "#0891b2", "#059669", "#dc2626"],
            hole=0.45,
        )
        fig_donut.update_traces(textposition="inside", textinfo="percent+label")
        fig_donut.update_layout(
            showlegend=False,
            margin=dict(l=0, r=0, t=48, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    # Headcount bar chart
    fig_hc = px.bar(
        df,
        x="period",
        y="headcount",
        labels={"headcount": "Employees Paid", "period": "Period"},
        title="Headcount per Pay Period",
        color_discrete_sequence=["#2563eb"],
        text="headcount",
    )
    fig_hc.update_traces(textposition="outside")
    fig_hc.update_layout(
        margin=dict(l=0, r=0, t=48, b=0),
        yaxis=dict(rangemode="tozero"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig_hc.update_xaxes(showgrid=False)
    fig_hc.update_yaxes(gridcolor="#f3f4f6")
    st.plotly_chart(fig_hc, use_container_width=True)


# ============================================================
# Main Page Render
# ============================================================

def render():
    inject_css()

    # ── Load all data ─────────────────────────────────
    company             = _load_company()
    active_count        = _load_active_employee_count()
    total_count         = _load_all_employee_count()
    periods             = _load_pay_periods()
    history             = _load_payroll_history()
    deadlines           = _get_deadlines()
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

    # ── 1. Action Bar ─────────────────────────────────
    _render_action_bar(company, next_period)

    # ── 2. Alerts / To-Do ─────────────────────────────
    _render_alerts(deadlines, periods, pending_leave, pending_ot)

    # ── 3. Quick Stat Cards ───────────────────────────
    _render_stat_cards(active_count, total_count, total_gross, total_net, total_cost, latest_period, history)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── 4. Last Payroll Summary ───────────────────────
    _render_last_payroll_summary(latest_period, latest_entries)

    # ── 5. Remittance + Deadlines ─────────────────────
    _render_remittance_and_deadlines(latest_entries, latest_period, deadlines)

    # ── 6. Analytics (secondary) ──────────────────────
    with st.expander("Payroll Analytics", expanded=False):
        _render_analytics(history)
