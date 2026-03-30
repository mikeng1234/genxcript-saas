"""
Shared UI styles, themes, and helper functions for GeNXcript Payroll.

Provides semantic CSS tokens via custom properties, named pastel themes,
status badges, and styled components reusable across all pages.
Call inject_css() once per page render.
"""

import streamlit as st
import streamlit.components.v1 as _components


# ============================================================
# Themes
# ============================================================

THEMES: dict[str, dict] = {
    "midnight": {
        "label": "Midnight Navy",
        "emoji": '<span class="mdi mdi-weather-night" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-auto-fix" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-leaf" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-flower" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-fire" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-wave" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-tree" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-hexagon" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-cloud" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-file-document-outline" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-spa" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-flower-outline" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-weather-partly-cloudy" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-flower" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-white-balance-sunny" style="font-size:18px;"></span>',
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
        "emoji": '<span class="mdi mdi-grass" style="font-size:18px;"></span>',
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

    # ── Tactile Sanctuary — Material 3 Editorial Minimalism ────
    "tactile": {
        "label": "Tactile",
        "emoji": '<span class="mdi mdi-diamond-stone" style="font-size:18px;"></span>',
        "light": True,
        "swatches": ["#f8f9fa", "#ffffff", "#005bc1", "#fbbc05"],
        "vars": {
            "--gxp-bg":         "#f8f9fa",
            "--gxp-surface":    "#ffffff",
            "--gxp-surface2":   "#f3f4f5",
            "--gxp-border":     "#edeeef",
            "--gxp-text":       "#191c1d",
            "--gxp-text2":      "#424753",
            "--gxp-text3":      "#727784",
            "--gxp-accent":     "#005bc1",
            "--gxp-accent-bg":  "#d8e2ff",
            "--gxp-accent-fg":  "#004494",
            "--gxp-success":    "#006e2d",
            "--gxp-success-bg": "#c4f5d0",
            "--gxp-success-fg": "#005320",
            "--gxp-warning":    "#795900",
            "--gxp-warning-bg": "#ffdea0",
            "--gxp-warning-fg": "#5c4300",
            "--gxp-danger":     "#ba1a1a",
            "--gxp-danger-bg":  "#ffdad6",
            "--gxp-danger-fg":  "#93000a",
            # ── Extended M3 tokens (used by Tactile-specific CSS) ──
            "--gxp-m3-primary-container":     "#005bc1",
            "--gxp-m3-on-primary-container":  "#c9d9ff",
            "--gxp-m3-secondary-container":   "#febf0d",
            "--gxp-m3-tertiary-fixed":        "#89fa9b",
            "--gxp-m3-surface-container":     "#edeeef",
            "--gxp-m3-surface-container-low": "#f3f4f5",
            "--gxp-m3-outline-variant":       "#c2c6d5",
            "--gxp-m3-ambient-shadow":        "0px 20px 40px rgba(45,51,53,0.06)",
        },
    },
}

DEFAULT_THEME = "tactile"

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
    "draft":     {"bg": "#d8e2ff", "fg": "#004494", "label": "DRAFT"},
    "reviewed":  {"bg": "#e8def8", "fg": "#4a2590", "label": "REVIEWED"},
    "finalized": {"bg": "#ffdea0", "fg": "#5c4300", "label": "FINALIZED"},
    "paid":      {"bg": "#c4f5d0", "fg": "#005320", "label": "PAID"},
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
    # Load Plus Jakarta Sans + Material Symbols — @import inside <style>
    st.markdown(
        '<span class="gxp-css-inject"></span>'
        "<style>"
        "@font-face {"
        "  font-family: 'Material Symbols Outlined';"
        "  font-style: normal;"
        "  font-weight: 100 700;"
        "  font-display: block;"
        "  src: url('/app/static/MaterialSymbolsOutlined.woff2') format('woff2');"
        "}"
        "@font-face {"
        "  font-family: 'Material Symbols Rounded';"
        "  font-style: normal;"
        "  font-weight: 100 700;"
        "  font-display: block;"
        "  src: url('/app/static/MaterialSymbolsRounded.woff2') format('woff2');"
        "}"
        "@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');"
        ".material-symbols-outlined{"
        "  font-family:'Material Symbols Outlined';"
        "  font-weight:normal;font-style:normal;font-size:24px;"
        "  line-height:1;letter-spacing:normal;text-transform:none;"
        "  display:inline-block;white-space:nowrap;word-wrap:normal;"
        "  direction:ltr;-webkit-font-smoothing:antialiased;"
        "  font-variation-settings:'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 24;"
        "}"
        ".material-symbols-rounded{"
        "  font-family:'Material Symbols Rounded';"
        "  font-weight:normal;font-style:normal;font-size:24px;"
        "  line-height:1;letter-spacing:normal;text-transform:none;"
        "  display:inline-block;white-space:nowrap;word-wrap:normal;"
        "  direction:ltr;-webkit-font-smoothing:antialiased;"
        "  font-variation-settings:'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 24;"
        "}"
        "[data-testid='stExpanderToggleIcon']{display:none!important;}"
        ".stExpander summary svg{display:none!important;}"
        ".stExpander summary span[translate='no']{display:none!important;}"
        "</style>",
        unsafe_allow_html=True,
    )

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
            padding-top: 0.75rem !important;
            padding-bottom: 2rem !important;
        }}

        /* ── Collapse zero-height component iframes ── */
        /* Use animation to delay display:none — gives JS 1s to execute first */
        @keyframes gxp-collapse {{
            0%   {{ height: 0; min-height: 0; margin: 0; padding: 0; overflow: hidden; }}
            99%  {{ height: 0; min-height: 0; margin: 0; padding: 0; overflow: hidden; }}
            100% {{ display: none; height: 0; }}
        }}
        [data-testid="stElementContainer"][height="0px"],
        [data-testid="stElementContainer"][height="0"],
        [data-testid="stElementContainer"]:has(iframe[height="0"]) {{
            display: none !important;
        }}
        /* Collapse CSS injection containers (marked with gxp-css-inject) */
        [data-testid="stElementContainer"]:has(.gxp-css-inject) {{
            display: none !important;
        }}
        /* ── Collapse empty element containers ── */
        [data-testid="stElementContainer"]:empty {{
            position: absolute !important;
            width: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }}

        /* ── Body / general text ── */
        body, .stApp                           {{ font-size: 14px; }}
        </style>""",
        unsafe_allow_html=True,
    )

    # ── 2. Component styles (all use var(--gxp-*)) ───────────
    st.markdown("""
    <span class="gxp-css-inject"></span>
    <style>

    /* ── Ripple effect ───────────────────────────── */
    @keyframes gxp-ripple {
        0%   { transform: scale(0); opacity: 0.35; }
        100% { transform: scale(4); opacity: 0; }
    }
    .gxp-ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255,255,255,0.5);
        pointer-events: none;
        animation: gxp-ripple 0.5s ease-out forwards;
    }
    .gxp-ripple-dark {
        background: rgba(0,0,0,0.12);
    }

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
        /* Equal-height: flex column so the total row always sticks to the bottom */
        display: flex;
        flex-direction: column;
        height: 100%;
        min-height: 116px;
        box-sizing: border-box;
    }
    .gxp-remit-card h4 {
        font-size: 13px;
        font-weight: 700;
        margin: 0 0 6px 0;
        color: var(--gxp-text);
        flex-shrink: 0;
    }
    /* The rows group grows to fill space — pushes total line to the bottom */
    .gxp-remit-rows { flex: 1; display: flex; flex-direction: column; justify-content: flex-end; }
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
        margin-top: 6px;
        padding-top: 6px;
        font-weight: 700;
        font-size: 13px;
        display: flex;
        justify-content: space-between;
        color: var(--gxp-text);
        flex-shrink: 0;
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
        background: var(--gxp-surface);
        border: none;
        border-radius: 1rem;
        padding: 24px 28px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        box-shadow: var(--gxp-m3-ambient-shadow, 0px 20px 40px rgba(45,51,53,0.06));
    }
    .gxp-action-bar-left { flex: 1; }
    .gxp-action-bar-greeting { font-size: 26px; font-weight: 700; color: var(--gxp-text); margin-bottom: 4px; }
    .gxp-action-bar-sub { font-size: 13px; color: var(--gxp-text2); }
    .gxp-action-bar-sub strong { color: var(--gxp-accent-fg); }
    .gxp-action-bar-right { display: flex; align-items: center; gap: 16px; }
    .gxp-action-bar-next { text-align: right; }
    .gxp-action-bar-next-label { font-size: 11px; color: var(--gxp-text2); text-transform: uppercase; letter-spacing: 0.5px; }
    .gxp-action-bar-next-date  { font-size: 14px; font-weight: 600; color: var(--gxp-text); }

    /* ── Alert grid cards (pure HTML, no action buttons) ── */
    /* All styling is inline in _alert_card_html(); nothing extra needed here. */

    /* ── ADP-Style Stat Cards ────────────────────────── */
    .gxp-stat-card {
        background: var(--gxp-surface);
        border: none;
        border-radius: 1rem;
        padding: 20px 18px;
        position: relative;
        overflow: hidden;
        height: 100%;
        box-shadow: var(--gxp-m3-ambient-shadow, 0px 20px 40px rgba(45,51,53,0.06));
        transition: box-shadow 0.15s ease, transform 0.15s ease;
    }

    /* ── Reminder swipe-reveal cards ─────────────────────────────── */
    .gxp-remind-swipe {
        position: relative !important;
        overflow: hidden !important;
        border-radius: 10px !important;
    }
    .gxp-remind-actions {
        position: absolute !important;
        top: 0 !important; right: 0 !important; bottom: 0 !important;
        width: 110px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 6px !important;
        padding: 8px 6px !important;
        border-radius: 0 10px 10px 0 !important;
        z-index: 0 !important;
    }
    .gxp-remind-card-inner {
        position: relative !important;
        z-index: 1 !important;
        transition: transform 0.25s cubic-bezier(.4,0,.2,1) !important;
    }
    .gxp-remind-swipe:hover .gxp-remind-card-inner {
        transform: translateX(-110px) !important;
    }
    .gxp-remind-action-btn {
        position: relative !important;
        overflow: hidden !important;
        border-radius: 8px !important;
        padding: 6px 10px !important;
        font-size: 10px !important;
        font-weight: 700 !important;
        cursor: pointer !important;
        width: 90px !important;
        text-align: center !important;
        font-family: inherit !important;
        transition: transform 0.12s, box-shadow 0.12s !important;
    }
    .gxp-remind-action-btn:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
    }
    .gxp-remind-action-btn:active {
        transform: scale(0.97) !important;
    }

    /* ── Reminder pills — stat-card pattern, guarded against col_alerts bleed ──
     *
     * PROBLEM: stHorizontalBlock:has(.gxp-remind-leave) matches BOTH the inner
     * 2-col reminders row AND the outer 3-col row (col_alerts|col_charts|col_remit),
     * because the outer row contains those markers as descendants.  col_alerts is
     * nth-child(1) of that outer row, so hovering any alert card (inside col_alerts)
     * also triggers the reminder pill hover via the outer stHorizontalBlock → col_alerts.
     *
     * FIX: add :not(:has(.gxp-alert-gov-marker)) to the stColumn condition.
     *   col_l / col_r  → no alert marker → MATCHES (correct)
     *   col_alerts     → has alert marker as descendant → EXCLUDED
     * ──────────────────────────────────────────────────────────────────────── */

    /* ── Reminder hidden buttons — fully invisible, used only as JS click targets ── */
    [data-testid="stVerticalBlockBorderWrapper"]:has(.gxp-remind-section)
        [data-testid="stButton"] {
        height:     0 !important;
        min-height: 0 !important;
        overflow:   hidden !important;
        margin:     0 !important;
        padding:    0 !important;
        opacity:    0 !important;
        pointer-events: none !important;
    }
    /* Card lift on reminder container hover */
    [data-testid="stVerticalBlockBorderWrapper"]:has(.gxp-remind-section):hover
        .gxp-remind-leave,
    [data-testid="stVerticalBlockBorderWrapper"]:has(.gxp-remind-section):hover
        .gxp-remind-ot {
        box-shadow: 0 8px 24px rgba(0,0,0,0.10) !important;
        transform:  translateY(-4px) !important;
    }

    /* ── Alert hidden buttons — fully invisible, used only as JS click targets ── */
    [data-testid="stVerticalBlockBorderWrapper"]:has(.gxp-alert-section)
        [data-testid="stButton"] {
        height:     0 !important;
        min-height: 0 !important;
        overflow:   hidden !important;
        margin:     0 !important;
        padding:    0 !important;
        opacity:    0 !important;
        pointer-events: none !important;
    }

    /* ── Stat card swipe-up-to-reveal ─────────────────────────────────────── */
    .gxp-stat-swipe {
        position: relative !important;
        overflow: hidden !important;
        border-radius: 1rem !important;
        /* Fixed height prevents layout shift on hover */
        height: auto !important;
    }
    /* Prevent parent column from shifting width during hover */
    div[data-testid="stColumn"]:has(.gxp-stat-swipe) {
        min-width: 0 !important;
    }
    .gxp-stat-actions {
        position: absolute !important;
        left: 0 !important; right: 0 !important; bottom: 0 !important;
        height: 46px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 12px !important;
        border-radius: 0 0 1rem 1rem !important;
        z-index: 0 !important;
    }
    .gxp-stat-card-inner {
        position: relative !important;
        z-index: 1 !important;
        transition: transform 0.25s cubic-bezier(.4,0,.2,1) !important;
    }
    .gxp-stat-swipe:hover .gxp-stat-card-inner {
        transform: translateY(-46px) !important;
        box-shadow: 0 12px 32px rgba(0,0,0,0.13) !important;
    }
    .gxp-stat-action-btn {
        border-radius: 8px !important;
        padding: 6px 14px !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        cursor: pointer !important;
        text-align: center !important;
        width: 100% !important;
        transition: transform 0.12s, box-shadow 0.12s !important;
    }
    .gxp-stat-action-btn:hover {
        transform: scale(1.03) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
    }
    .gxp-stat-action-btn:active {
        transform: scale(0.97) !important;
    }
    /* Hide the Streamlit buttons behind stat cards */
    div[class*="st-key-stat_card_"] {
        position: absolute !important;
        width: 1px !important; height: 1px !important;
        overflow: hidden !important;
        clip: rect(0,0,0,0) !important;
        white-space: nowrap !important;
        border: 0 !important;
        padding: 0 !important; margin: -1px !important;
    }

    /* ── Skeleton shimmer animation ────────────────────────────────── */
    @keyframes gxp-shimmer {
        0%   { background-position: -400px 0; }
        100% { background-position: 400px 0; }
    }
    .gxp-skeleton {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 800px 100%;
        animation: gxp-shimmer 1.5s infinite ease-in-out;
        border-radius: 12px;
    }

    /* ── Individual team tile hover lift ───────────────────────────────── */
    .gxp-team-tile {
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .gxp-team-tile:hover {
        transform: translateY(-4px);
    }
    .gxp-team-tile:active {
        transform: translateY(-2px) scale(0.97);
        transition-duration: 0.08s;
    }
    /* Avatar-colored hover shadows */
    .gxp-tile-c0:hover { box-shadow: 0 8px 24px rgba(37,99,235,0.30); }
    .gxp-tile-c1:hover { box-shadow: 0 8px 24px rgba(217,119,6,0.30); }
    .gxp-tile-c2:hover { box-shadow: 0 8px 24px rgba(5,150,105,0.30); }
    .gxp-tile-c3:hover { box-shadow: 0 8px 24px rgba(124,58,237,0.30); }
    .gxp-tile-c4:hover { box-shadow: 0 8px 24px rgba(71,85,105,0.30); }
    .gxp-tile-c5:hover { box-shadow: 0 8px 24px rgba(190,24,93,0.30); }
    .gxp-tile-c6:hover { box-shadow: 0 8px 24px rgba(67,56,202,0.30); }
    .gxp-tile-c7:hover { box-shadow: 0 8px 24px rgba(161,98,7,0.30); }

    /* Loading overlay for 201 dialog */
    .gxp-loading-overlay {
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(255,255,255,0.6);
        backdrop-filter: blur(2px);
        z-index: 99999;
        display: flex; align-items: center; justify-content: center;
        transition: opacity 0.2s;
    }
    .gxp-loading-spinner {
        width: 36px; height: 36px;
        border: 3px solid #e5e7eb;
        border-top-color: #2563eb;
        border-radius: 50%;
        animation: gxp-spin 0.7s linear infinite;
    }
    @keyframes gxp-spin {
        to { transform: rotate(360deg); }
    }

    /* ── Pure HTML 201 Modal (instant, no Streamlit rerun) ── */
    .gxp-201-overlay {
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.45);
        backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
        z-index: 99999;
        display: flex; align-items: center; justify-content: center;
        opacity: 0; pointer-events: none;
        transition: opacity 0.2s ease;
    }
    .gxp-201-overlay.gxp-201-open {
        opacity: 1; pointer-events: auto;
    }
    .gxp-201-modal {
        background: #fff; border-radius: 18px;
        width: 96vw; max-width: 1400px; max-height: 92vh;
        overflow-y: auto; padding: 36px 48px 32px;
        box-shadow: 0 24px 64px rgba(0,0,0,0.22);
        transform: translateY(12px) scale(0.97);
        transition: transform 0.25s ease;
    }
    .gxp-201-open .gxp-201-modal {
        transform: translateY(0) scale(1);
    }
    .gxp-201-close {
        position: absolute; top: 18px; right: 24px;
        width: 36px; height: 36px; border-radius: 50%;
        border: none; background: #f1f5f9; color: #475569;
        font-size: 20px; cursor: pointer; display: flex;
        align-items: center; justify-content: center;
        transition: background 0.15s;
    }
    .gxp-201-close:hover { background: #e2e8f0; }
    .gxp-201-hdr {
        display: flex; align-items: center; gap: 20px; margin-bottom: 24px;
    }
    .gxp-201-avatar {
        width: 80px; height: 80px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; overflow: hidden;
        background-size: cover; background-position: center;
    }
    .gxp-201-avatar span { color: #fff; font-weight: 700; font-size: 28px; }
    .gxp-201-name { font-size: 24px; font-weight: 800; color: #191c1d; }
    .gxp-201-sub { font-size: 14px; color: #727784; margin-top: 4px; }
    .gxp-201-badge {
        display: inline-block; padding: 4px 14px; border-radius: 9999px;
        font-size: 12px; font-weight: 700; margin-top: 8px;
    }
    .gxp-201-divider {
        height: 1px; background: #e2e8f0; margin: 20px 0;
    }
    .gxp-201-grid {
        display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px;
    }
    .gxp-201-section-title {
        font-size: 12px; font-weight: 800; color: #191c1d;
        text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 10px;
    }
    .gxp-201-field {
        font-size: 13.5px; color: #727784; margin-bottom: 6px; line-height: 1.5;
    }
    .gxp-201-field b { color: #191c1d; font-weight: 700; }
    .gxp-201-gov-grid {
        display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 16px;
    }

    /* ── Hide stale content inside tabs to prevent previous-tab flash ── */
    [role="tabpanel"] [data-stale="true"] {
        opacity: 0 !important;
        transition: none !important;
    }

    /* ── Card entrance animation — fade-in + slide-up ─────────────── */
    @keyframes gxp-card-in {
        from { opacity: 0; transform: translateY(20px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .gxp-bento-hero-card,
    .gxp-bento-clickable,
    .gxp-count-stat,
    .gxp-remind-swipe,
    .gxp-qa-card {
        animation: gxp-card-in 0.4s ease-out both;
    }
    /* Staggered delays per column position */
    [data-testid="stColumn"]:nth-child(1) .gxp-bento-hero-card,
    [data-testid="stColumn"]:nth-child(1) .gxp-bento-clickable,
    [data-testid="stColumn"]:nth-child(1) .gxp-count-stat { animation-delay: 0s; }
    [data-testid="stColumn"]:nth-child(2) .gxp-bento-hero-card,
    [data-testid="stColumn"]:nth-child(2) .gxp-bento-clickable,
    [data-testid="stColumn"]:nth-child(2) .gxp-count-stat { animation-delay: 0.08s; }
    [data-testid="stColumn"]:nth-child(3) .gxp-bento-hero-card,
    [data-testid="stColumn"]:nth-child(3) .gxp-bento-clickable,
    [data-testid="stColumn"]:nth-child(3) .gxp-count-stat { animation-delay: 0.16s; }
    [data-testid="stColumn"]:nth-child(4) .gxp-count-stat { animation-delay: 0.24s; }
    [data-testid="stColumn"]:nth-child(5) .gxp-count-stat { animation-delay: 0.32s; }
    [data-testid="stColumn"]:nth-child(6) .gxp-count-stat { animation-delay: 0.40s; }
    /* Reminders + Alerts in sidebar column */
    .gxp-remind-swipe { animation-delay: 0.12s; }

    /* ── Bento hero row — uniform fixed-height cards ───────────────── */
    [data-testid="stHorizontalBlock"]:has(.gxp-bento-hero-card) {
        align-items: stretch !important;
    }
    .gxp-bento-hero-card {
        display: flex !important;
        flex-direction: column !important;
        height: 320px !important;
        min-height: 320px !important;
        max-height: 320px !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }
    .gxp-bento-hero-card::-webkit-scrollbar { width: 4px; }
    .gxp-bento-hero-card::-webkit-scrollbar-track { background: transparent; }
    .gxp-bento-hero-card::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }
    .gxp-bento-hero-card::-webkit-scrollbar-thumb:hover { background: #9ca3af; }

    /* Scrollable widget columns (Reminders, Alerts, Pending Requests) */
    [data-testid="stColumn"]:has(.gxp-wdg-scroll-marker) {
        position: relative !important;
    }
    [data-testid="stColumn"]:has(.gxp-wdg-scroll-marker) > div[data-testid="stVerticalBlock"] {
        height: 320px !important;
        max-height: 320px !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        background: #fff;
        border-radius: 16px;
        padding: 8px 16px 16px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    }
    [data-testid="stColumn"]:has(.gxp-wdg-scroll-marker) > div[data-testid="stVerticalBlock"]::-webkit-scrollbar { width: 4px; }
    [data-testid="stColumn"]:has(.gxp-wdg-scroll-marker) > div[data-testid="stVerticalBlock"]::-webkit-scrollbar-track { background: transparent; }
    [data-testid="stColumn"]:has(.gxp-wdg-scroll-marker) > div[data-testid="stVerticalBlock"]::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }
    .gxp-wdg-scroll-marker { display: none !important; }
    [data-testid="stElementContainer"]:has(.gxp-wdg-scroll-marker),
    [data-testid="stMarkdown"]:has(.gxp-wdg-scroll-marker),
    [data-testid="stMarkdownContainer"]:has(.gxp-wdg-scroll-marker) {
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* ── Bento clickable cards ──────────────────────────────────────── */
    /* Hide the pill button */
    [data-testid="stHorizontalBlock"]:has(.gxp-bento-clickable)
        > [data-testid="stColumn"]:has(.gxp-bento-clickable)
        [data-testid="stButton"] {
        height: 0 !important; overflow: hidden !important;
        margin: 0 !important; padding: 0 !important;
    }
    /* Cursor + hover lift + tactile press on card */
    .gxp-bento-clickable {
        cursor: pointer !important;
        position: relative !important;
        overflow: hidden !important;
        transition: box-shadow 0.18s ease,
                    transform 0.18s cubic-bezier(.34,1.56,.64,1) !important;
    }
    .gxp-bento-clickable:hover {
        box-shadow: 0 8px 28px rgba(0,0,0,0.12) !important;
        transform:  translateY(-4px) !important;
    }
    .gxp-bento-clickable:active {
        transform: scale(0.96) !important;
        transition-duration: 0.08s !important;
    }

    /* ── Quick Action pill buttons ─────────────────────────────────────── */
    [data-testid="stHorizontalBlock"]:has(.gxp-qa-card)
        [data-testid="stColumn"]
        [data-testid="stButton"] button {
        height:        10px  !important;
        min-height:    0     !important;
        padding:       0 8px !important;
        font-size:     0     !important;
        color:         rgba(255,255,255,0) !important;
        border:        none  !important;
        border-radius: 99px  !important;
        background:    var(--gxp-border) !important;
        box-shadow:    none  !important;
        cursor:        pointer !important;
        margin-top:    4px   !important;
        overflow:      hidden !important;
        letter-spacing: 0.3px !important;
        font-weight:   600   !important;
        transition:    background  0.2s ease,
                       box-shadow  0.2s ease,
                       height      0.18s ease,
                       color       0.15s ease !important;
    }
    /* QA col 1: indigo (Add Employee) */
    [data-testid="stHorizontalBlock"]:has(.gxp-qa-card)
        [data-testid="stColumn"]:nth-child(1):hover
        [data-testid="stButton"] button {
        height:26px !important; font-size:9px !important;
        color:rgba(255,255,255,.88) !important;
        background:#4f46e5 !important;
        box-shadow:0 0 0 3px rgba(79,70,229,.22), 0 0 14px 4px rgba(79,70,229,.40) !important;
    }
    /* QA col 2: blue (Run Payroll) */
    [data-testid="stHorizontalBlock"]:has(.gxp-qa-card)
        [data-testid="stColumn"]:nth-child(2):hover
        [data-testid="stButton"] button {
        height:26px !important; font-size:9px !important;
        color:rgba(255,255,255,.88) !important;
        background:#005bc1 !important;
        box-shadow:0 0 0 3px rgba(0,91,193,.22), 0 0 14px 4px rgba(0,91,193,.40) !important;
    }
    /* QA col 3: teal (Attendance) */
    [data-testid="stHorizontalBlock"]:has(.gxp-qa-card)
        [data-testid="stColumn"]:nth-child(3):hover
        [data-testid="stButton"] button {
        height:26px !important; font-size:9px !important;
        color:rgba(255,255,255,.88) !important;
        background:#0d9488 !important;
        box-shadow:0 0 0 3px rgba(13,148,136,.22), 0 0 14px 4px rgba(13,148,136,.40) !important;
    }
    /* QA col 4: amber (Gov. Reports) */
    [data-testid="stHorizontalBlock"]:has(.gxp-qa-card)
        [data-testid="stColumn"]:nth-child(4):hover
        [data-testid="stButton"] button {
        height:26px !important; font-size:9px !important;
        color:rgba(0,0,0,.75) !important;
        background:#f59e0b !important;
        box-shadow:0 0 0 3px rgba(245,158,11,.22), 0 0 14px 4px rgba(245,158,11,.40) !important;
    }
    /* QA col 5: rose (Calendar) */
    [data-testid="stHorizontalBlock"]:has(.gxp-qa-card)
        [data-testid="stColumn"]:nth-child(5):hover
        [data-testid="stButton"] button {
        height:26px !important; font-size:9px !important;
        color:rgba(255,255,255,.88) !important;
        background:#e11d48 !important;
        box-shadow:0 0 0 3px rgba(225,29,72,.22), 0 0 14px 4px rgba(225,29,72,.40) !important;
    }
    /* QA col 6: slate (Settings) */
    [data-testid="stHorizontalBlock"]:has(.gxp-qa-card)
        [data-testid="stColumn"]:nth-child(6):hover
        [data-testid="stButton"] button {
        height:26px !important; font-size:9px !important;
        color:rgba(255,255,255,.88) !important;
        background:#475569 !important;
        box-shadow:0 0 0 3px rgba(71,85,105,.22), 0 0 14px 4px rgba(71,85,105,.40) !important;
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
        border: none;
        border-radius: 1rem;
        padding: 20px 24px;
        margin-bottom: 24px;
        box-shadow: var(--gxp-m3-ambient-shadow, 0px 20px 40px rgba(45,51,53,0.06));
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

    /* ── Grouped sidebar navigation ────────────────────── */

    /* Group label */
    [data-testid="stSidebarContent"] .gxp-nav-group {
        font-size:      9.5px;
        font-weight:    700;
        letter-spacing: .7px;
        text-transform: uppercase;
        color:          #9ca3af;
        margin:         12px 0 2px 6px;
        padding:        0;
        line-height:    1;
    }

    /* Marker div is zero-height — purely a CSS hook */
    [data-testid="stSidebarContent"] .gxp-nav-marker {
        height: 0; line-height: 0; margin: 0; padding: 0;
    }

    /* Every nav button: flat, left-aligned, icon + label */
    [data-testid="stSidebarContent"] .gxp-nav-marker
        + [data-testid="stButton"] button {
        background:      transparent           !important;
        border:          none                  !important;
        box-shadow:      none                  !important;
        text-align:      left                  !important;
        justify-content: flex-start            !important;
        padding:         6px 10px             !important;
        border-radius:   7px                   !important;
        font-size:       13px                  !important;
        font-weight:     400                   !important;
        color:           var(--gxp-text2)      !important;
        width:           100%                  !important;
        transition:      background .12s ease, color .12s ease;
    }
    [data-testid="stSidebarContent"] .gxp-nav-marker
        + [data-testid="stButton"] button:hover {
        background: var(--gxp-surface2) !important;
        color:      var(--gxp-text)     !important;
    }

    /* Active page highlight */
    [data-testid="stSidebarContent"] .gxp-nav-marker.gxp-nav-active
        + [data-testid="stButton"] button {
        background:  var(--gxp-accent-bg) !important;
        color:       var(--gxp-accent-fg) !important;
        font-weight: 600                  !important;
    }

    /* Remove Streamlit's default gap between marker+button pairs */
    [data-testid="stSidebarContent"] .gxp-nav-marker
        + [data-testid="stButton"] {
        margin-top: -0.4rem !important;
    }

    /* ── Alerts column: stay at natural height, don't stretch to fill row ── */
    [data-testid="stColumn"]:has(.gxp-alert-card),
    [data-testid="stColumn"]:has(.gxp-alert-row),
    [data-testid="stColumn"]:has(.gxp-alert-info) {
        align-self: flex-start !important;
    }

    /* ── Global: buttons never wrap text ─────────────── */
    [data-testid="stBaseButton-primary"] > button,
    [data-testid="stBaseButton-secondary"] > button {
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* ── Quick Action Buttons Row ────────────────────── */
    .gxp-quick-actions { margin-top: -12px; margin-bottom: 24px; }

    /* ── Phase D: Bento Grid Cards ───────────────────── */
    .gxp-bento-card {{
        background: #ffffff;
        border-radius: 1rem;
        padding: 2rem;
        box-shadow: 0px 20px 40px rgba(45,51,53,0.06);
        min-height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .gxp-bento-label {{
        font-size: 0.62rem;
        font-weight: 700;
        color: #004494;
        text-transform: uppercase;
        letter-spacing: 0.2em;
        margin-bottom: 1rem;
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    }}
    .gxp-bento-muted-label {{
        font-size: 0.62rem;
        font-weight: 700;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.2em;
        margin-bottom: 1rem;
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    }}
    .gxp-bento-hero-date {{
        font-size: 4.5rem;
        font-weight: 800;
        color: #005bc1;
        line-height: 1;
        letter-spacing: -2px;
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    }}
    .gxp-bento-badge {{
        display: inline-flex;
        align-items: center;
        padding: 4px 14px;
        border-radius: 9999px;
        font-size: 0.62rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    }}
    .gxp-bento-badge-green  {{ background: #89fa9b; color: #005320; }}
    .gxp-bento-badge-yellow {{ background: #ffdea0; color: #5c4300; }}
    .gxp-bento-badge-red    {{ background: #ffdad6; color: #93000a; }}
    .gxp-bento-badge-blue   {{ background: #d8e2ff; color: #001a41; }}
    .gxp-bento-accent-card {{
        background: #febf0d;
        border-radius: 1rem;
        padding: 2rem;
        min-height: 220px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .gxp-bento-big-number {{
        font-size: 4rem;
        font-weight: 900;
        color: #000000;
        line-height: 1;
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    }}
    .gxp-bento-number-label {{ font-size: 1.15rem; font-weight: 700; color: #000000; }}
    .gxp-bento-number-sub   {{ font-size: 0.82rem; font-weight: 500; color: rgba(0,0,0,0.55); margin-top: 4px; }}
    .gxp-mini-bars {{
        display: flex;
        align-items: flex-end;
        gap: 6px;
        height: 72px;
        margin-top: 1.5rem;
    }}
    .gxp-mini-bar {{
        flex: 1;
        border-radius: 4px 4px 0 0;
        background: #e5e7eb;
        min-height: 4px;
    }}
    .gxp-mini-bar.gxp-bar-active {{ background: #005bc1; }}
    .gxp-activity-list {{ display: flex; flex-direction: column; gap: 2px; }}
    .gxp-activity-item {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px;
        border-radius: 12px;
        transition: background 0.15s;
    }}
    .gxp-activity-item:hover {{ background: #f3f4f5; }}
    .gxp-activity-icon {{
        width: 36px; height: 36px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
        font-size: 15px;
    }}
    .gxp-activity-body {{ flex: 1; min-width: 0; }}
    .gxp-activity-title {{ font-size: 12px; font-weight: 700; color: #191c1d; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .gxp-activity-sub   {{ font-size: 10px; color: #9ca3af; margin-top: 1px; }}
    .gxp-activity-time  {{ font-size: 10px; color: #9ca3af; font-weight: 500; flex-shrink: 0; }}
    .gxp-qa-m3-card {{
        background: #ffffff;
        border-radius: 1rem;
        padding: 1.25rem 0.5rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        box-shadow: 0px 4px 20px rgba(0,0,0,0.03);
        text-align: center;
    }}
    .gxp-qa-m3-icon {{
        width: 44px; height: 44px;
        border-radius: 12px;
        background: #edeeef;
        display: flex; align-items: center; justify-content: center;
        color: #004494;
        font-size: 22px;
        transition: background 0.15s;
    }}
    .gxp-qa-m3-label {{ font-size: 10px; font-weight: 700; color: #191c1d; }}

    </style>
    """, unsafe_allow_html=True)

    # ── 3. Button hover / press / ripple effects ──────────────────
    st.markdown(
        f"""<style>
        /* ── Base: buttons have position:relative so ripple spans work ── */
        .stButton > button,
        [data-testid^="stBaseButton"] button {{
            position: relative !important;
            overflow: hidden !important;
            transition:
                transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1),
                box-shadow 0.18s cubic-bezier(0.34, 1.56, 0.64, 1),
                filter 0.18s ease !important;
        }}

        /* ── Hover: lift + deepen shadow + accent glow ── */
        .stButton > button:hover,
        [data-testid^="stBaseButton"] button:hover {{
            transform: scale(1.035) !important;
            box-shadow:
                0 2px 6px rgba(0,0,0,0.14),
                0 6px 18px rgba(0,0,0,0.16),
                0 0 0 3px {accent}26 !important;
            filter: brightness(1.05) !important;
        }}

        /* ── Primary button: stronger accent glow on hover ── */
        [data-testid="stBaseButton-primary"] button:hover {{
            box-shadow:
                0 2px 6px rgba(0,0,0,0.2),
                0 8px 22px rgba(0,0,0,0.2),
                0 0 0 4px {accent}40 !important;
        }}

        /* ── Press / active: scale down + inward shadow (tactile) ── */
        .stButton > button:active,
        [data-testid^="stBaseButton"] button:active {{
            transform: scale(0.97) !important;
            transition:
                transform 0.08s cubic-bezier(0.4, 0, 0.2, 1),
                box-shadow 0.08s cubic-bezier(0.4, 0, 0.2, 1),
                filter 0.08s ease !important;
            box-shadow:
                inset 0 2px 4px rgba(0,0,0,0.18),
                inset 0 1px 2px rgba(0,0,0,0.12) !important;
            filter: brightness(0.96) !important;
        }}

        /* ── Hidden JS-only trigger buttons: no visual effects at all ── */
        .st-key-remind_approvals_pill .stButton > button,
        .st-key-alert_nav_gov .stButton > button,
        .st-key-alert_nav_payroll .stButton > button {{
            transform: none !important;
            box-shadow: none !important;
            filter: none !important;
            opacity: 0 !important;
            pointer-events: none !important;
            height: 0 !important;
            min-height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
            overflow: hidden !important;
        }}
        .st-key-remind_approvals_pill,
        .st-key-alert_nav_gov,
        .st-key-alert_nav_payroll {{
            height: 0 !important;
            overflow: hidden !important;
            margin: 0 !important;
            padding: 0 !important;
        }}

        /* ══════════════════════════════════════════════════════════
           UNIFIED INTERACTION SYSTEM — 3 tiers, consistent everywhere
           ══════════════════════════════════════════════════════════ */

        /* ── Tier 1: Large cards (bento, hero cards) ── */
        .gxp-hover-lg,
        .gxp-bento-hero-card {{
            transition: transform 0.18s cubic-bezier(.34,1.56,.64,1), box-shadow 0.18s ease !important;
            cursor: pointer !important;
            will-change: transform !important;
            backface-visibility: hidden !important;
        }}
        .gxp-hover-lg:hover,
        .gxp-bento-hero-card:not(:has(.gxp-team-tile)):not(.gxp-no-lift):hover {{
            transform: translateY(-4px) !important;
            box-shadow: 0 8px 28px rgba(0,0,0,0.12) !important;
        }}
        .gxp-hover-lg:active,
        .gxp-bento-hero-card:not(:has(.gxp-team-tile)):not(.gxp-no-lift):active {{
            transform: translateY(-2px) scale(0.98) !important;
            transition-duration: 0.08s !important;
        }}
        .gxp-bento-hero-card.gxp-no-lift {{
            cursor: default !important;
        }}
        /* ── Mini calendar day tooltip ── */
        .gxp-cal-cell {{
            cursor: default;
        }}
        .gxp-cal-tip {{
            display: none;
            position: absolute;
            bottom: calc(100% + 6px);
            left: 50%;
            transform: translateX(-50%);
            background: #191c1d;
            color: #fff;
            font-size: 10px;
            font-weight: 600;
            padding: 6px 10px;
            border-radius: 8px;
            white-space: nowrap;
            z-index: 20;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            pointer-events: none;
            font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
        }}
        .gxp-cal-tip::after {{
            content: '';
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 5px solid transparent;
            border-top-color: #191c1d;
        }}
        .gxp-cal-cell:hover .gxp-cal-tip {{
            display: block;
        }}

        /* Employee cards — no hover lift, cursor default (swipe only) */
        .gxp-emp-card {{
            cursor: default !important;
        }}

        /* ── Hidden employee card action buttons (triggered via swipe JS) ── */
        div[class*="st-key-edit_"],
        div[class*="st-key-deact_"],
        div[class*="st-key-react_"],
        div[class*="st-key-print201_"],
        div[class*="st-key-invite_"],
        div[class*="st-key-inv_yes_"],
        div[class*="st-key-inv_no_"],
        div[class*="st-key-invite_confirm_"],
        div[class*="st-key-_wl_"],
        div[class*="st-key-_wr_"],
        div[class*="st-key-_wu_"],
        div[class*="st-key-_wd_"],
        div[class*="st-key-_wh_"],
        div[class*="st-key-_dash_edit_hidden"],
        div[class*="st-key-bento_quick_stats"],
        div[class*="st-key-bento_onboarding"],
        div[class*="st-key-bento_payroll_overview"],
        div[class*="st-key-bento_workforce"],
        div[class*="st-key-bento_mini_cal"],
        div[class*="st-key-bento_recent_payroll"],
        div[class*="st-key-bento_attendance"],
        div[class*="st-key-alert_nav_gov"],
        div[class*="st-key-alert_nav_payroll"] {{
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            overflow: hidden !important;
            clip: rect(0,0,0,0) !important;
            white-space: nowrap !important;
            margin: -1px !important;
            padding: 0 !important;
            border: 0 !important;
        }}

        /* Hide widget marker divs */
        .gxp-wdg-marker {{
            display: none !important;
        }}
        [data-testid="stElementContainer"]:has(.gxp-wdg-marker) {{
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }}

        /* ── Employee card swipe-to-reveal (mirrors gxp-remind-swipe pattern) ── */
        .emp-swipe-wrap {{
            position: relative !important;
            overflow: hidden !important;
            border-radius: 14px !important;
            margin-bottom: 6px !important;
        }}
        /* Reduce Streamlit default row gap between employee card rows */
        .emp-swipe-wrap .emp-swipe-card {{
            background: var(--gxp-surface, #fff) !important;
        }}
        /* Reduce vertical gap between employee card rows — only target inner column block */
        div[data-testid="stColumn"]:has(.emp-swipe-wrap) > div > div > div[data-testid="stVerticalBlock"] {{
            gap: 0 !important;
        }}
        .emp-swipe-actions {{
            position: absolute !important;
            top: 0 !important; left: 0 !important; bottom: 0 !important;
            width: 110px !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: stretch !important;
            justify-content: stretch !important;
            gap: 0 !important;
            padding: 0 !important;
            border-radius: 16px 0 0 16px !important;
            z-index: 0 !important;
            overflow: hidden !important;
            background: linear-gradient(135deg, #e3e8ef, #dfe4ec) !important;
        }}
        .emp-swipe-card {{
            position: relative !important;
            z-index: 1 !important;
            transition: transform 0.25s cubic-bezier(.4,0,.2,1) !important;
        }}
        .emp-swipe-wrap:hover .emp-swipe-card {{
            transform: translateX(110px) !important;
        }}
        .emp-act {{
            position: relative !important;
            overflow: hidden !important;
            border-radius: 0 !important;
            padding: 0 6px !important;
            font-size: 14px !important;
            cursor: pointer !important;
            width: 100% !important;
            flex: 1 !important;
            text-align: center !important;
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 5px !important;
            color: #fff !important;
            transition: filter 0.12s !important;
            user-select: none !important;
        }}
        .emp-act span {{
            font-size: 10px !important;
            font-weight: 700 !important;
            letter-spacing: 0.03em !important;
        }}
        .emp-act:hover {{
            filter: brightness(1.1) !important;
        }}
        .emp-act:active {{
            filter: brightness(0.9) !important;
        }}
        .emp-act-sm {{
            flex: 0 0 32px !important;
            font-size: 11px !important;
            opacity: 0.85 !important;
        }}

        /* ── Payslip swipe cards ── */
        .ps-swipe-wrap {{
            position: relative !important;
            overflow: hidden !important;
            border-radius: 14px !important;
            margin-bottom: 6px !important;
        }}
        .ps-swipe-actions {{
            position: absolute !important;
            top: 0 !important; left: 0 !important; bottom: 0 !important;
            width: 90px !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: stretch !important;
            justify-content: stretch !important;
            gap: 0 !important;
            padding: 0 !important;
            border-radius: 14px 0 0 14px !important;
            z-index: 0 !important;
            overflow: hidden !important;
            background: linear-gradient(135deg, #e3e8ef, #dfe4ec) !important;
        }}
        .ps-swipe-act {{
            flex: 1 !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            transition: filter 0.12s !important;
            user-select: none !important;
            line-height: 1.2 !important;
        }}
        .ps-swipe-act:hover {{
            filter: brightness(1.1) !important;
        }}
        .ps-swipe-card {{
            position: relative !important;
            z-index: 1 !important;
            transition: transform 0.25s cubic-bezier(.4,0,.2,1) !important;
        }}
        .ps-swipe-wrap:hover .ps-swipe-card {{
            transform: translateX(90px) !important;
        }}
        /* Hide the checkbox + download button Streamlit widgets */
        div[data-testid="stColumn"]:has(.ps-swipe-wrap) > div > div > div[data-testid="stVerticalBlock"] {{
            gap: 0 !important;
        }}
        [class*="st-key-ps_chk_"],
        [class*="st-key-ps_dl_"]:not([class*="st-key-ps_dl_all"]) {{
            position: absolute !important;
            width: 1px !important; height: 1px !important;
            overflow: hidden !important;
            clip: rect(0,0,0,0) !important;
            white-space: nowrap !important;
            border: 0 !important;
        }}

        /* ── Tier 2: Medium cards (filter cards, calendar cells, action buttons) ── */
        .gxp-hover-md,
        .gxp-filter-card,
        .gxp-cal-cell:not(.empty),
        .gxp-remind-action-btn {{
            transition: transform 0.18s cubic-bezier(.34,1.56,.64,1), box-shadow 0.18s ease !important;
            cursor: pointer !important;
        }}
        .gxp-hover-md:hover,
        .gxp-filter-card:hover,
        .gxp-cal-cell:not(.empty):hover,
        .gxp-remind-action-btn:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08) !important;
        }}
        .gxp-hover-md:active,
        .gxp-filter-card:active,
        .gxp-cal-cell:not(.empty):active,
        .gxp-remind-action-btn:active {{
            transform: scale(0.97) !important;
            transition-duration: 0.06s !important;
        }}

        /* ── Tier 3: Small/subtle (table rows, list items) ── */
        .gxp-hover-sm {{
            transition: transform 0.15s ease, background 0.15s ease !important;
            cursor: pointer !important;
        }}
        .gxp-hover-sm:hover {{
            transform: translateY(-1px) !important;
            background: rgba(0,0,0,0.02) !important;
        }}
        .gxp-hover-sm:active {{
            transform: scale(0.99) !important;
        }}

        /* ── Stat card filter buttons — hide visually ── */
        [class*="st-key-_sf_"] .stButton {{
            height: 0 !important;
            overflow: hidden !important;
            margin: 0 !important;
            padding: 0 !important;
        }}

        /* ── Payroll employee card open buttons — hide visually ── */
        [class*="st-key-_pr_open_"] {{
            position: absolute !important;
            width: 1px !important; height: 1px !important;
            overflow: hidden !important;
            clip: rect(0,0,0,0) !important;
            border: 0 !important;
        }}

        /* ── DTR selectable rows — hide trigger buttons visually but keep clickable ── */
        [class*="st-key-dtr_sel_"] {{
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            opacity: 0 !important;
            pointer-events: none !important;
            overflow: hidden !important;
        }}
        /* DTR row styling handled by JS inline (highlight, hover lift, click) */

        /* ── Ripple span ── */
        @keyframes gxp-ripple {{
            0%   {{ transform: scale(0);   opacity: 0.38; }}
            70%  {{ transform: scale(2.8); opacity: 0.1; }}
            100% {{ transform: scale(3.2); opacity: 0; }}
        }}
        .gxp-ripple-wave {{
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.45);
            width: 120px;
            height: 120px;
            margin-top: -60px;
            margin-left: -60px;
            pointer-events: none;
            animation: gxp-ripple 0.65s cubic-bezier(0.22, 0.61, 0.36, 1) forwards;
        }}
        </style>""",
        unsafe_allow_html=True,
    )

    # ── Ripple JS — listens for clicks in window.parent.document ──
    _components.html("""
<script>
(function(){
  var d = window.parent.document;
  if (d._gxpRippleInit) return;
  d._gxpRippleInit = true;

  function attachRipple(btn) {
    if (btn._gxpRipple) return;
    btn._gxpRipple = true;
    btn.addEventListener('pointerdown', function(e) {
      var wave = d.createElement('span');
      wave.className = 'gxp-ripple-wave';
      var rect = btn.getBoundingClientRect();
      wave.style.left = (e.clientX - rect.left) + 'px';
      wave.style.top  = (e.clientY - rect.top)  + 'px';
      btn.appendChild(wave);
      wave.addEventListener('animationend', function() { wave.remove(); });
    });
  }

  function scanButtons() {
    d.querySelectorAll('.stButton > button, [data-testid^="stBaseButton"] button')
      .forEach(attachRipple);
  }

  // Initial scan + re-scan on Streamlit re-renders
  scanButtons();
  new MutationObserver(function(ml) {
    var changed = false;
    for (var i = 0; i < ml.length; i++) {
      if (ml[i].addedNodes.length) { changed = true; break; }
    }
    if (changed) scanButtons();
  }).observe(d.body, { childList: true, subtree: true });
})();
</script>
""", height=0, scrolling=False)

    # ── 4. Dark-mode font visibility catch-all ───────────────────────
    if not is_light:
        st.markdown(
            f"""<style>
            /* ── Dark theme: ensure MDI icons inherit parent color ── */
            .mdi {{ color: inherit; }}

            /* ── Caption / small helper text ── */
            [data-testid="stCaptionContainer"] p,
            [data-testid="stCaptionContainer"] span,
            .stCaptionContainer p {{ color: {text2} !important; }}

            /* ── Expander headers ── */
            .stExpander summary p,
            .stExpander summary span,
            [data-testid="stExpander"] summary p {{ color: {text} !important; }}
            [data-testid="stExpanderToggleIcon"] {{ display: none !important; }}

            /* ── Select / multiselect dropdown items ── */
            [data-baseweb="menu"] li,
            [data-baseweb="option"] {{ color: {text} !important; background: {surface} !important; }}
            [data-baseweb="option"]:hover {{ background: {t_vars["--gxp-surface2"]} !important; }}

            /* ── Multiselect tags ── */
            [data-baseweb="tag"] span {{ color: {text} !important; }}

            /* ── st.info / st.success / st.warning / st.error text ── */
            .stAlert p, .stAlert div {{ color: inherit !important; }}

            /* ── Markdown horizontal rule / divider ── */
            hr {{ border-color: {border} !important; opacity: 0.5; }}

            /* ── Code blocks ── */
            .stCode pre, .stCode code {{ color: {text} !important; background: {t_vars["--gxp-surface2"]} !important; }}

            /* ── Radio and checkbox label text ── */
            .stRadio label span, .stCheckbox label span {{ color: {text} !important; }}

            /* ── Number input arrows ── */
            [data-testid="stNumberInput"] button {{ color: {text2} !important; }}

            /* ── Plotly chart text (axis labels, legend) ── */
            .stPlotlyChart text {{ fill: {text2} !important; }}
            </style>""",
            unsafe_allow_html=True,
        )

    # ── 5. Table row-density CSS (compact / normal / relaxed) ─────
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

    # ── 6. Material 3 / Tactile Sanctuary component overrides ─────────
    # These apply to ALL themes but use var(--gxp-*) so they adapt.
    # The Tactile theme benefits most, but pill buttons & rounded inputs
    # look good on every theme.
    _is_tactile = st.session_state.get("gxp_theme", DEFAULT_THEME) == "tactile"

    st.markdown(
        f"""<style>
        /* ── Global Font: Plus Jakarta Sans ── */
        /* Use inheritance (no .stApp *) to avoid overriding Streamlit's
           button icon spans which need Material Symbols Outlined font. */
        html, body, .stApp,
        p, span:not([class*="material"]), div, label, input, textarea, select,
        .stMarkdown, .stTextInput, .stSelectbox, .stNumberInput,
        [data-testid="stSidebar"], [data-testid="stHeader"],
        [data-testid="stButton"] button {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont,
                         'Segoe UI', sans-serif !important;
        }}
        /* MDI icons inside buttons */
        [data-testid="stButton"] button .mdi {{
            line-height: 1;
        }}

        /* ── Pill-shaped Primary Buttons ── */
        [data-testid="stBaseButton-primary"] button {{
            border-radius: 9999px !important;
            background: linear-gradient(135deg, {accent} 0%, #3d89ff 100%) !important;
            border: none !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            padding: 0.6rem 1.5rem !important;
            letter-spacing: 0.01em !important;
            box-shadow: 0 4px 14px rgba(0,91,193,0.25) !important;
            transition: all 0.2s cubic-bezier(0.4,0,0.2,1) !important;
        }}
        [data-testid="stBaseButton-primary"] button:hover {{
            box-shadow: 0 6px 20px rgba(0,91,193,0.35) !important;
            transform: translateY(-1px) !important;
            filter: brightness(1.05) !important;
        }}
        [data-testid="stBaseButton-primary"] button:active {{
            transform: scale(0.98) !important;
            box-shadow: 0 2px 8px rgba(0,91,193,0.2) !important;
        }}

        /* ── Secondary / Default Buttons ── */
        [data-testid="stBaseButton-secondary"] button,
        .stButton > button:not([kind="primary"]) {{
            border-radius: 9999px !important;
            border: 1.5px solid {border} !important;
            background: transparent !important;
            color: {t_vars.get("--gxp-accent", accent)} !important;
            font-weight: 500 !important;
            padding: 0.5rem 1.25rem !important;
            transition: all 0.15s ease !important;
        }}
        [data-testid="stBaseButton-secondary"] button:hover,
        .stButton > button:not([kind="primary"]):hover {{
            background: {t_vars.get("--gxp-surface2", "#f3f4f5")} !important;
            border-color: {t_vars.get("--gxp-accent", accent)} !important;
        }}

        /* ── Rounded Input Fields ── */
        .stTextInput input,
        .stNumberInput input {{
            border-radius: 12px !important;
            background: {surface} !important;
            border: 1.5px solid {t_vars.get("--gxp-m3-outline-variant", "#c2c6d5")} !important;
            padding: 0.7rem 1rem !important;
            font-size: 0.875rem !important;
            color: {text} !important;
            transition: all 0.18s ease !important;
        }}
        .stTextInput input:hover,
        .stNumberInput input:hover {{
            border-color: {text2} !important;
        }}
        .stTextInput input:focus,
        .stNumberInput input:focus {{
            border-color: {accent} !important;
            box-shadow: 0 0 0 3px {accent}1a !important;
            background: {surface} !important;
        }}
        .stTextInput input::placeholder,
        .stNumberInput input::placeholder {{
            color: {t_vars.get("--gxp-m3-outline", "#727784")} !important;
            opacity: 0.7 !important;
        }}

        /* ── Textarea ── */
        .stTextArea textarea {{
            border-radius: 12px !important;
            background: {surface} !important;
            border: 1.5px solid {t_vars.get("--gxp-m3-outline-variant", "#c2c6d5")} !important;
            padding: 0.7rem 1rem !important;
            font-size: 0.875rem !important;
            color: {text} !important;
            transition: all 0.18s ease !important;
            line-height: 1.5 !important;
        }}
        .stTextArea textarea:hover {{
            border-color: {text2} !important;
        }}
        .stTextArea textarea:focus {{
            border-color: {accent} !important;
            box-shadow: 0 0 0 3px {accent}1a !important;
        }}

        /* ── Select / Dropdown ── */
        [data-baseweb="select"] > div {{
            border-radius: 12px !important;
            background: {surface} !important;
            border: 1.5px solid {t_vars.get("--gxp-m3-outline-variant", "#c2c6d5")} !important;
            transition: all 0.18s ease !important;
        }}
        [data-baseweb="select"] > div:hover {{
            border-color: {text2} !important;
        }}
        [data-baseweb="select"]:focus-within > div {{
            border-color: {accent} !important;
            box-shadow: 0 0 0 3px {accent}1a !important;
        }}

        /* ── Date Input ── */
        .stDateInput input {{
            border-radius: 12px !important;
            background: {surface} !important;
            border: 1.5px solid {t_vars.get("--gxp-m3-outline-variant", "#c2c6d5")} !important;
            padding: 0.7rem 1rem !important;
            transition: all 0.18s ease !important;
        }}
        .stDateInput input:hover {{
            border-color: {text2} !important;
        }}
        .stDateInput input:focus {{
            border-color: {accent} !important;
            box-shadow: 0 0 0 3px {accent}1a !important;
        }}

        /* ── Multiselect ── */
        [data-baseweb="select"][aria-expanded] > div {{
            border-radius: 12px !important;
        }}

        /* ── Checkbox + Radio ── */
        .stCheckbox label span[data-testid="stCheckbox"],
        .stRadio label span {{
            color: {text} !important;
        }}

        /* ── Widget labels ── */
        label[data-testid="stWidgetLabel"] {{
            font-size: 0.8125rem !important;
            font-weight: 600 !important;
            color: {text2} !important;
            letter-spacing: 0.01em !important;
            margin-bottom: 2px !important;
        }}

        /* ── File uploader ── */
        [data-testid="stFileUploader"] section {{
            border-radius: 12px !important;
            border: 1.5px dashed {t_vars.get("--gxp-m3-outline-variant", "#c2c6d5")} !important;
            background: {t_vars.get("--gxp-surface2", "#f3f4f5")} !important;
            transition: all 0.18s ease !important;
        }}
        [data-testid="stFileUploader"] section:hover {{
            border-color: {accent} !important;
            background: {surface} !important;
        }}

        /* ── Pill-Shaped Tab Switcher ── */
        .stTabs [data-baseweb="tab-list"] {{
            background: {t_vars.get("--gxp-surface2", "#f3f4f5")} !important;
            border-radius: 9999px !important;
            padding: 4px !important;
            gap: 2px !important;
            border-bottom: none !important;
            width: fit-content !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 9999px !important;
            padding: 0.4rem 1rem !important;
            font-size: 0.8125rem !important;
            font-weight: 500 !important;
            border-bottom: none !important;
            color: {text2} !important;
            background: transparent !important;
            transition: all 0.15s ease !important;
            white-space: nowrap !important;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            background: rgba(255,255,255,0.5) !important;
        }}
        .stTabs [aria-selected="true"] {{
            background: {surface} !important;
            color: {t_vars.get("--gxp-accent", accent)} !important;
            font-weight: 600 !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
            border-bottom: none !important;
        }}
        /* Hide the default Streamlit tab highlight bar */
        .stTabs [data-baseweb="tab-highlight"] {{
            display: none !important;
        }}
        .stTabs [data-baseweb="tab-border"] {{
            display: none !important;
        }}

        /* ── Card Containers (ambient shadow, no borders) ── */
        .gxp-card, .gxp-stat-card, .gxp-summary-card,
        .gxp-panel, .gxp-payslip-card, .gxp-remit-card,
        .gxp-period-card {{
            border-radius: 1rem !important;
            box-shadow: {t_vars.get("--gxp-m3-ambient-shadow", "0px 20px 40px rgba(45,51,53,0.06)")} !important;
        }}

        /* ── Expander / accordion cards (M3 style) ── */
        .stExpander {{
            border-radius: 1rem !important;
            border: none !important;
            overflow: hidden !important;
            background: {surface} !important;
            box-shadow: {t_vars.get("--gxp-m3-ambient-shadow", "0px 20px 40px rgba(45,51,53,0.06)")} !important;
            margin-bottom: 0.75rem !important;
        }}
        .stExpander summary {{
            display: flex !important;
            align-items: center !important;
            padding: 1rem 1.5rem !important;
            background: {surface} !important;
            border-radius: 1rem !important;
            font-size: 0.9375rem !important;
            font-weight: 600 !important;
        }}
        /* MDI funnel / filter icon (mask-image = theme-aware, no font needed) */
        .stExpander summary::before {{
            content: '' !important;
            display: inline-block !important;
            width: 18px !important;
            height: 18px !important;
            margin-right: 8px !important;
            flex-shrink: 0 !important;
            background-color: {text2} !important;
            -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M14 12v7.88c.04.3-.06.62-.29.83-.39.39-1.02.39-1.41 0l-2.01-2.01c-.23-.23-.33-.54-.29-.83V12h-.03L4.21 4.62c-.34-.43-.26-1.06.17-1.4C4.57 3.08 4.78 3 5 3h14c.22 0 .43.08.62.22.43.34.51.97.17 1.4L14.03 12H14z'/%3E%3C/svg%3E") !important;
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M14 12v7.88c.04.3-.06.62-.29.83-.39.39-1.02.39-1.41 0l-2.01-2.01c-.23-.23-.33-.54-.29-.83V12h-.03L4.21 4.62c-.34-.43-.26-1.06.17-1.4C4.57 3.08 4.78 3 5 3h14c.22 0 .43.08.62.22.43.34.51.97.17 1.4L14.03 12H14z'/%3E%3C/svg%3E") !important;
            -webkit-mask-size: contain !important;
            mask-size: contain !important;
            -webkit-mask-repeat: no-repeat !important;
            mask-repeat: no-repeat !important;
        }}
        .stExpander details[open] > summary {{
            border-radius: 1rem 1rem 0 0 !important;
            border-bottom: 1px solid {border} !important;
        }}
        .stExpander details > div[data-testid="stExpanderDetails"] {{
            background: {surface} !important;
            padding: 1.25rem 1.5rem 1.5rem !important;
        }}
        /* ── Hide broken Streamlit toggle icon text ── */
        [data-testid="stExpanderToggleIcon"],
        [data-testid="stExpander"] summary span[translate="no"],
        [data-testid="stExpander"] summary svg {{
            display: none !important;
        }}
        /* Replace with CSS arrow */
        [data-testid="stExpander"] summary::before {{
            content: '\\25B6';
            font-size: 10px;
            color: #9ca3af;
            margin-right: 8px;
            transition: transform 0.2s;
            display: inline-block;
        }}
        [data-testid="stExpander"][open] summary::before {{
            transform: rotate(90deg);
        }}

        /* ── Metric cards ── */
        [data-testid="metric-container"] {{
            border-radius: 1rem !important;
            border: none !important;
            box-shadow: {t_vars.get("--gxp-m3-ambient-shadow", "0px 20px 40px rgba(45,51,53,0.06)")} !important;
            padding: 1.25rem !important;
        }}

        /* ── Dialog / Modal styling ── */
        [data-testid="stModal"] > div {{
            border-radius: 1.5rem !important;
            box-shadow: 0 25px 50px rgba(0,0,0,0.12) !important;
        }}
        /* Widen large dialogs beyond Streamlit's 740px cap */
        [data-testid="stModal"] [data-testid="stDialog"] {{
            max-width: 960px !important;
            width: 92vw !important;
        }}

        /* ── Form submit button inherits pill style ── */
        .stFormSubmitButton button {{
            border-radius: 9999px !important;
        }}

        /* ── Checkbox & Radio — accent color ── */
        .stCheckbox input:checked + div,
        .stRadio input:checked + div {{
            background-color: {accent} !important;
            border-color: {accent} !important;
        }}

        /* ── Checkbox highlight fix ──
           Streamlit Emotion class on stCheckbox wrapper applies a colored
           background when checked. Override with transparent. */
        [data-testid="stCheckbox"][class*="st-emotion-cache"],
        [data-testid="stCheckbox"][class*="eczd22r"],
        div.row-widget.stCheckbox {{
            background: transparent !important;
            background-color: transparent !important;
        }}

        /* ── Download button ── */
        [data-testid="stBaseButton-secondary"]:has(svg) button {{
            border-radius: 9999px !important;
        }}

        /* ── Page-level editorial label ── */
        .gxp-page-label {{
            font-size: 0.6875rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: {accent};
            margin-bottom: 0.25rem;
        }}
        .gxp-editorial-heading {{
            font-size: 2.5rem;
            font-weight: 800;
            color: var(--gxp-text);
            line-height: 1.15;
            letter-spacing: -0.02em;
            margin: 0 0 0.5rem;
        }}
        .gxp-editorial-sub {{
            font-size: 1.1rem;
            font-weight: 400;
            color: var(--gxp-text2);
            margin: 0;
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
        check = '<span class="mdi mdi-check" style="color:'+accent+';margin-right:2px;font-size:18px;"></span> ' if is_active else ""

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

    with st.sidebar.expander("Themes", expanded=False):
        st.markdown(
            "<div style='font-size:10px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.8px;color:#94a3b8;margin-bottom:6px;'>"
            "<span class='mdi mdi-weather-night' style='font-size:18px;'></span>&nbsp;Dark</div>",
            unsafe_allow_html=True,
        )
        for key, theme in dark_themes.items():
            _theme_card(key, theme)

        st.markdown(
            "<div style='font-size:10px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.8px;color:#94a3b8;margin:10px 0 6px;'>"
            "<span class='mdi mdi-white-balance-sunny' style='font-size:18px;'></span>&nbsp;Light</div>",
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


def remit_card(
    title: str,
    color: str,
    rows: list[tuple[str, str]],
    total: tuple[str, str],
    remitted: bool = False,
) -> str:
    """Return HTML for a government remittance card.

    Parameters
    ----------
    remitted : bool
        When True, a green "✓ Remitted" badge is shown next to the title.
        When False, a grey "Pending" badge is shown.
    """
    if remitted:
        badge = (
            '<span style="margin-left:6px;font-size:9px;font-weight:700;'
            'background:#dcfce7;color:#16a34a;padding:2px 7px;border-radius:10px;'
            'vertical-align:middle">✓ Remitted</span>'
        )
    else:
        badge = (
            '<span style="margin-left:6px;font-size:9px;font-weight:700;'
            'background:#f3f4f6;color:#9ca3af;padding:2px 7px;border-radius:10px;'
            'vertical-align:middle">Pending</span>'
        )
    html  = f'<div class="gxp-remit-card" style="border-top-color:{color}">'
    html += f'<h4 style="display:flex;align-items:center">{title}{badge}</h4>'
    # Wrap data rows in a flex-grow container so the total line always sits at bottom
    html += '<div class="gxp-remit-rows">'
    for label, value in rows:
        html += f'<div class="gxp-remit-row"><span>{label}</span><span>{value}</span></div>'
    html += '</div>'
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
