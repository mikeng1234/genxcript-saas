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

PAGE: EMPLOYEES

Build an Employees page for "GenXcript Payroll".

Same top nav and left sidebar as Dashboard (Employees is the active nav item).

Main content — 3 pill-shaped tab switcher at top (not underline tabs):
  Tab 1: "Employee List"
  Tab 2: "Leave & OT Approvals" (badge showing "3 pending" in red pill)
  Tab 3: "Leave Balances"

Tab 1 — Employee List:
  - Editorial page title: "Employees"
  - Action bar: search input (rounded-full, #ebeef0 bg, placeholder "Search by name, ID...")
    left side. Right side: "Add Employee" gradient pill button with + icon.
  - Employee cards in a 3-column grid. Each card (white, radius 2rem, ambient shadow, padding 1.5rem):
    - Top: employee avatar circle (colored initials), name bold, position in #5a6062,
      department pill badge (rounded-full, #ebeef0 bg).
    - Middle row: "₱25,000/mo" salary, employment type badge (Regular/Probationary, pill).
    - Bottom row: gov ID status dots — SSS, PhilHealth, Pag-IBIG, TIN
      (green dot = on file, red dot = missing).
    - Hover: slight scale-up (1.02), shadow deepens.
  - Show 6 sample employees with varied statuses.

Tab 2 — Leave & OT Approvals:
  - Two equal columns side by side.
  - Left "Leave Requests": 3 pending cards (white, radius 1.5rem, ambient shadow).
    Each: employee avatar + name, leave type pill (VL=blue, SL=green, CL=amber),
    date range, reason text truncated. "Approve" green gradient button + "Reject" ghost red button.
  - Right "OT Requests": same card structure — employee, date, requested hours, reason.
    Approve/Reject buttons.

Tab 3 — Leave Balances:
  - 3 summary metric cards (amber, white, white): Total Employees, Avg VL Remaining, Avg SL Used.
  - Table (white card, radius 2rem): Employee | VL Rem / Total | SL Rem / Total | CL Rem / Total.
    Clean rows, no dividers, hover row highlights with #f1f4f5.
