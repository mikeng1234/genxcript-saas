"""
Government Remittance Deadlines — with weekend/holiday adjustment.

Philippine rules:
- If a deadline falls on a Saturday, Sunday, or holiday (regular or
  special_non_working), it moves to the next business day.
- special_working days count as business days.
"""

from datetime import date, timedelta


def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5  # Saturday=5, Sunday=6


def adjust_to_next_business_day(deadline: date, holidays: set[date]) -> date:
    """
    Shift a deadline forward until it lands on a business day.

    Parameters
    ----------
    deadline : date
        The original deadline date.
    holidays : set[date]
        Set of dates that are non-working (regular + special_non_working).
        Do NOT include special_working days here.
    """
    while _is_weekend(deadline) or deadline in holidays:
        deadline += timedelta(days=1)
    return deadline


def get_remittance_deadlines(
    today: date,
    holidays: set[date],
    remitted_set: "set[tuple[str, int, int]] | None" = None,
) -> list[dict]:
    """
    Return the upcoming government remittance deadlines adjusted for
    weekends and Philippine holidays.

    Each agency has a statutory deadline day-of-month. We compute the
    deadline for the current reporting month and adjust it.

    Parameters
    ----------
    today : date
        Current date (passed in so the function is testable).
    holidays : set[date]
        Non-working holiday dates for the relevant months.
    remitted_set : set of (agency, year, month) tuples, optional
        Agencies that have already been remitted for the reference period.
        Matching deadlines are marked ``remitted=True`` so alert code can
        suppress them without re-querying the database.
    """
    # Determine the reference month for remittances.
    # If we're still before the 20th, deadlines are for this month.
    # Otherwise show next month's deadlines.
    if today.day <= 20:
        ref_month = today.replace(day=1)
    else:
        next_month = today.replace(day=28) + timedelta(days=4)
        ref_month = next_month.replace(day=1)

    month_label = ref_month.strftime("%B %Y")
    _remitted = remitted_set or set()

    agencies = [
        {
            "agency": "SSS",
            "form": "R3 / R5",
            "description": f"Monthly contribution for {month_label}",
            "day": 10,
        },
        {
            "agency": "PhilHealth",
            "form": "RF-1",
            "description": f"Monthly remittance for {month_label}",
            "day": 15,
        },
        {
            "agency": "Pag-IBIG",
            "form": "MCRF",
            "description": f"Monthly contribution for {month_label}",
            "day": 15,
        },
        {
            "agency": "BIR",
            "form": "1601-C",
            "description": f"Withholding tax for {month_label}",
            "day": 10,
        },
    ]

    deadlines = []
    for a in agencies:
        raw_deadline = ref_month.replace(day=a["day"])
        adjusted = adjust_to_next_business_day(raw_deadline, holidays)
        days_until = (adjusted - today).days
        remitted = (a["agency"], ref_month.year, ref_month.month) in _remitted

        deadlines.append({
            "agency":       a["agency"],
            "form":         a["form"],
            "description":  a["description"],
            "raw_deadline": raw_deadline,
            "deadline":     adjusted,
            "days_until":   days_until,
            "remitted":     remitted,           # True → alert suppressed
            "period_year":  ref_month.year,
            "period_month": ref_month.month,
        })

    return deadlines


def load_holiday_set(db, year: int | None = None, company_id: str | None = None) -> set[date]:
    """
    Load non-working holidays and return as a set of effective dates.

    - National holidays (company_id IS NULL) are included for all companies.
    - Company-specific rows (company_id = <id>) shadow the same-named national holiday,
      applying that company's proclaimed observed_date instead of the global one.
    - 'special_working' days are excluded (they are treated as business days).

    Parameters
    ----------
    company_id : str, optional
        When provided, company-specific overrides for this company are merged in.
    """
    def _to_date(v):
        if v is None:
            return None
        return date.fromisoformat(v) if isinstance(v, str) else v

    # 1. Load national holidays
    nat_query = (
        db.table("holidays")
        .select("name, holiday_date, observed_date")
        .in_("type", ["regular", "special_non_working"])
        .is_("company_id", "null")
    )
    if year is not None:
        nat_query = nat_query.eq("year", year)
    national_rows = nat_query.execute().data or []

    # Build map: name → effective date (prefer observed_date over holiday_date)
    effective: dict[str, date] = {}
    for row in national_rows:
        raw = _to_date(row.get("observed_date")) or _to_date(row["holiday_date"])
        if raw:
            effective[row["name"]] = raw

    # 2. Merge company-specific overrides (they win over national dates)
    if company_id:
        co_query = (
            db.table("holidays")
            .select("name, holiday_date, observed_date")
            .in_("type", ["regular", "special_non_working"])
            .eq("company_id", company_id)
        )
        if year is not None:
            co_query = co_query.eq("year", year)
        for row in (co_query.execute().data or []):
            raw = _to_date(row.get("observed_date")) or _to_date(row["holiday_date"])
            if raw:
                effective[row["name"]] = raw  # override national

    return set(effective.values())
