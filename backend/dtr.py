"""
backend/dtr.py — DTR Computation Engine (Phase 4B)

Pure Python. Zero DB calls. Zero Streamlit imports.
All inputs are plain Python types; all outputs are dataclasses.

Usage:
    from backend.dtr import compute_dtr, resolve_schedule_for_date, DTRResult

    result = compute_dtr(
        time_in=time(8, 45),
        time_out=time(17, 0),
        expected_start=time(8, 0),
        expected_end=time(17, 0),
        expected_hours=8.0,
        break_minutes=60,
        is_overnight=False,
        grace_minutes=5,
    )
    # DTRResult(gross_hours=7.25, late_minutes=40, undertime_minutes=0,
    #           ot_hours=0.0, nsd_hours=0.0, status='present')
"""

import math
from dataclasses import dataclass
from datetime import time, date
from typing import Optional


# ── Result container ──────────────────────────────────────────────────────────

@dataclass
class DTRResult:
    gross_hours: float        # Actual hours worked (after deducting break)
    late_minutes: int         # Minutes arrived after grace period
    undertime_minutes: int    # Minutes left before scheduled end
    ot_hours: float           # Hours worked beyond expected shift
    nsd_hours: float          # Hours worked in NSD window (10PM–6AM, DOLE mandated +10%)
    status: str               # 'present' | 'absent' | 'half_day'


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_min(t: time) -> int:
    """Convert a time object to total minutes from midnight."""
    return t.hour * 60 + t.minute


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """
    Compute the great-circle distance between two GPS coordinates in metres.
    Uses the Haversine formula. Returns an integer (metres).
    """
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return int(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def nearest_location(lat: float, lng: float, locations: list[dict]) -> Optional[dict]:
    """
    Given a list of company_locations rows and a GPS fix, return the nearest
    active location and the distance in metres.

    Returns a dict with the location row + injected key 'distance_m',
    or None if locations is empty.
    """
    if not locations:
        return None
    best = None
    best_dist = float("inf")
    for loc in locations:
        if not loc.get("is_active", True):
            continue
        d = haversine_distance_m(lat, lng, float(loc["latitude"]), float(loc["longitude"]))
        if d < best_dist:
            best_dist = d
            best = {**loc, "distance_m": d}
    return best


def compute_nsd_hours(time_in: time, time_out: time, is_overnight: bool) -> float:
    """
    Compute hours worked within the Night Shift Differential window.

    Under DOLE regulations (Labor Code Art. 86), NSD is mandated for every
    hour worked between 10:00 PM and 6:00 AM — a 10% premium on top of the
    regular hourly rate.

    Returns total NSD hours as a float (e.g. 2.5).
    """
    in_m  = _to_min(time_in)
    out_m = _to_min(time_out)

    # For overnight shifts extend out_m past midnight
    if is_overnight and out_m <= in_m:
        out_m += 1440

    def _overlap(w_start: int, w_end: int) -> int:
        """Return overlap in minutes between [in_m, out_m] and [w_start, w_end]."""
        return max(0, min(out_m, w_end) - max(in_m, w_start))

    nsd_min = 0
    # Window A: 10 PM–midnight on day 1  (1320–1440)
    nsd_min += _overlap(22 * 60, 24 * 60)
    # Window B: midnight–6 AM on day 1   (0–360) — for shifts starting after midnight
    nsd_min += _overlap(0, 6 * 60)
    # Window C: midnight–6 AM on day 2   (1440–1800) — for overnight shifts
    if out_m > 1440:
        nsd_min += _overlap(1440, 1440 + 6 * 60)

    return round(nsd_min / 60, 2)


# ── Core computation ──────────────────────────────────────────────────────────

def compute_dtr(
    time_in: Optional[time],
    time_out: Optional[time],
    expected_start: time,
    expected_end: time,
    expected_hours: float,
    break_minutes: int,
    is_overnight: bool,
    grace_minutes: int = 5,
) -> DTRResult:
    """
    Compute late, undertime, gross hours, and OT from raw time-in/out
    vs the employee's assigned schedule.

    Args:
        time_in:         Actual clock-in time (None → absent)
        time_out:        Actual clock-out time (None → absent)
        expected_start:  Scheduled start time from the shift profile
        expected_end:    Scheduled end time from the shift profile
        expected_hours:  Net working hours defined by the shift (after break)
        break_minutes:   Break duration deducted from gross hours
        is_overnight:    True when the shift crosses midnight (e.g. 22:00–06:00)
        grace_minutes:   Minutes after expected_start before late penalty kicks in
                         (DOLE/company policy; default 5)

    Returns:
        DTRResult with all computed attendance fields.
    """
    if time_in is None or time_out is None:
        return DTRResult(
            gross_hours=0.0,
            late_minutes=0,
            undertime_minutes=0,
            ot_hours=0.0,
            nsd_hours=0.0,
            status="absent",
        )

    in_m  = _to_min(time_in)
    out_m = _to_min(time_out)
    s_m   = _to_min(expected_start)
    e_m   = _to_min(expected_end)

    # Adjust for overnight shifts (end < start) — add 24 hours to the "end" side
    if is_overnight:
        if e_m < s_m:
            e_m += 1440   # scheduled end wraps to next day
        if out_m <= in_m:
            out_m += 1440 # actual out wraps to next day

    # ── Late ──────────────────────────────────────────────────────────────────
    # Minutes late = actual_in − (scheduled_start + grace), floor at 0
    late_min = max(0, in_m - (s_m + grace_minutes))

    # ── Undertime ─────────────────────────────────────────────────────────────
    # Minutes left early = scheduled_end − actual_out, floor at 0
    undertime_min = max(0, e_m - out_m)

    # ── Gross hours worked ────────────────────────────────────────────────────
    # Raw span minus the break deduction; floor at 0 to handle edge cases
    gross_min = max(0, out_m - in_m - break_minutes)
    gross_h   = round(gross_min / 60, 2)

    # ── OT ────────────────────────────────────────────────────────────────────
    # OT is time worked PAST the scheduled end, independent of clock-in time.
    # This means:
    #   • A late employee who still leaves after the scheduled end gets full OT.
    #   • An early clock-in does NOT generate OT (start is clamped to s_m).
    #   • Consistent with DOLE: overtime starts when regular working hours end.
    ot_min = max(0, out_m - e_m)
    ot_h   = round(ot_min / 60, 2)

    # ── Night Shift Differential (NSD) ────────────────────────────────────────
    # DOLE Labor Code Art. 86: 10% premium for every hour between 10PM–6AM.
    # Computed separately; used by payroll to apply the NSD premium.
    nsd_h = compute_nsd_hours(time_in, time_out, is_overnight)

    # ── Status ────────────────────────────────────────────────────────────────
    if gross_h < 0.5:
        status = "absent"
    elif expected_hours > 0 and gross_h < expected_hours * 0.6:
        status = "half_day"
    else:
        status = "present"

    return DTRResult(
        gross_hours=gross_h,
        late_minutes=late_min,
        undertime_minutes=undertime_min,
        ot_hours=ot_h,
        nsd_hours=nsd_h,
        status=status,
    )


# ── Schedule resolution ───────────────────────────────────────────────────────

def resolve_schedule_for_date(
    employee: dict,
    schedules: dict,
    overrides: dict,
    work_date: date,
) -> Optional[dict]:
    """
    Return the effective schedule dict for an employee on a specific date,
    or None if the employee has a rest day or no schedule assigned.

    Lookup priority:
      1. schedule_overrides for (employee_id, work_date)
         - is_rest_day=True   → None (rest day, no DTR expected)
         - schedule_id set    → use that schedule instead
      2. employees.schedule_id (default shift profile)
      3. Check if work_date falls on a work_days day; if not → None (off day)

    Args:
        employee:   employees table row dict (needs 'id' and 'schedule_id')
        schedules:  {schedule_id: schedule_row} pre-loaded dict
        overrides:  {(employee_id, date_str): override_row} pre-loaded dict
        work_date:  The date to resolve for

    Returns:
        schedule row dict (with 'start_time', 'end_time', 'break_minutes',
        'is_overnight', 'work_days' etc.) or None.
    """
    key = (employee["id"], str(work_date))
    override = overrides.get(key)

    if override:
        if override.get("is_rest_day"):
            return None
        if override.get("schedule_id"):
            return schedules.get(override["schedule_id"])

    sched_id = employee.get("schedule_id")
    if not sched_id:
        return None

    sched = schedules.get(sched_id)
    if not sched:
        return None

    # Check work_days — stored as Postgres text array, loaded as Python list
    work_days = sched.get("work_days") or []
    day_abbr  = work_date.strftime("%a")  # 'Mon', 'Tue', ...
    if day_abbr not in work_days:
        return None

    return sched


def schedule_expected_hours(sched: dict) -> float:
    """
    Compute the net working hours defined by a schedule dict
    (gross shift span minus break).
    """
    s_m = _to_min(_parse_time(sched["start_time"]))
    e_m = _to_min(_parse_time(sched["end_time"]))
    if sched.get("is_overnight") and e_m < s_m:
        e_m += 1440
    gross_min = max(0, e_m - s_m)
    net_min   = max(0, gross_min - int(sched.get("break_minutes", 60)))
    return round(net_min / 60, 2)


def _parse_time(value) -> time:
    """
    Accept a Python time object or a 'HH:MM:SS' / 'HH:MM' string
    (Supabase returns TIME columns as strings).
    """
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        parts = value.split(":")
        return time(int(parts[0]), int(parts[1]))
    raise TypeError(f"Cannot parse time from {value!r}")
