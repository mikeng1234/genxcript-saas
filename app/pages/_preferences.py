"""
Preferences — User-level app settings.

Tabs:
  🎨 Appearance   — Themes
  📅 Formats      — Date / time / number formatting
  📊 Display      — Table density, default landing page
  🔔 Notifications — (roadmap stub)
"""

import streamlit as st
from app.styles import inject_css, THEMES, DEFAULT_THEME
from app.db_helper import get_db

# ── Preference defaults ────────────────────────────────────────
_PREF_DEFAULTS: dict = {
    "gxp_theme":         DEFAULT_THEME,
    "gxp_date_format":   "MMM D, YYYY",
    "gxp_time_format":   "12h",
    "gxp_week_start":    "Monday",
    "gxp_currency_pos":  "prefix",       # prefix = ₱1,000  (only supported format)
    "gxp_table_density": "normal",        # compact | normal | relaxed
    "gxp_default_page":  "Dashboard",
    "gxp_sidebar_open":  True,
}

DATE_FORMAT_OPTIONS = [
    "MMM D, YYYY",     # Mar 17, 2026
    "MM/DD/YYYY",      # 03/17/2026
    "DD/MM/YYYY",      # 17/03/2026
    "YYYY-MM-DD",      # 2026-03-17
    "D MMMM YYYY",     # 17 March 2026
]

DATE_FORMAT_EXAMPLES = {
    "MMM D, YYYY":   "Mar 17, 2026",
    "MM/DD/YYYY":    "03/17/2026",
    "DD/MM/YYYY":    "17/03/2026",
    "YYYY-MM-DD":    "2026-03-17",
    "D MMMM YYYY":   "17 March 2026",
}

PAGES_LIST = [
    "Dashboard", "Employees", "Payroll Run",
    "Payroll Comparison", "OT Analytics", "Government Reports",
    "Calendar", "Company Setup",
]


def load_user_prefs(user_id: str) -> None:
    """Fetch persisted preferences from Supabase and populate session_state.
    Safe to call on every login / session-restore — silently falls back to
    defaults if the row doesn't exist yet or the DB call fails.
    """
    if not user_id:
        return
    try:
        result = (
            get_db()
            .table("user_preferences")
            .select("prefs")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        saved: dict = (result.data or {}).get("prefs", {})
        for key, default in _PREF_DEFAULTS.items():
            st.session_state[key] = saved.get(key, default)
    except Exception:
        pass  # DB error → keep defaults already in session_state


def save_user_prefs(user_id: str) -> None:
    """Upsert all current preference values to Supabase. Non-fatal on error."""
    if not user_id:
        return
    try:
        prefs = {k: st.session_state.get(k, v) for k, v in _PREF_DEFAULTS.items()}
        get_db().table("user_preferences").upsert(
            {"user_id": user_id, "prefs": prefs},
            on_conflict="user_id",
        ).execute()
    except Exception:
        pass


def _pref(key: str):
    """Get preference from session state, falling back to default."""
    return st.session_state.get(key, _PREF_DEFAULTS[key])


def _set_pref(key: str, value) -> None:
    st.session_state[key] = value
    user_id = st.session_state.get("user_id")
    if user_id:
        save_user_prefs(user_id)


# ============================================================
# Tab renderers
# ============================================================

def _render_appearance():
    st.markdown("### Themes")
    st.caption("Choose a colour palette for the entire app. Changes apply immediately.")

    current = _pref("gxp_theme")
    dark_themes  = {k: v for k, v in THEMES.items() if not v.get("light")}
    light_themes = {k: v for k, v in THEMES.items() if v.get("light")}

    def _draw_group(group: dict):
        # Build fresh columns per row of 4 — never re-enter a closed column context
        items = list(group.items())
        for row_start in range(0, len(items), 4):
            row = items[row_start : row_start + 4]
            cols = st.columns(4)
            for col, (key, theme) in zip(cols, row):
                with col:
                    vars_      = theme["vars"]
                    is_active  = key == current
                    accent     = vars_["--gxp-accent"]
                    surface    = vars_["--gxp-surface"]
                    text       = vars_["--gxp-text"]
                    bdr_color  = vars_["--gxp-border"]
                    is_light   = theme.get("light", False)
                    border     = (f"2.5px solid {accent}" if is_active
                                  else f"1px solid {bdr_color}")
                    swatch_bdr = "rgba(0,0,0,0.12)" if is_light else "rgba(255,255,255,0.15)"

                    swatches = "".join(
                        f'<span style="display:inline-block;width:14px;height:14px;'
                        f'border-radius:50%;background:{c};margin-right:4px;'
                        f'border:1px solid {swatch_bdr};vertical-align:middle;"></span>'
                        for c in theme["swatches"]
                    )
                    check_icon = '<span class="mdi mdi-check" style="font-size:18px;"></span>' if is_active else ""

                    # Single-line HTML — avoids Streamlit markdown parser choking on newlines
                    card_html = (
                        f'<div style="border:{border};border-radius:10px;padding:12px;'
                        f'background:{surface};margin-bottom:6px;'
                        f'box-shadow:0 1px 3px rgba(0,0,0,0.08);">'
                        f'<div style="font-size:20px;margin-bottom:4px;color:{text};">{theme["emoji"]}</div>'
                        f'<div style="font-size:12px;font-weight:700;color:{text};'
                        f'margin-bottom:6px;">{check_icon}{theme["label"]}</div>'
                        f'<div>{swatches}</div>'
                        f'</div>'
                    )
                    st.markdown(card_html, unsafe_allow_html=True)

                    if not is_active:
                        if st.button("Apply", key=f"pref_theme_{key}",
                                     use_container_width=True):
                            _set_pref("gxp_theme", key)
                            st.rerun()
                    else:
                        st.markdown(
                            f'<div style="text-align:center;font-size:11px;'
                            f'color:{accent};font-weight:600;padding-bottom:4px;">'
                            f'● Active</div>',
                            unsafe_allow_html=True,
                        )

    col_light, col_dark = st.columns(2)

    with col_light:
        st.markdown(
            "<div style='font-size:11px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.8px;color:var(--gxp-text2);margin:0 0 8px;'>"
            '<span class="mdi mdi-white-balance-sunny" style="font-size:18px;"></span> Light Themes</div>',
            unsafe_allow_html=True,
        )
        _draw_group(light_themes)

    with col_dark:
        st.markdown(
            "<div style='font-size:11px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.8px;color:var(--gxp-text2);margin:0 0 8px;'>"
            '<span class="mdi mdi-weather-night" style="font-size:18px;"></span> Dark Themes</div>',
            unsafe_allow_html=True,
        )
        _draw_group(dark_themes)


def _render_formats():
    st.markdown("### Date & Time")
    st.caption("Controls how dates and times appear across the app.")

    c1, c2 = st.columns(2)

    with c1:
        cur_date = _pref("gxp_date_format")
        new_date = st.selectbox(
            "Date Format",
            DATE_FORMAT_OPTIONS,
            index=DATE_FORMAT_OPTIONS.index(cur_date),
            format_func=lambda f: f"{DATE_FORMAT_EXAMPLES[f]}  ({f})",
            key="pref_date_fmt",
        )
        if new_date != cur_date:
            _set_pref("gxp_date_format", new_date)
            st.rerun()

        cur_week = _pref("gxp_week_start")
        new_week = st.selectbox(
            "Week Starts On",
            ["Monday", "Sunday"],
            index=0 if cur_week == "Monday" else 1,
            key="pref_week_start",
        )
        if new_week != cur_week:
            _set_pref("gxp_week_start", new_week)
            st.rerun()

    with c2:
        cur_time = _pref("gxp_time_format")
        new_time = st.radio(
            "Time Format",
            ["12h", "24h"],
            index=0 if cur_time == "12h" else 1,
            format_func=lambda x: ("12-hour  (2:30 PM)" if x == "12h"
                                   else "24-hour  (14:30)"),
            key="pref_time_fmt",
        )
        if new_time != cur_time:
            _set_pref("gxp_time_format", new_time)
            st.rerun()

    st.divider()
    st.markdown("### Currency Display")
    st.info("Currency symbol (₱) always appears before the amount — e.g. **₱ 12,500.00**", icon="ℹ️")


def _render_display():
    st.markdown("### Display Options")
    st.caption("Controls layout density and default navigation behaviour.")

    c1, c2 = st.columns(2)

    with c1:
        cur_density = _pref("gxp_table_density")
        density_opts = ["compact", "normal", "relaxed"]
        density_labels = {
            "compact":  "Compact  — more rows visible",
            "normal":   "Normal  — balanced spacing",
            "relaxed":  "Relaxed  — more breathing room",
        }
        new_density = st.radio(
            "Table Row Density",
            density_opts,
            index=density_opts.index(cur_density),
            format_func=lambda x: density_labels[x],
            key="pref_table_density",
        )
        if st.button(
            "Apply Density",
            key="pref_apply_density",
            type="primary",
            icon="✅",
        ):
            if new_density != cur_density:
                _set_pref("gxp_table_density", new_density)
                st.success("Row density updated!")
                st.rerun()

    with c2:
        cur_page = _pref("gxp_default_page")
        new_page = st.selectbox(
            "Default Landing Page",
            PAGES_LIST,
            index=PAGES_LIST.index(cur_page) if cur_page in PAGES_LIST else 0,
            help="The page that opens first after you log in.",
            key="pref_default_page",
        )
        if new_page != cur_page:
            _set_pref("gxp_default_page", new_page)
            st.rerun()

    st.divider()
    st.markdown("### Numbers")

    # Preview density with a small sample table
    density_px = {"compact": 24, "normal": 36, "relaxed": 52}
    row_h = density_px.get(_pref("gxp_table_density"), 36)
    sample_rows = ""
    for name, val in [("Juan Santos", "₱ 28,500"), ("Maria Reyes", "₱ 32,100"), ("Carlos Tan", "₱ 45,800")]:
        sample_rows += (
            f'<tr><td style="padding:0 12px;height:{row_h}px;'
            f'border-bottom:1px solid var(--gxp-border);color:var(--gxp-text);">'
            f'{name}</td>'
            f'<td style="padding:0 12px;height:{row_h}px;'
            f'border-bottom:1px solid var(--gxp-border);color:var(--gxp-text);'
            f'text-align:right;font-family:monospace;">{val}</td></tr>'
        )
    st.markdown(
        f'<div style="font-size:11px;font-weight:600;color:var(--gxp-text2);'
        f'text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">'
        f'Row density preview</div>'
        f'<table style="width:100%;border-collapse:collapse;'
        f'background:var(--gxp-surface);border-radius:8px;overflow:hidden;'
        f'border:1px solid var(--gxp-border);">'
        f'<thead><tr>'
        f'<th style="padding:8px 12px;text-align:left;font-size:11px;'
        f'color:var(--gxp-text2);background:var(--gxp-surface2);">Employee</th>'
        f'<th style="padding:8px 12px;text-align:right;font-size:11px;'
        f'color:var(--gxp-text2);background:var(--gxp-surface2);">Salary</th>'
        f'</tr></thead><tbody>{sample_rows}</tbody></table>',
        unsafe_allow_html=True,
    )


def _render_notifications():
    st.markdown("### Notifications")
    st.info(
        "Notification preferences are coming in a future update. "
        "You'll be able to configure email alerts for payroll deadlines, "
        "government remittance due dates, and leave request approvals.",
        icon="🚧",
    )

    st.markdown("#### Planned options")
    coming_soon = [
        ('<span class="mdi mdi-email" style="font-size:18px;"></span> Payroll deadline reminders', "Get an email X days before each pay date"),
        ('<span class="mdi mdi-bank" style="font-size:18px;"></span> Government remittance alerts', "SSS, PhilHealth, Pag-IBIG, BIR due-date notices"),
        ('<span class="mdi mdi-clipboard-text" style="font-size:18px;"></span> Leave request notifications', "Email when an employee submits a leave request"),
        ('<span class="mdi mdi-cash-multiple" style="font-size:18px;"></span> Payslip availability', "Notify employees when their payslip is ready"),
        ('<span class="mdi mdi-alert" style="font-size:18px;"></span> Compliance warnings', "Alert when statutory contributions are out of date"),
    ]
    for title, desc in coming_soon:
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;gap:10px;'
            f'padding:10px 14px;border:1px solid var(--gxp-border);'
            f'border-radius:8px;background:var(--gxp-surface);margin-bottom:6px;">'
            f'<div style="flex:1;">'
            f'<div style="font-size:13px;font-weight:600;color:var(--gxp-text);">{title}</div>'
            f'<div style="font-size:12px;color:var(--gxp-text2);margin-top:2px;">{desc}</div>'
            f'</div>'
            f'<span style="font-size:11px;background:var(--gxp-surface2);'
            f'color:var(--gxp-text3);padding:2px 8px;border-radius:10px;'
            f'font-weight:600;white-space:nowrap;">Soon</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# Main render
# ============================================================

def render(standalone: bool = True):
    if standalone:
        inject_css()
        st.title("Preferences")
        st.caption("Personalise how GenXcript Payroll looks and behaves for you.")

    tab_appearance, tab_formats, tab_display, tab_notif = st.tabs([
        "Appearance",
        "Formats",
        "Display",
        "Notifications",
    ])

    with tab_appearance:
        _render_appearance()

    with tab_formats:
        _render_formats()

    with tab_display:
        _render_display()

    with tab_notif:
        _render_notifications()
