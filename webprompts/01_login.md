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

PAGE: LOGIN

Build a login page for "GenXcript Payroll" — a Philippine payroll SaaS product.

Layout:
- Full viewport. Left 40% = branded panel. Right 60% = login form.
- Left panel: gradient background (135deg, #005bc1 to #3d89ff).
  Centered vertically: large logo text "GenXcript" in white bold, tagline
  "PAYROLL SYSTEM" in uppercase tracking-widest, and 3 bullet features
  ("Philippine-compliant", "Multi-company", "Real-time payroll") each with
  a Material Symbol checkmark icon.
- Right panel: white bg (#ffffff). Vertically centered card (max-width 400px,
  margin auto, padding 3rem, radius 2rem, ambient shadow).
  Card contains:
    - "Welcome back!" in 2rem bold #2d3335
    - Subtitle: "Sign in to your account to continue." in #5a6062
    - Input: "Employee ID or Email" — filled bg #ebeef0, no border, radius 9999px, padding 1rem 1.5rem
    - Input: "Password" — same style, eye toggle icon right side
    - "Remember me" checkbox (small, blue when checked)
    - Primary CTA button: "Sign In" full width, gradient fill, pill shape, 1rem padding
    - Ghost link button: "Forgot your password?" centered below, #005bc1 text
    - Divider line (very light #ebeef0) then footer: "GenXcript Payroll System" in tiny uppercase tracking-widest #adb3b5
- No top navigation bar on this page.
