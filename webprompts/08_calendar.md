Design System: "Tactile Sanctuary" — High-End Editorial Minimalism
Font: Plus Jakarta Sans (weights 300–800). Use it for everything.
Theme: Light mode only.
Colors:
  - Primary: #005bc1 | Primary light: #3d89ff
  - Surface (page bg): #f8f9fa
  - Card (white): #ffffff
  - Surface low: #f1f4f5
  - Surface container: #ebeef0
  - Amber accent: #fbbc05 (for highlight cards)
  - Green accent: #89fa9b (for success states)
  - Text primary: #2d3335 (never pure black)
  - Text secondary: #5a6062
  - Error: #a83836

Rules:
  - NO 1px borders anywhere. Separate sections using background color shifts only.
  - Card radius: 2rem. Pill/button radius: 9999px.
  - Shadow (ambient only): 0px 20px 40px rgba(45,51,53,0.06)
  - Primary CTA: gradient fill linear-gradient(135deg, #005bc1 0%, #3d89ff 100%), white text, pill shape.
  - Navigation header: glassmorphism — rgba(255,255,255,0.7) + backdrop-filter blur(20px), fixed top.
  - Left sidebar: 240px, white/slate-50 bg, pill-shaped active nav item in blue-50 with #005bc1 text.
  - Page bg is #f8f9fa. Cards sit on top as white (#ffffff) rounded tiles.
  - Output: full HTML file using Tailwind CSS CDN + Material Symbols Outlined icons.

---

PAGE: CALENDAR

Build a Calendar page for "GenXcript Payroll".

Same top nav + sidebar. "Calendar" active.

Layout: two columns — left 68% = calendar card, right 32% = upcoming events panel.

Left — Calendar card (white, radius 2rem, ambient shadow, padding 2rem):
  - Month navigator row: "‹" ghost icon button | "March 2026" bold 1.25rem centered |
    "›" ghost icon button. "Today" pill button top-right.
  - Day-of-week header row: Mon Tue Wed Thu Fri Sat Sun in small uppercase gray.
  - Day grid (7 columns):
    Each day cell (radius 1rem, padding 0.5rem, min-height 80px):
    - Date number: small top-right of cell, bold if today.
    - Today: date number inside a #005bc1 circle, white text.
    - Pay period days: subtle blue-50 (#eff6ff) bg tint spanning the range.
      First day labeled "Pay Start" in tiny blue text. Last day "Pay End".
    - Holiday cells: amber (#fbbc05) at 15% opacity bg. Tiny holiday name below date.
    - Remittance deadline cells: red dot + "SSS Due" tiny label below date.
    - Weekend cells: slightly darker #f1f4f5 bg.
    - Cell hover: surface-container bg (#ebeef0), scale 1.02 transition.
  - Legend below calendar: colored dot key for Pay Period / Holiday / Deadline / Today.

Right — "Upcoming Events" card (white, radius 2rem, ambient shadow, padding 1.5rem):
  - Title "Upcoming" bold + current month small gray.
  - Scrollable event list (no dividers, spacing between items):
    Each event row: colored left accent bar (3px, rounded) + date bold + event name +
    "in X days" pill small right.
    Colors: blue=pay period, amber=holiday, red=deadline.
  - Show 6–8 upcoming events:
    Mar 31 — Next Pay Date (blue) | Apr 10 — SSS Remittance Due (red) |
    Apr 7 — Bataan Day (amber) | Apr 10 — PhilHealth Due (red) |
    Apr 15 — Pag-IBIG Due (red) | Apr 15 — Pay Period Start (blue).
