"""
Attendance & DTR — Admin page (Phase 4B)

Three tabs:
  📅 Daily Entry      — select a date, enter time-in/out for all employees
  📊 Attendance Summary — per-employee summary across a date range
  🔧 Corrections       — review and approve/reject employee DTR correction requests
"""

import streamlit as st
from datetime import date, datetime, time, timedelta, timezone
from app.db_helper import get_db, get_company_id, log_action
from app.styles import inject_css
from backend.dtr import (
    compute_dtr, compute_nsd_hours, resolve_schedule_for_date, schedule_expected_hours,
    nearest_location, haversine_distance_m, _parse_time,
)


# ============================================================
# Database helpers
# ============================================================

def _load_employees() -> list[dict]:
    return (
        get_db().table("employees")
        .select("id, employee_no, first_name, last_name, position, schedule_id")
        .eq("company_id", get_company_id())
        .eq("is_active", True)
        .order("last_name")
        .execute()
    ).data or []


def _load_schedules() -> dict:
    rows = (
        get_db().table("schedules")
        .select("*")
        .eq("company_id", get_company_id())
        .execute()
    ).data or []
    return {r["id"]: r for r in rows}


def _load_overrides_for_date(work_date: date) -> dict:
    rows = (
        get_db().table("schedule_overrides")
        .select("*")
        .eq("company_id", get_company_id())
        .eq("override_date", str(work_date))
        .execute()
    ).data or []
    return {(r["employee_id"], str(work_date)): r for r in rows}


def _load_time_logs_for_date(work_date: date) -> dict:
    rows = (
        get_db().table("time_logs")
        .select("*")
        .eq("company_id", get_company_id())
        .eq("work_date", str(work_date))
        .execute()
    ).data or []
    return {r["employee_id"]: r for r in rows}


def _load_time_logs_range(start: date, end: date) -> list[dict]:
    return (
        get_db().table("time_logs")
        .select("*")
        .eq("company_id", get_company_id())
        .gte("work_date", str(start))
        .lte("work_date", str(end))
        .execute()
    ).data or []


def _load_employee_profiles() -> dict:
    """Returns {employee_id: department}"""
    rows = (
        get_db().table("employee_profiles")
        .select("employee_id, department")
        .eq("company_id", get_company_id())
        .execute()
    ).data or []
    return {r["employee_id"]: (r.get("department") or "") for r in rows}


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


def _upsert_time_log(row: dict):
    """Insert or update a time_log row. Uses UNIQUE(employee_id, work_date)."""
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


def _load_corrections(status_filter: str = "pending") -> list[dict]:
    q = (
        get_db().table("dtr_corrections")
        .select("*, employees(first_name, last_name, employee_no)")
        .eq("company_id", get_company_id())
        .order("created_at", desc=True)
    )
    if status_filter != "all":
        q = q.eq("status", status_filter)
    return q.execute().data or []


def _update_correction(corr_id: str, status: str, admin_notes: str):
    get_db().table("dtr_corrections").update({
        "status": status,
        "admin_notes": admin_notes,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", corr_id).execute()


def _load_monthly_metrics() -> dict:
    """Compute attendance KPIs for the current calendar month."""
    today = date.today()
    month_start = today.replace(day=1)
    rows = (
        get_db().table("time_logs")
        .select("status, late_minutes, nsd_hours")
        .eq("company_id", get_company_id())
        .gte("work_date", str(month_start))
        .lte("work_date", str(today))
        .execute()
    ).data or []

    total       = len(rows)
    present     = sum(1 for r in rows if r.get("status") in ("present", "late", "half_day"))
    late_count  = sum(1 for r in rows if (r.get("late_minutes") or 0) > 0)
    nsd_total   = sum(float(r.get("nsd_hours") or 0) for r in rows)
    rate        = round(present / total * 100) if total else 0
    return {"rate": rate, "late": late_count, "nsd": nsd_total}


# ============================================================
# Helpers
# ============================================================

def _employee_display_name(emp: dict) -> str:
    return f"{emp['last_name']}, {emp['first_name']}"


_AVATAR_COLORS = [
    ("#005bc1","#d8e2ff"), ("#795900","#ffdea0"), ("#005320","#89fa9b"),
    ("#6a3b9c","#e8daef"), ("#b5470f","#fde8d0"), ("#006874","#cff4f8"),
    ("#7c4f00","#ffe8b0"), ("#444444","#e1e3e4"),
]

def _dtr_avatar(name: str, idx: int = 0, size: int = 34) -> str:
    initials = "".join(p[0].upper() for p in name.split()[:2] if p)
    fg, bg = _AVATAR_COLORS[idx % len(_AVATAR_COLORS)]
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
        f'background:{bg};color:{fg};display:inline-flex;align-items:center;'
        f'justify-content:center;font-size:{size//3}px;font-weight:700;'
        f'flex-shrink:0;margin-right:6px;">{initials}</div>'
    )

def _status_html(status: str) -> str:
    mapping = {
        "present":     ("✓",  "#005320", "#89fa9b"),
        "half_day":    ("½",  "#795900", "#ffdea0"),
        "absent":      ("✗",  "#5a6062", "#e7e8e9"),
        "on_leave":    ("🏖", "#004494", "#d8e2ff"),
        "holiday":     ("🎉", "#004494", "#d8e2ff"),
        "rest_day":    ("🛏", "#424753", "#e1e3e4"),
        "no_schedule": ("—",  "#424753", "#e1e3e4"),
        "late":        ("⏰", "#795900", "#ffdea0"),
    }
    icon, color, bg = mapping.get(status, ("?", "#424753", "#e1e3e4"))
    label = status.replace("_", " ").title()
    return (
        f'<span style="background:{bg};color:{color};padding:3px 10px;'
        f'border-radius:9999px;font-size:11px;font-weight:700;'
        f'display:inline-flex;align-items:center;gap:4px;white-space:nowrap;">'
        f'{icon} {label}</span>'
    )


def _fmt_time(t) -> str:
    if t is None:
        return "—"
    if isinstance(t, str):
        return t[:5]
    return t.strftime("%H:%M")


def _fmt_mins(m: int) -> str:
    if not m:
        return "—"
    h, rem = divmod(m, 60)
    return f"{h}h {rem}m" if h else f"{rem}m"


# ============================================================
# Tab 1 — Daily Entry
# ============================================================

def _render_daily_entry():
    # ── Persistent save message (survives st.rerun) ───────────
    if "dtr_save_msg" in st.session_state:
        kind, msg = st.session_state.pop("dtr_save_msg")
        if kind == "success":
            st.success(msg)
        elif kind == "info":
            st.info(msg)
        else:
            st.error(msg)

    # ── Date navigation ──────────────────────────────────────
    # on_click sets the key BEFORE the next render cycle, so the
    # date_input widget picks up the new value without conflict.
    if "dtr_date_picker" not in st.session_state:
        st.session_state["dtr_date_picker"] = date.today()

    def _jump_today():
        st.session_state["dtr_date_picker"] = date.today()

    col_date, col_today, col_spacer, col_save = st.columns([2, 1, 4, 1])
    with col_date:
        work_date = st.date_input(
            "Date",
            key="dtr_date_picker",
            label_visibility="collapsed",
        )
    with col_today:
        st.button("Today", key="dtr_today", help="Jump to today", on_click=_jump_today)
    with col_save:
        save_all_top = st.button("Save All", type="primary", key="dtr_save_all_top", width="stretch")

    st.caption(f"**{work_date.strftime('%A, %B %d, %Y')}**")

    # ── Load data ─────────────────────────────────────────────
    employees = _load_employees()
    schedules = _load_schedules()
    overrides = _load_overrides_for_date(work_date)
    existing  = _load_time_logs_for_date(work_date)

    if not employees:
        st.info("No active employees found.")
        return

    profiles = _load_employee_profiles()   # {employee_id: department}
    for emp in employees:
        emp["department"] = profiles.get(emp["id"], "")

    # ── Filter bar ────────────────────────────────────────────
    all_positions = sorted({(e.get("position") or "").strip() for e in employees} - {""})
    all_depts     = sorted({(e.get("department") or "").strip() for e in employees} - {""})
    _dept_names_structured = _load_dept_names_from_table()
    if _dept_names_structured:
        all_depts = _dept_names_structured
    # ── Collapsible filter bar ────────────────────────────────
    with st.expander("Filters", expanded=False):
        fcol, _ = st.columns([3, 2])
        with fcol:
            de_sel_dept = st.multiselect("Department", all_depts,     key="de_f_dept", placeholder="All departments")
            de_sel_pos  = st.multiselect("Position",   all_positions, key="de_f_pos",  placeholder="All positions")
            de_search   = st.text_input("Employee",    placeholder="Name or employee no…",
                                        label_visibility="visible", key="de_search")

    def _de_match(emp):
        if de_search:
            q = de_search.lower()
            name = f"{emp['last_name']} {emp['first_name']}".lower()
            if q not in name and q not in (emp.get("employee_no") or "").lower():
                return False
        if de_sel_pos  and (emp.get("position") or "") not in de_sel_pos:
            return False
        if de_sel_dept and (emp.get("department") or "") not in de_sel_dept:
            return False
        return True

    # ── Build per-employee rows ───────────────────────────────
    # Each entry: {emp, sched, existing_log, computed_result}
    entries = []
    for emp in employees:
        if not _de_match(emp):
            continue
        sched = resolve_schedule_for_date(emp, schedules, overrides, work_date)
        log   = existing.get(emp["id"])
        entries.append({"emp": emp, "sched": sched, "log": log})

    st.divider()

    # ── Column headers ────────────────────────────────────────
    cols_w = [2.2, 1.8, 1.3, 1.3, 1, 1, 1, 1.5]
    hdr = st.columns(cols_w)
    for c, lbl in zip(hdr, ["Employee", "Shift", "Time In", "Time Out", "Late (m)", "UT (m)", "OT", "Status"]):
        c.markdown(f'<span style="font-size:11px;font-weight:700;color:#5a6062;'
                   f'text-transform:uppercase;letter-spacing:0.08em;">{lbl}</span>',
                   unsafe_allow_html=True)

    # ── Per-employee rows ─────────────────────────────────────
    new_logs = {}   # employee_id → dict to upsert on Save All

    for i_entry, entry in enumerate(entries):
        emp   = entry["emp"]
        sched = entry["sched"]
        log   = entry["log"]
        eid   = emp["id"]
        name  = _employee_display_name(emp)
        avatar_html = _dtr_avatar(name, i_entry)

        # If rest day or no schedule — show greyed row
        if sched is None:
            row = st.columns(cols_w)
            row[0].markdown(
                f'<div style="display:flex;align-items:center;gap:6px;opacity:0.45;">'
                f'{avatar_html}'
                f'<div><div style="font-size:13px;font-weight:600;">{name}</div>'
                f'<div style="font-size:11px;color:#727784;">{emp.get("employee_no","")}</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            row[1].caption("—")
            row[2].text("—"); row[3].text("—")
            row[4].text("—"); row[5].text("—"); row[6].text("—")
            row[7].markdown(_status_html("rest_day"), unsafe_allow_html=True)
            continue

        # Parse existing times
        existing_in  = _parse_time(log["time_in"])  if log and log.get("time_in")  else None
        existing_out = _parse_time(log["time_out"]) if log and log.get("time_out") else None

        row = st.columns(cols_w)
        row[0].markdown(
            f'<div style="display:flex;align-items:center;gap:6px;">'
            f'{avatar_html}'
            f'<div><div style="font-size:13px;font-weight:600;">{name}</div>'
            f'<div style="font-size:11px;color:#727784;">{emp.get("employee_no","")}</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Shift pill (col 1)
        sched_name = sched.get("name", "—") if sched else "—"
        _s_start   = (sched.get("start_time") or "")[:5]
        _s_end     = (sched.get("end_time")   or "")[:5]
        shift_label = f"{_s_start}–{_s_end}" if _s_start else sched_name
        row[1].markdown(
            f'<span style="background:#e7e8e9;color:#424753;padding:3px 10px;'
            f'border-radius:9999px;font-size:11px;font-weight:600;">{shift_label}</span>',
            unsafe_allow_html=True,
        )

        with row[2]:
            t_in = st.time_input("In", value=existing_in or time(8, 0),
                                 key=f"dtr_in_{eid}", label_visibility="collapsed")
        with row[3]:
            t_out = st.time_input("Out", value=existing_out or time(17, 0),
                                  key=f"dtr_out_{eid}", label_visibility="collapsed")

        # Real-time DTR computation
        exp_hours    = schedule_expected_hours(sched)
        exp_start    = _parse_time(sched["start_time"])
        exp_end      = _parse_time(sched["end_time"])
        break_min    = int(sched.get("break_minutes", 60))
        is_overnight = bool(sched.get("is_overnight", False))

        # Only compute if user has actual times (not just defaults)
        has_entry = (log is not None) or (
            st.session_state.get(f"dtr_in_{eid}") is not None
        )
        if has_entry or log:
            result = compute_dtr(t_in, t_out, exp_start, exp_end,
                                  exp_hours, break_min, is_overnight)
            _late = result.late_minutes
            _ut   = result.undertime_minutes
            row[4].markdown(
                f'<span style="color:{"#ba1a1a" if _late else "#727784"};font-weight:{"700" if _late else "400"};">'
                f'{_fmt_mins(_late) if _late else "—"}</span>',
                unsafe_allow_html=True,
            )
            row[5].markdown(
                f'<span style="color:{"#ba1a1a" if _ut else "#727784"};font-weight:{"700" if _ut else "400"};">'
                f'{_fmt_mins(_ut) if _ut else "—"}</span>',
                unsafe_allow_html=True,
            )
            row[6].markdown(
                f'<span style="color:{"#005bc1" if result.ot_hours else "#727784"};font-weight:{"700" if result.ot_hours else "400"};">'
                f'{f"{result.ot_hours:.1f}h" if result.ot_hours else "—"}</span>',
                unsafe_allow_html=True,
            )
            row[7].markdown(_status_html(result.status), unsafe_allow_html=True)
        else:
            row[4].markdown('<span style="color:#727784;">—</span>', unsafe_allow_html=True)
            row[5].markdown('<span style="color:#727784;">—</span>', unsafe_allow_html=True)
            row[6].markdown('<span style="color:#727784;">—</span>', unsafe_allow_html=True)
            row[7].markdown(_status_html("absent"), unsafe_allow_html=True)
            result = None

        # Stage for bulk save
        if result:
            new_logs[eid] = {
                "employee_id":       eid,
                "work_date":         str(work_date),
                "schedule_id":       sched["id"],
                "expected_start":    str(exp_start),
                "expected_end":      str(exp_end),
                "expected_hours":    exp_hours,
                "time_in":           str(t_in),
                "time_out":          str(t_out),
                "time_in_method":    "manual",
                "time_out_method":   "manual",
                "gross_hours":       result.gross_hours,
                "late_minutes":      result.late_minutes,
                "undertime_minutes": result.undertime_minutes,
                "ot_hours":          result.ot_hours,
                "nsd_hours":         result.nsd_hours,
                "status":            result.status,
            }

    # ── Save All button (below table) ────────────────────────
    st.divider()
    sa1, _ = st.columns([1.5, 6.5])
    with sa1:
        save_all = st.button("Save All", type="primary", key="dtr_save_all", width="stretch")

    if save_all or save_all_top:
        saved = 0
        errors = []
        for eid, row_data in new_logs.items():
            try:
                _upsert_time_log(row_data)
                saved += 1
            except Exception as ex:
                errors.append(str(ex))
        if errors:
            st.session_state["dtr_save_msg"] = (
                "error",
                f"Saved {saved} rows with {len(errors)} error(s): {errors[0]}",
            )
        else:
            log_action("batch_saved", "time_logs", get_company_id(),
                       f"{work_date} — {saved} records")
            label = work_date.strftime('%A, %B %d, %Y')
            st.session_state["dtr_save_msg"] = (
                "success",
                f"Saved {saved} attendance record(s) for **{label}**.",
            )
        st.rerun()


# ============================================================
# Tab 2 — Attendance Summary
# ============================================================

def _render_summary():
    today = date.today()
    month_start = today.replace(day=1)

    # Range picker — first click sets "from", second click sets "to"
    date_range = st.date_input(
        "Select date range",
        value=(month_start, today),
        key="dtr_sum_range",
        help="Click a start date, then click an end date",
    )
    # date_input returns a tuple when a range is selected; guard for partial picks
    if not isinstance(date_range, (list, tuple)) or len(date_range) < 2:
        st.info("Pick a start and end date to view the summary.")
        return
    range_start, range_end = date_range[0], date_range[1]

    if range_start > range_end:
        st.error("Start date must be before end date.")
        return

    employees = _load_employees()
    profiles  = _load_employee_profiles()
    logs      = _load_time_logs_range(range_start, range_end)

    if not employees:
        st.info("No active employees found.")
        return

    # Merge department into employees
    for emp in employees:
        emp["department"] = profiles.get(emp["id"], "")

    # ── Filter bar ────────────────────────────────────────────
    all_positions = sorted({(e.get("position") or "").strip() for e in employees} - {""})
    all_depts     = sorted({(e.get("department") or "").strip() for e in employees} - {""})
    _dept_names_structured = _load_dept_names_from_table()
    if _dept_names_structured:
        all_depts = _dept_names_structured
    # ── Filter bar (vertical) ─────────────────────────────────
    fcol, _ = st.columns([2, 5])
    with fcol:
        sm_sel_dept = st.multiselect("Department", all_depts,     key="sm_f_dept", placeholder="All departments")
        sm_sel_pos  = st.multiselect("Position",   all_positions, key="sm_f_pos",  placeholder="All positions")
        sm_search   = st.text_input("Employee",    placeholder="Name or employee no…",
                                    label_visibility="visible",   key="sm_search")

    # Aggregate per employee
    from collections import defaultdict
    agg: dict[str, dict] = {}
    for emp in employees:
        eid = emp["id"]
        agg[eid] = {
            "emp_no":    emp.get("employee_no", ""),
            "name":      _employee_display_name(emp),
            "position":  emp.get("position") or "—",
            "dept":      emp.get("department") or "—",
            "present":   0,
            "half_day":  0,
            "absent":    0,
            "late":      0,
            "late_mins": 0,
            "undertime_mins": 0,
            "ot_hours":  0.0,
            "nsd_hours": 0.0,
            "days_logged": 0,
        }

    for log in logs:
        eid = log["employee_id"]
        if eid not in agg:
            continue
        a = agg[eid]
        a["days_logged"] += 1
        status = log.get("status", "absent")
        if status == "present":
            a["present"] += 1
        elif status == "half_day":
            a["half_day"] += 1
        elif status == "absent":
            a["absent"] += 1
        lm = log.get("late_minutes") or 0
        if lm > 0:
            a["late"] += 1
            a["late_mins"] += lm
        a["undertime_mins"] += log.get("undertime_minutes") or 0
        a["ot_hours"]       += float(log.get("ot_hours")  or 0)
        a["nsd_hours"]      += float(log.get("nsd_hours") or 0)

    # Build filtered employee list for summary + detail
    filtered_employees = []
    for emp in employees:
        eid = emp["id"]
        a = agg[eid]
        if a["days_logged"] == 0:
            continue
        if sm_search:
            q = sm_search.lower()
            if q not in a["name"].lower() and q not in a["emp_no"].lower():
                continue
        if sm_sel_pos  and (emp.get("position") or "") not in sm_sel_pos:
            continue
        if sm_sel_dept and (emp.get("department") or "") not in sm_sel_dept:
            continue
        filtered_employees.append(emp)

    if not filtered_employees:
        st.info("No attendance records found for the selected filters.")
        return

    # Employee selection for day-by-day detail
    emp_options = {_employee_display_name(e): e["id"] for e in filtered_employees}
    emp_names = list(emp_options.keys())

    # Default to first employee
    selected_name = st.session_state.get("dtr_detail_emp", emp_names[0])
    if selected_name not in emp_options:
        selected_name = emp_names[0]

    # Render summary table
    hdr_cols = [1, 1.8, 1.5, 1.5, 1, 1, 1, 1, 1.2, 1.2, 1.5]
    hdr = st.columns(hdr_cols)
    for c, lbl in zip(hdr, ["No.", "Name", "Position", "Dept", "Present", "Late", "Half Day", "Absent", "OT Hrs", "NSD Hrs", "Late Time"]):
        c.markdown(f"**{lbl}**")

    for emp in filtered_employees:
        eid = emp["id"]
        a = agg[eid]
        name = _employee_display_name(emp)
        is_selected = (name == selected_name)

        # Wrap each row in a container with a marker for JS click wiring
        with st.container():
            sel_marker = "gxp-dtr-row-selected" if is_selected else "gxp-dtr-row"
            st.markdown(
                f'<div class="{sel_marker}" data-emp-id="{eid}"'
                f' style="height:0;overflow:hidden;margin:0;padding:0;"></div>',
                unsafe_allow_html=True,
            )

            row = st.columns(hdr_cols)
            row[0].caption(a["emp_no"])
            row[1].markdown(
                f'<span class="gxp-dtr-name" data-emp-id="{eid}"'
                f' style="cursor:pointer;">{a["name"]}</span>',
                unsafe_allow_html=True,
            )
            row[2].caption(a["position"])
            row[3].caption(a["dept"])
            row[4].text(str(a["present"]))

            # Heatmap color: 0=green, 1=dark yellow, 2=orange, >2=red
            def _heat(v):
                if v == 0: return "#2e7d32"
                if v == 1: return "#f9a825"
                if v == 2: return "#ef6c00"
                return "#c62828"

            row[5].markdown(
                f'<span style="color:{_heat(a["late"])};font-weight:600">{a["late"]}</span>',
                unsafe_allow_html=True,
            )
            row[6].text(str(a["half_day"]))

            row[7].markdown(
                f'<span style="color:{_heat(a["absent"])};font-weight:600">{a["absent"]}</span>',
                unsafe_allow_html=True,
            )
            row[8].text(f"{a['ot_hours']:.1f}" if a["ot_hours"] else "—")
            row[9].text(f"{a['nsd_hours']:.2f}" if a["nsd_hours"] else "—")
            row[10].text(_fmt_mins(a["late_mins"]))

            # Hidden button for JS click wiring
            if st.button("\u200b", key=f"dtr_sel_{eid}"):
                st.session_state["dtr_detail_emp"] = name
                st.rerun()

    # JS: event delegation + CSS-based styling (no per-row attachment)
    import streamlit.components.v1 as _stc

    # Inject a <style> tag for row hover/selected (pure CSS, no JS timing issues)
    _stc.html("""<script>
    (function(){
      var pd = window.parent.document;
      var styleId = 'gxp-dtr-row-styles';
      var old = pd.getElementById(styleId);
      if(old) old.remove();
      var s = pd.createElement('style');
      s.id = styleId;
      s.textContent = [
        '[data-dtr-row]{ cursor:pointer; border-radius:8px;',
        '  transition: transform 0.18s cubic-bezier(.34,1.56,.64,1), box-shadow 0.18s ease, background 0.15s ease, outline 0.15s ease; }',
        '[data-dtr-row]:hover{ background:rgba(0,0,0,0.03); transform:translateY(-2px); box-shadow:0 4px 16px rgba(0,0,0,0.08); }',
        '[data-dtr-row="selected"]{ background:rgba(0,91,193,0.07)!important; outline:2px solid #005bc1; outline-offset:-1px; }',
        '[data-dtr-row="selected"]:hover{ background:rgba(0,91,193,0.10)!important; }',
      ].join('\\n');
      pd.head.appendChild(s);

      /* Tag row containers with data-dtr-row attribute */
      function tagRows(){
        /* Remove old tags */
        pd.querySelectorAll('[data-dtr-row]').forEach(function(el){
          el.removeAttribute('data-dtr-row');
          delete el._dtrEid;
        });
        /* Strategy: find each hidden button, walk up to find the
           container that also holds the marker with matching emp-id */
        var btns = pd.querySelectorAll('[class*="st-key-dtr_sel_"]');
        btns.forEach(function(btnWrap){
          var cls = btnWrap.className || '';
          var m = cls.match(/st-key-dtr_sel_([\w-]+)/);
          if(!m) return;
          var eid = m[1];
          var el = btnWrap;
          for(var i=0;i<15;i++){
            el = el.parentElement;
            if(!el) return;
            var marker = el.querySelector('[data-emp-id="' + eid + '"]');
            if(marker){
              var isSel = marker.classList.contains('gxp-dtr-row-selected');
              el.setAttribute('data-dtr-row', isSel ? 'selected' : eid);
              el._dtrEid = eid;
              break;
            }
          }
        });
      }

      /* Single delegated click handler — always re-attach (remove old) */
      if(pd.body._dtrHandler){
        pd.body.removeEventListener('click', pd.body._dtrHandler);
      }
      pd.body._dtrHandler = function(e){
        if(e.target.tagName==='BUTTON'||e.target.tagName==='INPUT') return;
        var rowEl = e.target.closest('[data-dtr-row]');
        if(!rowEl) return;
        var eid = rowEl._dtrEid;
        console.log('[DTR-CLICK] rowEl found, eid=', eid);
        if(!eid) return;
        var btn = pd.querySelector('[class*="st-key-dtr_sel_' + eid + '"] button');
        console.log('[DTR-CLICK] btn=', btn);
        if(!btn) return;
        /* Instant visual update */
        pd.querySelectorAll('[data-dtr-row]').forEach(function(el){
          el.setAttribute('data-dtr-row', el._dtrEid || '');
        });
        rowEl.setAttribute('data-dtr-row', 'selected');
        btn.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));
      };
      pd.body.addEventListener('click', pd.body._dtrHandler);

      tagRows();
      setTimeout(tagRows, 800);
      setTimeout(tagRows, 2000);
    })();
    </script>""", height=0)

    # ── Day-by-Day Detail — Visual Timeline ──
    st.divider()
    selected_id = emp_options[selected_name]
    st.subheader(f"Day-by-Day Detail — {selected_name}")

    detail_logs = [l for l in logs if l["employee_id"] == selected_id]
    if not detail_logs:
        st.info("No attendance records in this range for the selected employee.")
        return

    detail_logs.sort(key=lambda l: l["work_date"])

    # Load schedule for this employee
    schedules = _load_schedules()
    sel_emp = next((e for e in filtered_employees if e["id"] == selected_id), None)

    def _time_to_minutes(t_str):
        """Parse HH:MM:SS or HH:MM string to minutes from midnight."""
        if not t_str:
            return None
        parts = t_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])

    def _bar_pct(minutes):
        """Convert minutes-from-midnight to % of 24h bar."""
        return round((minutes / 1440) * 100, 2)

    def _span(start_m, end_m):
        """Return (left_pct, width_pct) handling overnight wrap-around."""
        if end_m >= start_m:
            return _bar_pct(start_m), _bar_pct(end_m - start_m)
        else:
            # Overnight: end < start → wraps past midnight
            return _bar_pct(start_m), _bar_pct((1440 - start_m) + end_m)

    # Determine if we're showing an overnight employee (needed before row loop)
    any_overnight = False
    shift_origin = 0
    if sel_emp and detail_logs:
        s0 = resolve_schedule_for_date(sel_emp, schedules, {}, date.fromisoformat(detail_logs[0]["work_date"]))
        if s0 and s0.get("is_overnight"):
            any_overnight = True
            shift_origin = _time_to_minutes(s0.get("start_time")) or 0

    # Vertical grid lines HTML (injected into each row's timeline bar)
    grid_lines = ""
    for i in range(24):
        left_pct = round((i * 60 / 1440) * 100, 2)
        if i % 3 == 0:
            # Major grid line every 3 hours
            grid_lines += (
                f'<div style="position:absolute;left:{left_pct}%;top:0;bottom:0;'
                f'width:1.5px;background:rgba(0,0,0,0.22);pointer-events:none;z-index:0;"></div>'
            )
        else:
            # Minor grid line every hour
            grid_lines += (
                f'<div style="position:absolute;left:{left_pct}%;top:0;bottom:0;'
                f'width:1px;background:rgba(0,0,0,0.12);pointer-events:none;z-index:0;"></div>'
            )

    # Build HTML timeline
    rows_html = []
    for l in detail_logs:
        d = date.fromisoformat(l["work_date"])
        day_label = d.strftime("%b %d")
        day_name = d.strftime("%a")

        # Schedule info
        sched = None
        if sel_emp:
            sched = resolve_schedule_for_date(sel_emp, schedules, {}, d)
        sched_name = sched.get("name", "—") if sched else "—"
        sched_start = _time_to_minutes(sched.get("start_time")) if sched and sched.get("start_time") else None
        sched_end = _time_to_minutes(sched.get("end_time")) if sched and sched.get("end_time") else None
        is_overnight = bool(sched.get("is_overnight", False)) if sched else False
        break_mins_allowed = sched.get("break_minutes", 60) if sched else 60

        # Time values
        t_in = _time_to_minutes(l.get("time_in"))
        t_out = _time_to_minutes(l.get("time_out"))
        b_out = _time_to_minutes(l.get("break_out"))
        b_in = _time_to_minutes(l.get("break_in"))

        # For overnight shifts, normalize times relative to shift start
        # so the bar renders correctly across midnight
        if is_overnight and t_in is not None and t_out is not None:
            # If t_out < t_in, it's the next day — add 24h
            if t_out < t_in:
                t_out += 1440
            if b_out is not None and b_out < t_in:
                b_out += 1440
            if b_in is not None and b_in < t_in:
                b_in += 1440
            if sched_end is not None and sched_end < sched_start:
                sched_end += 1440

        # Metrics
        late_m = l.get("late_minutes") or 0
        ut_m = l.get("undertime_minutes") or 0
        ot_h = float(l.get("ot_hours") or 0)
        nsd_h = float(l.get("nsd_hours") or 0)
        status = l.get("status", "absent")
        actual_break = l.get("actual_break_minutes") or 0
        overbreak = actual_break > break_mins_allowed if b_out and b_in else False

        # Status colors
        status_colors = {
            "present": ("#2e7d32", "Present"),
            "late":    ("#ef6c00", "Late"),
            "absent":  ("#c62828", "Absent"),
            "half_day": ("#795900", "Half Day"),
            "rest_day": ("#424753", "Rest Day"),
            "no_schedule": ("#424753", "—"),
        }
        s_color, s_label = status_colors.get(status, ("#424753", status.title()))

        # For overnight bars, compute using a shifted 24h window
        # starting at shift_start instead of midnight
        if is_overnight and sched_start is not None:
            # Shift origin: sched_start becomes 0, everything offset
            origin = sched_start

            def _ov_pct(m):
                """Minutes relative to shift origin → % of 24h bar."""
                return round(((m - origin) / 1440) * 100, 2)
        else:
            origin = 0
            _ov_pct = _bar_pct

        # Build bar segments
        segments_html = ""

        # NSD window band (10PM–6AM) for overnight shifts
        if is_overnight:
            nsd_start = 22 * 60  # 10PM
            nsd_end = 6 * 60 + 1440  # 6AM next day (normalized)
            nsd_left = _ov_pct(nsd_start)
            nsd_width = _ov_pct(nsd_end) - _ov_pct(nsd_start)
            segments_html += (
                f'<div style="position:absolute;left:{nsd_left}%;'
                f'width:{nsd_width}%;'
                f'top:0;bottom:0;background:rgba(13,71,161,0.06);'
                f'border-left:1px solid rgba(13,71,161,0.15);'
                f'border-right:1px solid rgba(13,71,161,0.15);" '
                f'title="NSD Window 10PM–6AM"></div>'
            )

        if t_in is not None and t_out is not None:
            # Schedule background (ghost bar)
            if sched_start is not None and sched_end is not None:
                g_left = _ov_pct(sched_start)
                g_width = _ov_pct(sched_end) - _ov_pct(sched_start)
                segments_html += (
                    f'<div style="position:absolute;left:{g_left}%;'
                    f'width:{g_width}%;'
                    f'top:2px;bottom:2px;background:rgba(0,91,193,0.08);'
                    f'border-radius:4px;border:1px dashed rgba(0,91,193,0.2);"></div>'
                )

            # Work segment 1: time_in → break_out (or time_out if no break)
            seg1_end = b_out if b_out else t_out
            work_color = "#005bc1" if status == "present" else "#ef6c00" if status == "late" else "#795900"
            segments_html += (
                f'<div style="position:absolute;left:{_ov_pct(t_in)}%;'
                f'width:{_ov_pct(seg1_end) - _ov_pct(t_in)}%;'
                f'top:4px;bottom:4px;background:{work_color};'
                f'border-radius:4px 0 0 4px;opacity:0.85;" '
                f'title="In: {l.get("time_in","")[:5]}"></div>'
            )

            # Break segment
            if b_out and b_in:
                brk_color = "#c62828" if overbreak else "#9e9e9e"
                segments_html += (
                    f'<div style="position:absolute;left:{_ov_pct(b_out)}%;'
                    f'width:{_ov_pct(b_in) - _ov_pct(b_out)}%;'
                    f'top:4px;bottom:4px;background:{brk_color};'
                    f'border-radius:0;opacity:0.45;" '
                    f'title="Break: {actual_break}m{" (OVER)" if overbreak else ""}"></div>'
                )
                # Work segment 2: break_in → time_out
                segments_html += (
                    f'<div style="position:absolute;left:{_ov_pct(b_in)}%;'
                    f'width:{_ov_pct(t_out) - _ov_pct(b_in)}%;'
                    f'top:4px;bottom:4px;background:{work_color};'
                    f'border-radius:0 4px 4px 0;opacity:0.85;" '
                    f'title="Out: {l.get("time_out","")[:5]}"></div>'
                )
            else:
                # No break data — round right edge
                segments_html = segments_html.rsplit("</div>", 1)[0].replace(
                    "border-radius:4px 0 0 4px", "border-radius:4px"
                ) + "</div>"

            # OT indicator (past schedule end)
            if ot_h > 0 and sched_end and t_out > sched_end:
                segments_html += (
                    f'<div style="position:absolute;left:{_ov_pct(sched_end)}%;'
                    f'width:{_ov_pct(t_out) - _ov_pct(sched_end)}%;'
                    f'top:4px;bottom:4px;background:#7b1fa2;'
                    f'border-radius:0 4px 4px 0;opacity:0.7;" '
                    f'title="OT: {ot_h:.1f}h"></div>'
                )

        # Absent — red dashed in schedule slot
        elif status == "absent" and sched_start is not None and sched_end is not None:
            g_left = _ov_pct(sched_start)
            g_width = _ov_pct(sched_end) - _ov_pct(sched_start)
            segments_html += (
                f'<div style="position:absolute;left:{g_left}%;'
                f'width:{g_width}%;'
                f'top:4px;bottom:4px;background:repeating-linear-gradient('
                f'45deg,transparent,transparent 3px,rgba(198,40,40,0.15) 3px,rgba(198,40,40,0.15) 6px);'
                f'border:1px dashed #c62828;border-radius:4px;opacity:0.6;"></div>'
            )

        # Heatmap helper
        def _hv(v):
            if v == 0: return "#2e7d32"
            if v <= 5: return "#f9a825"
            if v <= 15: return "#ef6c00"
            return "#c62828"

        row_html = f'''
        <div style="display:grid;grid-template-columns:70px 40px 80px minmax(200px,1fr) 42px 42px 42px 42px 70px;
                    align-items:center;gap:4px;padding:6px 8px;border-bottom:1px solid rgba(0,0,0,0.06);
                    font-size:13px;font-family:'Plus Jakarta Sans',sans-serif;">
          <div style="font-weight:600;color:#191c1d;">{day_label}</div>
          <div style="color:#5a6062;font-size:11px;">{day_name}</div>
          <div style="color:#5a6062;font-size:11px;white-space:nowrap;">{sched_name}</div>
          <div style="position:relative;height:22px;background:#f4f5f6;border-radius:4px;overflow:hidden;">
            {grid_lines}{segments_html}
          </div>
          <div style="text-align:center;font-weight:600;color:{_hv(late_m)};">{_fmt_mins(late_m) if late_m else "—"}</div>
          <div style="text-align:center;font-weight:600;color:{_hv(ut_m)};">{_fmt_mins(ut_m) if ut_m else "—"}</div>
          <div style="text-align:center;color:#7b1fa2;font-weight:600;">{f"{ot_h:.1f}" if ot_h else "—"}</div>
          <div style="text-align:center;color:#0d47a1;font-weight:600;">{f"{nsd_h:.1f}" if nsd_h else "—"}</div>
          <div style="text-align:center;">
            <span style="display:inline-block;padding:2px 8px;border-radius:9999px;font-size:10px;
                         font-weight:700;color:{s_color};background:{s_color}18;
                         text-transform:uppercase;letter-spacing:0.04em;">{s_label}</span>
          </div>
        </div>'''
        rows_html.append(row_html)

    # Hour markers for the timeline header — label every 3h, tick every 1h
    hour_markers = ""
    for i in range(24):
        m = (shift_origin + i * 60) % 1440
        left_pct = round((i * 60 / 1440) * 100, 2)
        if i % 3 == 0:
            h = m // 60
            ampm = "a" if h < 12 else "p"
            h12 = h % 12 or 12
            lbl = f"{h12}{ampm}"
            hour_markers += (
                f'<div style="position:absolute;left:{left_pct}%;font-size:9px;'
                f'color:#7a7a7a;transform:translateX(-50%);top:-1px;font-weight:600;">{lbl}</div>'
            )
        else:
            hour_markers += (
                f'<div style="position:absolute;left:{left_pct}%;top:10px;'
                f'width:1px;height:6px;background:rgba(0,0,0,0.12);"></div>'
            )

    # Legend
    legend_items = [
        ("#005bc1", 0.85, "Work"),
        ("#ef6c00", 0.85, "Late"),
        ("#9e9e9e", 0.45, "Break"),
        ("#c62828", 0.45, "Overbreak"),
        ("#7b1fa2", 0.7, "OT"),
    ]
    legend_html = '<div style="display:flex;gap:14px;flex-wrap:wrap;margin:8px 0 4px;font-size:11px;color:#5a6062;">'
    for color, opacity, label in legend_items:
        legend_html += (
            f'<span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;'
            f'background:{color};opacity:{opacity};margin-right:3px;vertical-align:middle;"></span>{label}</span>'
        )
    # Scheduled (dashed border, special)
    legend_html += (
        '<span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;'
        'background:rgba(0,91,193,0.08);border:1px dashed rgba(0,91,193,0.3);margin-right:3px;'
        'vertical-align:middle;"></span>Scheduled</span>'
    )
    if any_overnight:
        legend_html += (
            '<span><span style="display:inline-block;width:10px;height:10px;border-radius:2px;'
            'background:rgba(13,71,161,0.08);border:1px solid rgba(13,71,161,0.2);margin-right:3px;'
            'vertical-align:middle;"></span>NSD Window</span>'
        )
    legend_html += '</div>'

    full_html = f'''
    <div style="background:white;border-radius:12px;padding:12px 16px;
                box-shadow:0 1px 4px rgba(0,0,0,0.06);">
      {legend_html}
      <div style="display:grid;grid-template-columns:70px 40px 80px minmax(200px,1fr) 42px 42px 42px 42px 70px;
                  align-items:center;gap:4px;padding:6px 8px;border-bottom:2px solid rgba(0,0,0,0.1);
                  font-size:11px;font-weight:700;color:#5a6062;text-transform:uppercase;letter-spacing:0.06em;">
        <div>Date</div>
        <div>Day</div>
        <div>Shift</div>
        <div style="position:relative;height:16px;border-bottom:1px solid rgba(0,0,0,0.08);">
          {hour_markers}
        </div>
        <div style="text-align:center;">Late</div>
        <div style="text-align:center;">UT</div>
        <div style="text-align:center;">OT</div>
        <div style="text-align:center;">NSD</div>
        <div style="text-align:center;">Status</div>
      </div>
      {"".join(rows_html)}
    </div>'''

    # Use components.html to avoid st.markdown sanitizer truncating large HTML
    import streamlit.components.v1 as _stc
    row_count = len(detail_logs)
    timeline_height = 80 + row_count * 38  # legend ~50px + header ~30px + rows
    _stc.html(full_html, height=timeline_height, scrolling=True)


# ============================================================
# Tab 3 — Corrections
# ============================================================

def _render_corrections():
    col_filter, _ = st.columns([2, 5])
    with col_filter:
        status_filter = st.selectbox(
            "Show", ["pending", "all", "approved", "rejected"],
            key="corr_filter",
        )

    corrections = _load_corrections(status_filter)

    if not corrections:
        st.info("No correction requests found.")
        return

    pending_count = sum(1 for c in corrections if c["status"] == "pending")
    if pending_count:
        st.warning(f"**{pending_count}** correction request(s) pending review.")

    for i_corr, corr in enumerate(corrections):
        emp_data = corr.get("employees") or {}
        emp_name = f"{emp_data.get('last_name', '')}, {emp_data.get('first_name', '')}"
        work_date_str = date.fromisoformat(corr["work_date"]).strftime("%B %d, %Y")

        status = corr["status"]
        _st_pill = {
            "pending":  ("#795900", "#ffdea0"),
            "approved": ("#005320", "#89fa9b"),
            "rejected": ("#ba1a1a", "#ffdad6"),
        }.get(status, ("#424753", "#e1e3e4"))

        # Load the original time log for comparison
        original = (
            get_db().table("time_logs")
            .select("time_in, time_out, status")
            .eq("employee_id", corr["employee_id"])
            .eq("work_date", corr["work_date"])
            .execute()
        ).data
        orig = original[0] if original else {}

        corr_type = "MISSING IN" if not orig.get("time_in") else "OUT ADJUST" if orig.get("time_out") else "TIME ADJUST"

        with st.container():
            # Card header HTML
            st.markdown(
                f'<div style="background:#ffffff;border-radius:16px;padding:20px 24px 12px;'
                f'box-shadow:0 4px 20px rgba(45,51,53,0.06);margin-bottom:4px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">'
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f'{_dtr_avatar(emp_name, i_corr, 44)}'
                f'<div><div style="font-size:14px;font-weight:700;color:#191c1d;">{emp_name}</div>'
                f'<div style="font-size:11px;color:#727784;">Requested {work_date_str}</div></div></div>'
                f'<div style="display:flex;gap:8px;align-items:center;">'
                f'<span style="background:#e7e8e9;color:#424753;padding:3px 10px;border-radius:9999px;'
                f'font-size:10px;font-weight:700;">{corr_type}</span>'
                f'<span style="background:{_st_pill[1]};color:{_st_pill[0]};padding:3px 10px;'
                f'border-radius:9999px;font-size:10px;font-weight:700;">{status.upper()}</span>'
                f'</div></div>'
                f'<div style="background:#f3f4f5;border-radius:12px;padding:14px 16px;'
                f'display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
                f'<div><div style="font-size:9px;font-weight:700;color:#727784;text-transform:uppercase;letter-spacing:0.08em;">Original</div>'
                f'<div style="font-size:14px;font-weight:700;margin-top:2px;">{_fmt_time(orig.get("time_in"))} → {_fmt_time(orig.get("time_out"))}</div></div>'
                f'<span class="material-symbols-outlined" style="color:#c2c6d5;font-size:20px;">east</span>'
                f'<div style="text-align:right;"><div style="font-size:9px;font-weight:700;color:#005bc1;text-transform:uppercase;letter-spacing:0.08em;">Requested</div>'
                f'<div style="font-size:14px;font-weight:700;color:#005bc1;margin-top:2px;">{_fmt_time(corr.get("requested_time_in"))} → {_fmt_time(corr.get("requested_time_out"))}</div></div>'
                f'</div>'
                f'<div style="font-size:12px;color:#5a6062;font-style:italic;margin-bottom:8px;">'
                f'"{corr.get("reason") or "No reason provided."}"</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if corr.get("admin_notes"):
                st.caption(f"Admin notes: {corr['admin_notes']}")

            if status == "pending":
                notes_key = f"corr_notes_{corr['id']}"
                notes = st.text_input("Admin notes (optional)", key=notes_key,
                                       label_visibility="collapsed",
                                       placeholder="Admin notes (optional)")
                btn1, btn2, _ = st.columns([1.5, 1.5, 5])
                with btn1:
                    if st.button("Approve", key=f"corr_approve_{corr['id']}", type="primary"):
                        try:
                            _update_correction(corr["id"], "approved", notes)
                            # Apply the correction to the time_log
                            if orig:
                                req_in  = corr.get("requested_time_in")
                                req_out = corr.get("requested_time_out")
                                # Reload schedule to re-compute
                                emp_row = (
                                    get_db().table("employees")
                                    .select("*, schedule_id")
                                    .eq("id", corr["employee_id"])
                                    .execute()
                                ).data
                                if emp_row and req_in and req_out:
                                    schedules = _load_schedules()
                                    emp       = emp_row[0]
                                    work_date = date.fromisoformat(corr["work_date"])
                                    overrides = _load_overrides_for_date(work_date)
                                    sched     = resolve_schedule_for_date(emp, schedules, overrides, work_date)
                                    if sched:
                                        exp_h = schedule_expected_hours(sched)
                                        result = compute_dtr(
                                            _parse_time(req_in), _parse_time(req_out),
                                            _parse_time(sched["start_time"]),
                                            _parse_time(sched["end_time"]),
                                            exp_h,
                                            int(sched.get("break_minutes", 60)),
                                            bool(sched.get("is_overnight", False)),
                                        )
                                        _upsert_time_log({
                                            "employee_id":      corr["employee_id"],
                                            "work_date":        corr["work_date"],
                                            "time_in":          req_in,
                                            "time_out":         req_out,
                                            "gross_hours":      result.gross_hours,
                                            "late_minutes":     result.late_minutes,
                                            "undertime_minutes": result.undertime_minutes,
                                            "ot_hours":         result.ot_hours,
                                            "nsd_hours":        result.nsd_hours,
                                            "status":           result.status,
                                        })
                            log_action("approved", "dtr_correction", corr["id"],
                                       f"{emp_name} {corr['work_date']}")
                            st.success("Correction approved and applied.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error: {ex}")
                with btn2:
                    if st.button("Reject", key=f"corr_reject_{corr['id']}"):
                        try:
                            _update_correction(corr["id"], "rejected", notes)
                            log_action("rejected", "dtr_correction", corr["id"],
                                       f"{emp_name} {corr['work_date']}")
                            st.success("Correction rejected.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error: {ex}")


# ============================================================
# Main render
# ============================================================

def render():
    inject_css()

    # ── Editorial heading ─────────────────────────────────────
    st.markdown(
        '<p class="gxp-page-label">ATTENDANCE</p>'
        '<h2 class="gxp-editorial-heading">Attendance</h2>'
        '<p class="gxp-editorial-sub">Daily Time Record &amp; Corrections</p>',
        unsafe_allow_html=True,
    )

    # ── Monthly KPI cards ─────────────────────────────────────
    try:
        _m = _load_monthly_metrics()
    except Exception:
        _m = {"rate": 0, "late": 0, "nsd": 0.0}

    _rate_color = "#005320" if _m["rate"] >= 90 else ("#795900" if _m["rate"] >= 75 else "#ba1a1a")
    _kpi_style = (
        "background:#ffffff;border-radius:16px;padding:20px 24px;"
        "box-shadow:0 4px 20px rgba(45,51,53,0.06);"
    )
    k1, k2, k3 = st.columns(3)
    k1.markdown(
        f'<div style="{_kpi_style}">'
        f'<div style="font-size:10px;font-weight:700;color:#5a6062;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">Avg Attendance Rate</div>'
        f'<div style="display:flex;align-items:flex-end;gap:8px;">'
        f'<span style="font-size:2.2rem;font-weight:800;color:#191c1d;line-height:1;">{_m["rate"]}%</span>'
        f'<span style="font-size:12px;font-weight:700;color:{_rate_color};margin-bottom:4px;">MTD</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    _late_color = "#ba1a1a" if _m["late"] > 0 else "#005320"
    k2.markdown(
        f'<div style="{_kpi_style}">'
        f'<div style="font-size:10px;font-weight:700;color:#5a6062;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">Late Incidents</div>'
        f'<div style="display:flex;align-items:flex-end;gap:8px;">'
        f'<span style="font-size:2.2rem;font-weight:800;color:#191c1d;line-height:1;">{_m["late"]}</span>'
        f'<span style="font-size:12px;font-weight:700;color:{_late_color};margin-bottom:4px;">MTD</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    k3.markdown(
        f'<div style="{_kpi_style}">'
        f'<div style="font-size:10px;font-weight:700;color:#5a6062;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">Total NSD Hours</div>'
        f'<div style="display:flex;align-items:flex-end;gap:8px;">'
        f'<span style="font-size:2.2rem;font-weight:800;color:#191c1d;line-height:1;">{_m["nsd"]:.1f}</span>'
        f'<span style="font-size:12px;font-weight:700;color:#424753;margin-bottom:4px;">MTD</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    tab_entry, tab_summary, tab_corrections = st.tabs([
        "📅 Daily Entry",
        "📊 Attendance Summary",
        "🔧 Corrections",
    ])

    with tab_entry:
        _render_daily_entry()

    with tab_summary:
        _render_summary()

    with tab_corrections:
        _render_corrections()
