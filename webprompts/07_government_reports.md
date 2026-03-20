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

PAGE: GOVERNMENT REPORTS

Build a Government Reports page for "GenXcript Payroll" (Philippine statutory compliance).

Same top nav + sidebar. "Government Reports" active.

4 pill-shaped tab switcher: "Monthly Reports" | "Annual Reports" | "DOLE 13th Month" | "Remittance Log"

Tab 1 — Monthly Reports (shown by default):
  - Two pill dropdowns side by side (#ebeef0 bg, no border, rounded-full):
    "Select Pay Period" | "Select Report" (options: SSS R3/R5, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C)
  - Report preview card (white, radius 2rem, ambient shadow, padding 2rem):
    Header: icon + "SSS R3 / R5" title bold, description gray below.
    "Period: Mar 1–31, 2026 · Employees: 11" small info line.
    Table (no borders, alternating subtle row bg):
      Employee | SSS No. | EE Share | ER Share | Total
    Footer (3 columns, larger text): Employee Total | Employer Total | Grand Total (bold #005bc1).
  - "Download SSS R3/R5 (PDF)" gradient full-width pill button below card.

Tab 2 — Annual Reports:
  - Year selector pill dropdown. Report type: "BIR 2316 (per employee)" or "BIR 1604-C Alphalist".
  - Employee list (white card, radius 2rem):
    Each row: employee name + TIN | "Download 2316 PDF" small blue ghost button per row.
  - "Download Full Alphalist (BIR 1604-C)" gradient button bottom.

Tab 3 — DOLE 13th Month:
  - Year selector pill. 3 metric cards (white, radius 2rem):
    "Total Employed: 11" | "Benefitted: 11" | "Total 13th Month: ₱142,500" (amber card).
  - Table (white card, radius 2rem): Employee (A–Z) | Monthly Basic Pay | 13th Month Pay.
  - Contact info form below: Name, Position, Tel inputs (rounded-full, #ebeef0).
  - "Download DOLE 13th Month PDF" gradient button.

Tab 4 — Remittance Log:
  - Grid card (white, radius 2rem): months as columns (Jan–Dec), agencies as rows
    (SSS, PhilHealth, Pag-IBIG, BIR). Each cell:
    - Filed: green pill with reference number + date.
    - Overdue: red pill "OVERDUE".
    - Upcoming: gray pill with due date.
  - "Log Remittance" gradient button top-right to record a new payment.
