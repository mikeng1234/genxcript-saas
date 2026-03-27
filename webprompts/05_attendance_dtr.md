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

PAGE: ATTENDANCE / DTR

Build an Attendance (Daily Time Record) page for "GeNXcript Payroll".

Same top nav + sidebar. "Attendance" active.

3 pill-shaped tab switcher: "Daily Entry" | "Attendance Summary" | "Corrections"

Tab 1 — Daily Entry (shown by default):
  - Top action bar: date picker (rounded-full, #ebeef0 bg, today pre-selected) left.
    "Save All" gradient pill button right.
  - White card table (radius 2rem, ambient shadow). Column headers:
    Employee | Shift | Time In | Time Out | Late (min) | Undertime (min) | NSD Hrs | OT Hrs | Status
  - Time In/Out: pill input fields (#ebeef0 bg, no border) inline in each row.
  - Shift column: small pill showing "8AM–5PM" in #ebeef0.
  - Status pill per row: Present (green #89fa9b bg), Absent (red), Late (amber #fbbc05 bg).
  - Show 8 sample employee rows with varied statuses.
  - No divider lines between rows — alternate very subtle #f8f9fa row bg.

Tab 2 — Attendance Summary:
  - Filter bar: "From" date + "To" date inputs (rounded-full) + employee dropdown, all #ebeef0.
  - 3 summary metric cards (white, radius 2rem):
    "Avg Attendance Rate 94%", "Total Late Incidents 12", "Total NSD Hours 48".
  - Per-employee expandable cards (white, radius 1.5rem):
    Collapsed: name + attendance % pill + "View Detail" link.
    Expanded: mini month calendar grid — each day a small colored dot
    (green=present, red=absent, amber=late, gray=rest day).

Tab 3 — Corrections:
  - "Pending Corrections" section title.
    Cards per correction (white, radius 1.5rem, ambient shadow):
    Employee avatar + name | Original time | Requested time | Reason text.
    "Approve & Apply" green gradient button | "Reject" ghost red button.
  - "Correction History" collapsible section below with approved/rejected log table.
