# GeNXcript Payroll SaaS — Marketing Landing Page

## INSTRUCTION

Generate a complete, single-file, self-contained HTML landing page (HTML + CSS + JS inline) for **GeNXcript Payroll** — a cloud-based Payroll & HR Management System built for Philippine SMEs. This is a **marketing/explainer website**, NOT the application itself. It should feel like a premium SaaS landing page (think Gusto, Rippling, or Deel — but localized for the Philippines).

The output must be a single HTML file. No external dependencies except Google Fonts. Fully responsive. All CSS and JS inline within the HTML file.

---

## GLOBAL DESIGN SYSTEM

### Colors
```
--primary: #005bc1        /* GeNXcript Blue — headers, buttons, links */
--primary-dark: #003d82   /* Darker blue for hover states */
--primary-light: #e8f0fe  /* Light blue for backgrounds, badges */
--accent: #10b981         /* Green — success states, checkmarks, CTAs */
--accent-dark: #059669    /* Darker green for hover */
--warning: #f59e0b        /* Amber — highlights, badges */
--dark: #191c1d           /* Near-black for body text */
--gray-700: #374151       /* Secondary text */
--gray-500: #6b7280       /* Muted text */
--gray-300: #d1d5db       /* Borders */
--gray-100: #f3f4f6       /* Section alternate backgrounds */
--light: #f8fafc          /* Page background */
--white: #ffffff
--glass-bg: rgba(255, 255, 255, 0.7)
--glass-border: rgba(255, 255, 255, 0.3)
```

### Typography
- Font: `'Plus Jakarta Sans', sans-serif` — import from Google Fonts: `https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap`
- Hero headline: 800 weight, 3.5rem desktop / 2.25rem mobile
- Section headings: 700 weight, 2.5rem desktop / 1.75rem mobile
- Subheadings: 600 weight, 1.25rem
- Body: 400 weight, 1rem, line-height 1.7, color var(--gray-700)
- Small/caption: 0.875rem

### Spacing & Layout
- Max content width: 1200px, centered with auto margins
- Section padding: 100px vertical desktop, 60px mobile
- Card border-radius: 16px
- Button border-radius: 12px

### Effects
- Glass morphism cards: `background: rgba(255,255,255,0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.3); box-shadow: 0 8px 32px rgba(0,91,193,0.08);`
- Gradient backgrounds for hero and CTA sections: subtle diagonal gradients using primary colors
- Smooth transitions: `transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);`
- Hover lift on cards: `transform: translateY(-4px); box-shadow: 0 20px 40px rgba(0,91,193,0.12);`

### Animations (IntersectionObserver)
- Use `IntersectionObserver` with threshold 0.1 to trigger animations when elements scroll into view
- Elements start with `opacity: 0; transform: translateY(30px);` and animate to `opacity: 1; transform: translateY(0);`
- Stagger child animations by 100ms each using CSS `transition-delay`
- Add a CSS class `.animate-in` that is toggled by the observer
- Apply to all section headings, cards, feature items, pricing cards, testimonials, and FAQ items

---

## PAGE STRUCTURE — SECTION BY SECTION

---

### 1. STICKY NAVIGATION BAR

**Behavior:**
- Position fixed at top, full width, z-index 1000
- Initially transparent background with white text
- On scroll past 80px: solid white background, subtle bottom shadow, dark text — transition smoothly
- Mobile: hamburger icon (three lines) that toggles a full-screen overlay menu

**Content (left to right):**
- Logo: Bold text "GeNXcript" in primary blue + "Payroll" in normal weight gray-700 (or swap to white when on transparent bg). Font size 1.5rem.
- Nav links (desktop only, horizontal): Features | Modules | Pricing | FAQ | Contact
- Each link smooth-scrolls to the corresponding section
- Right side: "Login" text link + "Start Free Trial" button (primary blue bg, white text, 12px radius, padding 10px 24px)

**Mobile nav overlay:**
- Full screen white overlay with centered vertical nav links, 1.5rem font size
- Close (X) button top right
- Same links plus "Start Free Trial" button at bottom

---

### 2. HERO SECTION

**Purpose (AIDA — Attention):** Instantly communicate what GeNXcript does and why it matters for Philippine businesses.

**Layout:** Full viewport height (100vh), centered content, gradient background.

**Background:** Diagonal gradient from `#005bc1` (top-left) to `#003d82` (bottom-right), with a subtle dot-grid pattern overlay (CSS-generated using radial-gradient, opacity 0.05, white dots).

**Content (centered, max-width 800px):**

1. **Badge** (above headline): A small pill-shaped badge with light background: "🇵🇭 Built for Philippine Businesses" — font-size 0.875rem, padding 6px 16px, border-radius 100px, background rgba(255,255,255,0.15), color white, backdrop-filter blur.

2. **Headline** (white, 800 weight):
   ```
   Payroll That Runs Itself.
   Compliance That Never Sleeps.
   ```

3. **Subheadline** (white, 300 weight, 1.25rem, opacity 0.85, max-width 600px):
   ```
   The cloud payroll system that automates SSS, PhilHealth, Pag-IBIG, and BIR computations — so you can focus on growing your business, not chasing compliance deadlines.
   ```

4. **CTA Buttons** (side by side, gap 16px, centered):
   - Primary: "Start Free Trial" — background var(--accent) #10b981, white text, padding 16px 32px, font-weight 600, font-size 1.1rem, rounded 12px. Hover: darken to #059669, slight scale(1.02).
   - Secondary: "Book a Demo" — transparent border 2px white, white text, same sizing. Hover: fill white bg, text color primary.
   - Below buttons, small text: "No credit card required · 14-day free trial · Cancel anytime" — white, opacity 0.6, font-size 0.8rem.

5. **Hero Stats Row** (below CTAs, 48px margin-top): Three stats in a row with vertical dividers.
   - "500+" / "Companies Trust Us"
   - "₱2.1B+" / "Payroll Processed"
   - "99.9%" / "Uptime SLA"
   - Each stat: number in white 700 weight 2rem, label in white opacity 0.7 0.875rem
   - These are aspirational/placeholder metrics

6. **Floating UI Mockup hint** (optional): Below the stats, a subtle downward chevron arrow that pulses (CSS animation, bounce up and down gently), encouraging scroll. White, opacity 0.5.

---

### 3. TRUSTED BY / SOCIAL PROOF BAR

**Purpose (AIDA — Attention/Interest):** Build immediate credibility.

**Layout:** Horizontal strip, background white, padding 40px, border-bottom 1px solid var(--gray-300).

**Content:**
- Small centered label: "TRUSTED BY LEADING PHILIPPINE COMPANIES" — font-size 0.75rem, letter-spacing 3px, uppercase, color var(--gray-500), margin-bottom 24px.
- Row of 6 placeholder company logos — use styled text placeholders in gray-400: "TechCorp PH", "Manila Foods Inc.", "Visayas Trading", "Pacific Ventures", "Metro Staffing", "Cebu Digital". Each in a slightly different font-weight/style to simulate different logos. Opacity 0.4. Grayscale. Spaced evenly with flexbox. On hover, opacity goes to 0.7.
- On mobile: horizontally scrollable or wrap to 2 rows of 3.

---

### 4. PAIN POINTS SECTION

**Purpose (AIDA — Interest):** Identify the prospect's problems and agitate them.

**Section ID:** `#features`

**Background:** var(--light) #f8fafc

**Content:**

**Section label** (above heading): Small uppercase text "WHY GENXCRIPT" in primary blue, font-weight 600, letter-spacing 2px, font-size 0.8rem.

**Heading:** "Stop Losing Money to Manual Payroll"
**Subheading:** "Philippine businesses lose an average of 40 hours per month on manual payroll processing. Here's what that really costs you."

**Pain Point Cards** (3 cards in a row, 1 column on mobile):

Card 1:
- Icon: Use a large emoji or CSS icon — "⏰"
- Title: "Wasted Hours on Manual Computation"
- Description: "Your HR team spends days computing SSS, PhilHealth, Pag-IBIG, and tax withholdings manually — every single pay period. That's time and talent better spent growing your team."
- Stat highlight: "40+ hrs/month" in bold primary color

Card 2:
- Icon: "⚠️"
- Title: "Compliance Penalties & Audit Risk"
- Description: "One miscalculated BIR 1601-C or late SSS R3 submission can cost you six-figure penalties. Manual processes make errors inevitable, not just possible."
- Stat highlight: "₱250K+ avg. penalty" in bold red

Card 3:
- Icon: "😤"
- Title: "Employee Frustration & Turnover"
- Description: "Late payslips, wrong deductions, and no self-service access — nothing erodes trust faster. Your best employees won't tolerate payroll chaos."
- Stat highlight: "23% higher turnover" in bold warning color

**Card styling:** White background, 16px border-radius, padding 32px, subtle shadow. Top border 3px solid — Card 1: primary, Card 2: red (#ef4444), Card 3: warning. Hover lift effect.

---

### 5. FEATURES OVERVIEW

**Purpose (AIDA — Interest/Desire):** Showcase key capabilities.

**Background:** White

**Section label:** "PLATFORM CAPABILITIES"
**Heading:** "Everything You Need. Nothing You Don't."
**Subheading:** "A modular payroll platform — start with what you need, add modules as you grow."

**Feature Grid** (2 columns desktop, 1 column mobile, alternating icon-left/icon-right layout — or a consistent grid of 6 feature cards):

Feature 1 — "Automated Gov't Contributions"
- Icon/emoji: "🏛️"
- Text: "SSS, PhilHealth, Pag-IBIG, and BIR withholding tax — automatically computed based on the latest contribution tables. Updated when regulations change."

Feature 2 — "One-Click Payroll Run"
- Icon: "▶️"
- Text: "Set up your pay period, review earnings, and execute payroll in minutes — not days. Automatic computation of gross-to-net with all mandatory deductions."

Feature 3 — "Employee Self-Service Portal"
- Icon: "👤"
- Text: "Employees view payslips, file leaves, request OT, clock in via GPS, and update their profiles — without bugging HR."

Feature 4 — "Real-Time Compliance Reports"
- Icon: "📊"
- Text: "Generate SSS R3, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C, 2316, and 1604-C — all formatted and ready to submit."

Feature 5 — "Supervisor Dashboard"
- Icon: "👥"
- Text: "Team leads get their own portal with approval workflows for leave, OT, and DTR corrections — plus team payroll expenditure breakdowns."

Feature 6 — "Analytics & Insights"
- Icon: "📈"
- Text: "Period-over-period payroll comparison, OT heatmaps, lateness tracking, break monitoring, and expenditure trend charts."

**Card style:** Glass morphism card. Emoji icon in a 56px circle with primary-light background. Title 600 weight 1.1rem. Description gray-700. Padding 28px. On hover, subtle lift.

---

### 6. PLUGIN ARCHITECTURE / MODULE SHOWCASE

**Purpose (AIDA — Desire):** Show the modular "pay for what you need" model.

**Section ID:** `#modules`

**Background:** var(--gray-100) with a very subtle CSS gradient mesh or dotted pattern.

**Section label:** "MODULAR ARCHITECTURE"
**Heading:** "Build Your Perfect Payroll Stack"
**Subheading:** "Start with Core and add modules as your business grows. No bloat. No paying for features you'll never use."

**Module Cards** (interactive, horizontally scrollable on mobile, grid on desktop):

Create 7 module cards arranged in a visually appealing layout. Each card represents a module with its color code.

**Card Layout per module:**
- Color-coded left border (4px) or top accent stripe
- Module color dot (12px circle) + module name in bold
- "Included in: [Tier name]" badge
- Bullet list of 4-5 key features (short, one line each)
- Tag/pill at bottom showing the tier

**Module cards data:**

1. **CORE** (Green #10b981, dot: 🟢)
   - Always Included
   - Features: Company Setup, Employee Management (201 files), Role-Based Access, Employee Self-Service Portal, Theme & Preferences
   - Badge: "Included in ALL plans"

2. **PAYROLL ENGINE** (Blue #3b82f6, dot: 🔵)
   - Features: Automated Payroll Run, Gov't Contributions (SSS/PhilHealth/Pag-IBIG/BIR), Payslip Generation & PDF, Gov't Report Filing, 13th Month Computation
   - Badge: "Essential plan & above"

3. **TIME & ATTENDANCE** (Yellow #eab308, dot: 🟡)
   - Features: Daily Time Records (DTR), Shift Schedule Management, DTR Correction Workflows, GPS Clock-in with Geofencing, Night Shift Differential (NSD)
   - Badge: "Professional plan & above"

4. **LEAVE & OT MANAGEMENT** (Orange #f97316, dot: 🟠)
   - Features: Leave Filing & Approval Workflow, Leave Balance & Entitlements, OT Request & Approval, Special Leaves (Solo Parent, Maternity, Paternity)
   - Badge: "Professional plan & above"

5. **SUPERVISOR PORTAL** (Red #ef4444, dot: 🔴)
   - Features: Team Bento Dashboard, Team Payroll View, Subordinate 201 Cards, Multi-level Approval Workflows
   - Badge: "Enterprise plan"

6. **ANALYTICS & INSIGHTS** (Purple #8b5cf6, dot: 🟣)
   - Features: Payroll Period Comparison, Workforce OT Heatmap, Lateness & Undertime Monitoring, Break Tracking & Trend Charts
   - Badge: "Enterprise plan"

7. **COMPLIANCE+** (Dark #374151, dot: ⚫)
   - Premium Add-on
   - Features: BIR 2316 Annual Certificates, BIR 1604-C + Alphalist, Full Audit Trail & Export, Custom Holiday Management
   - Badge: "Premium Add-on"

**Interactivity:** When a user hovers over a card, it lifts slightly and the border color intensifies. On mobile, cards are in a horizontal scroll container with snap points.

**Below the cards**, add a centered text: "Not sure which modules you need? **Book a free consultation →**" with "Book a free consultation" as a link styled in primary color.

---

### 7. PRICING TABLE

**Purpose (AIDA — Desire/Action):** Convert interest into action with clear, anchored pricing.

**Section ID:** `#pricing`

**Background:** White

**Section label:** "SIMPLE PRICING"
**Heading:** "Transparent Pricing. No Hidden Fees."
**Subheading:** "Choose the plan that fits your team size and needs. Scale up anytime."

**Pricing Toggle:** Above the cards, a toggle switch between "Monthly" and "Annual (Save 20%)" — the toggle is a pill-shaped switcher. When Annual is selected, prices update (multiply by 0.8, display monthly equivalent). Default: Monthly selected.

**4 Pricing Cards** in a row (stack on mobile):

**Card 1 — Starter**
- Header bg: white
- Price: "₱2,999" /month (annual: ₱2,399/mo billed annually)
- Subtitle: "For small teams getting started"
- Employee limit: "Up to 20 employees"
- Feature list (checkmarks ✓ in green):
  - ✓ Company Setup & Profile
  - ✓ Employee Management
  - ✓ Role-Based Authentication
  - ✓ Employee Self-Service Portal
  - ✓ Theme Preferences
  - ✗ Payroll Engine (grayed out with ✗)
  - ✗ Time & Attendance
  - ✗ Leave & OT Management
  - ✗ Supervisor Portal
  - ✗ Analytics
- CTA button: "Start Free Trial" — outlined style, primary color border

**Card 2 — Essential**
- Same white style
- Price: "₱5,999" /month (annual: ₱4,799/mo)
- Subtitle: "For teams that run payroll"
- Employee limit: "Up to 50 employees"
- Feature list:
  - ✓ Everything in Starter
  - ✓ Automated Payroll Run
  - ✓ Gov't Contributions (SSS, PhilHealth, Pag-IBIG, BIR)
  - ✓ Payslip Generation & PDF
  - ✓ Gov't Compliance Reports
  - ✓ 13th Month Pay Computation
  - ✗ Time & Attendance
  - ✗ Leave & OT
  - ✗ Supervisor Portal
  - ✗ Analytics
- CTA: "Start Free Trial" — outlined

**Card 3 — Professional** ⭐ MOST POPULAR
- **This card is visually elevated:** Slightly larger scale (transform: scale(1.05)), primary blue border (2px), a "Most Popular" ribbon/badge at the top (small absolute-positioned pill, background primary, white text, rotated or flat at top-right corner).
- Price: "₱9,999" /month (annual: ₱7,999/mo)
- Subtitle: "For growing companies"
- Employee limit: "Up to 100 employees"
- Feature list:
  - ✓ Everything in Essential
  - ✓ Daily Time Records (DTR)
  - ✓ Shift Scheduling
  - ✓ GPS Clock-in & Geofencing
  - ✓ Night Differential (NSD)
  - ✓ Leave Filing & Approvals
  - ✓ OT Requests & Approvals
  - ✓ Special Leave Types
  - ✗ Supervisor Portal
  - ✗ Analytics
- CTA: "Start Free Trial" — **solid primary blue bg, white text** (stands out)

**Card 4 — Enterprise**
- Header: Subtle dark gradient background (#191c1d to #374151), white text for price
- Price: "₱14,999" /month (annual: ₱11,999/mo)
- Subtitle: "For large organizations"
- Employee limit: "Unlimited employees"
- Feature list (all white/light text):
  - ✓ Everything in Professional
  - ✓ Supervisor Team Dashboard
  - ✓ Team Payroll View
  - ✓ Approval Workflows
  - ✓ Payroll Comparison Analytics
  - ✓ Workforce OT Heatmap
  - ✓ Lateness & Break Monitoring
  - ✓ Trend Charts & Insights
  - ✓ Priority Support
- CTA: "Contact Sales" — accent green bg, white text

**Below pricing cards:**
- Note: "Need more than your plan allows? Add employees for just **₱50–₱100/head/month** beyond your tier threshold."
- Another note: "All plans include a **14-day free trial**. No credit card required."
- Link: "Need a custom plan? **Talk to our team →**"

**Pricing card styling:** Border-radius 20px, padding 36px, min-height: auto. Glass morphism for the standard cards. Each card has a subtle hover lift. The Professional card has a subtle glow/shadow in primary blue.

---

### 8. HOW IT WORKS

**Purpose:** Reduce perceived complexity.

**Background:** var(--gray-100)

**Section label:** "GET STARTED IN MINUTES"
**Heading:** "From Sign-Up to First Payroll in 4 Steps"

**4 Steps in a horizontal row** (vertical stack on mobile), connected by a dashed line (CSS border-top dashed between step circles on desktop):

Step 1:
- Circle with number "1" (primary bg, white text, 48px circle)
- Title: "Create Your Account"
- Description: "Sign up in 30 seconds. No credit card needed. Set up your company profile and departments."

Step 2:
- Circle "2"
- Title: "Add Your Employees"
- Description: "Import your team via CSV or add them manually. Employee profiles, 201 files, and org chart — done."

Step 3:
- Circle "3"
- Title: "Configure & Customize"
- Description: "Set pay frequencies, contribution tables, leave policies, and shift schedules. We handle the compliance rules."

Step 4:
- Circle "4"
- Title: "Run Your First Payroll"
- Description: "One click. Earnings computed, deductions calculated, payslips generated, gov't reports ready. That's it."

**Below steps:** Centered CTA button — "Start Your Free Trial →" in accent green.

---

### 9. TESTIMONIALS

**Purpose (Social Proof):** Build trust through peer validation.

**Background:** White

**Section label:** "WHAT OUR CLIENTS SAY"
**Heading:** "Loved by HR Teams Across the Philippines"

**3 Testimonial Cards** (horizontal on desktop, vertical stack or carousel on mobile):

Testimonial 1:
- Quote: "We used to spend 3 days every cutoff manually computing SSS and PhilHealth. With GeNXcript, payroll is done in 2 hours. Our HR team can finally focus on what matters — our people."
- Name: "Maria Santos"
- Role: "HR Manager, TechStartup Manila"
- Avatar: CSS-generated circle with initials "MS" in primary-light bg, primary text

Testimonial 2:
- Quote: "The BIR compliance reports alone are worth the subscription. No more last-minute panic before filing deadlines. Everything is auto-generated and accurate."
- Name: "Roberto Cruz"
- Role: "Finance Director, Visayas Manufacturing Co."
- Avatar: Initials "RC"

Testimonial 3:
- Quote: "Our employees love the self-service portal. Leave filing, payslip downloads, DTR viewing — they don't need to email HR for every little thing anymore. Game changer."
- Name: "Jennifer Reyes"
- Role: "VP Operations, Pacific BPO Solutions"
- Avatar: Initials "JR"

**Card styling:** White bg card, left border 3px primary-light, padding 32px, large curly open-quote character " at top in primary-light color (font-size 4rem, opacity 0.2, absolute positioned). Star rating (5 filled stars ★ in amber #f59e0b) above the quote.

---

### 10. COMPLIANCE & AUTHORITY BADGES

**Purpose (Authority):** Reinforce trust through compliance signals.

**Layout:** Centered row of badges/icons on a light background strip, padding 48px.

**Badges** (styled as pill-shaped items with icons):
- "🏛️ DOLE Compliant"
- "📋 BIR-Ready Reports"
- "🔒 Bank-Grade Security"
- "☁️ 99.9% Uptime SLA"
- "🇵🇭 Built in the Philippines"
- "🔄 Auto-Updated Contribution Tables"

Each badge: background white, border 1px solid var(--gray-300), border-radius 100px, padding 10px 20px, font-size 0.85rem, font-weight 500. Inline-flex with gap. On mobile: wrap to multiple rows.

---

### 11. FAQ ACCORDION

**Purpose:** Overcome objections.

**Section ID:** `#faq`

**Background:** var(--gray-100)

**Section label:** "FREQUENTLY ASKED QUESTIONS"
**Heading:** "Got Questions? We've Got Answers."

**FAQ Items** (accordion — click to expand, only one open at a time):

Q1: "Is GeNXcript compliant with Philippine labor laws?"
A1: "Absolutely. GeNXcript is built from the ground up for Philippine compliance. We auto-compute SSS, PhilHealth, Pag-IBIG, and BIR withholding tax based on the latest contribution tables and tax schedules. Our system generates DOLE-formatted reports including SSS R3, PhilHealth RF-1, Pag-IBIG MCRF, BIR 1601-C, 2316, and 1604-C."

Q2: "How long does it take to set up?"
A2: "Most companies are up and running within a day. You can import employees via CSV, configure your pay periods and contribution settings, and run your first payroll immediately. Our onboarding team is available to guide you through the process at no extra cost."

Q3: "Is my payroll data secure?"
A3: "Yes. GeNXcript runs on enterprise-grade cloud infrastructure with bank-level encryption (AES-256), role-based access controls, and full audit trails. Your data is backed up continuously and we maintain a 99.9% uptime SLA."

Q4: "Can I switch plans or add modules later?"
A4: "Absolutely. Our modular architecture means you can start with just the Core plan and add Payroll Engine, Time & Attendance, Leave Management, or any other module whenever you're ready. Upgrades take effect immediately — no data migration needed."

Q5: "Do you support multiple companies or branches?"
A5: "Yes. GeNXcript supports multi-company management from a single account. Perfect for holding companies, franchises, or businesses with multiple branches across the Philippines."

Q6: "What happens after the free trial ends?"
A6: "After your 14-day free trial, you can choose any plan that fits your needs. Your data is preserved — nothing is deleted. If you decide not to continue, you can export all your data before your account is deactivated."

Q7: "How is the 13th month pay handled?"
A7: "GeNXcript automatically tracks 13th month pay accruals throughout the year and generates the DOLE-compliant 13th month pay report. You can view accrued amounts at any time and process the payout with a single click."

**Accordion styling:** Each item is a white card with 16px border-radius, margin-bottom 12px. Question row has padding 20px 24px, font-weight 600, cursor pointer, flex with a chevron/plus icon on the right that rotates on open. Answer panel slides down with max-height transition (0 to auto via a fixed max-height like 500px). Answer text padding 0 24px 20px 24px, color gray-700. Active item has left border 3px primary blue.

---

### 12. FINAL CTA SECTION WITH CONTACT FORM

**Purpose (AIDA — Action):** Convert.

**Section ID:** `#contact`

**Background:** Full-width gradient same as hero (#005bc1 to #003d82), with subtle pattern overlay.

**Layout:** Two columns on desktop (text left, form right). Single column on mobile.

**Left Column:**
- Heading (white, 700): "Ready to Transform Your Payroll?"
- Subheading (white, opacity 0.85): "Join 500+ Philippine companies that have ditched spreadsheets and manual calculations. Start your free trial today — no credit card required."
- Bullet points (white, with green checkmarks):
  - ✓ 14-day free trial, full access
  - ✓ Free onboarding assistance
  - ✓ No long-term contracts
  - ✓ Cancel anytime
- **Urgency element:** A small banner/badge: "🔥 Limited Time: Early-bird pricing locked for life for first 100 sign-ups" — background rgba(255,255,255,0.1), border 1px rgba(255,255,255,0.2), rounded 12px, padding 12px 20px, font-size 0.9rem.

**Right Column — Contact Form:**
- White card, border-radius 20px, padding 36px, box-shadow large
- Heading inside card: "Get Started Free" — dark text, 600 weight, 1.5rem
- Form fields (each with label above, 12px border-radius, border 1px var(--gray-300), padding 12px 16px, full width, margin-bottom 16px):
  - Full Name (text input)
  - Work Email (email input)
  - Company Name (text input)
  - Number of Employees (select dropdown: "1-20", "21-50", "51-100", "101-500", "500+")
  - Which modules interest you? (multi-select checkboxes in a 2-column grid: Payroll Engine, Time & Attendance, Leave & OT, Supervisor Portal, Analytics, Compliance+)
- Submit button: Full width, "Start My Free Trial →", background accent green, white text, padding 16px, font-weight 600, font-size 1.1rem, border-radius 12px. Hover: darker green.
- Below button: "Or **book a live demo** with our team" — small text link.
- The form does not need to actually submit. On click, show a brief success message: "Thank you! We'll be in touch within 24 hours." replacing the form content with a checkmark animation.

---

### 13. FOOTER

**Background:** var(--dark) #191c1d, color white.

**Layout:** 4 columns on desktop, stacked on mobile.

**Column 1 — Brand:**
- "GeNXcript" logo text (1.25rem, 700 weight, white)
- Tagline: "Cloud Payroll & HR for Philippine Businesses" — opacity 0.6, 0.875rem
- Social icons row (placeholder styled circles): Facebook, LinkedIn, Twitter/X — 32px circles, border 1px rgba(255,255,255,0.2), centered icon letters "f", "in", "X"

**Column 2 — Product:**
- Heading: "Product" (font-weight 600, 0.9rem, uppercase, letter-spacing 1px, opacity 0.5, margin-bottom 16px)
- Links (opacity 0.7, hover opacity 1): Features, Modules, Pricing, Integrations, Roadmap, Changelog

**Column 3 — Resources:**
- Heading: "Resources"
- Links: Documentation, API Reference, Help Center, Blog, Compliance Guides, System Status

**Column 4 — Company:**
- Heading: "Company"
- Links: About Us, Careers, Contact, Partners, Privacy Policy, Terms of Service

**Bottom Bar:** Full-width border-top 1px rgba(255,255,255,0.1), padding 24px 0, flex between:
- Left: "© 2026 GeNXcript Technologies. All rights reserved."
- Right: "Made with 💙 in the Philippines"

---

## JAVASCRIPT BEHAVIORS

### 1. Smooth Scroll
All anchor links with `href="#section-id"` should smooth scroll using `element.scrollIntoView({ behavior: 'smooth', block: 'start' })`. Offset for the sticky navbar height (approx 72px) — adjust scroll position accordingly using `window.scrollTo` with calculated offset.

### 2. Navbar Scroll Effect
On `window.scroll`, if `scrollY > 80`, add class `nav-scrolled` to the navbar that changes background to white, text to dark, and adds `box-shadow: 0 2px 20px rgba(0,0,0,0.08)`.

### 3. Mobile Menu Toggle
Hamburger button toggles a class on the mobile overlay. Clicking any nav link inside the overlay also closes it.

### 4. Scroll Animations (IntersectionObserver)
Select all elements with class `.animate-on-scroll`. Use `IntersectionObserver` with `{ threshold: 0.1, rootMargin: '0px 0px -50px 0px' }`. When intersecting, add class `.animated` which transitions from `opacity:0; transform:translateY(30px)` to `opacity:1; transform:translateY(0)`. For card groups, stagger children by adding incremental `transition-delay`.

### 5. FAQ Accordion
Click on a question toggles its answer panel. Close any previously open panel first (only one open at a time). Rotate the chevron icon. Use max-height transition for smooth open/close.

### 6. Pricing Toggle
Toggle between monthly and annual pricing. When annual is active, update all price displays to the annual rate. Use a smooth CSS transition or fade effect on the number change.

### 7. Animated Counters (Hero Stats)
When the hero stats scroll into view (or on page load since they're above fold), animate the numbers from 0 to their target value over 2 seconds using `requestAnimationFrame`. Format numbers with commas/symbols as needed.

### 8. Form Submission
On form submit (preventDefault), validate that required fields are filled, then replace the form with a success message div containing a green checkmark (CSS-drawn circle with checkmark) and "Thank you! We'll be in touch within 24 hours."

---

## RESPONSIVE BREAKPOINTS

- Desktop: > 1024px — full multi-column layouts
- Tablet: 768px–1024px — 2-column grids become 2 columns (or reduce to 1 where needed), nav may switch to hamburger
- Mobile: < 768px — single column everything, hamburger nav, horizontal scroll for module cards, stacked pricing cards, larger touch targets (min 48px), adjusted font sizes (hero heading 2.25rem, section headings 1.75rem)

---

## CRITICAL REQUIREMENTS

1. **Single HTML file** — ALL CSS in a `<style>` tag in `<head>`, ALL JS in a `<script>` tag before `</body>`.
2. **No external dependencies** except the Google Fonts link.
3. **No placeholder images or broken image links** — use CSS shapes, gradients, emojis, or SVG-drawn icons only.
4. **Every section must have the `animate-on-scroll` class** on appropriate elements.
5. **All interactive elements must work** — nav scroll, mobile menu, FAQ accordion, pricing toggle, form submission, counter animation.
6. **Semantic HTML** — use `<header>`, `<nav>`, `<main>`, `<section>`, `<footer>`, `<article>` appropriately.
7. **Accessibility basics** — alt text where needed, proper heading hierarchy (one H1 only), focus styles on interactive elements, ARIA labels on buttons.
8. **Performance** — no heavy computations, use CSS transitions over JS animation where possible, `will-change` on animated elements.
9. **The page should look polished and production-ready**, not like a template or wireframe.
10. **Philippine cultural context** — currency in ₱ (Philippine Peso), references to Philippine government agencies (DOLE, BIR, SSS, PhilHealth, Pag-IBIG), Filipino business context.

---

## FINAL NOTE

Generate the COMPLETE HTML file with all content, all CSS, and all JS. Do not use shorthand like "/* more styles here */" or "// similar for other sections" — write out every line. The output should be copy-paste ready and render a fully functional, beautiful marketing landing page in any modern browser.
