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

PAGE: COMPANY SETUP

Build a Company Setup page for "GeNXcript Payroll".

Same top nav + sidebar. "Company Setup" active.

Horizontal scrollable pill tab switcher (8 tabs):
  General | Gov't Numbers | Payroll Policy | Holidays | Schedules | Locations | Leave Templates | Preferences

Show "General" tab as active.

Main content — two white cards stacked (radius 2rem, ambient shadow, padding 2.5rem each):

Card 1 — "Company Information":
  Section label "COMPANY INFORMATION" small uppercase tracking-widest #005bc1.
  Form fields in a 2-column grid (each input: rounded-full, #ebeef0 bg, no border, padding 1rem 1.5rem):
    - Company Name (full width)
    - Region (dropdown)        | Pay Frequency (dropdown: Semi-monthly / Monthly / Weekly)
    - Industry                 | TIN (Tax ID)
  Background color shift (no line) to next section.

Card 2 — "Payroll Policy":
  Section label "PAYROLL POLICY" small uppercase tracking-widest #005bc1.
  - Daily Rate Divisor row:
    Label "Daily Rate Divisor" bold + helper "Divides monthly salary into daily rate" gray small.
    3 pill option buttons side by side: "22 · 6-day week" | "26 · 5-day (DOLE)" | "30 · Calendar month"
    Active pill: #005bc1 bg white text. Inactive: #ebeef0 bg #2d3335 text.
    Below: amber info card (#fbbc05 at 10% bg, radius 1rem, padding 1rem):
      "₱25,000 ÷ 26 = ₱961.54 / day" — live preview example.
  - OT Minimum Hours: number input (rounded-full, #ebeef0) + "hours" suffix label.
  - Probationary Period: number input + "months" suffix label.

  "Save Changes" gradient pill button bottom-right of page.
