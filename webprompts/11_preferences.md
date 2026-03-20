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

PAGE: PREFERENCES

Build a Preferences page for "GenXcript Payroll".

Same top nav + sidebar. "Preferences" active.

Editorial page title: "Preferences"
Subtitle: "Customize your GenXcript experience."

3 white cards stacked (radius 2rem, ambient shadow, padding 2.5rem, gap 1.5rem):

Card 1 — "Appearance":
  Section label "APPEARANCE" small uppercase tracking-widest #005bc1.
  - Theme: label left, "Light / Dark" pill switcher right (Light = #005bc1 bg active).
  - Accent Color: label left, 5 color swatches right (blue, green, amber, purple, teal —
    each a 32px circle, selected has 3px #005bc1 ring offset).
  - Font Size: "S / M / L" 3-pill switcher, M active.
  - Date Format: dropdown (rounded-full #ebeef0) — MM/DD/YYYY | DD/MM/YYYY | YYYY-MM-DD.

Card 2 — "Notifications":
  Section label "NOTIFICATIONS" small uppercase tracking-widest #005bc1.
  Toggle rows (no dividers, spacing via padding only):
  Each row: Material Symbol icon (colored) + label bold + description gray small — left.
    iOS-style pill toggle right (blue when on).
  Toggles:
    - notifications · Payroll Finalized · "Get notified when payroll is approved" — ON
    - check_circle · Leave Approved · "When your leave request is approved" — ON
    - schedule · OT Approved · "When your overtime request is approved" — ON
    - calendar_month · Remittance Reminder · "3 days before government dues" — ON
    - person_add · New Employee · "When a new employee is onboarded" — OFF

Card 3 — "Account":
  Section label "ACCOUNT" small uppercase tracking-widest #005bc1.
  - Display Name input (rounded-full, #ebeef0, current value pre-filled "Jasper Dizon").
    "Update Name" small blue ghost pill button inline right.
  - Change Password subsection label small gray.
    3 inputs stacked (rounded-full, #ebeef0): Current Password | New Password | Confirm Password.
  - "Save Changes" gradient pill button bottom-right.
