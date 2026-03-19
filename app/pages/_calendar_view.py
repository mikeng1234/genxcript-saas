"""
Calendar View — Streamlit page.

Monthly grid showing:
- Pay period spans (draft / finalized / paid, color-coded)
- Philippine holidays (regular and special non-working)
- Government remittance deadlines (adjusted for weekends/holidays)
- Payment dates

Below the calendar: a collapsible Philippine Holiday reference table
for the viewed year.
"""

import streamlit as st
import streamlit.components.v1 as _stc
from datetime import date, timedelta
import calendar as _cal

from app.db_helper import get_db, get_company_id
from app.styles import inject_css
from backend.deadlines import get_remittance_deadlines, load_holiday_set


# ============================================================
# Database helpers
# ============================================================

def _load_holidays(year: int) -> list[dict]:
    """
    Return merged holiday list for the current company for a given year.
    - National holidays (company_id IS NULL) are the base.
    - Company-specific overrides replace the national entry for the same holiday name.
    - Company-added custom holidays (unique names) are appended.
    """
    db  = get_db()
    cid = get_company_id()

    def _to_date(v):
        if v is None:
            return None
        return date.fromisoformat(v) if isinstance(v, str) else v

    def _parse(r):
        return {
            "holiday_date":  _to_date(r["holiday_date"]),
            "observed_date": _to_date(r.get("observed_date")),
            "name": r["name"],
            "type": r["type"],
        }

    national = [
        _parse(r) for r in (
            db.table("holidays")
            .select("holiday_date, observed_date, name, type")
            .eq("year", year)
            .is_("company_id", "null")
            .order("holiday_date")
            .execute()
        ).data
    ]
    company_rows = [
        _parse(r) for r in (
            db.table("holidays")
            .select("holiday_date, observed_date, name, type")
            .eq("year", year)
            .eq("company_id", cid)
            .order("holiday_date")
            .execute()
        ).data
    ]

    national_names = {h["name"] for h in national}
    # Company overrides replace the national entry for the same name
    overrides = {h["name"]: h for h in company_rows if h["name"] in national_names}
    customs   = [h for h in company_rows if h["name"] not in national_names]

    merged = []
    for h in national:
        merged.append(overrides.get(h["name"], h))
    merged.extend(customs)
    merged.sort(key=lambda h: h["holiday_date"] or date.min)
    return merged


def _load_pay_periods_overlapping(year: int, month: int) -> list[dict]:
    """Return pay periods whose date range overlaps with the given month."""
    db     = get_db()
    first  = date(year, month, 1).isoformat()
    last   = date(year, month, _cal.monthrange(year, month)[1]).isoformat()
    result = (
        db.table("pay_periods")
        .select("*")
        .eq("company_id", get_company_id())
        .lte("period_start", last)   # period starts before or on month-end
        .gte("period_end",   first)  # period ends on or after month-start
        .order("period_start")
        .execute()
    )
    return result.data


# ============================================================
# Event builder
# ============================================================

# Visual styling per pay period status
_STATUS_BG     = {"draft": "#cfe2ff", "reviewed": "#e8daef", "finalized": "#fff3cd", "paid": "#d1e7dd"}
_STATUS_FG     = {"draft": "#084298", "reviewed": "#6c3483", "finalized": "#664d03", "paid": "#0a3622"}
_STATUS_BORDER = {"draft": "#0d6efd", "reviewed": "#8e44ad", "finalized": "#ffc107", "paid": "#198754"}


def _build_day_events(
    year: int,
    month: int,
    holidays: list[dict],
    pay_periods: list[dict],
    deadlines: list[dict],
) -> dict[date, list[dict]]:
    """
    Aggregate all calendar events into a {date: [event, ...]} dict.

    Event types:
      hol_reg, hol_spec          — Philippine holidays
      period_span                — day falls inside a pay period
      payment                    — payment date of a period
      deadline_sss / _philhealth / _pagibig / _bir   — gov remittance deadlines
    """
    events: dict[date, list[dict]] = {}

    def add(d: date, evt: dict):
        events.setdefault(d, []).append(evt)

    # ── Holidays ─────────────────────────────────────────────
    for h in holidays:
        # Use observed_date when set (government-proclaimed movement)
        obs = h.get("observed_date")
        effective_d = obs if obs else h["holiday_date"]
        if effective_d.year == year and effective_d.month == month:
            t   = "hol_reg" if h["type"] == "regular" else "hol_spec"
            name_short = h["name"][:18] + "…" if len(h["name"]) > 18 else h["name"]
            lbl = (name_short + " (moved)") if obs else name_short
            add(effective_d, {"type": t, "label": lbl, "priority": 0})

    # ── Pay periods ───────────────────────────────────────────
    for p in pay_periods:
        p_start = date.fromisoformat(p["period_start"])
        p_end   = date.fromisoformat(p["period_end"])
        p_pay   = date.fromisoformat(p["payment_date"])
        status  = p["status"]
        bg      = _STATUS_BG.get(status, "#e2e3e5")
        fg      = _STATUS_FG.get(status, "#41464b")
        border  = _STATUS_BORDER.get(status, "#6c757d")
        short   = f"{p_start.strftime('%m/%d')}–{p_end.strftime('%m/%d')}"

        # Mark every day in the period that falls in this month
        d = p_start
        while d <= p_end:
            if d.year == year and d.month == month:
                if d == p_start:
                    lbl = f"▶ {short} [{status.upper()}]"
                elif d == p_end:
                    lbl = f"◀ {short} [{status.upper()}]"
                else:
                    lbl = f"━ {status.upper()}"
                add(d, {
                    "type": "period_span", "label": lbl,
                    "bg": bg, "fg": fg, "border": border, "priority": 1,
                })
            d += timedelta(days=1)

        # Payment date badge
        if p_pay.year == year and p_pay.month == month:
            add(p_pay, {
                "type": "payment",
                "label": f"Pay Day ({status.upper()})",
                "priority": 2,
            })

    # ── Government deadlines ──────────────────────────────────
    _deadline_type = {
        "SSS":        "deadline_sss",
        "PhilHealth": "deadline_philhealth",
        "Pag-IBIG":   "deadline_pagibig",
        "BIR":        "deadline_bir",
    }
    for dl in deadlines:
        d = dl["deadline"]
        if d.year == year and d.month == month:
            dtype = _deadline_type.get(dl["agency"], "deadline_bir")
            lbl   = f"{dl['agency']} due"
            if dl["deadline"] != dl["raw_deadline"]:
                lbl += " (adj)"
            add(d, {"type": dtype, "label": lbl, "priority": 3})

    # Sort each day's events by priority so holidays appear first
    for d in events:
        events[d].sort(key=lambda e: e.get("priority", 9))

    return events


# ============================================================
# HTML calendar renderer
# ============================================================

_CALENDAR_CSS = """
<style>
/* ── Calendar — dark base (matches config.toml base=dark) ── */
.gxp-cal-wrap { overflow-x: auto; margin-bottom: 4px; }
.gxp-cal {
    width: 100%; border-collapse: collapse; table-layout: fixed;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.gxp-cal th {
    background: #1e3a5f; color: #e2e8f0; padding: 8px 2px;
    text-align: center; font-size: 12px; letter-spacing: 0.4px;
}
.gxp-cal td {
    border: 1px solid #2d3748; vertical-align: top;
    padding: 4px 4px 2px; height: 90px; width: 14.28%;
    box-sizing: border-box; overflow: hidden;
    background: #1a2030;
}
.gxp-cal .empty-cell { background: #131920 !important; }
.gxp-cal .weekend    { background: #161d28 !important; }
.gxp-cal .hol-reg    { background: #3b1515 !important; }
.gxp-cal .hol-spec   { background: #3b2f0a !important; }
.day-num {
    font-size: 12px; font-weight: 700; color: #e2e8f0;
    display: inline-block; margin-bottom: 2px; line-height: 1;
}
.day-num.is-today {
    background: #3b82f6; color: #fff; border-radius: 50%;
    width: 20px; height: 20px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 11px;
}
.evt {
    display: block; font-size: 9px; font-weight: 600;
    padding: 1px 3px; border-radius: 3px; margin-bottom: 1px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.evt-hol-reg             { background: #dc3545; color: #fff; }
.evt-hol-spec            { background: #fd7e14; color: #fff; }
.evt-payment             { background: #198754; color: #fff; }
.evt-deadline-sss        { background: #7c3aed; color: #fff; }
.evt-deadline-philhealth { background: #0891b2; color: #fff; }
.evt-deadline-pagibig    { background: #db2777; color: #fff; }
.evt-deadline-bir        { background: #dc2626; color: #fff; }

/* ── Light mode overrides ── */
@media (prefers-color-scheme: light) {
    .gxp-cal td          { background: #ffffff; border-color: #dee2e6; }
    .gxp-cal .empty-cell { background: #f0f2f5 !important; }
    .gxp-cal .weekend    { background: #f7f8fa !important; }
    .gxp-cal .hol-reg    { background: #fff0f0 !important; }
    .gxp-cal .hol-spec   { background: #fffaed !important; }
    .day-num             { color: #343a40; }
    .day-num.is-today    { background: #0d6efd; color: #fff; }
    .evt-deadline-philhealth { color: #000; }
}
</style>
"""

_TYPE_CSS = {
    "hol_reg":             "evt-hol-reg",
    "hol_spec":            "evt-hol-spec",
    "payment":             "evt-payment",
    "deadline_sss":        "evt-deadline-sss",
    "deadline_philhealth": "evt-deadline-philhealth",
    "deadline_pagibig":    "evt-deadline-pagibig",
    "deadline_bir":        "evt-deadline-bir",
}


def _render_calendar_html(
    year: int, month: int, day_events: dict[date, list[dict]]
) -> str:
    today = date.today()
    weeks = _cal.monthcalendar(year, month)

    parts = [_CALENDAR_CSS, '<div class="gxp-cal-wrap"><table class="gxp-cal">']

    # Header row
    parts.append(
        "<tr>"
        + "".join(f"<th>{h}</th>" for h in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        + "</tr>"
    )

    for week in weeks:
        parts.append("<tr>")
        for wi, day_num in enumerate(week):
            if day_num == 0:
                parts.append('<td class="empty-cell"></td>')
                continue

            d    = date(year, month, day_num)
            evts = day_events.get(d, [])

            is_weekend  = wi >= 5
            has_reg_hol = any(e["type"] == "hol_reg"  for e in evts)
            has_spec_hol = any(e["type"] == "hol_spec" for e in evts)
            period_evts = [e for e in evts if e["type"] == "period_span"]

            # Cell class
            cls = ""
            if has_reg_hol:
                cls = "hol-reg"
            elif has_spec_hol:
                cls = "hol-spec"
            elif is_weekend:
                cls = "weekend"

            # Left border from first pay period in cell
            style = ""
            if period_evts:
                style = f'border-left: 3px solid {period_evts[0]["border"]};'

            parts.append(f'<td class="{cls}" style="{style}">')

            # Day number (circle on today)
            num_cls = "day-num is-today" if d == today else "day-num"
            parts.append(f'<span class="{num_cls}">{day_num}</span>')

            # Events
            for e in evts:
                t   = e["type"]
                lbl = e["label"]
                if t == "period_span":
                    parts.append(
                        f'<span class="evt" style="background:{e["bg"]};color:{e["fg"]}">'
                        f"{lbl}</span>"
                    )
                else:
                    css_cls = _TYPE_CSS.get(t, "")
                    parts.append(f'<span class="evt {css_cls}">{lbl}</span>')

            parts.append("</td>")

        parts.append("</tr>")

    parts.append("</table></div>")
    return "".join(parts)


# ============================================================
# Legend
# ============================================================

def _render_legend():
    st.markdown(
        """
        <div style="display:flex;flex-wrap:wrap;gap:6px;font-size:10.5px;align-items:center;margin-top:4px">
          <span style="background:#dc3545;color:#fff;padding:2px 7px;border-radius:3px">Regular Holiday</span>
          <span style="background:#fd7e14;color:#fff;padding:2px 7px;border-radius:3px">Special Non-Working</span>
          <span style="background:#cfe2ff;color:#084298;padding:2px 7px;border-radius:3px;border-left:4px solid #0d6efd">Draft Period</span>
          <span style="background:#fff3cd;color:#664d03;padding:2px 7px;border-radius:3px;border-left:4px solid #ffc107">Finalized Period</span>
          <span style="background:#d1e7dd;color:#0a3622;padding:2px 7px;border-radius:3px;border-left:4px solid #198754">Paid Period</span>
          <span style="background:#198754;color:#fff;padding:2px 7px;border-radius:3px">Pay Day</span>
          <span style="background:#6f42c1;color:#fff;padding:2px 7px;border-radius:3px">SSS</span>
          <span style="background:#0dcaf0;color:#000;padding:2px 7px;border-radius:3px">PhilHealth</span>
          <span style="background:#d63384;color:#fff;padding:2px 7px;border-radius:3px">Pag-IBIG</span>
          <span style="background:#343a40;color:#fff;padding:2px 7px;border-radius:3px">BIR</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Holiday reference table
# ============================================================

def _render_holiday_table(holidays: list[dict]):
    if not holidays:
        st.info("No holidays on record for this year.")
        return

    _TYPE_BADGE = {
        "regular": (
            "Regular",
            "#dc3545", "#fff",
        ),
        "special_non_working": (
            "Special Non-Working",
            "#fd7e14", "#fff",
        ),
        "special_working": (
            "Special Working",
            "#198754", "#fff",
        ),
    }

    rows_html = ""
    for h in holidays:
        label, bg, fg = _TYPE_BADGE.get(h["type"], (h["type"], "#6b7280", "#fff"))
        badge = (
            f'<span style="background:{bg};color:{fg};padding:2px 8px;'
            f'border-radius:4px;font-size:11px;font-weight:600;">{label}</span>'
        )
        obs = h.get("observed_date")
        orig_d = h["holiday_date"]
        if obs:
            date_str = (
                f'{obs.strftime("%b %d, %Y (%A)")}'
                f'<br><span style="color:#9ca3af;font-size:11px;text-decoration:line-through;">'
                f'orig: {orig_d.strftime("%b %d") if hasattr(orig_d, "strftime") else orig_d}</span>'
            )
        else:
            date_str = orig_d.strftime("%b %d, %Y (%A)") if hasattr(orig_d, "strftime") else str(orig_d)
        rows_html += (
            f'<tr>'
            f'<td style="padding:6px 10px;border-bottom:1px solid var(--gxp-border);'
            f'color:var(--gxp-text2);font-size:12px;white-space:nowrap;">{date_str}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid var(--gxp-border);'
            f'color:var(--gxp-text);font-size:13px;">{h["name"]}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid var(--gxp-border);">{badge}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr>'
        f'<th style="padding:6px 10px;text-align:left;font-size:11px;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.5px;color:var(--gxp-text2);">Date</th>'
        f'<th style="padding:6px 10px;text-align:left;font-size:11px;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.5px;color:var(--gxp-text2);">Holiday</th>'
        f'<th style="padding:6px 10px;text-align:left;font-size:11px;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.5px;color:var(--gxp-text2);">Type</th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table>',
        unsafe_allow_html=True,
    )


# ============================================================
# Main render
# ============================================================

def render():
    inject_css()

    _col_title, _col_clock = st.columns([3, 1])
    with _col_title:
        st.title("Calendar")
    with _col_clock:
        _stc.html(
            """
            <div id="gxp-clock-wrap" style="
                display:flex;flex-direction:column;align-items:flex-end;
                justify-content:center;height:80px;padding-right:4px;
                font-family:'Inter',system-ui,sans-serif;">
              <div id="gxp-time" style="
                font-size:22px;font-weight:700;letter-spacing:0.5px;
                color:#1e293b;line-height:1.1;"></div>
              <div id="gxp-date" style="
                font-size:11px;font-weight:400;color:#64748b;
                margin-top:3px;"></div>
            </div>
            <script>
            (function(){
              var timEl = document.getElementById('gxp-time');
              var datEl = document.getElementById('gxp-date');
              var days  = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
              var months= ['Jan','Feb','Mar','Apr','May','Jun',
                           'Jul','Aug','Sep','Oct','Nov','Dec'];
              function pad(n){return n<10?'0'+n:n;}
              function tick(){
                var n  = new Date();
                var h  = n.getHours(), m = n.getMinutes(), s = n.getSeconds();
                var ap = h >= 12 ? 'PM' : 'AM';
                h = h % 12 || 12;
                timEl.textContent = pad(h)+':'+pad(m)+':'+pad(s)+' '+ap;
                datEl.textContent = days[n.getDay()]+', '+months[n.getMonth()]+' '+n.getDate()+', '+n.getFullYear();
              }
              tick();
              setInterval(tick, 1000);
            })();
            </script>
            """,
            height=84,
            scrolling=False,
        )

    today = date.today()

    # ── Month navigator ───────────────────────────────────────
    if "cal_year" not in st.session_state:
        st.session_state.cal_year  = today.year
        st.session_state.cal_month = today.month

    col_prev, col_label, col_today, col_next = st.columns([1, 4, 1, 1])

    with col_prev:
        st.write("")
        if st.button("", width="stretch", icon=":material/chevron_left:", help="Previous month"):
            m, y = st.session_state.cal_month, st.session_state.cal_year
            if m == 1:
                st.session_state.cal_month, st.session_state.cal_year = 12, y - 1
            else:
                st.session_state.cal_month = m - 1
            st.rerun()

    with col_label:
        month_label = date(
            st.session_state.cal_year, st.session_state.cal_month, 1
        ).strftime("%B %Y")
        st.markdown(
            f"<h3 style='text-align:center;margin:6px 0'>{month_label}</h3>",
            unsafe_allow_html=True,
        )

    with col_today:
        st.write("")
        if st.button("Today", width="stretch"):
            st.session_state.cal_year  = today.year
            st.session_state.cal_month = today.month
            st.rerun()

    with col_next:
        st.write("")
        if st.button("", width="stretch", icon=":material/chevron_right:", help="Next month"):
            m, y = st.session_state.cal_month, st.session_state.cal_year
            if m == 12:
                st.session_state.cal_month, st.session_state.cal_year = 1, y + 1
            else:
                st.session_state.cal_month = m + 1
            st.rerun()

    year  = st.session_state.cal_year
    month = st.session_state.cal_month

    # ── Load data ─────────────────────────────────────────────
    db          = get_db()
    holidays    = _load_holidays(year)
    holiday_set = load_holiday_set(db, year=year, company_id=get_company_id())
    pay_periods = _load_pay_periods_overlapping(year, month)

    # Deadlines for the viewed month.
    # Passing the 1st of the month (day ≤ 20) causes get_remittance_deadlines
    # to compute deadlines for that same month — exactly what we want.
    deadlines = get_remittance_deadlines(date(year, month, 1), holiday_set)

    # ── Build event map ───────────────────────────────────────
    day_events = _build_day_events(year, month, holidays, pay_periods, deadlines)

    # ── Calendar grid ─────────────────────────────────────────
    st.markdown(
        _render_calendar_html(year, month, day_events),
        unsafe_allow_html=True,
    )

    # ── Legend ────────────────────────────────────────────────
    _render_legend()

    st.divider()

    # ── Holiday reference table ───────────────────────────────
    with st.expander(f"Philippine Holidays — {year}", expanded=False):
        # Allow switching year for the table (independent of the calendar month)
        col_yr, _ = st.columns([1, 3])
        with col_yr:
            table_year = st.selectbox(
                "Year",
                options=[year - 1, year, year + 1],
                index=1,
                key="holiday_table_year",
                label_visibility="collapsed",
            )
        table_holidays = _load_holidays(table_year) if table_year != year else holidays
        _render_holiday_table(table_holidays)
