"""
Calendar View — Streamlit page.

Monthly grid showing:
- Pay period spans (draft / finalized / paid, color-coded)
- Philippine holidays (regular and special non-working)
- Government remittance deadlines (adjusted for weekends/holidays)
- Payment dates

Right sidebar: Upcoming events list with countdown badges.
Below the calendar: a collapsible Philippine Holiday reference table.
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

@st.cache_data(ttl=600, show_spinner=False)
def _load_holidays(year: int, _cid: str = "") -> list[dict]:
    """
    Return merged holiday list for the current company for a given year. Cached 10 min.
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
    overrides = {h["name"]: h for h in company_rows if h["name"] in national_names}
    customs   = [h for h in company_rows if h["name"] not in national_names]

    merged = []
    for h in national:
        merged.append(overrides.get(h["name"], h))
    merged.extend(customs)
    merged.sort(key=lambda h: h["holiday_date"] or date.min)
    return merged


@st.cache_data(ttl=120, show_spinner=False)
def _load_pay_periods_overlapping(year: int, month: int, _cid: str = "") -> list[dict]:
    """Return pay periods whose date range overlaps with the given month."""
    db     = get_db()
    first  = date(year, month, 1).isoformat()
    last   = date(year, month, _cal.monthrange(year, month)[1]).isoformat()
    result = (
        db.table("pay_periods")
        .select("*")
        .eq("company_id", get_company_id())
        .lte("period_start", last)
        .gte("period_end",   first)
        .order("period_start")
        .execute()
    )
    return result.data


# ============================================================
# Event builder
# ============================================================

_STATUS_BG     = {"draft": "#dbeafe", "reviewed": "#ede9fe", "finalized": "#fef3c7", "paid": "#d1fae5"}
_STATUS_FG     = {"draft": "#1e40af", "reviewed": "#5b21b6", "finalized": "#92400e", "paid": "#065f46"}
_STATUS_BORDER = {"draft": "#3b82f6", "reviewed": "#8b5cf6", "finalized": "#f59e0b", "paid": "#10b981"}


def _build_day_events(
    year: int,
    month: int,
    holidays: list[dict],
    pay_periods: list[dict],
    deadlines: list[dict],
) -> dict[date, list[dict]]:
    events: dict[date, list[dict]] = {}

    def add(d: date, evt: dict):
        events.setdefault(d, []).append(evt)

    # Holidays
    for h in holidays:
        obs = h.get("observed_date")
        effective_d = obs if obs else h["holiday_date"]
        if effective_d.year == year and effective_d.month == month:
            t   = "hol_reg" if h["type"] == "regular" else "hol_spec"
            name_short = h["name"][:18] + "\u2026" if len(h["name"]) > 18 else h["name"]
            lbl = (name_short + " (moved)") if obs else name_short
            add(effective_d, {"type": t, "label": lbl, "priority": 0})

    # Pay periods
    for p in pay_periods:
        p_start = date.fromisoformat(p["period_start"])
        p_end   = date.fromisoformat(p["period_end"])
        p_pay   = date.fromisoformat(p["payment_date"])
        status  = p["status"]
        bg      = _STATUS_BG.get(status, "#f3f4f6")
        fg      = _STATUS_FG.get(status, "#374151")
        border  = _STATUS_BORDER.get(status, "#9ca3af")

        d = p_start
        while d <= p_end:
            if d.year == year and d.month == month:
                if d == p_start:
                    lbl = f"Pay Start"
                elif d == p_end:
                    lbl = f"Pay End"
                else:
                    lbl = ""
                add(d, {
                    "type": "period_span", "label": lbl,
                    "bg": bg, "fg": fg, "border": border,
                    "status": status, "priority": 1,
                })
            d += timedelta(days=1)

        if p_pay.year == year and p_pay.month == month:
            add(p_pay, {
                "type": "payment",
                "label": "Pay Day",
                "priority": 2,
            })

    # Deadlines
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
            lbl   = f"{dl['agency']} Due"
            if dl["deadline"] != dl["raw_deadline"]:
                lbl += " (adj)"
            add(d, {"type": dtype, "label": lbl, "priority": 3})

    for d in events:
        events[d].sort(key=lambda e: e.get("priority", 9))

    return events


# ============================================================
# M3 Calendar CSS + HTML renderer
# ============================================================

_CALENDAR_CSS = """
<style>
.gxp-cal-wrap {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
}
.gxp-cal-grid {
    display: grid; grid-template-columns: repeat(7, 1fr);
    gap: 6px;
}
.gxp-cal-hdr {
    text-align: center; padding: 8px 2px;
    font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em;
    color: #424753;
}
.gxp-cal-cell {
    min-height: 90px; padding: 6px 8px;
    border-radius: 12px; display: flex;
    flex-direction: column; position: relative;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
    cursor: pointer; overflow: hidden;
    background: #ffffff;
    border: 1px solid #e7e8e9;
}
.gxp-cal-cell:hover {
    transform: scale(1.02);
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    z-index: 1;
}
.gxp-cal-cell.empty {
    background: #f3f4f5; border-color: transparent;
    cursor: default; opacity: 0.4;
}
.gxp-cal-cell.empty:hover { transform: none; box-shadow: none; }
.gxp-cal-cell.weekend { background: #f7f8fa; border-color: #edeeef; }
.gxp-cal-cell.hol-reg { background: #fef2f2; border-color: #fecaca; }
.gxp-cal-cell.hol-spec { background: #fffbeb; border-color: #fde68a; }
.gxp-cal-cell.in-period { background: #eff6ff; border-color: #bfdbfe; }
.gxp-cal-cell.in-period.hol-reg { background: #fef2f2; border-color: #fecaca; }
.gxp-cal-cell.in-period.hol-spec { background: #fffbeb; border-color: #fde68a; }
.gxp-cal-num {
    font-size: 12px; font-weight: 700; color: #191c1d;
    line-height: 1; margin-bottom: 4px;
}
.gxp-cal-cell.weekend .gxp-cal-num,
.gxp-cal-cell.empty .gxp-cal-num { color: #9ca3af; }
.gxp-cal-today {
    background: #005bc1; color: #fff !important; border-radius: 50%;
    width: 24px; height: 24px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 800;
}
.gxp-cal-evts { margin-top: auto; display: flex; flex-direction: column; gap: 2px; }
.gxp-cal-evt {
    font-size: 9px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.02em; padding: 1px 4px; border-radius: 4px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    line-height: 1.4;
}
.gxp-cal-evt.hol-reg { color: #dc2626; }
.gxp-cal-evt.hol-spec { color: #d97706; }
.gxp-cal-evt.payment { background: #10b981; color: #fff; }
.gxp-cal-evt.period { color: #1e40af; font-weight: 800; }
.gxp-cal-evt.deadline {
    display: flex; align-items: center; gap: 3px;
}
.gxp-cal-dot {
    width: 5px; height: 5px; border-radius: 50%;
    display: inline-block; flex-shrink: 0;
}
.gxp-cal-dot.sss { background: #7c3aed; }
.gxp-cal-dot.philhealth { background: #0891b2; }
.gxp-cal-dot.pagibig { background: #db2777; }
.gxp-cal-dot.bir { background: #dc2626; }
</style>
"""

_DOT_CLASS = {
    "deadline_sss": "sss",
    "deadline_philhealth": "philhealth",
    "deadline_pagibig": "pagibig",
    "deadline_bir": "bir",
}
_DEADLINE_COLOR = {
    "deadline_sss": "#7c3aed",
    "deadline_philhealth": "#0891b2",
    "deadline_pagibig": "#db2777",
    "deadline_bir": "#dc2626",
}


def _render_calendar_html(
    year: int, month: int, day_events: dict[date, list[dict]]
) -> str:
    today = date.today()
    weeks = _cal.monthcalendar(year, month)

    parts = [_CALENDAR_CSS, '<div class="gxp-cal-wrap">']

    # Weekday header
    parts.append('<div class="gxp-cal-grid" style="margin-bottom:2px;">')
    for h in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        parts.append(f'<div class="gxp-cal-hdr">{h}</div>')
    parts.append('</div>')

    # Day grid
    parts.append('<div class="gxp-cal-grid">')

    for week in weeks:
        for wi, day_num in enumerate(week):
            if day_num == 0:
                parts.append('<div class="gxp-cal-cell empty"></div>')
                continue

            d    = date(year, month, day_num)
            evts = day_events.get(d, [])

            is_weekend  = wi >= 5
            has_reg_hol = any(e["type"] == "hol_reg"  for e in evts)
            has_spec_hol = any(e["type"] == "hol_spec" for e in evts)
            in_period   = any(e["type"] == "period_span" for e in evts)

            cls_parts = ["gxp-cal-cell"]
            if has_reg_hol:
                cls_parts.append("hol-reg")
            elif has_spec_hol:
                cls_parts.append("hol-spec")
            elif is_weekend:
                cls_parts.append("weekend")

            if in_period and not has_reg_hol and not has_spec_hol:
                cls_parts.append("in-period")

            # Left accent border for pay period
            style = ""
            period_evts = [e for e in evts if e["type"] == "period_span"]
            if period_evts:
                style = f'border-left:3px solid {period_evts[0]["border"]};'

            parts.append(f'<div class="{" ".join(cls_parts)}" style="{style}">')

            # Day number
            if d == today:
                parts.append(f'<span class="gxp-cal-today">{day_num}</span>')
            else:
                parts.append(f'<span class="gxp-cal-num">{day_num}</span>')

            # Events area
            parts.append('<div class="gxp-cal-evts">')
            for e in evts:
                t   = e["type"]
                lbl = e["label"]
                if not lbl:
                    continue

                if t == "hol_reg":
                    parts.append(f'<span class="gxp-cal-evt hol-reg">{lbl}</span>')
                elif t == "hol_spec":
                    parts.append(f'<span class="gxp-cal-evt hol-spec">{lbl}</span>')
                elif t == "payment":
                    parts.append(f'<span class="gxp-cal-evt payment">{lbl}</span>')
                elif t == "period_span":
                    parts.append(f'<span class="gxp-cal-evt period">{lbl}</span>')
                elif t.startswith("deadline_"):
                    dot_cls = _DOT_CLASS.get(t, "bir")
                    dl_color = _DEADLINE_COLOR.get(t, "#dc2626")
                    parts.append(
                        f'<span class="gxp-cal-evt deadline">'
                        f'<span class="gxp-cal-dot {dot_cls}"></span>'
                        f'<span style="color:{dl_color};">{lbl}</span></span>'
                    )

            parts.append('</div>')  # evts
            parts.append('</div>')  # cell

    parts.append('</div>')  # grid
    parts.append('</div>')  # wrap
    return "".join(parts)


# ============================================================
# Legend
# ============================================================

def _render_legend():
    st.markdown(
        """
        <div style="display:flex;flex-wrap:wrap;gap:16px;font-size:11px;
                    align-items:center;margin:12px 0 4px;color:#424753;">
          <span style="display:flex;align-items:center;gap:4px;">
            <span style="width:20px;height:20px;border-radius:50%;background:#005bc1;
                         display:inline-flex;align-items:center;justify-content:center;
                         color:#fff;font-size:9px;font-weight:800;">22</span>
            Today
          </span>
          <span style="display:flex;align-items:center;gap:4px;">
            <span style="width:12px;height:12px;border-radius:3px;background:#eff6ff;
                         border:1px solid #bfdbfe;"></span>
            Pay Period
          </span>
          <span style="display:flex;align-items:center;gap:4px;">
            <span style="width:12px;height:12px;border-radius:3px;background:#fef2f2;
                         border:1px solid #fecaca;"></span>
            Regular Holiday
          </span>
          <span style="display:flex;align-items:center;gap:4px;">
            <span style="width:12px;height:12px;border-radius:3px;background:#fffbeb;
                         border:1px solid #fde68a;"></span>
            Special Holiday
          </span>
          <span style="display:flex;align-items:center;gap:4px;">
            <span style="width:12px;height:12px;border-radius:9999px;background:#10b981;"></span>
            Pay Day
          </span>
          <span style="display:flex;align-items:center;gap:4px;">
            <span style="width:6px;height:6px;border-radius:50%;background:#7c3aed;"></span>
            SSS
          </span>
          <span style="display:flex;align-items:center;gap:4px;">
            <span style="width:6px;height:6px;border-radius:50%;background:#0891b2;"></span>
            PhilHealth
          </span>
          <span style="display:flex;align-items:center;gap:4px;">
            <span style="width:6px;height:6px;border-radius:50%;background:#db2777;"></span>
            Pag-IBIG
          </span>
          <span style="display:flex;align-items:center;gap:4px;">
            <span style="width:6px;height:6px;border-radius:50%;background:#dc2626;"></span>
            BIR
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Upcoming Events sidebar
# ============================================================

_EVENT_BORDER_COLOR = {
    "payment":             "#10b981",
    "hol_reg":             "#f59e0b",
    "hol_spec":            "#f59e0b",
    "period_start":        "#3b82f6",
    "period_end":          "#3b82f6",
    "deadline_sss":        "#7c3aed",
    "deadline_philhealth": "#0891b2",
    "deadline_pagibig":    "#db2777",
    "deadline_bir":        "#dc2626",
}

_BADGE_COLORS = {
    "payment":             ("#d1fae5", "#065f46"),
    "hol_reg":             ("#fef3c7", "#92400e"),
    "hol_spec":            ("#fef3c7", "#92400e"),
    "period_start":        ("#dbeafe", "#1e40af"),
    "period_end":          ("#dbeafe", "#1e40af"),
    "deadline_sss":        ("#ede9fe", "#5b21b6"),
    "deadline_philhealth": ("#cffafe", "#155e75"),
    "deadline_pagibig":    ("#fce7f3", "#9d174d"),
    "deadline_bir":        ("#fee2e2", "#991b1b"),
}


def _build_upcoming_events(
    year: int, month: int,
    holidays: list[dict],
    pay_periods: list[dict],
    deadlines: list[dict],
) -> list[dict]:
    """Build a sorted list of upcoming events from today onward (next 60 days)."""
    today = date.today()
    end = today + timedelta(days=60)
    events = []

    # Pay period boundaries + pay days
    for p in pay_periods:
        p_start = date.fromisoformat(p["period_start"])
        p_end   = date.fromisoformat(p["period_end"])
        p_pay   = date.fromisoformat(p["payment_date"])
        status  = p["status"]

        if today <= p_start <= end:
            events.append({
                "date": p_start, "type": "period_start",
                "label": f"Pay Period Start ({status.title()})",
            })
        if today <= p_end <= end:
            events.append({
                "date": p_end, "type": "period_end",
                "label": f"Pay Period End ({status.title()})",
            })
        if today <= p_pay <= end:
            events.append({
                "date": p_pay, "type": "payment",
                "label": f"Pay Day ({status.title()})",
            })

    # Holidays
    for h in holidays:
        obs = h.get("observed_date")
        effective_d = obs if obs else h["holiday_date"]
        if effective_d and today <= effective_d <= end:
            t = "hol_reg" if h["type"] == "regular" else "hol_spec"
            events.append({
                "date": effective_d, "type": t,
                "label": h["name"],
            })

    # Deadlines
    _dl_type = {
        "SSS": "deadline_sss", "PhilHealth": "deadline_philhealth",
        "Pag-IBIG": "deadline_pagibig", "BIR": "deadline_bir",
    }
    for dl in deadlines:
        d = dl["deadline"]
        if today <= d <= end:
            events.append({
                "date": d,
                "type": _dl_type.get(dl["agency"], "deadline_bir"),
                "label": f"{dl['agency']} Remittance Due",
            })

    events.sort(key=lambda e: e["date"])
    return events[:8]  # Show at most 8


def _render_upcoming_events(events: list[dict]):
    """Render the upcoming events card in the right sidebar."""
    today = date.today()

    st.markdown(
        '<p style="font-size:18px;font-weight:800;color:#191c1d;margin:0 0 12px;">Upcoming Events</p>',
        unsafe_allow_html=True,
    )

    if not events:
        st.caption("No upcoming events in the next 60 days.")
        return

    cards_html = ""
    for evt in events:
        d = evt["date"]
        delta = (d - today).days
        if delta == 0:
            badge_text = "Today"
        elif delta == 1:
            badge_text = "Tomorrow"
        else:
            badge_text = f"in {delta} days"

        border_color = _EVENT_BORDER_COLOR.get(evt["type"], "#9ca3af")
        badge_bg, badge_fg = _BADGE_COLORS.get(evt["type"], ("#f3f4f6", "#374151"))

        date_label = d.strftime("%b %d")
        day_name = d.strftime("%a")

        cards_html += f'''
        <div style="position:relative;background:#f3f4f5;padding:12px 16px 12px 20px;
                    border-radius:12px;display:flex;align-items:flex-start;gap:12px;
                    transition:background 0.15s ease;">
          <div style="position:absolute;left:0;top:10px;bottom:10px;width:3px;
                      border-radius:2px;background:{border_color};"></div>
          <div style="flex:1;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">
              <span style="font-size:10px;font-weight:700;color:#424753;text-transform:uppercase;
                           letter-spacing:0.04em;">{date_label} ({day_name})</span>
              <span style="background:{badge_bg};color:{badge_fg};padding:2px 8px;border-radius:9999px;
                           font-size:9px;font-weight:800;text-transform:uppercase;
                           letter-spacing:0.03em;">{badge_text}</span>
            </div>
            <p style="font-size:13px;font-weight:600;color:#191c1d;margin:0;line-height:1.3;">
              {evt["label"]}
            </p>
          </div>
        </div>'''

    st.markdown(
        f'<div style="display:flex;flex-direction:column;gap:8px;">{cards_html}</div>',
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
        "regular":             ("Regular",             "#dc2626", "#fff"),
        "special_non_working": ("Special Non-Working", "#d97706", "#fff"),
        "special_working":     ("Special Working",     "#10b981", "#fff"),
    }

    rows_html = ""
    for h in holidays:
        label, bg, fg = _TYPE_BADGE.get(h["type"], (h["type"], "#6b7280", "#fff"))
        badge = (
            f'<span style="background:{bg};color:{fg};padding:2px 10px;'
            f'border-radius:9999px;font-size:10px;font-weight:700;">{label}</span>'
        )
        obs = h.get("observed_date")
        orig_d = h["holiday_date"]
        if obs:
            date_str = (
                f'{obs.strftime("%b %d, %Y (%A)")}'
                f'<br><span style="color:#9ca3af;font-size:10px;text-decoration:line-through;">'
                f'orig: {orig_d.strftime("%b %d") if hasattr(orig_d, "strftime") else orig_d}</span>'
            )
        else:
            date_str = orig_d.strftime("%b %d, %Y (%A)") if hasattr(orig_d, "strftime") else str(orig_d)
        rows_html += (
            f'<tr style="transition:background 0.12s ease;"'
            f' onmouseenter="this.style.background=\'rgba(0,0,0,0.02)\'"'
            f' onmouseleave="this.style.background=\'\'">'
            f'<td style="padding:8px 12px;border-bottom:1px solid #e7e8e9;'
            f'color:#424753;font-size:12px;white-space:nowrap;">{date_str}</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid #e7e8e9;'
            f'color:#191c1d;font-size:13px;font-weight:500;">{h["name"]}</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid #e7e8e9;">{badge}</td>'
            f'</tr>'
        )

    st.markdown(
        f'''<div style="background:#fff;border-radius:12px;padding:4px 0;
                        box-shadow:0 1px 4px rgba(0,0,0,0.04);overflow:hidden;">
        <table style="width:100%;border-collapse:collapse;">
        <thead><tr style="background:#f8f9fa;">
        <th style="padding:8px 12px;text-align:left;font-size:10px;font-weight:700;
            text-transform:uppercase;letter-spacing:.06em;color:#424753;">Date</th>
        <th style="padding:8px 12px;text-align:left;font-size:10px;font-weight:700;
            text-transform:uppercase;letter-spacing:.06em;color:#424753;">Holiday</th>
        <th style="padding:8px 12px;text-align:left;font-size:10px;font-weight:700;
            text-transform:uppercase;letter-spacing:.06em;color:#424753;">Type</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
        </table></div>''',
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
                font-family:'Plus Jakarta Sans',system-ui,sans-serif;">
              <div id="gxp-time" style="
                font-size:22px;font-weight:700;letter-spacing:0.5px;
                color:#191c1d;line-height:1.1;"></div>
              <div id="gxp-date" style="
                font-size:11px;font-weight:400;color:#424753;
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
        if st.button("◀", width="stretch", help="Previous month"):
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
            f"<h3 style='text-align:center;margin:6px 0;font-weight:800;color:#191c1d;'>{month_label}</h3>",
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
        if st.button("▶", width="stretch", help="Next month"):
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

    deadlines = get_remittance_deadlines(date(year, month, 1), holiday_set)

    # Also load next month's data for upcoming events
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    next_holidays = _load_holidays(next_year) if next_year != year else holidays
    next_pay_periods = _load_pay_periods_overlapping(next_year, next_month)
    next_holiday_set = load_holiday_set(db, year=next_year, company_id=get_company_id()) if next_year != year else holiday_set
    next_deadlines = get_remittance_deadlines(date(next_year, next_month, 1), next_holiday_set)

    # ── Build event map ───────────────────────────────────────
    day_events = _build_day_events(year, month, holidays, pay_periods, deadlines)

    # ── Two-column layout: Calendar (left) + Upcoming Events (right) ──
    col_cal, col_upcoming = st.columns([7, 3])

    with col_cal:
        # Calendar grid
        st.markdown(
            _render_calendar_html(year, month, day_events),
            unsafe_allow_html=True,
        )

        # Legend
        _render_legend()

    with col_upcoming:
        upcoming = _build_upcoming_events(
            year, month,
            holidays + next_holidays,
            pay_periods + next_pay_periods,
            deadlines + next_deadlines,
        )
        _render_upcoming_events(upcoming)

    st.divider()

    # ── Holiday reference table ───────────────────────────────
    with st.expander(f"Philippine Holidays — {year}", expanded=False):
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
