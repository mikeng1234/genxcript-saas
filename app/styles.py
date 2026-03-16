"""
Shared UI styles and helper functions for GenXcript Payroll.

Provides consistent CSS tokens, status badges, and styled components
reusable across all pages. Call inject_css() once per page render.
"""

import streamlit as st


# ============================================================
# Color Tokens (semantic)
# ============================================================

STATUS_COLORS = {
    "draft":     {"bg": "#dbeafe", "fg": "#1e40af", "label": "DRAFT"},
    "reviewed":  {"bg": "#ede9fe", "fg": "#5b21b6", "label": "REVIEWED"},
    "finalized": {"bg": "#fef3c7", "fg": "#92400e", "label": "FINALIZED"},
    "paid":      {"bg": "#d1fae5", "fg": "#065f46", "label": "PAID"},
}

URGENCY_COLORS = {
    "overdue":  "#dc2626",
    "warning":  "#d97706",
    "ok":       "#16a34a",
}

GOV_COLORS = {
    "SSS":        "#7c3aed",
    "PhilHealth": "#0891b2",
    "Pag-IBIG":   "#059669",
    "BIR":        "#dc2626",
}


# ============================================================
# CSS Injection
# ============================================================

def inject_css():
    """Inject shared CSS. Call once at the top of each page render()."""
    st.markdown("""
    <style>
    /* ── Status Badges ────────────────────────────── */
    .gxp-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.3px;
        line-height: 1.6;
    }
    .gxp-badge-draft     { background: #dbeafe; color: #1e40af; }
    .gxp-badge-reviewed  { background: #ede9fe; color: #5b21b6; }
    .gxp-badge-finalized { background: #fef3c7; color: #92400e; }
    .gxp-badge-paid      { background: #d1fae5; color: #065f46; }

    /* ── Urgency Dots ─────────────────────────────── */
    .gxp-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
    }
    .gxp-dot-overdue { background: #dc2626; }
    .gxp-dot-warning { background: #d97706; }
    .gxp-dot-ok      { background: #16a34a; }

    /* ── Section Cards ────────────────────────────── */
    .gxp-card {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px;
        background: #fafafa;
        margin-bottom: 8px;
    }

    /* ── Section Headers ──────────────────────────── */
    .gxp-section-header {
        font-size: 15px;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 8px;
        padding-bottom: 8px;
        border-bottom: 2px solid #e5e7eb;
    }

    /* ── Info Bar (status line) ────────────────────── */
    .gxp-info-bar {
        padding: 10px 16px;
        border-radius: 8px;
        font-size: 13px;
        margin-bottom: 16px;
        border-left: 4px solid;
    }
    .gxp-info-bar-draft     { background: #eff6ff; border-color: #3b82f6; }
    .gxp-info-bar-reviewed  { background: #f5f3ff; border-color: #7c3aed; }
    .gxp-info-bar-finalized { background: #fffbeb; border-color: #f59e0b; }
    .gxp-info-bar-paid      { background: #ecfdf5; border-color: #10b981; }

    /* ── Financial Table ──────────────────────────── */
    .gxp-fin-table {
        width: 100%;
        font-size: 13px;
        border-collapse: collapse;
    }
    .gxp-fin-table td {
        padding: 4px 0;
        font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
    }
    .gxp-fin-table td:first-child {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        color: #6b7280;
        padding-right: 12px;
    }
    .gxp-fin-table td:last-child {
        text-align: right;
        font-weight: 500;
        color: #1f2937;
    }
    .gxp-fin-table tr.gxp-fin-total td {
        border-top: 1px solid #d1d5db;
        font-weight: 700;
        padding-top: 8px;
    }

    /* ── Remittance Grid ──────────────────────────── */
    .gxp-remit-card {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 12px 16px;
        background: #f9fafb;
        border-top: 3px solid;
    }
    .gxp-remit-card h4 {
        font-size: 13px;
        font-weight: 700;
        margin: 0 0 8px 0;
    }
    .gxp-remit-card .gxp-remit-row {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        padding: 2px 0;
        color: #4b5563;
    }
    .gxp-remit-card .gxp-remit-row span:last-child {
        font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
        font-weight: 500;
    }
    .gxp-remit-card .gxp-remit-total {
        border-top: 1px solid #d1d5db;
        margin-top: 4px;
        padding-top: 6px;
        font-weight: 700;
        font-size: 13px;
        display: flex;
        justify-content: space-between;
    }
    .gxp-remit-card .gxp-remit-total span:last-child {
        font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
    }

    /* ── Deadline List ────────────────────────────── */
    .gxp-deadline {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 8px 0;
        border-bottom: 1px solid #f3f4f6;
    }
    .gxp-deadline:last-child { border-bottom: none; }
    .gxp-deadline-info {
        flex: 1;
    }
    .gxp-deadline-agency {
        font-weight: 600;
        font-size: 13px;
        color: #1f2937;
    }
    .gxp-deadline-desc {
        font-size: 12px;
        color: #6b7280;
        margin-top: 1px;
    }
    .gxp-deadline-date {
        font-size: 12px;
        font-weight: 600;
        color: #374151;
        text-align: right;
        white-space: nowrap;
    }
    .gxp-deadline-status {
        font-size: 11px;
        color: #6b7280;
        text-align: right;
    }

    /* ── Progress Bar ─────────────────────────────── */
    .gxp-progress {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
    }
    .gxp-progress-bar {
        flex: 1;
        height: 6px;
        background: #e5e7eb;
        border-radius: 3px;
        overflow: hidden;
    }
    .gxp-progress-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s;
    }
    .gxp-progress-label {
        font-size: 12px;
        color: #6b7280;
        white-space: nowrap;
    }

    /* ── Edit Panel ───────────────────────────────── */
    .gxp-edit-panel {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 24px;
    }
    .gxp-edit-panel-title {
        font-size: 14px;
        font-weight: 700;
        color: #1e40af;
        margin-bottom: 4px;
    }
    .gxp-edit-panel-desc {
        font-size: 12px;
        color: #6b7280;
        margin-bottom: 12px;
    }

    /* ── Period Card ───────────────────────────────── */
    .gxp-period-card {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 14px 16px;
        background: #fafafa;
        min-height: 110px;
    }
    .gxp-period-card-empty {
        border: 1px dashed #d1d5db;
        border-radius: 8px;
        padding: 14px 16px;
        background: #f9fafb;
        min-height: 110px;
        text-align: center;
    }
    .gxp-period-slot {
        font-size: 11px;
        color: #6b7280;
        margin-bottom: 3px;
    }
    .gxp-period-dates {
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 8px;
        color: #1f2937;
    }
    .gxp-period-stats {
        margin-top: 10px;
        font-size: 12px;
        color: #4b5563;
    }
    .gxp-period-gross {
        font-size: 11px;
        color: #9ca3af;
        margin-top: 2px;
    }

    /* ── ADP-Style Action Bar ────────────────────────── */
    .gxp-action-bar {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
    }
    .gxp-action-bar-left {
        flex: 1;
    }
    .gxp-action-bar-greeting {
        font-size: 20px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 4px;
    }
    .gxp-action-bar-sub {
        font-size: 13px;
        color: #94a3b8;
    }
    .gxp-action-bar-sub strong {
        color: #60a5fa;
    }
    .gxp-action-bar-right {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .gxp-action-bar-next {
        text-align: right;
    }
    .gxp-action-bar-next-label {
        font-size: 11px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .gxp-action-bar-next-date {
        font-size: 15px;
        font-weight: 600;
        color: #ffffff;
    }

    /* ── ADP-Style Alert Cards ───────────────────────── */
    .gxp-alerts-section {
        margin-bottom: 24px;
    }
    .gxp-alert-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
        border-left: 4px solid;
    }
    .gxp-alert-overdue {
        background: #fef2f2;
        border-color: #dc2626;
    }
    .gxp-alert-warning {
        background: #fffbeb;
        border-color: #d97706;
    }
    .gxp-alert-info {
        background: #eff6ff;
        border-color: #3b82f6;
    }
    .gxp-alert-icon {
        font-size: 18px;
        flex-shrink: 0;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .gxp-alert-overdue .gxp-alert-icon { background: #fee2e2; color: #dc2626; }
    .gxp-alert-warning .gxp-alert-icon { background: #fef3c7; color: #d97706; }
    .gxp-alert-info .gxp-alert-icon    { background: #dbeafe; color: #3b82f6; }
    .gxp-alert-body {
        flex: 1;
    }
    .gxp-alert-title {
        font-size: 13px;
        font-weight: 600;
        color: #1f2937;
    }
    .gxp-alert-desc {
        font-size: 12px;
        color: #6b7280;
        margin-top: 1px;
    }
    .gxp-alert-action {
        font-size: 12px;
        font-weight: 600;
        color: #374151;
        white-space: nowrap;
    }

    /* ── Global: buttons never wrap text ─────────────── */
    [data-testid="stBaseButton-primary"] > button,
    [data-testid="stBaseButton-secondary"] > button {
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* ── Alert Navigation Buttons (pill style) ───────── */
    .gxp-alert-nav-btn [data-testid="stBaseButton-secondary"] > button {
        border-radius: 20px !important;
        font-size: 11px !important;
        padding: 4px 14px !important;
        border-width: 1.5px !important;
    }

    /* ── Quick Action Buttons Row ────────────────────── */
    .gxp-quick-actions {
        margin-top: -12px;
        margin-bottom: 24px;
    }

    /* ── ADP-Style Stat Cards ────────────────────────── */
    .gxp-stat-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 18px 16px;
        position: relative;
        overflow: hidden;
        height: 100%;
    }
    .gxp-stat-icon {
        width: 38px;
        height: 38px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 12px;
    }
    .gxp-stat-icon svg {
        display: block;
    }
    .gxp-stat-label {
        font-size: 11px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .gxp-stat-value {
        font-size: 20px;
        font-weight: 700;
        color: #0f172a;
        font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
        line-height: 1.2;
    }
    .gxp-stat-trend-row {
        margin-top: 3px;
        margin-bottom: 2px;
    }
    .gxp-stat-trend {
        font-size: 11px;
        font-weight: 600;
        padding: 1px 6px;
        border-radius: 4px;
    }
    .gxp-stat-trend-up      { color: #059669; background: #d1fae5; }
    .gxp-stat-trend-down    { color: #dc2626; background: #fee2e2; }
    .gxp-stat-trend-neutral { color: #6b7280; background: #f3f4f6; }
    .gxp-stat-sub {
        font-size: 11px;
        color: #9ca3af;
        margin-top: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* ── ADP-Style Last Payroll Summary ──────────────── */
    .gxp-summary-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 20px 24px;
        margin-bottom: 24px;
    }
    .gxp-summary-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid #f3f4f6;
    }
    .gxp-summary-title {
        font-size: 15px;
        font-weight: 700;
        color: #0f172a;
    }
    .gxp-summary-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
    }
    .gxp-summary-item {
        text-align: center;
        padding: 8px 0;
    }
    .gxp-summary-item-label {
        font-size: 11px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        margin-bottom: 4px;
    }
    .gxp-summary-item-value {
        font-size: 16px;
        font-weight: 600;
        color: #1f2937;
        font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
    }

    /* ── Employee Portal Hero ────────────────────────── */
    .gxp-portal-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 20px;
    }
    .gxp-portal-hero-avatar {
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: linear-gradient(135deg, #3b82f6, #06b6d4);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        font-weight: 700;
        color: #ffffff;
        flex-shrink: 0;
        letter-spacing: -0.5px;
    }
    .gxp-portal-hero-info {
        flex: 1;
    }
    .gxp-portal-hero-name {
        font-size: 20px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 3px;
    }
    .gxp-portal-hero-meta {
        font-size: 13px;
        color: #60a5fa;
        font-weight: 500;
        margin-bottom: 2px;
    }
    .gxp-portal-hero-sub {
        font-size: 12px;
        color: #94a3b8;
    }

    /* ── Employee Portal Payslip Cards ───────────────── */
    .gxp-payslip-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 20px 24px 4px 24px;
        margin-bottom: 4px;
        border-left: 4px solid #2563eb;
    }
    .gxp-payslip-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 12px;
        padding-bottom: 12px;
        border-bottom: 1px solid #f3f4f6;
    }
    .gxp-payslip-period {
        font-size: 15px;
        font-weight: 700;
        color: #0f172a;
    }
    .gxp-payslip-payment {
        font-size: 12px;
        color: #6b7280;
        margin-top: 3px;
    }
    .gxp-payslip-net {
        font-size: 22px;
        font-weight: 700;
        color: #059669;
        font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
        text-align: right;
    }
    .gxp-payslip-net-label {
        font-size: 12px;
        font-weight: 400;
        color: #6b7280;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    .gxp-payslip-section-label {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #9ca3af;
        margin-top: 12px;
        margin-bottom: 4px;
    }

    /* ── ADP-Style Section Panel ─────────────────────── */
    .gxp-panel {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 20px 24px;
        margin-bottom: 24px;
    }
    .gxp-panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
    }
    .gxp-panel-title {
        font-size: 15px;
        font-weight: 700;
        color: #0f172a;
    }
    .gxp-panel-subtitle {
        font-size: 12px;
        color: #6b7280;
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# Component Helpers
# ============================================================

def status_badge(status: str) -> str:
    """Return HTML for a status badge. Use inside st.markdown(unsafe_allow_html=True)."""
    info = STATUS_COLORS.get(status, {"bg": "#e5e7eb", "fg": "#374151", "label": status.upper()})
    return f'<span class="gxp-badge gxp-badge-{status}">{info["label"]}</span>'


def urgency_dot(days_until: int) -> str:
    """Return HTML for an urgency indicator dot."""
    if days_until < 0:
        cls = "overdue"
    elif days_until <= 3:
        cls = "warning"
    else:
        cls = "ok"
    return f'<span class="gxp-dot gxp-dot-{cls}"></span>'


def section_header(title: str, edit_mode: bool = False) -> str:
    """Return HTML for a section header."""
    faded = "color:#9ca3af;" if edit_mode else ""
    prefix = "&#9776; " if edit_mode else ""
    return (
        f'<div class="gxp-section-header" style="{faded}">'
        f'{prefix}{title}</div>'
    )


def info_bar(status: str, text: str) -> str:
    """Return HTML for a colored info bar based on status."""
    return f'<div class="gxp-info-bar gxp-info-bar-{status}">{text}</div>'


def fin_table(rows: list[tuple[str, str]], total: tuple[str, str] | None = None) -> str:
    """Return HTML for a financial breakdown table.

    rows: list of (label, formatted_value) tuples
    total: optional (label, formatted_value) for the total row
    """
    html = '<table class="gxp-fin-table">'
    for label, value in rows:
        html += f'<tr><td>{label}</td><td>{value}</td></tr>'
    if total:
        html += f'<tr class="gxp-fin-total"><td>{total[0]}</td><td>{total[1]}</td></tr>'
    html += '</table>'
    return html


def remit_card(title: str, color: str, rows: list[tuple[str, str]], total: tuple[str, str]) -> str:
    """Return HTML for a government remittance card."""
    html = f'<div class="gxp-remit-card" style="border-top-color:{color}">'
    html += f'<h4>{title}</h4>'
    for label, value in rows:
        html += f'<div class="gxp-remit-row"><span>{label}</span><span>{value}</span></div>'
    html += f'<div class="gxp-remit-total"><span>{total[0]}</span><span>{total[1]}</span></div>'
    html += '</div>'
    return html


def progress_bar(current: int, total: int, label: str = "") -> str:
    """Return HTML for a progress indicator."""
    pct = (current / total * 100) if total > 0 else 0
    color = "#16a34a" if current == total else "#3b82f6"
    lbl = label or f"{current} of {total}"
    return (
        f'<div class="gxp-progress">'
        f'<div class="gxp-progress-bar">'
        f'<div class="gxp-progress-fill" style="width:{pct:.0f}%;background:{color}"></div>'
        f'</div>'
        f'<div class="gxp-progress-label">{lbl}</div>'
        f'</div>'
    )
