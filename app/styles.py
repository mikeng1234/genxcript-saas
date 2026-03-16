"""
Shared UI styles, themes, and helper functions for GenXcript Payroll.

Provides semantic CSS tokens via custom properties, named pastel themes,
status badges, and styled components reusable across all pages.
Call inject_css() once per page render.
"""

import streamlit as st


# ============================================================
# Themes
# ============================================================

THEMES: dict[str, dict] = {
    "midnight": {
        "label": "Midnight Navy",
        "emoji": "🌙",
        "swatches": ["#0f172a", "#1e2530", "#3b82f6", "#93c5fd"],
        "vars": {
            "--gxp-bg":         "#0f172a",
            "--gxp-surface":    "#1e2530",
            "--gxp-surface2":   "#161d28",
            "--gxp-border":     "#2d3748",
            "--gxp-text":       "#e2e8f0",
            "--gxp-text2":      "#94a3b8",
            "--gxp-text3":      "#64748b",
            "--gxp-accent":     "#3b82f6",
            "--gxp-accent-bg":  "#1e3a5f",
            "--gxp-accent-fg":  "#93c5fd",
            "--gxp-success":    "#10b981",
            "--gxp-success-bg": "#064e3b",
            "--gxp-success-fg": "#6ee7b7",
            "--gxp-warning":    "#f59e0b",
            "--gxp-warning-bg": "#3b2f0a",
            "--gxp-warning-fg": "#fde68a",
            "--gxp-danger":     "#ef4444",
            "--gxp-danger-bg":  "#3b1515",
            "--gxp-danger-fg":  "#fca5a5",
        },
    },
    "lavender": {
        "label": "Lavender Dusk",
        "emoji": "💜",
        "swatches": ["#100d1e", "#1a1530", "#a78bfa", "#ddd6fe"],
        "vars": {
            "--gxp-bg":         "#100d1e",
            "--gxp-surface":    "#1a1530",
            "--gxp-surface2":   "#130f26",
            "--gxp-border":     "#2e2550",
            "--gxp-text":       "#ede9fe",
            "--gxp-text2":      "#a89bc2",
            "--gxp-text3":      "#6b5f8a",
            "--gxp-accent":     "#a78bfa",
            "--gxp-accent-bg":  "#2e1d5e",
            "--gxp-accent-fg":  "#ddd6fe",
            "--gxp-success":    "#34d399",
            "--gxp-success-bg": "#0a3028",
            "--gxp-success-fg": "#a7f3d0",
            "--gxp-warning":    "#fbbf24",
            "--gxp-warning-bg": "#3b2c0a",
            "--gxp-warning-fg": "#fde68a",
            "--gxp-danger":     "#f87171",
            "--gxp-danger-bg":  "#3b1515",
            "--gxp-danger-fg":  "#fca5a5",
        },
    },
    "forest": {
        "label": "Forest Moss",
        "emoji": "🌿",
        "swatches": ["#0d1a12", "#162118", "#4ade80", "#bbf7d0"],
        "vars": {
            "--gxp-bg":         "#0d1a12",
            "--gxp-surface":    "#162118",
            "--gxp-surface2":   "#0f1c14",
            "--gxp-border":     "#1f3d29",
            "--gxp-text":       "#dcfce7",
            "--gxp-text2":      "#86a892",
            "--gxp-text3":      "#4d7a58",
            "--gxp-accent":     "#4ade80",
            "--gxp-accent-bg":  "#0a3020",
            "--gxp-accent-fg":  "#bbf7d0",
            "--gxp-success":    "#34d399",
            "--gxp-success-bg": "#064e3b",
            "--gxp-success-fg": "#a7f3d0",
            "--gxp-warning":    "#fbbf24",
            "--gxp-warning-bg": "#3b2f0a",
            "--gxp-warning-fg": "#fde68a",
            "--gxp-danger":     "#f87171",
            "--gxp-danger-bg":  "#3b1515",
            "--gxp-danger-fg":  "#fca5a5",
        },
    },
    "rose": {
        "label": "Rose Quartz",
        "emoji": "🌹",
        "swatches": ["#1a1014", "#251520", "#fb7185", "#fecdd3"],
        "vars": {
            "--gxp-bg":         "#1a1014",
            "--gxp-surface":    "#251520",
            "--gxp-surface2":   "#1e1218",
            "--gxp-border":     "#3d2030",
            "--gxp-text":       "#fff1f2",
            "--gxp-text2":      "#c09aaa",
            "--gxp-text3":      "#7a5566",
            "--gxp-accent":     "#fb7185",
            "--gxp-accent-bg":  "#4c1629",
            "--gxp-accent-fg":  "#fecdd3",
            "--gxp-success":    "#34d399",
            "--gxp-success-bg": "#064e3b",
            "--gxp-success-fg": "#a7f3d0",
            "--gxp-warning":    "#fbbf24",
            "--gxp-warning-bg": "#3b2f0a",
            "--gxp-warning-fg": "#fde68a",
            "--gxp-danger":     "#f87171",
            "--gxp-danger-bg":  "#3b1515",
            "--gxp-danger-fg":  "#fca5a5",
        },
    },
    "amber": {
        "label": "Amber Ember",
        "emoji": "🔥",
        "swatches": ["#1a1508", "#251e0d", "#fbbf24", "#fef3c7"],
        "vars": {
            "--gxp-bg":         "#1a1508",
            "--gxp-surface":    "#251e0d",
            "--gxp-surface2":   "#1e1a0a",
            "--gxp-border":     "#3d3010",
            "--gxp-text":       "#fffbeb",
            "--gxp-text2":      "#bba060",
            "--gxp-text3":      "#7a6530",
            "--gxp-accent":     "#fbbf24",
            "--gxp-accent-bg":  "#4c3508",
            "--gxp-accent-fg":  "#fef3c7",
            "--gxp-success":    "#34d399",
            "--gxp-success-bg": "#064e3b",
            "--gxp-success-fg": "#a7f3d0",
            "--gxp-warning":    "#f59e0b",
            "--gxp-warning-bg": "#3b2f0a",
            "--gxp-warning-fg": "#fde68a",
            "--gxp-danger":     "#f87171",
            "--gxp-danger-bg":  "#3b1515",
            "--gxp-danger-fg":  "#fca5a5",
        },
    },
    "ocean": {
        "label": "Ocean Mist",
        "emoji": "🌊",
        "swatches": ["#0d1820", "#132030", "#22d3ee", "#a5f3fc"],
        "vars": {
            "--gxp-bg":         "#0d1820",
            "--gxp-surface":    "#132030",
            "--gxp-surface2":   "#0f1c28",
            "--gxp-border":     "#1e3a4a",
            "--gxp-text":       "#e0f9ff",
            "--gxp-text2":      "#72a8b8",
            "--gxp-text3":      "#3d6a7a",
            "--gxp-accent":     "#22d3ee",
            "--gxp-accent-bg":  "#0a3040",
            "--gxp-accent-fg":  "#a5f3fc",
            "--gxp-success":    "#34d399",
            "--gxp-success-bg": "#064e3b",
            "--gxp-success-fg": "#a7f3d0",
            "--gxp-warning":    "#fbbf24",
            "--gxp-warning-bg": "#3b2f0a",
            "--gxp-warning-fg": "#fde68a",
            "--gxp-danger":     "#f87171",
            "--gxp-danger-bg":  "#3b1515",
            "--gxp-danger-fg":  "#fca5a5",
        },
    },
    "sakura": {
        "label": "Sakura",
        "emoji": "🌸",
        "swatches": ["#180f14", "#221520", "#f472b6", "#fce7f3"],
        "vars": {
            "--gxp-bg":         "#180f14",
            "--gxp-surface":    "#221520",
            "--gxp-surface2":   "#1c1018",
            "--gxp-border":     "#3d2035",
            "--gxp-text":       "#fce7f3",
            "--gxp-text2":      "#c08aaa",
            "--gxp-text3":      "#7a4566",
            "--gxp-accent":     "#f472b6",
            "--gxp-accent-bg":  "#4a1040",
            "--gxp-accent-fg":  "#fce7f3",
            "--gxp-success":    "#34d399",
            "--gxp-success-bg": "#064e3b",
            "--gxp-success-fg": "#a7f3d0",
            "--gxp-warning":    "#fbbf24",
            "--gxp-warning-bg": "#3b2f0a",
            "--gxp-warning-fg": "#fde68a",
            "--gxp-danger":     "#f87171",
            "--gxp-danger-bg":  "#3b1515",
            "--gxp-danger-fg":  "#fca5a5",
        },
    },
    "slate": {
        "label": "Charcoal Slate",
        "emoji": "🪨",
        "swatches": ["#111827", "#1f2937", "#60a5fa", "#bfdbfe"],
        "vars": {
            "--gxp-bg":         "#111827",
            "--gxp-surface":    "#1f2937",
            "--gxp-surface2":   "#1a2233",
            "--gxp-border":     "#374151",
            "--gxp-text":       "#f9fafb",
            "--gxp-text2":      "#9ca3af",
            "--gxp-text3":      "#6b7280",
            "--gxp-accent":     "#60a5fa",
            "--gxp-accent-bg":  "#1e3a5f",
            "--gxp-accent-fg":  "#bfdbfe",
            "--gxp-success":    "#34d399",
            "--gxp-success-bg": "#064e3b",
            "--gxp-success-fg": "#a7f3d0",
            "--gxp-warning":    "#fbbf24",
            "--gxp-warning-bg": "#3b2f0a",
            "--gxp-warning-fg": "#fde68a",
            "--gxp-danger":     "#f87171",
            "--gxp-danger-bg":  "#3b1515",
            "--gxp-danger-fg":  "#fca5a5",
        },
    },

    # ── Light Themes ─────────────────────────────────────────
    "cloud": {
        "label": "Cloud",
        "emoji": "☁️",
        "light": True,
        "swatches": ["#f8fafc", "#ffffff", "#3b82f6", "#1e40af"],
        "vars": {
            "--gxp-bg":         "#f0f4f8",
            "--gxp-surface":    "#ffffff",
            "--gxp-surface2":   "#f1f5f9",
            "--gxp-border":     "#e2e8f0",
            "--gxp-text":       "#0f172a",
            "--gxp-text2":      "#475569",
            "--gxp-text3":      "#94a3b8",
            "--gxp-accent":     "#3b82f6",
            "--gxp-accent-bg":  "#dbeafe",
            "--gxp-accent-fg":  "#1e40af",
            "--gxp-success":    "#059669",
            "--gxp-success-bg": "#d1fae5",
            "--gxp-success-fg": "#065f46",
            "--gxp-warning":    "#d97706",
            "--gxp-warning-bg": "#fef3c7",
            "--gxp-warning-fg": "#92400e",
            "--gxp-danger":     "#dc2626",
            "--gxp-danger-bg":  "#fee2e2",
            "--gxp-danger-fg":  "#991b1b",
        },
    },
    "parchment": {
        "label": "Parchment",
        "emoji": "📜",
        "light": True,
        "swatches": ["#fdf8f0", "#ffffff", "#b45309", "#78350f"],
        "vars": {
            "--gxp-bg":         "#fdf8f0",
            "--gxp-surface":    "#fffdf7",
            "--gxp-surface2":   "#f5efe0",
            "--gxp-border":     "#e8d8b8",
            "--gxp-text":       "#1c1408",
            "--gxp-text2":      "#6b4f2a",
            "--gxp-text3":      "#a87c4a",
            "--gxp-accent":     "#b45309",
            "--gxp-accent-bg":  "#fef3c7",
            "--gxp-accent-fg":  "#78350f",
            "--gxp-success":    "#059669",
            "--gxp-success-bg": "#d1fae5",
            "--gxp-success-fg": "#065f46",
            "--gxp-warning":    "#d97706",
            "--gxp-warning-bg": "#fef9c3",
            "--gxp-warning-fg": "#92400e",
            "--gxp-danger":     "#dc2626",
            "--gxp-danger-bg":  "#fee2e2",
            "--gxp-danger-fg":  "#991b1b",
        },
    },
    "mint": {
        "label": "Mint Fresh",
        "emoji": "🍃",
        "light": True,
        "swatches": ["#f0fdf4", "#ffffff", "#059669", "#065f46"],
        "vars": {
            "--gxp-bg":         "#f0fdf8",
            "--gxp-surface":    "#ffffff",
            "--gxp-surface2":   "#ecfdf5",
            "--gxp-border":     "#d1fae5",
            "--gxp-text":       "#064e3b",
            "--gxp-text2":      "#047857",
            "--gxp-text3":      "#6ee7b7",
            "--gxp-accent":     "#059669",
            "--gxp-accent-bg":  "#d1fae5",
            "--gxp-accent-fg":  "#065f46",
            "--gxp-success":    "#059669",
            "--gxp-success-bg": "#d1fae5",
            "--gxp-success-fg": "#065f46",
            "--gxp-warning":    "#d97706",
            "--gxp-warning-bg": "#fef3c7",
            "--gxp-warning-fg": "#92400e",
            "--gxp-danger":     "#dc2626",
            "--gxp-danger-bg":  "#fee2e2",
            "--gxp-danger-fg":  "#991b1b",
        },
    },
    "blush": {
        "label": "Blush",
        "emoji": "🌷",
        "light": True,
        "swatches": ["#fdf2f8", "#ffffff", "#db2777", "#831843"],
        "vars": {
            "--gxp-bg":         "#fdf2f8",
            "--gxp-surface":    "#ffffff",
            "--gxp-surface2":   "#fce7f3",
            "--gxp-border":     "#fbcfe8",
            "--gxp-text":       "#500724",
            "--gxp-text2":      "#9d174d",
            "--gxp-text3":      "#f472b6",
            "--gxp-accent":     "#db2777",
            "--gxp-accent-bg":  "#fce7f3",
            "--gxp-accent-fg":  "#831843",
            "--gxp-success":    "#059669",
            "--gxp-success-bg": "#d1fae5",
            "--gxp-success-fg": "#065f46",
            "--gxp-warning":    "#d97706",
            "--gxp-warning-bg": "#fef3c7",
            "--gxp-warning-fg": "#92400e",
            "--gxp-danger":     "#dc2626",
            "--gxp-danger-bg":  "#fee2e2",
            "--gxp-danger-fg":  "#991b1b",
        },
    },
    "sky": {
        "label": "Sky",
        "emoji": "🩵",
        "light": True,
        "swatches": ["#f0f9ff", "#ffffff", "#0284c7", "#075985"],
        "vars": {
            "--gxp-bg":         "#f0f9ff",
            "--gxp-surface":    "#ffffff",
            "--gxp-surface2":   "#e0f2fe",
            "--gxp-border":     "#bae6fd",
            "--gxp-text":       "#0c4a6e",
            "--gxp-text2":      "#0369a1",
            "--gxp-text3":      "#7dd3fc",
            "--gxp-accent":     "#0284c7",
            "--gxp-accent-bg":  "#e0f2fe",
            "--gxp-accent-fg":  "#075985",
            "--gxp-success":    "#059669",
            "--gxp-success-bg": "#d1fae5",
            "--gxp-success-fg": "#065f46",
            "--gxp-warning":    "#d97706",
            "--gxp-warning-bg": "#fef3c7",
            "--gxp-warning-fg": "#92400e",
            "--gxp-danger":     "#dc2626",
            "--gxp-danger-bg":  "#fee2e2",
            "--gxp-danger-fg":  "#991b1b",
        },
    },
    "lavender_light": {
        "label": "Lavender Mist",
        "emoji": "🪻",
        "light": True,
        "swatches": ["#faf5ff", "#ffffff", "#7c3aed", "#4c1d95"],
        "vars": {
            "--gxp-bg":         "#faf5ff",
            "--gxp-surface":    "#ffffff",
            "--gxp-surface2":   "#f3e8ff",
            "--gxp-border":     "#e9d5ff",
            "--gxp-text":       "#2e1065",
            "--gxp-text2":      "#6d28d9",
            "--gxp-text3":      "#c4b5fd",
            "--gxp-accent":     "#7c3aed",
            "--gxp-accent-bg":  "#ede9fe",
            "--gxp-accent-fg":  "#4c1d95",
            "--gxp-success":    "#059669",
            "--gxp-success-bg": "#d1fae5",
            "--gxp-success-fg": "#065f46",
            "--gxp-warning":    "#d97706",
            "--gxp-warning-bg": "#fef3c7",
            "--gxp-warning-fg": "#92400e",
            "--gxp-danger":     "#dc2626",
            "--gxp-danger-bg":  "#fee2e2",
            "--gxp-danger-fg":  "#991b1b",
        },
    },
    "sand": {
        "label": "Sand Dune",
        "emoji": "🏜️",
        "light": True,
        "swatches": ["#fefce8", "#fffef5", "#ca8a04", "#713f12"],
        "vars": {
            "--gxp-bg":         "#fefce8",
            "--gxp-surface":    "#fffef5",
            "--gxp-surface2":   "#fef9c3",
            "--gxp-border":     "#fde68a",
            "--gxp-text":       "#431407",
            "--gxp-text2":      "#92400e",
            "--gxp-text3":      "#fbbf24",
            "--gxp-accent":     "#ca8a04",
            "--gxp-accent-bg":  "#fef9c3",
            "--gxp-accent-fg":  "#713f12",
            "--gxp-success":    "#059669",
            "--gxp-success-bg": "#d1fae5",
            "--gxp-success-fg": "#065f46",
            "--gxp-warning":    "#d97706",
            "--gxp-warning-bg": "#fef3c7",
            "--gxp-warning-fg": "#92400e",
            "--gxp-danger":     "#dc2626",
            "--gxp-danger-bg":  "#fee2e2",
            "--gxp-danger-fg":  "#991b1b",
        },
    },
    "sage": {
        "label": "Sage",
        "emoji": "🌾",
        "light": True,
        "swatches": ["#f7fee7", "#ffffff", "#4d7c0f", "#1a2e05"],
        "vars": {
            "--gxp-bg":         "#f7fee7",
            "--gxp-surface":    "#ffffff",
            "--gxp-surface2":   "#ecfccb",
            "--gxp-border":     "#d9f99d",
            "--gxp-text":       "#1a2e05",
            "--gxp-text2":      "#365314",
            "--gxp-text3":      "#a3e635",
            "--gxp-accent":     "#4d7c0f",
            "--gxp-accent-bg":  "#ecfccb",
            "--gxp-accent-fg":  "#1a2e05",
            "--gxp-success":    "#059669",
            "--gxp-success-bg": "#d1fae5",
            "--gxp-success-fg": "#065f46",
            "--gxp-warning":    "#d97706",
            "--gxp-warning-bg": "#fef3c7",
            "--gxp-warning-fg": "#92400e",
            "--gxp-danger":     "#dc2626",
            "--gxp-danger-bg":  "#fee2e2",
            "--gxp-danger-fg":  "#991b1b",
        },
    },
}

DEFAULT_THEME = "cloud"

# Themes that need Streamlit in light mode (native widgets)
_LIGHT_THEMES = {k for k, v in THEMES.items() if v.get("light")}


def _get_theme() -> dict:
    key = st.session_state.get("gxp_theme", DEFAULT_THEME)
    return THEMES.get(key, THEMES[DEFAULT_THEME])


def _vars_css(vars: dict) -> str:
    """Build a :root { } CSS block from a vars dict."""
    lines = "\n".join(f"    {k}: {v};" for k, v in vars.items())
    return f":root {{\n{lines}\n}}"


# ============================================================
# Color Tokens (semantic — kept for backward compat)
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
    """Inject shared CSS with active theme variables. Call once per page render()."""
    theme   = _get_theme()
    t_vars  = theme["vars"]
    is_light = theme.get("light", False)

    # ── 1. Theme CSS custom properties + Streamlit bg override ──
    bg      = t_vars["--gxp-bg"]
    surface = t_vars["--gxp-surface"]
    text    = t_vars["--gxp-text"]
    text2   = t_vars["--gxp-text2"]
    border  = t_vars["--gxp-border"]
    accent  = t_vars["--gxp-accent"]

    st.markdown(
        f"""<style>
        {_vars_css(t_vars)}

        /* ── Override Streamlit's own app shell to match theme ── */
        .stApp                                 {{ background: {bg} !important; }}
        section[data-testid="stSidebar"]       {{ background: {surface} !important; }}
        [data-testid="stSidebarContent"]       {{ background: {surface} !important; }}
        .stMainBlockContainer                  {{ background: {bg} !important; }}

        /* Text in widgets follows theme */
        .stMarkdown p, .stMarkdown li,
        label[data-testid="stWidgetLabel"] > div,
        .stSelectbox label, .stTextInput label,
        .stNumberInput label, .stDateInput label,
        .stCheckbox label, .stRadio label        {{ color: {text} !important; }}

        /* Input fields */
        .stTextInput input, .stNumberInput input,
        .stDateInput input, .stSelectbox select,
        [data-baseweb="select"] [data-testid="stWidgetLabel"]
                                               {{ background: {surface} !important;
                                                  color: {text} !important;
                                                  border-color: {border} !important; }}

        /* ── Tabs ── */
        .stTabs [data-baseweb="tab"]           {{ color: {text2} !important;
                                                  font-size: 14px !important;
                                                  font-weight: 500 !important; }}
        .stTabs [aria-selected="true"]         {{ color: {accent} !important;
                                                  font-weight: 600 !important;
                                                  border-bottom-color: {accent} !important; }}

        /* ── Metric cards ── */
        [data-testid="metric-container"]       {{ background: {surface} !important;
                                                  border-color: {border} !important; }}
        [data-testid="stMetricValue"]          {{ color: {text} !important; }}
        [data-testid="stMetricLabel"]          {{ color: {text2} !important; }}

        /* ── Sidebar text ── */
        .stSidebar .stMarkdown,
        .stSidebar p, .stSidebar small,
        .stSidebar [data-testid="stCaptionContainer"] {{ color: {text2} !important; }}
        .stSidebar .stRadio label              {{ color: {text} !important; }}

        /* ── Typography scale — normalize all heading levels ── */
        /* h1 — let Streamlit's native title size win; just theme the color */
        .stMarkdown h1, .stHeading h1,
        [data-testid="stHeading"] h1           {{ font-weight: 700 !important;
                                                  color: {text} !important; margin-top: 0 !important; }}
        .stMarkdown h2, .stHeading h2,
        [data-testid="stHeading"] h2           {{ font-size: 20px !important; font-weight: 700 !important;
                                                  color: {text} !important; }}
        .stMarkdown h3, .stHeading h3,
        [data-testid="stHeading"] h3           {{ font-size: 16px !important; font-weight: 600 !important;
                                                  color: {text} !important; }}
        .stMarkdown h4, .stHeading h4,
        [data-testid="stHeading"] h4           {{ font-size: 14px !important; font-weight: 600 !important;
                                                  color: {text} !important; }}
        .stMarkdown h5, .stHeading h5,
        [data-testid="stHeading"] h5           {{ font-size: 13px !important; font-weight: 600 !important;
                                                  color: {text2} !important; }}
        .stMarkdown p                          {{ font-size: 14px !important; color: {text} !important; }}

        /* ── Reduce default top padding (Streamlit adds 4-6rem by default) ── */
        .block-container, .stMainBlockContainer {{
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
        }}

        /* ── Body / general text ── */
        body, .stApp                           {{ font-size: 14px; }}
        </style>""",
        unsafe_allow_html=True,
    )

    # ── 2. Component styles (all use var(--gxp-*)) ───────────
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
    .gxp-badge-draft     { background: var(--gxp-accent-bg);  color: var(--gxp-accent-fg); }
    .gxp-badge-reviewed  { background: #2e1d5e; color: #c4b5fd; }
    .gxp-badge-finalized { background: var(--gxp-warning-bg); color: var(--gxp-warning-fg); }
    .gxp-badge-paid      { background: var(--gxp-success-bg); color: var(--gxp-success-fg); }

    /* ── Urgency Dots ─────────────────────────────── */
    .gxp-dot {
        display: inline-block;
        width: 8px; height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
    }
    .gxp-dot-overdue { background: var(--gxp-danger); }
    .gxp-dot-warning { background: var(--gxp-warning); }
    .gxp-dot-ok      { background: var(--gxp-success); }

    /* ── Section Cards ────────────────────────────── */
    .gxp-card {
        border: 1px solid var(--gxp-border);
        border-radius: 8px;
        padding: 16px;
        background: var(--gxp-surface);
        margin-bottom: 8px;
    }

    /* ── Section Headers ──────────────────────────── */
    .gxp-section-header {
        font-size: 15px;
        font-weight: 700;
        color: var(--gxp-text);
        margin-bottom: 8px;
        padding-bottom: 8px;
        border-bottom: 2px solid var(--gxp-border);
    }

    /* ── Info Bar (status line) ────────────────────── */
    .gxp-info-bar {
        padding: 10px 16px;
        border-radius: 8px;
        font-size: 13px;
        margin-bottom: 16px;
        border-left: 4px solid;
    }
    .gxp-info-bar-draft     { background: var(--gxp-accent-bg);  border-color: var(--gxp-accent);  color: var(--gxp-accent-fg); }
    .gxp-info-bar-reviewed  { background: #2e1d5e; border-color: #7c3aed; color: #ddd6fe; }
    .gxp-info-bar-finalized { background: var(--gxp-warning-bg); border-color: var(--gxp-warning); color: var(--gxp-warning-fg); }
    .gxp-info-bar-paid      { background: var(--gxp-success-bg); border-color: var(--gxp-success); color: var(--gxp-success-fg); }

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
        color: var(--gxp-text2);
        padding-right: 12px;
    }
    .gxp-fin-table td:last-child {
        text-align: right;
        font-weight: 500;
        color: var(--gxp-text);
    }
    .gxp-fin-table tr.gxp-fin-total td {
        border-top: 1px solid var(--gxp-border);
        font-weight: 700;
        padding-top: 8px;
    }

    /* ── Remittance Grid ──────────────────────────── */
    .gxp-remit-card {
        border: 1px solid var(--gxp-border);
        border-radius: 8px;
        padding: 12px 16px;
        background: var(--gxp-surface);
        border-top: 3px solid;
    }
    .gxp-remit-card h4 {
        font-size: 13px;
        font-weight: 700;
        margin: 0 0 8px 0;
        color: var(--gxp-text);
    }
    .gxp-remit-card .gxp-remit-row {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        padding: 2px 0;
        color: var(--gxp-text2);
    }
    .gxp-remit-card .gxp-remit-row span:last-child {
        font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
        font-weight: 500;
    }
    .gxp-remit-card .gxp-remit-total {
        border-top: 1px solid var(--gxp-border);
        margin-top: 4px;
        padding-top: 6px;
        font-weight: 700;
        font-size: 13px;
        display: flex;
        justify-content: space-between;
        color: var(--gxp-text);
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
        border-bottom: 1px solid var(--gxp-border);
    }
    .gxp-deadline:last-child { border-bottom: none; }
    .gxp-deadline-info { flex: 1; }
    .gxp-deadline-agency {
        font-weight: 600;
        font-size: 13px;
        color: var(--gxp-text);
    }
    .gxp-deadline-desc {
        font-size: 12px;
        color: var(--gxp-text2);
        margin-top: 1px;
    }
    .gxp-deadline-date {
        font-size: 12px;
        font-weight: 600;
        color: var(--gxp-text);
        text-align: right;
        white-space: nowrap;
    }
    .gxp-deadline-status {
        font-size: 11px;
        color: var(--gxp-text3);
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
        background: var(--gxp-border);
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
        color: var(--gxp-text2);
        white-space: nowrap;
    }

    /* ── Edit Panel ───────────────────────────────── */
    .gxp-edit-panel {
        background: var(--gxp-accent-bg);
        border: 1px solid var(--gxp-accent);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 24px;
    }
    .gxp-edit-panel-title {
        font-size: 14px;
        font-weight: 700;
        color: var(--gxp-accent-fg);
        margin-bottom: 4px;
    }
    .gxp-edit-panel-desc {
        font-size: 12px;
        color: var(--gxp-text2);
        margin-bottom: 12px;
    }

    /* ── Period Card ───────────────────────────────── */
    .gxp-period-card {
        border: 1px solid var(--gxp-border);
        border-radius: 8px;
        padding: 14px 16px;
        background: var(--gxp-surface);
        min-height: 110px;
    }
    .gxp-period-card-empty {
        border: 1px dashed var(--gxp-border);
        border-radius: 8px;
        padding: 14px 16px;
        background: var(--gxp-surface2);
        min-height: 110px;
        text-align: center;
    }
    .gxp-period-slot  { font-size: 11px; color: var(--gxp-text2); margin-bottom: 3px; }
    .gxp-period-dates { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: var(--gxp-text); }
    .gxp-period-stats { margin-top: 10px; font-size: 12px; color: var(--gxp-text2); }
    .gxp-period-gross { font-size: 11px; color: var(--gxp-text3); margin-top: 2px; }

    /* ── ADP-Style Action Bar ────────────────────────── */
    .gxp-action-bar {
        background: linear-gradient(135deg, var(--gxp-bg) 0%, var(--gxp-accent-bg) 100%);
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
    }
    .gxp-action-bar-left { flex: 1; }
    .gxp-action-bar-greeting { font-size: 26px; font-weight: 700; color: var(--gxp-text); margin-bottom: 4px; }
    .gxp-action-bar-sub { font-size: 13px; color: var(--gxp-text2); }
    .gxp-action-bar-sub strong { color: var(--gxp-accent-fg); }
    .gxp-action-bar-right { display: flex; align-items: center; gap: 16px; }
    .gxp-action-bar-next { text-align: right; }
    .gxp-action-bar-next-label { font-size: 11px; color: var(--gxp-text2); text-transform: uppercase; letter-spacing: 0.5px; }
    .gxp-action-bar-next-date  { font-size: 14px; font-weight: 600; color: var(--gxp-text); }

    /* ── ADP-Style Alert Cards ───────────────────────── */
    .gxp-alerts-section { margin-bottom: 24px; }
    .gxp-alert-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
        border-left: 4px solid;
    }
    .gxp-alert-overdue { background: var(--gxp-danger-bg);  border-color: var(--gxp-danger); }
    .gxp-alert-warning { background: var(--gxp-warning-bg); border-color: var(--gxp-warning); }
    .gxp-alert-info    { background: var(--gxp-accent-bg);  border-color: var(--gxp-accent); }
    .gxp-alert-icon {
        font-size: 18px; flex-shrink: 0;
        width: 32px; height: 32px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
    }
    .gxp-alert-overdue .gxp-alert-icon { background: color-mix(in srgb, var(--gxp-danger-bg) 60%, black); color: var(--gxp-danger-fg); }
    .gxp-alert-warning .gxp-alert-icon { background: color-mix(in srgb, var(--gxp-warning-bg) 60%, black); color: var(--gxp-warning-fg); }
    .gxp-alert-info    .gxp-alert-icon { background: var(--gxp-accent-bg); color: var(--gxp-accent-fg); }
    .gxp-alert-body   { flex: 1; }
    .gxp-alert-title  { font-size: 13px; font-weight: 600; color: var(--gxp-text); }
    .gxp-alert-desc   { font-size: 12px; color: var(--gxp-text2); margin-top: 1px; }
    .gxp-alert-action { font-size: 12px; font-weight: 600; color: var(--gxp-text2); white-space: nowrap; }

    /* ── ADP-Style Stat Cards ────────────────────────── */
    .gxp-stat-card {
        background: var(--gxp-surface);
        border: 1px solid var(--gxp-border);
        border-radius: 10px;
        padding: 18px 16px;
        position: relative;
        overflow: hidden;
        height: 100%;
    }
    .gxp-stat-icon {
        width: 38px; height: 38px;
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        margin-bottom: 12px;
    }
    .gxp-stat-icon svg { display: block; }
    .gxp-stat-label {
        font-size: 11px;
        color: var(--gxp-text2);
        text-transform: uppercase;
        letter-spacing: 0.4px;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .gxp-stat-value {
        font-size: 20px;
        font-weight: 700;
        color: var(--gxp-text);
        font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
        line-height: 1.2;
    }
    .gxp-stat-trend-row { margin-top: 3px; margin-bottom: 2px; }
    .gxp-stat-trend { font-size: 11px; font-weight: 600; padding: 1px 6px; border-radius: 4px; }
    .gxp-stat-trend-up      { color: var(--gxp-success-fg); background: var(--gxp-success-bg); }
    .gxp-stat-trend-down    { color: var(--gxp-danger-fg);  background: var(--gxp-danger-bg); }
    .gxp-stat-trend-neutral { color: var(--gxp-text2);      background: var(--gxp-surface2); }
    .gxp-stat-sub { font-size: 11px; color: var(--gxp-text3); margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* ── ADP-Style Last Payroll Summary ──────────────── */
    .gxp-summary-card {
        background: var(--gxp-surface);
        border: 1px solid var(--gxp-border);
        border-radius: 10px;
        padding: 20px 24px;
        margin-bottom: 24px;
    }
    .gxp-summary-header {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 16px; padding-bottom: 12px;
        border-bottom: 1px solid var(--gxp-border);
    }
    .gxp-summary-title { font-size: 15px; font-weight: 700; color: var(--gxp-text); }
    .gxp-summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
    .gxp-summary-item { text-align: center; padding: 8px 0; }
    .gxp-summary-item-label {
        font-size: 11px;
        color: var(--gxp-text2);
        text-transform: uppercase;
        letter-spacing: 0.3px;
        margin-bottom: 4px;
    }
    .gxp-summary-item-value {
        font-size: 16px; font-weight: 600; color: var(--gxp-text);
        font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
    }

    /* ── Employee Portal Hero ────────────────────────── */
    .gxp-portal-hero {
        background: linear-gradient(135deg, var(--gxp-bg) 0%, var(--gxp-accent-bg) 100%);
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 8px;
        display: flex; align-items: center; gap: 20px;
    }
    .gxp-portal-hero-avatar {
        width: 56px; height: 56px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--gxp-accent), var(--gxp-success));
        display: flex; align-items: center; justify-content: center;
        font-size: 22px; font-weight: 700; color: #ffffff;
        flex-shrink: 0; letter-spacing: -0.5px;
    }
    .gxp-portal-hero-info { flex: 1; }
    .gxp-portal-hero-name { font-size: 20px; font-weight: 700; color: var(--gxp-text); margin-bottom: 3px; }
    .gxp-portal-hero-meta { font-size: 13px; color: var(--gxp-accent-fg); font-weight: 500; margin-bottom: 2px; }
    .gxp-portal-hero-sub  { font-size: 12px; color: var(--gxp-text2); }

    /* ── Employee Portal Payslip Cards ───────────────── */
    .gxp-payslip-card {
        background: var(--gxp-surface);
        border: 1px solid var(--gxp-border);
        border-radius: 10px;
        padding: 20px 24px 4px 24px;
        margin-bottom: 4px;
        border-left: 4px solid var(--gxp-accent);
    }
    .gxp-payslip-header {
        display: flex; align-items: flex-start; justify-content: space-between;
        margin-bottom: 12px; padding-bottom: 12px;
        border-bottom: 1px solid var(--gxp-border);
    }
    .gxp-payslip-period  { font-size: 15px; font-weight: 700; color: var(--gxp-text); }
    .gxp-payslip-payment { font-size: 12px; color: var(--gxp-text2); margin-top: 3px; }
    .gxp-payslip-net {
        font-size: 22px; font-weight: 700; color: var(--gxp-success);
        font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
        text-align: right;
    }
    .gxp-payslip-net-label {
        font-size: 12px; font-weight: 400; color: var(--gxp-text2);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    .gxp-payslip-section-label {
        font-size: 11px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.5px;
        color: var(--gxp-text3); margin-top: 12px; margin-bottom: 4px;
    }

    /* ── ADP-Style Section Panel ─────────────────────── */
    .gxp-panel {
        background: var(--gxp-surface);
        border: 1px solid var(--gxp-border);
        border-radius: 10px;
        padding: 20px 24px;
        margin-bottom: 24px;
    }
    .gxp-panel-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
    .gxp-panel-title    { font-size: 15px; font-weight: 700; color: var(--gxp-text); }
    .gxp-panel-subtitle { font-size: 12px; color: var(--gxp-text2); }

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
    .gxp-quick-actions { margin-top: -12px; margin-bottom: 24px; }

    </style>
    """, unsafe_allow_html=True)

    # ── 3. Table row-density CSS (compact / normal / relaxed) ─────
    _density_px = {"compact": 24, "normal": 36, "relaxed": 52}
    _row_h = _density_px.get(
        st.session_state.get("gxp_table_density", "normal"), 36
    )
    # Padding values that give the target row height at ~13px font
    _pad = {"compact": "3px 8px", "normal": "7px 8px", "relaxed": "14px 8px"}[
        st.session_state.get("gxp_table_density", "normal")
    ]
    st.markdown(
        f"""<style>
        :root {{ --gxp-row-height: {_row_h}px; }}

        /* Custom HTML tables (.gxp-fin-table etc.) */
        .gxp-fin-table td  {{ padding: {_pad}; }}

        /* Streamlit native st.dataframe / st.table rows */
        [data-testid="stDataFrame"] .dvn-scroller .cell-wrap,
        [data-testid="stDataFrame"] canvas {{ min-height: {_row_h}px; }}

        /* Streamlit st.table (static HTML table) */
        [data-testid="stTable"] tbody td,
        [data-testid="stTable"] tbody th {{
            padding: {_pad} !important;
        }}
        </style>""",
        unsafe_allow_html=True,
    )


# ============================================================
# Theme Picker UI
# ============================================================

def render_theme_picker():
    """Render the theme selection grid in the sidebar."""
    current = st.session_state.get("gxp_theme", DEFAULT_THEME)

    dark_themes  = {k: v for k, v in THEMES.items() if not v.get("light")}
    light_themes = {k: v for k, v in THEMES.items() if v.get("light")}

    def _theme_card(key: str, theme: dict):
        vars_     = theme["vars"]
        is_active = key == current
        accent    = vars_["--gxp-accent"]
        surface   = vars_["--gxp-surface"]
        text      = vars_["--gxp-text"]
        bdr_color = vars_["--gxp-border"]
        border    = f"2px solid {accent}" if is_active else f"1px solid {bdr_color}"
        opacity   = "1" if is_active else "0.8"
        swatch_border = "rgba(0,0,0,0.15)" if theme.get("light") else "rgba(255,255,255,0.15)"

        swatches_html = "".join(
            f'<span style="display:inline-block;width:11px;height:11px;'
            f'border-radius:50%;background:{c};margin-right:3px;'
            f'border:1px solid {swatch_border};"></span>'
            for c in theme["swatches"]
        )
        check = "✓ " if is_active else ""

        st.markdown(
            f"""<div style="border:{border};border-radius:8px;padding:8px 10px;
            background:{surface};margin-bottom:4px;opacity:{opacity};">
            <div style="font-size:12px;font-weight:600;color:{text};margin-bottom:4px;">
            {theme['emoji']}&nbsp;{check}{theme['label']}</div>
            <div>{swatches_html}</div></div>""",
            unsafe_allow_html=True,
        )
        if not is_active:
            if st.button(
                f"Apply",
                key=f"gxp_theme_btn_{key}",
                use_container_width=True,
            ):
                st.session_state["gxp_theme"] = key
                st.rerun()

    with st.sidebar.expander("🎨 Themes", expanded=False):
        st.markdown(
            "<div style='font-size:10px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.8px;color:#94a3b8;margin-bottom:6px;'>🌙 Dark</div>",
            unsafe_allow_html=True,
        )
        for key, theme in dark_themes.items():
            _theme_card(key, theme)

        st.markdown(
            "<div style='font-size:10px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.8px;color:#94a3b8;margin:10px 0 6px;'>☀️ Light</div>",
            unsafe_allow_html=True,
        )
        for key, theme in light_themes.items():
            _theme_card(key, theme)


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
    color = "var(--gxp-success)" if current == total else "var(--gxp-accent)"
    lbl = label or f"{current} of {total}"
    return (
        f'<div class="gxp-progress">'
        f'<div class="gxp-progress-bar">'
        f'<div class="gxp-progress-fill" style="width:{pct:.0f}%;background:{color}"></div>'
        f'</div>'
        f'<div class="gxp-progress-label">{lbl}</div>'
        f'</div>'
    )
