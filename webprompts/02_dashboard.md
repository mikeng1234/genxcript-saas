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

PAGE: DASHBOARD

Build a dashboard page for "GeNXcript Payroll" — a Philippine payroll SaaS.

Include fixed glassmorphism top nav: logo "GeNXcript" left, search bar center-right
(rounded-full, #ebeef0 bg), notification bell icon, user avatar circle.

Left sidebar (240px, fixed):
  - "GeNXcript" brand bold blue top, "Admin Portal" caption gray below.
  - Nav items (pill shape, full width): Dashboard (active, blue-50 bg), Employees,
    Payroll Run, Attendance, Workforce Analytics, Government Reports, Calendar,
    Company Setup, Preferences.
  - Icons from Material Symbols for each item.
  - Bottom: "Run Payroll" gradient pill button (full width).

Main content (margin-left 240px, padding 3rem):
  Section 1 — Editorial header:
    - "OVERVIEW" in 0.65rem bold uppercase tracking-widest #005bc1
    - "Good morning, Admin." in 3.5rem extrabold #2d3335
    - Subtitle: "Everything is ready for your next pay cycle." in #5a6062
    - Large faint sparkle icon (Material Symbol: auto_awesome) top-right, opacity 8%.

  Section 2 — Bento grid (CSS grid, 12 columns, gap 2rem):
    Row 1:
      - Col 1–8: "Next Pay Date" white card (radius 2rem, ambient shadow, padding 2rem).
        "UPCOMING MILESTONE" label small uppercase blue. Big date "MAR 31" in 5rem
        black bold #005bc1. "IN 11 DAYS" green pill badge. Bottom: avatar stack
        (3 circles + "+7") left, "Review Cycle" ghost pill button right.
      - Col 9–12: Amber card (bg #fbbc05, radius 2rem). Groups icon top-left,
        arrow top-right. Big number "10" in 4rem black. "Active Employees" bold.
        "2 new this month" small below.

    Row 2:
      - Col 1–7: "Payroll Expenditure" white card. Header: title left, "₱142,500"
        bold right with green "↑ 2.4% vs last cycle" below it. Bar chart below
        (6 bars, last one solid blue, others light blue, month labels beneath,
        rounded tops).
      - Col 8–12: "Recent Activity" card (bg #f1f4f5). Title + "VIEW ALL" blue link.
        4 activity rows, each: colored circle icon left (green=approved, blue=onboarded,
        amber=document, red=warning), bold title, gray subtitle, timestamp right.
        Each row white card on hover.

  Section 3 — "QUICK ACTIONS" label uppercase small:
    6 icon cards in a row (white, radius 2rem, centered icon + label below):
    Add Employee | Run Payroll | Attendance | Government Reports | Calendar | Settings
