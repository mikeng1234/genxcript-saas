"""
Dashboard — Streamlit page.

Card-based layout with an Edit Dashboard mode that lets users reorder,
resize, and hide sections. Layout is persisted in st.session_state.
"""

import streamlit as st
from datetime import date
import calendar as cal_mod
from collections import defaultdict
from app.db_helper import get_db, get_company_id
from backend.deadlines import get_remittance_deadlines, load_holiday_set
import plotly.express as px
import pandas as pd


# ============================================================
# Card Definitions & Layout Config
# ============================================================

_CARDS = [
    {"id": "kpi",        "name": "KPI Metrics",                   "default_width": "full"},
    {"id": "trends",     "name": "Payroll Trends",                "default_width": "full"},
    {"id": "headcount",  "name": "Headcount per Pay Period",      "default_width": "full"},
    {"id": "periods",    "name": "Pay Periods",                   "default_width": "large"},
    {"id": "deadlines",  "name": "Remittance Deadlines",          "default_width": "small"},
    {"id": "remittance", "name": "Government Remittance Summary", "default_width": "full"},
]

_CARD_NAME = {c["id"]: c["name"] for c in _CARDS}

_WIDTH_OPTIONS = ["full", "large", "small", "half"]
_WIDTH_LABELS  = {
    "full":  "Full Width",
    "large": "Wide (2/3)",
    "small": "Narrow (1/3)",
    "half":  "Half Width",
}


def _init_layout():
    if "dash_layout" not in st.session_state:
        st.session_state.dash_layout = [
            {"id": c["id"], "width": c["default_width"], "visible": True}
            for c in _CARDS
        ]
    if "dash_edit" not in st.session_state:
        st.session_state.dash_edit = False


# ============================================================
# Data Helpers
# ============================================================

def _fmt(centavos: int) -> str:
    return f"₱{centavos / 100:,.2f}"


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


def _get_accurate_deadlines() -> list[dict]:
    db = get_db()
    today = date.today()
    holidays = load_holiday_set(db, year=today.year)
    return get_remittance_deadlines(today, holidays)


# ============================================================
# Period Timeline
# ============================================================

def _month_offset(base: str, n: int) -> str:
    y, m = int(base[:4]), int(base[5:7])
    m += n
    while m > 12: m -= 12; y += 1
    while m < 1:  m += 12; y -= 1
    return f"{y:04d}-{m:02d}"


def _render_period_timeline(periods: list[dict], pay_frequency: str = "semi-monthly"):
    today = date.today()
    cur = today.strftime("%Y-%m")

    if pay_frequency == "monthly":
        expected_slots = 1
        slot_labels = ["Monthly"]
    elif pay_frequency == "weekly":
        expected_slots = 5
        slot_labels = ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"]
    else:
        expected_slots = 2
        slot_labels = ["1st Half", "2nd Half"]

    by_month = defaultdict(list)
    for p in periods:
        by_month[p["period_start"][:7]].append(p)

    if "tl_month" not in st.session_state:
        st.session_state.tl_month = cur
    sel = st.session_state.tl_month

    slots = [_month_offset(sel, i) for i in range(-2, 3)]

    cols = st.columns([1, 1.3, 2, 1.3, 1])
    for col, ym in zip(cols, slots):
        y, m = int(ym[:4]), int(ym[5:7])
        label = f"{cal_mod.month_abbr[m]} {y}"
        is_sel    = ym == sel
        is_future = ym > cur

        with col:
            if is_sel:
                st.markdown(
                    f"<div style='text-align:center;font-weight:700;font-size:15px;"
                    f"color:#0d6efd;border-bottom:3px solid #0d6efd;"
                    f"padding-bottom:6px;margin-bottom:8px'>{label}</div>",
                    unsafe_allow_html=True,
                )
            elif is_future:
                st.markdown(
                    f"<div style='text-align:center;font-size:11px;"
                    f"color:#ced4da;padding-bottom:6px;margin-bottom:8px'>{label}</div>",
                    unsafe_allow_html=True,
                )
            else:
                if st.button(label, key=f"tl_{ym}", use_container_width=True):
                    st.session_state.tl_month = ym
                    st.rerun()

    _STATUS_CARD = {
        "draft":     ("#cfe2ff", "#084298", "DRAFT"),
        "reviewed":  ("#e8daef", "#6c3483", "REVIEWED"),
        "finalized": ("#fff3cd", "#664d03", "FINALIZED"),
        "paid":      ("#d1e7dd", "#0a3622", "PAID"),
    }

    month_periods = sorted(by_month.get(sel, []), key=lambda p: p["period_start"])

    if not month_periods:
        msg = "Future period — not yet created." if sel > cur else "No pay periods for this month."
        st.caption(msg)
        return

    display_count = len(month_periods) if pay_frequency == "weekly" else expected_slots
    card_cols = st.columns(display_count)

    for i in range(display_count):
        with card_cols[i]:
            slot_label = slot_labels[i] if i < len(slot_labels) else f"Period {i+1}"
            if i < len(month_periods):
                p = month_periods[i]
                entries = _load_payroll_entries(p["id"])
                count = len(entries)
                gross = sum(e.get("gross_pay", 0) for e in entries) / 100 if entries else 0
                net   = sum(e.get("net_pay",   0) for e in entries) / 100 if entries else 0
                bg, fg, slabel = _STATUS_CARD.get(p["status"], ("#e9ecef", "#495057", p["status"].upper()))
                net_str   = f"₱{net:,.0f}" if net   else "—"
                gross_str = f"₱{gross:,.0f}" if gross else "—"
                st.markdown(f"""
                <div style="border:1px solid #dee2e6;border-radius:10px;
                            padding:14px 16px;background:#fafafa;min-height:110px">
                  <div style="font-size:11px;color:#6c757d;margin-bottom:3px">{slot_label}</div>
                  <div style="font-size:13px;font-weight:600;margin-bottom:8px">
                    {p['period_start']} → {p['period_end']}
                  </div>
                  <span style="padding:2px 10px;border-radius:12px;font-size:11px;
                               font-weight:700;background:{bg};color:{fg}">{slabel}</span>
                  <div style="margin-top:10px;font-size:12px;color:#495057">
                    {count} employees &nbsp;·&nbsp;
                    <span style="font-weight:600">Net {net_str}</span>
                  </div>
                  <div style="font-size:11px;color:#adb5bd;margin-top:2px">Gross {gross_str}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="border:1px dashed #dee2e6;border-radius:10px;
                            padding:14px 16px;background:#f8f9fa;
                            min-height:110px;text-align:center">
                  <div style="font-size:11px;color:#adb5bd;margin-top:24px">{slot_label}</div>
                  <div style="font-size:12px;color:#ced4da">Not created yet</div>
                </div>
                """, unsafe_allow_html=True)


# ============================================================
# Card Section Renderers
# ============================================================

def _section_kpi(data: dict, container):
    active_count   = data["active_count"]
    inactive_count = data["total_count"] - active_count
    total_gross    = data["total_gross"]
    total_net      = data["total_net"]
    total_cost     = data["total_cost"]
    latest_period  = data["latest_period"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Active Employees", active_count,
            delta=f"{inactive_count} inactive" if inactive_count else None,
            delta_color="off",
        )
    with col2:
        st.metric("Total Gross Pay", _fmt(total_gross))
    with col3:
        st.metric("Total Net Pay", _fmt(total_net))
    with col4:
        st.metric(
            "Total Employer Cost", _fmt(total_cost),
            help="Gross pay + employer SSS, PhilHealth, Pag-IBIG",
        )

    if latest_period:
        st.caption(
            f"Based on latest finalized period: "
            f"{latest_period['period_start']} to {latest_period['period_end']}"
        )
    else:
        st.caption("No finalized pay periods yet. Totals will appear after your first payroll run.")


def _section_trends(data: dict, container):
    history = data["history"]
    if len(history) < 2:
        st.info("Charts will appear once you have 2 or more finalized pay periods.")
        return

    df = pd.DataFrame(history)
    col_trend, col_pie = st.columns([3, 2])

    with col_trend:
        fig_trend = px.line(
            df,
            x="period",
            y=["gross_pay", "net_pay"],
            labels={"value": "Amount (₱)", "period": "Period", "variable": ""},
            color_discrete_map={"gross_pay": "#1f77b4", "net_pay": "#2ca02c"},
            markers=True,
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
        )
        st.plotly_chart(fig_trend, width="stretch")

    with col_pie:
        latest = history[-1]
        fig_pie = px.pie(
            names=["SSS", "PhilHealth", "Pag-IBIG", "BIR Withholding"],
            values=[latest["sss"], latest["philhealth"], latest["pagibig"], latest["bir"]],
            title=f"Deductions Breakdown ({latest['period'][:7]})",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hole=0.35,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(showlegend=False, margin=dict(l=0, r=0, t=48, b=0))
        st.plotly_chart(fig_pie, width="stretch")


def _section_headcount(data: dict, container):
    history = data["history"]
    if len(history) < 1:
        st.info("Charts will appear once you have finalized pay periods.")
        return

    df = pd.DataFrame(history)
    fig_hc = px.bar(
        df,
        x="period",
        y="headcount",
        labels={"headcount": "Employees Paid", "period": "Period"},
        title="Headcount per Pay Period",
        color_discrete_sequence=["#ff7f0e"],
        text="headcount",
    )
    fig_hc.update_traces(textposition="outside")
    fig_hc.update_layout(
        margin=dict(l=0, r=0, t=48, b=0),
        yaxis=dict(rangemode="tozero"),
    )
    st.plotly_chart(fig_hc, width="stretch")


def _section_periods(data: dict, container):
    _render_period_timeline(
        data["periods"],
        data["company"].get("pay_frequency", "semi-monthly"),
    )


def _section_deadlines(data: dict, container):
    for d in data["deadlines"]:
        days_until = d["days_until"]
        if days_until < 0:
            icon, status = "🔴", "OVERDUE"
        elif days_until <= 3:
            icon, status = "🟡", f"in {days_until} days"
        else:
            icon, status = "🟢", f"in {days_until} days"

        deadline_str = d["deadline"].strftime("%b %d")
        if d["deadline"] != d["raw_deadline"]:
            deadline_str += " (adjusted)"

        st.markdown(
            f"{icon} **{d['agency']}** ({d['form']}) — {deadline_str}  \n"
            f"{d['description']} · *{status}*"
        )


def _section_remittance(data: dict, container):
    latest_entries = data["latest_entries"]
    latest_period  = data["latest_period"]

    if not latest_entries:
        st.info("Remittance summary will appear after the first finalized payroll.")
        return

    st.caption(f"Period: {latest_period['period_start']} to {latest_period['period_end']}")

    total_sss_ee = sum(e["sss_employee"]        for e in latest_entries)
    total_sss_er = sum(e["sss_employer"]        for e in latest_entries)
    total_ph_ee  = sum(e["philhealth_employee"] for e in latest_entries)
    total_ph_er  = sum(e["philhealth_employer"] for e in latest_entries)
    total_pi_ee  = sum(e["pagibig_employee"]    for e in latest_entries)
    total_pi_er  = sum(e["pagibig_employer"]    for e in latest_entries)
    total_wht    = sum(e["withholding_tax"]     for e in latest_entries)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("**SSS**")
        st.text(f"Employee:  {_fmt(total_sss_ee)}")
        st.text(f"Employer:  {_fmt(total_sss_er)}")
        st.markdown(f"**Total:   {_fmt(total_sss_ee + total_sss_er)}**")

    with col2:
        st.markdown("**PhilHealth**")
        st.text(f"Employee:  {_fmt(total_ph_ee)}")
        st.text(f"Employer:  {_fmt(total_ph_er)}")
        st.markdown(f"**Total:   {_fmt(total_ph_ee + total_ph_er)}**")

    with col3:
        st.markdown("**Pag-IBIG**")
        st.text(f"Employee:  {_fmt(total_pi_ee)}")
        st.text(f"Employer:  {_fmt(total_pi_er)}")
        st.markdown(f"**Total:   {_fmt(total_pi_ee + total_pi_er)}**")

    with col4:
        st.markdown("**BIR Withholding Tax**")
        st.text(f"Total:     {_fmt(total_wht)}")
        st.markdown("")
        all_gov = (
            total_sss_ee + total_sss_er
            + total_ph_ee + total_ph_er
            + total_pi_ee + total_pi_er
            + total_wht
        )
        st.markdown(f"**All Gov:  {_fmt(all_gov)}**")


_SECTION_RENDERERS = {
    "kpi":        _section_kpi,
    "trends":     _section_trends,
    "headcount":  _section_headcount,
    "periods":    _section_periods,
    "deadlines":  _section_deadlines,
    "remittance": _section_remittance,
}


# ============================================================
# Edit Panel
# ============================================================

def _render_edit_panel():
    layout = st.session_state.dash_layout

    st.markdown(
        """
        <div style="background:#f0f4ff;border:1px solid #c5d3f6;border-radius:12px;
                    padding:18px 20px;margin-bottom:24px">
          <div style="font-size:15px;font-weight:700;color:#1a3a8f;margin-bottom:4px">
            ✏️ Dashboard Layout Editor
          </div>
          <div style="font-size:12px;color:#6c757d;margin-bottom:14px">
            Reorder cards with ↑ ↓, change width, or hide sections with 👁.
            Pair <em>Wide (2/3)</em> + <em>Narrow (1/3)</em>, or two <em>Half Width</em>
            cards to display side-by-side.
          </div>
        """,
        unsafe_allow_html=True,
    )

    for i, card in enumerate(layout):
        name = _CARD_NAME.get(card["id"], card["id"])
        vis  = card["visible"]

        c_name, c_width, c_vis, c_up, c_dn = st.columns([3.5, 2, 0.6, 0.5, 0.5])

        with c_name:
            faded = "" if vis else "opacity:0.4;"
            st.markdown(
                f"<div style='padding-top:6px;{faded}font-size:14px'>{name}</div>",
                unsafe_allow_html=True,
            )

        with c_width:
            new_w = st.selectbox(
                "w",
                options=_WIDTH_OPTIONS,
                format_func=lambda x: _WIDTH_LABELS[x],
                index=_WIDTH_OPTIONS.index(card["width"]),
                key=f"dw_{card['id']}_{i}",
                label_visibility="collapsed",
                disabled=not vis,
            )
            if new_w != card["width"]:
                st.session_state.dash_layout[i]["width"] = new_w
                st.rerun()

        with c_vis:
            if st.button("👁" if vis else "🚫", key=f"dv_{i}", help="Show / Hide"):
                st.session_state.dash_layout[i]["visible"] = not vis
                st.rerun()

        with c_up:
            if i > 0:
                if st.button("↑", key=f"du_{i}"):
                    layout[i], layout[i - 1] = layout[i - 1], layout[i]
                    st.rerun()

        with c_dn:
            if i < len(layout) - 1:
                if st.button("↓", key=f"dd_{i}"):
                    layout[i], layout[i + 1] = layout[i + 1], layout[i]
                    st.rerun()

    _, col_reset = st.columns([5, 1])
    with col_reset:
        if st.button("↺ Reset", help="Restore default layout"):
            del st.session_state.dash_layout
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# Layout Renderer (smart column pairing)
# ============================================================

def _render_dashboard_layout(data: dict):
    layout  = st.session_state.dash_layout
    edit    = st.session_state.dash_edit
    visible = [c for c in layout if c["visible"]]

    i = 0
    while i < len(visible):
        card = visible[i]
        w    = card["width"]
        name = _CARD_NAME.get(card["id"], card["id"])
        renderer = _SECTION_RENDERERS.get(card["id"])
        if not renderer:
            i += 1
            continue

        next_card = visible[i + 1] if i + 1 < len(visible) else None
        next_w    = next_card["width"] if next_card else None

        # Determine if this card pairs with the next
        pairs = (
            (w == "large" and next_w == "small") or
            (w == "small" and next_w == "large") or
            (w == "half"  and next_w == "half")
        )

        if pairs:
            if w == "large" or (w == "half" and next_w == "half"):
                ratio = [2, 1] if w == "large" else [1, 1]
            else:
                ratio = [1, 2]

            col_a, col_b = st.columns(ratio)
            next_name     = _CARD_NAME.get(next_card["id"], next_card["id"])
            next_renderer = _SECTION_RENDERERS.get(next_card["id"])

            with col_a:
                _draw_card(name, card["id"], edit, renderer, data)
            with col_b:
                if next_renderer:
                    _draw_card(next_name, next_card["id"], edit, next_renderer, data)
            i += 2
        else:
            _draw_card(name, card["id"], edit, renderer, data)
            i += 1

        st.divider()


def _draw_card(title: str, card_id: str, edit_mode: bool, renderer, data: dict):
    """Render a single card with its styled header."""
    prefix = "☰ " if edit_mode else ""
    faded  = "color:#adb5bd;" if edit_mode else "color:#343a40;"
    st.markdown(
        f"<div style='font-size:15px;font-weight:700;{faded}"
        f"margin-bottom:10px;padding-bottom:6px;"
        f"border-bottom:2px solid #e9ecef;'>{prefix}{title}</div>",
        unsafe_allow_html=True,
    )
    renderer(data, st)


# ============================================================
# Main Page Render
# ============================================================

def render():
    _init_layout()

    company      = _load_company()
    company_name = company.get("name", "Your Company")

    # ── Page heading + Edit Dashboard button ──────────────────
    h_col, btn_col = st.columns([5, 1])
    with h_col:
        st.title(f"{company_name} — Dashboard")
    with btn_col:
        st.markdown("<div style='padding-top:18px'>", unsafe_allow_html=True)
        edit_label = "✅ Done" if st.session_state.dash_edit else "✏️ Edit Dashboard"
        if st.button(edit_label, use_container_width=True):
            st.session_state.dash_edit = not st.session_state.dash_edit
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Edit panel (shown when edit mode is on) ───────────────
    if st.session_state.dash_edit:
        _render_edit_panel()

    # ── Pre-load all data ─────────────────────────────────────
    active_count  = _load_active_employee_count()
    total_count   = _load_all_employee_count()
    periods       = _load_pay_periods()
    history       = _load_payroll_history()
    deadlines     = _get_accurate_deadlines()

    latest_period  = None
    latest_entries = []
    for p in periods:
        if p["status"] in ("finalized", "paid"):
            latest_period  = p
            latest_entries = _load_payroll_entries(p["id"])
            break

    total_gross = sum(e["gross_pay"] for e in latest_entries) if latest_entries else 0
    total_net   = sum(e["net_pay"]   for e in latest_entries) if latest_entries else 0
    total_er    = sum(
        e["sss_employer"] + e["philhealth_employer"] + e["pagibig_employer"]
        for e in latest_entries
    ) if latest_entries else 0
    total_cost  = total_gross + total_er

    data = {
        "company":        company,
        "active_count":   active_count,
        "total_count":    total_count,
        "periods":        periods,
        "latest_period":  latest_period,
        "latest_entries": latest_entries,
        "history":        history,
        "deadlines":      deadlines,
        "total_gross":    total_gross,
        "total_net":      total_net,
        "total_er":       total_er,
        "total_cost":     total_cost,
    }

    # ── Render cards in layout order ─────────────────────────
    _render_dashboard_layout(data)
