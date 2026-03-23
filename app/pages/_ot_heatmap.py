"""
Workforce Analytics — attendance, overtime, late, and undertime analytics.

Tabs:
  1. OT Analytics    — Heatmaps + Top Contributors (with dept + shift)
  2. Late Monitoring  — Top late employees + per-employee 3-month calendar grid
  3. Undertime        — Top undertime employees + per-employee 3-month calendar grid
  4. Break Monitoring — Scheduled vs actual break analysis
"""

from __future__ import annotations

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
from calendar import monthrange

from app.db_helper import get_db, get_company_id
from app.styles import inject_css


# ── Constants ────────────────────────────────────────────────────────────────

_DOW_ORDER   = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]
_MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# M3 chart layout defaults
_CHART_LAYOUT = dict(
    font=dict(family="Plus Jakarta Sans, system-ui, sans-serif", size=12, color="#191c1d"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#f8f9fa",
    margin=dict(l=0, r=0, t=50, b=0),
)

# Avatar color palette (same 8-color as employees page)
_AVATAR_COLORS = [
    "#005bc1", "#7c3aed", "#0891b2", "#059669",
    "#d97706", "#dc2626", "#db2777", "#4f46e5",
]


# ── Data helpers ─────────────────────────────────────────────────────────────

def _load_ot_data(year: int) -> list[dict]:
    """Return all approved OT requests for the given year, company-scoped."""
    result = (
        get_db().table("overtime_requests")
        .select("id, employee_id, ot_date, hours, status")
        .eq("company_id", get_company_id())
        .eq("status", "approved")
        .gte("ot_date", f"{year}-01-01")
        .lte("ot_date", f"{year}-12-31")
        .execute()
    )
    return result.data or []


def _load_employee_map() -> dict:
    """
    Returns {employee_id: {name, department, shift_name}}.
    """
    db         = get_db()
    company_id = get_company_id()

    emps = (
        db.table("employees")
        .select("id, first_name, last_name, schedule_id")
        .eq("company_id", company_id)
        .execute()
    )

    # Load schedule names
    sched_map: dict[str, str] = {}
    try:
        scheds = db.table("schedules").select("id, name").eq("company_id", company_id).execute()
        sched_map = {s["id"]: s["name"] for s in (scheds.data or [])}
    except Exception:
        pass

    emp_map: dict = {}
    for e in (emps.data or []):
        sid = e.get("schedule_id")
        emp_map[e["id"]] = {
            "name":       f"{(e.get('last_name') or '').strip()}, {(e.get('first_name') or '').strip()}",
            "department": "",
            "shift":      sched_map.get(sid, "\u2014") if sid else "\u2014",
        }

    # Enrich with department
    try:
        profiles = db.table("employee_profiles").select("employee_id, department").execute()
        for p in (profiles.data or []):
            eid = p.get("employee_id")
            if eid and eid in emp_map and p.get("department"):
                emp_map[eid]["department"] = p["department"]
    except Exception:
        pass

    return emp_map


def _load_time_logs(start_date: date, end_date: date) -> list[dict]:
    """Return time_logs rows for the given date range, company-scoped."""
    result = (
        get_db().table("time_logs")
        .select(
            "employee_id, work_date, late_minutes, undertime_minutes, "
            "gross_hours, expected_hours, status, time_in, time_out, "
            "break_out, break_in, actual_break_minutes, overbreak_minutes"
        )
        .eq("company_id", get_company_id())
        .gte("work_date", str(start_date))
        .lte("work_date", str(end_date))
        .execute()
    )
    return result.data or []


# ── M3 UI Helpers ────────────────────────────────────────────────────────────

def _initials(name: str) -> str:
    parts = name.replace(",", " ").split()
    return "".join(p[0].upper() for p in parts[:2] if p)


def _metric_card(label: str, value: str, icon_bg: str, icon_color: str, icon: str) -> str:
    """Return HTML for an M3-styled metric card with icon badge."""
    return f'''
    <div style="background:#fff;padding:24px;border-radius:16px;
                box-shadow:0 1px 4px rgba(0,0,0,0.04);
                display:flex;align-items:center;justify-content:space-between;
                border:1px solid #e7e8e9;">
      <div>
        <p style="font-size:10px;font-weight:700;text-transform:uppercase;
                  letter-spacing:0.06em;color:#727784;margin:0 0 6px;">{label}</p>
        <p style="font-size:24px;font-weight:800;color:#191c1d;margin:0;
                  line-height:1.1;">{value}</p>
      </div>
      <div style="width:48px;height:48px;border-radius:14px;background:{icon_bg};
                  display:flex;align-items:center;justify-content:center;
                  font-size:24px;color:{icon_color};flex-shrink:0;">
        {icon}
      </div>
    </div>'''


def _render_metrics_row(metrics: list[tuple[str, str, str, str, str]]):
    """Render a row of M3 metric cards."""
    cols = st.columns(len(metrics))
    for i, (label, value, bg, fg, icon) in enumerate(metrics):
        cols[i].markdown(_metric_card(label, value, bg, fg, icon), unsafe_allow_html=True)


def _employee_row_html(
    rank: int, name: str, dept: str, shift: str,
    value_label: str, value: str,
    secondary_label: str = "", secondary_value: str = "",
    accent_color: str = "#005bc1",
    is_top: bool = False,
) -> str:
    """Render a single row in the Top Contributors table as M3-styled HTML."""
    initials = _initials(name)
    idx = rank % len(_AVATAR_COLORS)
    avatar_bg = _AVATAR_COLORS[idx] if not is_top else accent_color
    row_bg = f"background:rgba(0,91,193,0.04);" if is_top else ""
    rank_color = accent_color if is_top else "#727784"
    rank_weight = "800" if is_top else "700"

    secondary_html = ""
    if secondary_label and secondary_value:
        secondary_html = f'''
        <div style="text-align:right;">
          <div style="font-size:10px;color:#727784;text-transform:uppercase;
                      letter-spacing:0.04em;font-weight:600;">{secondary_label}</div>
          <div style="font-size:14px;font-weight:700;color:#191c1d;">{secondary_value}</div>
        </div>'''

    hover_cls = "gxp-wa-row-top" if is_top else "gxp-wa-row"
    return f'''
    <div class="{hover_cls}" style="display:grid;grid-template-columns:40px 1fr auto auto auto;
                align-items:center;gap:16px;padding:14px 16px;
                border-bottom:1px solid #f3f4f5;{row_bg}
                transition:background 0.12s ease;">
      <div style="font-size:14px;font-weight:{rank_weight};color:{rank_color};
                  text-align:center;">{rank:02d}</div>
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:32px;height:32px;border-radius:50%;background:{avatar_bg};
                    color:#fff;font-size:11px;font-weight:700;
                    display:flex;align-items:center;justify-content:center;
                    flex-shrink:0;">{initials}</div>
        <div>
          <div style="font-size:13px;font-weight:600;color:#191c1d;">{name}</div>
          <div style="font-size:11px;color:#727784;">{dept} &middot; {shift}</div>
        </div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:10px;color:#727784;text-transform:uppercase;
                    letter-spacing:0.04em;font-weight:600;">{value_label}</div>
        <div style="font-size:14px;font-weight:700;color:{accent_color};">{value}</div>
      </div>
      {secondary_html}
      <div></div>
    </div>'''


def _render_employee_table(
    title: str, rows_data: list[dict],
    value_key: str, value_label: str, value_fmt: str = "{:.1f} hrs",
    secondary_key: str = "", secondary_label: str = "", secondary_fmt: str = "",
    accent: str = "#005bc1",
):
    """Render an M3-styled employee ranking table."""
    st.markdown(
        f'<p style="font-size:18px;font-weight:800;color:#191c1d;margin:16px 0 8px;">{title}</p>',
        unsafe_allow_html=True,
    )

    if not rows_data:
        st.caption("No data available.")
        return

    # Header
    header_html = '''
    <div style="display:grid;grid-template-columns:40px 1fr auto auto auto;
                align-items:center;gap:16px;padding:8px 16px;
                border-bottom:2px solid #e7e8e9;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                  letter-spacing:0.06em;color:#727784;text-align:center;">#</div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                  letter-spacing:0.06em;color:#727784;">Employee</div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                  letter-spacing:0.06em;color:#727784;text-align:right;">''' + value_label + '''</div>'''

    if secondary_label:
        header_html += f'''
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                  letter-spacing:0.06em;color:#727784;text-align:right;">{secondary_label}</div>'''
    else:
        header_html += '<div></div>'

    header_html += '<div></div></div>'

    rows_html = ""
    for i, row in enumerate(rows_data):
        val = value_fmt.format(row.get(value_key, 0))
        sec_val = secondary_fmt.format(row.get(secondary_key, 0)) if secondary_key else ""
        rows_html += _employee_row_html(
            rank=i + 1,
            name=row.get("name", "Unknown"),
            dept=row.get("department", "\u2014"),
            shift=row.get("shift", "\u2014"),
            value_label=value_label,
            value=val,
            secondary_label=secondary_label if secondary_key else "",
            secondary_value=sec_val,
            accent_color=accent,
            is_top=(i == 0),
        )

    import streamlit.components.v1 as _stc
    full_html = f'''<style>
    .gxp-wa-row:hover {{ background: rgba(0,0,0,0.02) !important; }}
    .gxp-wa-row-top {{ background: rgba(0,91,193,0.04); }}
    .gxp-wa-row-top:hover {{ background: rgba(0,91,193,0.07) !important; }}
    </style>
    <div style="background:#fff;border-radius:16px;overflow:hidden;
                    box-shadow:0 1px 4px rgba(0,0,0,0.04);border:1px solid #e7e8e9;
                    font-family:'Plus Jakarta Sans',system-ui,sans-serif;">
    {header_html}{rows_html}</div>'''
    # Estimate height: header ~40px + rows ~48px each + padding
    est_h = 48 + len(rows_data) * 50 + 16
    _stc.html(full_html, height=est_h, scrolling=False)


# ── Page ─────────────────────────────────────────────────────────────────────

def render() -> None:
    inject_css()
    st.title("Workforce Analytics")
    st.caption("Overtime, attendance, late, and undertime patterns at a glance.")

    today        = date.today()
    current_year = today.year
    year_options = list(range(current_year, current_year - 4, -1))

    col_year, _ = st.columns([1, 4])
    with col_year:
        selected_year = st.selectbox("Year", year_options, index=0, key="wa_year")

    # ── Top-level tabs ────────────────────────────────────────────────────────
    tab_ot, tab_late, tab_ut, tab_brk = st.tabs([
        "OT Analytics",
        "Late Monitoring",
        "Undertime",
        "Break Monitoring",
    ])

    # =========================================================================
    # TAB 1 — OT Analytics
    # =========================================================================
    with tab_ot:
        ot_data = _load_ot_data(selected_year)
        emp_map = _load_employee_map()

        if not ot_data:
            st.info(
                f"No approved overtime requests found for **{selected_year}**. "
                "Patterns will appear here once OT requests are approved.",
                icon="\u2139\ufe0f"
            )
        else:
            df = pd.DataFrame(ot_data)
            df["ot_date"]      = pd.to_datetime(df["ot_date"])
            df["hours"]        = pd.to_numeric(df["hours"], errors="coerce").fillna(0)
            df["day_of_week"]  = df["ot_date"].dt.day_name()
            df["month_name"]   = df["ot_date"].dt.strftime("%b")
            df["month_num"]    = df["ot_date"].dt.month
            df["employee_name"] = df["employee_id"].map(
                lambda eid: emp_map.get(eid, {}).get("name", "Unknown")
            )
            df["department"]   = df["employee_id"].map(
                lambda eid: emp_map.get(eid, {}).get("department", "")
            )
            df["shift"]        = df["employee_id"].map(
                lambda eid: emp_map.get(eid, {}).get("shift", "\u2014")
            )

            # ── Metric cards ─────────────────────────────────────────────────
            total_hrs     = df["hours"].sum()
            peak_day      = df.groupby("day_of_week")["hours"].sum().idxmax()
            peak_month_nm = df.groupby("month_num")["hours"].sum().idxmax()
            peak_month    = _MONTH_ORDER[peak_month_nm - 1]
            n_emp_ot      = df["employee_id"].nunique()

            _render_metrics_row([
                ("Total OT Hours", f"{total_hrs:.0f} hrs",
                 "#d8e2ff", "#004494", "&#9200;"),
                ("Peak Day", peak_day,
                 "#ffdea0", "#795900", "&#128197;"),
                ("Peak Month", peak_month,
                 "#89fa9b", "#005320", "&#128200;"),
                ("Employees with OT", str(n_emp_ot),
                 "#e7e8e9", "#424753", "&#128101;"),
            ])

            st.write("")

            ot_sub1, ot_sub2, ot_sub3 = st.tabs([
                "Calendar Heat Map", "By Employee", "Day of Week"
            ])

            # ── OT sub-tab 1: Calendar Heat Map ──────────────────────────────
            with ot_sub1:
                pivot = (
                    df.groupby(["month_name", "day_of_week"])["hours"]
                    .sum().reset_index()
                    .pivot(index="month_name", columns="day_of_week", values="hours")
                    .fillna(0)
                )
                pivot = pivot.reindex(
                    index=[m for m in _MONTH_ORDER if m in pivot.index],
                    columns=[d for d in _DOW_ORDER  if d in pivot.columns],
                )
                fig1 = px.imshow(
                    pivot,
                    labels=dict(x="Day of Week", y="Month", color="OT Hours"),
                    color_continuous_scale=["#f3f4f5", "#adc6ff", "#3d89ff", "#005bc1"],
                    title=f"Approved OT Hours \u2014 Day \u00d7 Month  ({selected_year})",
                    text_auto=".1f", aspect="auto",
                )
                fig1.update_layout(height=420, **_CHART_LAYOUT,
                                   coloraxis_colorbar=dict(title="hrs"))
                fig1.update_xaxes(side="bottom")
                st.plotly_chart(fig1, use_container_width=True)

            # ── OT sub-tab 2: By Employee + Top Contributors ──────────────────
            with ot_sub2:
                emp_month = (
                    df.groupby(["employee_name", "month_name"])["hours"]
                    .sum().reset_index()
                    .pivot(index="employee_name", columns="month_name", values="hours")
                    .fillna(0)
                )
                emp_month = emp_month.reindex(
                    columns=[m for m in _MONTH_ORDER if m in emp_month.columns]
                )
                emp_month["_total"] = emp_month.sum(axis=1)
                emp_month = emp_month.sort_values("_total", ascending=False).drop(columns=["_total"])

                fig2 = px.imshow(
                    emp_month,
                    labels=dict(x="Month", y="Employee", color="OT Hours"),
                    color_continuous_scale=["#f3f4f5", "#adc6ff", "#3d89ff", "#005bc1"],
                    title=f"OT Hours per Employee  ({selected_year})",
                    text_auto=".1f", aspect="auto",
                )
                fig2.update_layout(
                    height=max(300, len(emp_month) * 35 + 120),
                    **_CHART_LAYOUT,
                    coloraxis_colorbar=dict(title="hrs"),
                )
                st.plotly_chart(fig2, use_container_width=True)

                # Top Contributors table
                top_agg = (
                    df.groupby(["employee_id", "employee_name", "department", "shift"])["hours"]
                    .sum().reset_index()
                    .sort_values("hours", ascending=False)
                    .head(15)
                    .reset_index(drop=True)
                )
                top_rows = []
                for _, r in top_agg.iterrows():
                    top_rows.append({
                        "name": r["employee_name"],
                        "department": r["department"] or "\u2014",
                        "shift": r["shift"],
                        "hours": r["hours"],
                    })

                _render_employee_table(
                    "Top OT Contributors", top_rows,
                    value_key="hours", value_label="Total OT Hrs",
                    value_fmt="{:.1f} hrs",
                    accent="#005bc1",
                )

            # ── OT sub-tab 3: Day of Week + Department breakdown ──────────────
            with ot_sub3:
                dow_df = (
                    df.groupby("day_of_week")["hours"].sum()
                    .reindex(_DOW_ORDER).fillna(0).reset_index()
                )
                dow_df.columns = ["Day", "Hours"]
                fig3 = px.bar(
                    dow_df, x="Day", y="Hours", color="Hours",
                    color_continuous_scale=["#adc6ff", "#3d89ff", "#005bc1"],
                    title=f"Total OT Hours by Day of Week  ({selected_year})",
                    labels={"Hours": "Total OT Hours"}, text_auto=".1f",
                )
                fig3.update_coloraxes(showscale=False)
                fig3.update_layout(height=400, **_CHART_LAYOUT, xaxis_title=None)
                fig3.update_traces(marker_line_width=0, marker_cornerradius=8)
                st.plotly_chart(fig3, use_container_width=True)

                has_dept = df["department"].ne("").any()
                if has_dept:
                    st.markdown(
                        '<p style="font-size:18px;font-weight:800;color:#191c1d;margin:16px 0 8px;">By Department</p>',
                        unsafe_allow_html=True,
                    )
                    dept_pivot = (
                        df[df["department"] != ""]
                        .groupby(["department", "day_of_week"])["hours"]
                        .sum().reset_index()
                        .pivot(index="department", columns="day_of_week", values="hours")
                        .fillna(0)
                    )
                    dept_pivot = dept_pivot.reindex(
                        columns=[d for d in _DOW_ORDER if d in dept_pivot.columns]
                    )
                    fig4 = px.imshow(
                        dept_pivot,
                        labels=dict(x="Day of Week", y="Department", color="OT Hours"),
                        color_continuous_scale=["#f3f4f5", "#c084fc", "#7c3aed"],
                        title="OT Hours by Department \u00d7 Day of Week",
                        text_auto=".1f", aspect="auto",
                    )
                    fig4.update_layout(
                        height=max(250, len(dept_pivot) * 50 + 120),
                        **_CHART_LAYOUT,
                    )
                    st.plotly_chart(fig4, use_container_width=True)

    # =========================================================================
    # TAB 2 — Late Monitoring
    # =========================================================================
    with tab_late:
        range_start = date(selected_year, 1, 1)
        range_end   = min(date(selected_year, 12, 31), today)
        logs_raw    = _load_time_logs(range_start, range_end)
        emp_map2    = _load_employee_map()

        late_rows = [r for r in logs_raw if (r.get("late_minutes") or 0) > 0]

        if not late_rows:
            st.info(f"No late records found for **{selected_year}**.", icon="\u2139\ufe0f")
        else:
            df_late = pd.DataFrame(late_rows)
            df_late["late_minutes"] = pd.to_numeric(df_late["late_minutes"], errors="coerce").fillna(0)
            df_late["employee_name"] = df_late["employee_id"].map(
                lambda eid: emp_map2.get(eid, {}).get("name", "Unknown")
            )
            df_late["department"] = df_late["employee_id"].map(
                lambda eid: emp_map2.get(eid, {}).get("department", "")
            )

            # ── Metric cards ─────────────────────────────────────────────────
            total_late_days = len(df_late)
            total_late_mins = int(df_late["late_minutes"].sum())
            n_late_emps     = df_late["employee_id"].nunique()
            avg_late        = round(df_late["late_minutes"].mean(), 1)

            _render_metrics_row([
                ("Total Late Incidents", str(total_late_days),
                 "#fee2e2", "#991b1b", "&#128680;"),
                ("Total Late Minutes", f"{total_late_mins:,} min",
                 "#fef3c7", "#92400e", "&#9201;"),
                ("Employees Affected", str(n_late_emps),
                 "#e7e8e9", "#424753", "&#128101;"),
                ("Avg Late / Incident", f"{avg_late} min",
                 "#dbeafe", "#1e40af", "&#128202;"),
            ])

            st.write("")

            # ── Interactive bar chart — click a bar to drill down ────────────
            agg = (
                df_late.groupby(["employee_id", "employee_name", "department"])
                .agg(count=("late_minutes", "count"), total_mins=("late_minutes", "sum"))
                .reset_index()
                .sort_values("total_mins", ascending=True)  # ascending for horizontal bar
            )
            agg["avg_mins"] = (agg["total_mins"] / agg["count"]).round(1)
            agg["bar_text"] = agg.apply(
                lambda r: f"{int(r['total_mins'])} min ({int(r['count'])}x)", axis=1
            )

            # ── Department aggregate ─────────────────────────────────────────
            dept_agg = (
                agg.groupby("department")
                .agg(total_mins=("total_mins", "sum"), count=("count", "sum"),
                     employees=("employee_id", "nunique"))
                .reset_index()
                .sort_values("total_mins", ascending=True)
            )
            dept_agg["bar_text"] = dept_agg.apply(
                lambda r: f"{int(r['total_mins'])} min ({int(r['count'])}x, {int(r['employees'])} emp)", axis=1
            )

            # Default department selection
            sel_dept = st.session_state.get("wa_late_dept")
            if sel_dept not in dept_agg["department"].values:
                sel_dept = dept_agg["department"].iloc[-1]  # top dept
                st.session_state.wa_late_dept = sel_dept

            # Filter employees by selected department
            agg_filtered = agg[agg["department"] == sel_dept].sort_values("total_mins", ascending=True)

            dept_chart_h = max(240, len(dept_agg) * 45 + 100)
            emp_chart_h  = max(240, len(agg_filtered) * 45 + 100)

            # ── Side-by-side: Department (left) → Employee (right) ───────────
            col_dept, col_emp = st.columns(2)

            with col_dept:
                dept_colors = [
                    "#dc2626" if d == sel_dept else "#fca5a5"
                    for d in dept_agg["department"]
                ]
                fig_dept = go.Figure(go.Bar(
                    x=dept_agg["total_mins"],
                    y=dept_agg["department"],
                    orientation="h",
                    text=dept_agg["bar_text"],
                    textposition="auto",
                    marker=dict(color=dept_colors, cornerradius=6),
                    hovertemplate="<b>%{y}</b><br>Total: %{x} min<extra></extra>",
                ))
                fig_dept.update_layout(
                    title="By Department (click to filter)",
                    height=max(dept_chart_h, emp_chart_h),
                    **_CHART_LAYOUT,
                    xaxis_title="Total Late Minutes",
                    yaxis_title=None,
                    showlegend=False,
                    bargap=0.25,
                )
                evt_dept = st.plotly_chart(
                    fig_dept, use_container_width=True,
                    key="late_dept_chart",
                    on_select="rerun",
                    selection_mode="points",
                )
                if evt_dept and evt_dept.selection and evt_dept.selection.get("points"):
                    ci = evt_dept.selection["points"][0].get("point_index")
                    if ci is not None and ci < len(dept_agg):
                        new_dept = dept_agg.iloc[ci]["department"]
                        if new_dept != sel_dept:
                            st.session_state.wa_late_dept = new_dept
                            st.rerun()

            with col_emp:
                # Color per employee (cycling palette) — shared between bar + calendar
                _EMP_COLORS = ["#2563eb", "#ea580c", "#d97706", "#0891b2",
                               "#7c3aed", "#db2777", "#0d9488", "#6366f1"]
                emp_color_map = {}      # eid → color
                emp_name_color_map = {} # name → color (for scatter plot)
                for i, (_, erow) in enumerate(agg_filtered.iterrows()):
                    c = _EMP_COLORS[i % len(_EMP_COLORS)]
                    emp_color_map[erow["employee_id"]] = c
                    emp_name_color_map[erow["employee_name"]] = c

                emp_colors = [emp_color_map[eid] for eid in agg_filtered["employee_id"]]

                # Highlight selected employee bar
                sel_late_eid = st.session_state.get("wa_late_emp")
                if sel_late_eid not in agg_filtered["employee_id"].values:
                    sel_late_eid = None  # no employee selected = show all full opacity

                bar_opacities = []
                for eid in agg_filtered["employee_id"]:
                    if sel_late_eid is None or eid == sel_late_eid:
                        bar_opacities.append(1.0)
                    else:
                        bar_opacities.append(0.25)

                fig_emp = go.Figure(go.Bar(
                    x=agg_filtered["total_mins"],
                    y=agg_filtered["employee_name"],
                    orientation="h",
                    text=agg_filtered["bar_text"],
                    textposition="auto",
                    marker=dict(color=emp_colors, cornerradius=6,
                                opacity=bar_opacities),
                    hovertemplate="<b>%{y}</b><br>Total: %{x} min<extra></extra>",
                    customdata=agg_filtered["employee_id"].values,
                ))
                fig_emp.update_layout(
                    title=f"Employees in {sel_dept}" + (f" \u2014 click to highlight" if sel_late_eid is None else ""),
                    height=max(dept_chart_h, emp_chart_h),
                    **_CHART_LAYOUT,
                    xaxis_title="Total Late Minutes",
                    yaxis_title=None,
                    showlegend=False,
                    bargap=0.25,
                )
                evt_emp = st.plotly_chart(
                    fig_emp, use_container_width=True,
                    key="late_emp_chart",
                    on_select="rerun",
                    selection_mode="points",
                )
                if evt_emp and evt_emp.selection and evt_emp.selection.get("points"):
                    ci = evt_emp.selection["points"][0].get("point_index")
                    if ci is not None and ci < len(agg_filtered):
                        new_eid = agg_filtered.iloc[ci]["employee_id"]
                        if new_eid == sel_late_eid:
                            # Clicking same bar again = deselect (show all)
                            st.session_state.wa_late_emp = None
                        else:
                            st.session_state.wa_late_emp = new_eid
                        st.rerun()

            # ── Detail panel ─────────────────────────────────────────────────
            dept_row = dept_agg[dept_agg["department"] == sel_dept].iloc[0]
            # Show employee detail if one is selected, otherwise department summary
            if sel_late_eid and sel_late_eid in agg_filtered["employee_id"].values:
                sel_emp_row = agg_filtered[agg_filtered["employee_id"] == sel_late_eid].iloc[0]
                sel_emp_name = sel_emp_row["employee_name"]
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #e7e8e9;border-radius:12px;'
                    f'padding:16px 20px;margin:8px 0 16px;box-shadow:0 1px 4px rgba(0,0,0,0.04);">'
                    f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">'
                    f'<span style="font-size:16px;font-weight:800;color:#191c1d;">{sel_emp_name}</span>'
                    f'<span style="background:#e0e7ff;color:#3730a3;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">{sel_dept}</span>'
                    f'<span style="background:#fee2e2;color:#991b1b;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">{int(sel_emp_row["count"])}x late</span>'
                    f'<span style="background:#fef3c7;color:#92400e;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">{int(sel_emp_row["total_mins"])} min total</span>'
                    f'<span style="background:#dbeafe;color:#1e40af;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">avg {sel_emp_row["avg_mins"]} min</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #e7e8e9;border-radius:12px;'
                    f'padding:16px 20px;margin:8px 0 16px;box-shadow:0 1px 4px rgba(0,0,0,0.04);">'
                    f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">'
                    f'<span style="font-size:16px;font-weight:800;color:#191c1d;">{sel_dept}</span>'
                    f'<span style="background:#fee2e2;color:#991b1b;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">{int(dept_row["count"])}x late incidents</span>'
                    f'<span style="background:#fef3c7;color:#92400e;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">{int(dept_row["total_mins"])} min total</span>'
                    f'<span style="background:#dbeafe;color:#1e40af;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">{int(dept_row["employees"])} employees</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

            # ── Drill-down calendar — ALL employees, selected one full opacity ─
            cal_end   = today
            cal_start = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
            dept_eids = agg_filtered["employee_id"].tolist()
            dept_logs = df_late[
                (df_late["employee_id"].isin(dept_eids)) &
                (df_late["work_date"] >= str(cal_start)) &
                (df_late["work_date"] <= str(cal_end))
            ]
            if not dept_logs.empty:
                cal_df = dept_logs.copy()
                cal_df["work_date"] = pd.to_datetime(cal_df["work_date"])
                cal_df["dow"]       = cal_df["work_date"].dt.day_name()
                cal_df["label"]     = cal_df["work_date"].dt.strftime("%b %d")

                # Build one trace per employee for individual opacity control
                sel_late_name = None
                if sel_late_eid:
                    match = agg_filtered[agg_filtered["employee_id"] == sel_late_eid]
                    if not match.empty:
                        sel_late_name = match.iloc[0]["employee_name"]

                # Sort by date for chronological x-axis
                cal_df = cal_df.sort_values("work_date")
                date_order = cal_df["label"].unique().tolist()

                cal_title = f"Late Pattern \u2014 {sel_dept}"
                if sel_late_name:
                    cal_title += f" (highlighting {sel_late_name})"
                cal_title += " (last 3 months)"

                fig_cal = go.Figure()
                for emp_name in cal_df["employee_name"].unique():
                    emp_data = cal_df[cal_df["employee_name"] == emp_name]
                    is_highlighted = (sel_late_name is None or emp_name == sel_late_name)
                    fig_cal.add_trace(go.Scatter(
                        x=emp_data["label"],
                        y=emp_data["dow"],
                        mode="markers+text",
                        name=emp_name,
                        text=emp_data["late_minutes"].astype(int).astype(str),
                        textposition="middle center",
                        textfont=dict(color="white", size=9),
                        marker=dict(
                            size=emp_data["late_minutes"].clip(lower=5) * 1.2 + 8,
                            color=emp_name_color_map.get(emp_name, "#6366f1"),
                            opacity=1.0 if is_highlighted else 0.15,
                            line=dict(width=1, color="rgba(255,255,255,0.5)"),
                        ),
                        hovertemplate=(
                            f"<b>{emp_name}</b><br>"
                            "Date: %{x}<br>"
                            "Late: %{text} min<br>"
                            "<extra></extra>"
                        ),
                    ))

                fig_cal.update_layout(
                    title=cal_title,
                    height=360, **_CHART_LAYOUT,
                    xaxis=dict(categoryorder="array", categoryarray=date_order),
                    yaxis=dict(categoryorder="array",
                               categoryarray=list(reversed(_DOW_ORDER))),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                xanchor="right", x=1, font=dict(size=10)),
                )
                st.plotly_chart(fig_cal, use_container_width=True,
                                key=f"late_cal_{sel_dept}_{sel_late_eid}")
            else:
                st.caption(f"No late records in the last 3 months for {sel_dept}.")

    # =========================================================================
    # TAB 3 — Undertime Monitoring
    # =========================================================================
    with tab_ut:
        range_start3 = date(selected_year, 1, 1)
        range_end3   = min(date(selected_year, 12, 31), today)
        logs_raw3    = _load_time_logs(range_start3, range_end3)
        emp_map3     = _load_employee_map()

        ut_rows = [r for r in logs_raw3 if (r.get("undertime_minutes") or 0) > 0]

        if not ut_rows:
            st.info(f"No undertime records found for **{selected_year}**.", icon="\u2139\ufe0f")
        else:
            df_ut = pd.DataFrame(ut_rows)
            df_ut["undertime_minutes"] = pd.to_numeric(df_ut["undertime_minutes"], errors="coerce").fillna(0)
            df_ut["employee_name"] = df_ut["employee_id"].map(
                lambda eid: emp_map3.get(eid, {}).get("name", "Unknown")
            )
            df_ut["department"] = df_ut["employee_id"].map(
                lambda eid: emp_map3.get(eid, {}).get("department", "")
            )

            total_ut_days = len(df_ut)
            total_ut_mins = int(df_ut["undertime_minutes"].sum())
            n_ut_emps     = df_ut["employee_id"].nunique()
            avg_ut        = round(df_ut["undertime_minutes"].mean(), 1)

            _render_metrics_row([
                ("Total UT Incidents", str(total_ut_days),
                 "#ffedd5", "#9a3412", "&#9888;"),
                ("Total UT Minutes", f"{total_ut_mins:,} min",
                 "#fef3c7", "#92400e", "&#9201;"),
                ("Employees Affected", str(n_ut_emps),
                 "#e7e8e9", "#424753", "&#128101;"),
                ("Avg UT / Incident", f"{avg_ut} min",
                 "#dbeafe", "#1e40af", "&#128202;"),
            ])

            st.write("")

            # ── Interactive bar chart — click a bar to drill down ────────────
            agg_ut = (
                df_ut.groupby(["employee_id", "employee_name", "department"])
                .agg(count=("undertime_minutes", "count"), total_mins=("undertime_minutes", "sum"))
                .reset_index()
                .sort_values("total_mins", ascending=True)
            )
            agg_ut["avg_mins"] = (agg_ut["total_mins"] / agg_ut["count"]).round(1)
            agg_ut["bar_text"] = agg_ut.apply(
                lambda r: f"{int(r['total_mins'])} min ({int(r['count'])}x)", axis=1
            )

            # ── Department aggregate ─────────────────────────────────────────
            dept_agg_ut = (
                agg_ut.groupby("department")
                .agg(total_mins=("total_mins", "sum"), count=("count", "sum"),
                     employees=("employee_id", "nunique"))
                .reset_index()
                .sort_values("total_mins", ascending=True)
            )
            dept_agg_ut["bar_text"] = dept_agg_ut.apply(
                lambda r: f"{int(r['total_mins'])} min ({int(r['count'])}x, {int(r['employees'])} emp)", axis=1
            )

            sel_ut_dept = st.session_state.get("wa_ut_dept")
            if sel_ut_dept not in dept_agg_ut["department"].values:
                sel_ut_dept = dept_agg_ut["department"].iloc[-1]
                st.session_state.wa_ut_dept = sel_ut_dept

            agg_ut_filtered = agg_ut[agg_ut["department"] == sel_ut_dept].sort_values("total_mins", ascending=True)

            dept_ut_h = max(240, len(dept_agg_ut) * 45 + 100)
            emp_ut_h  = max(240, len(agg_ut_filtered) * 45 + 100)

            _UT_EMP_COLORS = ["#2563eb", "#ea580c", "#d97706", "#0891b2",
                              "#7c3aed", "#db2777", "#0d9488", "#6366f1"]

            # ── Side-by-side: Department (left) → Employee (right) ───────────
            col_ut_dept, col_ut_emp = st.columns(2)

            with col_ut_dept:
                dept_colors_ut = [
                    "#d97706" if d == sel_ut_dept else "#fcd34d"
                    for d in dept_agg_ut["department"]
                ]
                fig_ut_dept = go.Figure(go.Bar(
                    x=dept_agg_ut["total_mins"],
                    y=dept_agg_ut["department"],
                    orientation="h",
                    text=dept_agg_ut["bar_text"],
                    textposition="auto",
                    marker=dict(color=dept_colors_ut, cornerradius=6),
                    hovertemplate="<b>%{y}</b><br>Total: %{x} min<extra></extra>",
                ))
                fig_ut_dept.update_layout(
                    title="By Department (click to filter)",
                    height=max(dept_ut_h, emp_ut_h),
                    **_CHART_LAYOUT,
                    xaxis_title="Total Undertime Minutes",
                    yaxis_title=None,
                    showlegend=False,
                    bargap=0.25,
                )
                evt_ut_dept = st.plotly_chart(
                    fig_ut_dept, use_container_width=True,
                    key="ut_dept_chart",
                    on_select="rerun",
                    selection_mode="points",
                )
                if evt_ut_dept and evt_ut_dept.selection and evt_ut_dept.selection.get("points"):
                    ci = evt_ut_dept.selection["points"][0].get("point_index")
                    if ci is not None and ci < len(dept_agg_ut):
                        new_dept = dept_agg_ut.iloc[ci]["department"]
                        if new_dept != sel_ut_dept:
                            st.session_state.wa_ut_dept = new_dept
                            st.rerun()

            with col_ut_emp:
                ut_emp_color_map = {}
                ut_emp_name_color_map = {}
                for i, (_, erow) in enumerate(agg_ut_filtered.iterrows()):
                    c = _UT_EMP_COLORS[i % len(_UT_EMP_COLORS)]
                    ut_emp_color_map[erow["employee_id"]] = c
                    ut_emp_name_color_map[erow["employee_name"]] = c
                ut_emp_colors = [ut_emp_color_map[eid] for eid in agg_ut_filtered["employee_id"]]

                sel_ut_eid = st.session_state.get("wa_ut_emp")
                if sel_ut_eid not in agg_ut_filtered["employee_id"].values:
                    sel_ut_eid = None

                ut_bar_opacities = []
                for eid in agg_ut_filtered["employee_id"]:
                    if sel_ut_eid is None or eid == sel_ut_eid:
                        ut_bar_opacities.append(1.0)
                    else:
                        ut_bar_opacities.append(0.25)

                fig_ut_emp = go.Figure(go.Bar(
                    x=agg_ut_filtered["total_mins"],
                    y=agg_ut_filtered["employee_name"],
                    orientation="h",
                    text=agg_ut_filtered["bar_text"],
                    textposition="auto",
                    marker=dict(color=ut_emp_colors, cornerradius=6,
                                opacity=ut_bar_opacities),
                    hovertemplate="<b>%{y}</b><br>Total: %{x} min<extra></extra>",
                ))
                fig_ut_emp.update_layout(
                    title=f"Employees in {sel_ut_dept}" + (" \u2014 click to highlight" if sel_ut_eid is None else ""),
                    height=max(dept_ut_h, emp_ut_h),
                    **_CHART_LAYOUT,
                    xaxis_title="Total Undertime Minutes",
                    yaxis_title=None,
                    showlegend=False,
                    bargap=0.25,
                )
                evt_ut_emp = st.plotly_chart(
                    fig_ut_emp, use_container_width=True,
                    key="ut_emp_chart",
                    on_select="rerun",
                    selection_mode="points",
                )
                if evt_ut_emp and evt_ut_emp.selection and evt_ut_emp.selection.get("points"):
                    ci = evt_ut_emp.selection["points"][0].get("point_index")
                    if ci is not None and ci < len(agg_ut_filtered):
                        new_eid = agg_ut_filtered.iloc[ci]["employee_id"]
                        if new_eid == sel_ut_eid:
                            st.session_state.wa_ut_emp = None
                        else:
                            st.session_state.wa_ut_emp = new_eid
                        st.rerun()

            # ── Detail panel ─────────────────────────────────────────────────
            dept_ut_row = dept_agg_ut[dept_agg_ut["department"] == sel_ut_dept].iloc[0]
            if sel_ut_eid and sel_ut_eid in agg_ut_filtered["employee_id"].values:
                sel_ut_emp_row = agg_ut_filtered[agg_ut_filtered["employee_id"] == sel_ut_eid].iloc[0]
                sel_ut_emp_name = sel_ut_emp_row["employee_name"]
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #e7e8e9;border-radius:12px;'
                    f'padding:16px 20px;margin:8px 0 16px;box-shadow:0 1px 4px rgba(0,0,0,0.04);">'
                    f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">'
                    f'<span style="font-size:16px;font-weight:800;color:#191c1d;">{sel_ut_emp_name}</span>'
                    f'<span style="background:#e0e7ff;color:#3730a3;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">{sel_ut_dept}</span>'
                    f'<span style="background:#ffedd5;color:#9a3412;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">{int(sel_ut_emp_row["count"])}x undertime</span>'
                    f'<span style="background:#fef3c7;color:#92400e;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">{int(sel_ut_emp_row["total_mins"])} min total</span>'
                    f'<span style="background:#dbeafe;color:#1e40af;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">avg {sel_ut_emp_row["avg_mins"]} min</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #e7e8e9;border-radius:12px;'
                    f'padding:16px 20px;margin:8px 0 16px;box-shadow:0 1px 4px rgba(0,0,0,0.04);">'
                    f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">'
                    f'<span style="font-size:16px;font-weight:800;color:#191c1d;">{sel_ut_dept}</span>'
                    f'<span style="background:#ffedd5;color:#9a3412;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">{int(dept_ut_row["count"])}x undertime incidents</span>'
                    f'<span style="background:#fef3c7;color:#92400e;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">{int(dept_ut_row["total_mins"])} min total</span>'
                    f'<span style="background:#dbeafe;color:#1e40af;padding:2px 10px;border-radius:9999px;'
                    f'font-size:11px;font-weight:700;">{int(dept_ut_row["employees"])} employees</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

            # ── Drill-down calendar — per-employee opacity ───────────────────
            cal_end   = today
            cal_start = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
            dept_ut_eids = agg_ut_filtered["employee_id"].tolist()
            dept_ut_logs = df_ut[
                (df_ut["employee_id"].isin(dept_ut_eids)) &
                (df_ut["work_date"] >= str(cal_start)) &
                (df_ut["work_date"] <= str(cal_end))
            ]
            if not dept_ut_logs.empty:
                cal_df = dept_ut_logs.copy()
                cal_df["work_date"] = pd.to_datetime(cal_df["work_date"])
                cal_df["dow"]   = cal_df["work_date"].dt.day_name()
                cal_df["label"] = cal_df["work_date"].dt.strftime("%b %d")

                cal_df = cal_df.sort_values("work_date")
                ut_date_order = cal_df["label"].unique().tolist()

                sel_ut_name = None
                if sel_ut_eid:
                    match = agg_ut_filtered[agg_ut_filtered["employee_id"] == sel_ut_eid]
                    if not match.empty:
                        sel_ut_name = match.iloc[0]["employee_name"]

                cal_ut_title = f"Undertime Pattern \u2014 {sel_ut_dept}"
                if sel_ut_name:
                    cal_ut_title += f" (highlighting {sel_ut_name})"
                cal_ut_title += " (last 3 months)"

                fig_ut_cal = go.Figure()
                for emp_name in cal_df["employee_name"].unique():
                    emp_data = cal_df[cal_df["employee_name"] == emp_name]
                    is_highlighted = (sel_ut_name is None or emp_name == sel_ut_name)
                    fig_ut_cal.add_trace(go.Scatter(
                        x=emp_data["label"],
                        y=emp_data["dow"],
                        mode="markers+text",
                        name=emp_name,
                        text=emp_data["undertime_minutes"].astype(int).astype(str),
                        textposition="middle center",
                        textfont=dict(color="white", size=9),
                        marker=dict(
                            size=emp_data["undertime_minutes"].clip(lower=5) * 1.2 + 8,
                            color=ut_emp_name_color_map.get(emp_name, "#6366f1"),
                            opacity=1.0 if is_highlighted else 0.15,
                            line=dict(width=1, color="rgba(255,255,255,0.5)"),
                        ),
                        hovertemplate=(
                            f"<b>{emp_name}</b><br>"
                            "Date: %{x}<br>"
                            "UT: %{text} min<br>"
                            "<extra></extra>"
                        ),
                    ))

                fig_ut_cal.update_layout(
                    title=cal_ut_title,
                    height=360, **_CHART_LAYOUT,
                    xaxis=dict(categoryorder="array", categoryarray=ut_date_order),
                    yaxis=dict(categoryorder="array",
                               categoryarray=list(reversed(_DOW_ORDER))),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                xanchor="right", x=1, font=dict(size=10)),
                )
                st.plotly_chart(fig_ut_cal, use_container_width=True,
                                key=f"ut_cal_{sel_ut_dept}_{sel_ut_eid}")
            else:
                st.caption(f"No undertime records in the last 3 months for {sel_ut_dept}.")

    # =========================================================================
    # TAB 4 — Break Monitoring
    # =========================================================================
    with tab_brk:
        st.info(
            "**Break Monitoring** tracks when employees clock out for break and clock back in. "
            "This requires break clock-out / clock-in to be logged via the Employee Portal. "
            "Once break times are recorded, this tab will show overbreak counts and minutes per employee.",
            icon="\u2615",
        )

        # Derive implied break utilization from existing time_logs data
        range_start4 = date(selected_year, 1, 1)
        range_end4   = min(date(selected_year, 12, 31), today)
        logs_raw4    = _load_time_logs(range_start4, range_end4)
        emp_map4     = _load_employee_map()

        # Load scheduled break_minutes via schedules join
        try:
            scheds_raw = (
                get_db().table("schedules")
                .select("id, name, break_minutes")
                .eq("company_id", get_company_id())
                .execute()
            ).data or []
            sched_break_map = {s["id"]: int(s.get("break_minutes", 60)) for s in scheds_raw}
        except Exception:
            sched_break_map = {}

        break_data = []
        has_real_break = False
        for r in logs_raw4:
            if not r.get("time_in") or not r.get("time_out"):
                continue
            try:
                from backend.dtr import _parse_time, _to_min
                if r.get("break_in") and r.get("actual_break_minutes") is not None:
                    actual_break_min = int(r["actual_break_minutes"] or 0)
                    overbreak_min    = int(r.get("overbreak_minutes") or 0)
                    has_real_break   = True
                else:
                    in_m  = _to_min(_parse_time(r["time_in"]))
                    out_m = _to_min(_parse_time(r["time_out"]))
                    if out_m < in_m:
                        out_m += 1440
                    gross_h = float(r.get("gross_hours") or 0)
                    span_m  = out_m - in_m
                    actual_break_min = max(0, span_m - int(gross_h * 60))
                    overbreak_min    = 0

                break_data.append({
                    "employee_id":    r["employee_id"],
                    "work_date":      r["work_date"],
                    "break_min":      actual_break_min,
                    "overbreak_min":  overbreak_min,
                    "is_real":        r.get("break_in") is not None,
                })
            except Exception:
                continue

        if break_data:
            df_brk = pd.DataFrame(break_data)
            df_brk["employee_name"] = df_brk["employee_id"].map(
                lambda eid: emp_map4.get(eid, {}).get("name", "Unknown")
            )
            agg_brk = (
                df_brk.groupby(["employee_id", "employee_name"])
                .agg(
                    days=("break_min", "count"),
                    total_break=("break_min", "sum"),
                    avg_break=("break_min", "mean"),
                    total_overbreak=("overbreak_min", "sum"),
                    real_days=("is_real", "sum"),
                )
                .reset_index()
                .sort_values("total_overbreak", ascending=False)
            )
            agg_brk["avg_break"]     = agg_brk["avg_break"].round(1)
            agg_brk["real_days"]     = agg_brk["real_days"].astype(int)

            # ── Metric cards ─────────────────────────────────────────────────
            total_days = int(agg_brk["days"].sum())
            total_overbreak = int(agg_brk["total_overbreak"].sum())
            avg_break_all = round(agg_brk["avg_break"].mean(), 1) if len(agg_brk) > 0 else 0
            n_brk_emps = len(agg_brk)

            _render_metrics_row([
                ("Days Logged", str(total_days),
                 "#dbeafe", "#1e40af", "&#128197;"),
                ("Total Overbreak", f"{total_overbreak} min",
                 "#fee2e2", "#991b1b", "&#9888;"),
                ("Avg Break Duration", f"{avg_break_all} min",
                 "#fef3c7", "#92400e", "&#9749;"),
                ("Employees", str(n_brk_emps),
                 "#e7e8e9", "#424753", "&#128101;"),
            ])

            st.write("")

            if has_real_break:
                st.caption(
                    "Real break times from portal clock-out/in where available; "
                    "implied break (span \u2212 gross hours) used for remaining rows."
                )
            else:
                st.caption(
                    "Implied break = total time at work minus computed gross hours. "
                    "Enable break clock-out/in in the portal for precise tracking."
                )

            # Build table rows
            brk_table_rows = []
            for _, row in agg_brk.iterrows():
                brk_table_rows.append({
                    "name": row["employee_name"],
                    "department": emp_map4.get(row["employee_id"], {}).get("department", "") or "\u2014",
                    "shift": f"{row['real_days']} portal days" if row["real_days"] > 0 else "implied",
                    "avg_break": row["avg_break"],
                    "total_overbreak": int(row["total_overbreak"]),
                })

            _render_employee_table(
                "Break Duration Summary", brk_table_rows,
                value_key="avg_break", value_label="Avg Break",
                value_fmt="{:.1f} min",
                secondary_key="total_overbreak", secondary_label="Overbreak",
                secondary_fmt="{:.0f} min",
                accent="#0891b2",
            )
        else:
            st.caption("No time log data yet for the selected year.")
