# GeNXcript Payroll — Investor Business Proposal (Stitch Prompt)

## INSTRUCTION

Generate a complete, single-file, self-contained HTML page (HTML + CSS + JS inline) that serves as an **investor pitch deck / business proposal website** for **GeNXcript Payroll** — a cloud-based Payroll & HR Management System for Philippine SMEs.

This is NOT a marketing landing page. This is a **Sequoia-style pitch deck presented as a scrollable, interactive web page** — designed to be shared with potential investors and business partners. Think of it as a premium slide deck reimagined as a full-screen scrolling website.

The output must be a single HTML file. No external dependencies except Google Fonts. Fully responsive. All CSS and JS inline within the HTML file. Every section should feel like its own "slide" occupying the full viewport height.

---

## GLOBAL DESIGN SYSTEM

### Colors
```
--primary: #005bc1          /* GeNXcript Blue — headers, buttons, key metrics */
--primary-dark: #003d82     /* Darker blue for hover states, nav backgrounds */
--primary-light: #e8f0fe    /* Light blue for backgrounds, badges */
--accent: #10b981           /* Green — growth indicators, positive metrics */
--accent-dark: #059669      /* Darker green for hover */
--gold: #f59e0b             /* Gold/Amber — highlights, important callouts, stars */
--red: #ef4444              /* Red — for problem section emphasis */
--dark: #191c1d             /* Near-black for body text on light sections */
--gray-700: #374151         /* Secondary text */
--gray-500: #6b7280         /* Muted text */
--gray-300: #d1d5db         /* Borders, dividers */
--gray-100: #f3f4f6         /* Alternate section backgrounds */
--light: #f8fafc            /* Light section backgrounds */
--white: #ffffff
--section-dark-bg: #0f172a  /* Dark navy for dark sections */
--section-dark-text: #e2e8f0 /* Light text on dark sections */
```

### Typography
- Font: `'Plus Jakarta Sans', sans-serif` — import from Google Fonts: `https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap`
- Also load `'JetBrains Mono'` for any code/metric displays: `https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap`
- Section headlines: 800 weight, 3rem desktop / 2rem mobile, letter-spacing: -0.02em
- Section subheadlines: 400 weight, 1.25rem, color var(--gray-500), max-width 600px
- Metric numbers (large KPI displays): 'JetBrains Mono', 700 weight, 3.5rem
- Body text: 400 weight, 1.05rem, line-height 1.8, color var(--gray-700)
- Small labels/captions: 600 weight, 0.75rem, text-transform uppercase, letter-spacing 0.1em, color var(--gray-500)

### Spacing & Layout
- Each section: min-height 100vh, display flex, align-items center
- Max content width: 1100px, centered
- Section internal padding: 80px 40px (desktop), 60px 20px (mobile)
- Card border-radius: 16px
- Generous whitespace — this is a pitch deck, not a blog. Let content breathe.

### Visual Rhythm
Alternate between dark and light sections to create visual rhythm:
- Section 1 (Cover): Dark gradient background
- Section 2 (Problem): Light background
- Section 3 (Solution): Dark background
- Section 4 (Market): Light background
- Section 5 (Product): Dark background
- Section 6 (Architecture): Light background
- Section 7 (Business Model): Dark background
- Section 8 (Competition): Light background
- Section 9 (GTM): Dark background
- Section 10 (Traction): Light background
- Section 11 (Team): Dark background
- Section 12 (Financials): Light background
- Section 13 (The Ask): Dark gradient background (like cover, bookend feel)
- Section 14 (Contact): Light background

---

## INTERACTIVE BEHAVIORS

### 1. Scroll Progress Bar
A thin (3px) progress bar fixed at the very top of the viewport. Uses var(--primary) color. Updates on scroll to show how far through the document the user is. Full width = bottom of page. Use `requestAnimationFrame` or a throttled scroll listener for performance.

### 2. Section Navigation Dots
Fixed on the right side of the viewport (vertically centered). Small circular dots (8px), one per section. The active section's dot is filled with var(--primary) and slightly larger (10px). Other dots are outlined/hollow. Clicking a dot smooth-scrolls to that section. On hover, show a tiny tooltip label with the section name. Use IntersectionObserver to detect which section is currently in view.

### 3. Scroll-Triggered Animations
Use IntersectionObserver (threshold: 0.15) to trigger entrance animations as sections scroll into view:
- Default entrance: fade in + slide up 30px, duration 0.6s, ease-out
- Stagger children: cards, list items, and grid children should animate in sequence with 0.1s delay between each
- Metric counters: animate from 0 to final value when the section enters view (use requestAnimationFrame counter)
- Charts/bars: grow from 0 width/height to final value with a smooth ease-out over 1s
- Only animate ONCE — add a `.animated` class after first trigger and skip subsequent observations

### 4. Animated Counters
For key metrics (revenue numbers, percentages, company counts), animate the number counting up from 0 to the target value over 1.5 seconds when the element enters the viewport. Format numbers with commas. Prefix with the peso sign where appropriate. Use `Intl.NumberFormat('en-PH')` for formatting.

### 5. Keyboard Navigation
- Arrow Down / Space: scroll to next section
- Arrow Up: scroll to previous section
- Number keys 1-9: jump to that section number (0 = section 10, minus = 11, etc. — or just 1-9)

### 6. Print Styles
Add `@media print` styles that:
- Remove scroll animations, fixed elements (progress bar, nav dots)
- Force each section to start on a new page (`page-break-before: always`)
- Remove dark backgrounds, make all text dark on white
- Show all content (no overflow hidden, no max-height)
- Clean, report-style layout

---

## SECTION CONTENT — WRITE EXACTLY THIS COPY

---

### SECTION 1: COVER SLIDE
**Layout**: Full viewport, centered content, dark gradient background (`linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)`)

**Content**:

Top-left: Small GeNXcript logo placeholder — a simple styled text logo: "GeNXcript" in white, 700 weight, with a small blue square (8px) before it as a brand mark.

Center (vertically and horizontally):
- Small label above headline: "INVESTOR PRESENTATION 2026" — uppercase, letter-spacing 0.2em, color var(--gold), font-size 0.75rem, with a thin gold line (40px wide) on each side
- Main headline: "GeNXcript Payroll" — 4rem desktop, 2.5rem mobile, white, 800 weight
- Subheadline: "The Operating System for Philippine Payroll" — 1.5rem, color var(--gray-300), 400 weight
- Tagline: "Automate compliance. Eliminate errors. Scale confidently." — 1.1rem, color var(--accent), 500 weight, margin-top 16px
- Three key stats in a horizontal row (margin-top 48px), each in a subtle glass card (semi-transparent white border, backdrop blur):
  - "400K+" / "Target SMEs"
  - "₱10B+" / "Market Opportunity"
  - "85%+" / "Gross Margin"
- Bottom of viewport: subtle animated down-arrow (CSS bouncing animation) with text "Scroll to explore" in small muted text

**Visual effects**:
- Subtle animated gradient dots/particles in background using CSS only (small radial gradient dots at various positions with slow floating keyframe animation, very low opacity ~0.05)
- The three stat cards should have a subtle border glow using box-shadow with var(--primary) at low opacity

---

### SECTION 2: THE PROBLEM
**Layout**: Light background (var(--light)). Two-column layout on desktop; single column on mobile.

**Content**:

Left column (60% width):
- Section label: "THE PROBLEM" — small uppercase label with var(--red) color and a small red dot before it
- Headline: "Philippine Payroll is Broken" — 2.75rem, var(--dark), 800 weight
- Body paragraph: "For most Philippine SMEs, payroll day is still a nightmare. HR teams spend hours wrestling with spreadsheets, manually computing SSS, PhilHealth, and Pag-IBIG contributions, and praying they don't make a compliance error that triggers a BIR audit. It's 2026, and 78% of Philippine SMEs still run payroll on Excel."
- Below the paragraph, a list of 4 pain points, each with a red-tinted icon/emoji and bold lead text:
  1. **Manual Processing** — "Average SME spends 8-12 hours per week on payroll computation, cross-checking, and report generation."
  2. **Compliance Risk** — "₱50,000 to ₱200,000 in annual penalties for incorrect BIR filings, late SSS remittances, or PhilHealth discrepancies."
  3. **Zero Visibility** — "Supervisors and managers have no real-time view into team costs, overtime trends, or headcount changes."
  4. **Paper-Based HR** — "201 files stored in filing cabinets. Leave requests on paper forms. No audit trail. No analytics."

Right column (40% width):
- A large, visually striking "cost of doing nothing" card with a dark background (var(--section-dark-bg)):
  - Title: "The Hidden Cost of Manual Payroll" in white
  - Four stacked metric rows, each showing:
    - "₱156,000/yr" — "Wasted salary (HR staff doing manual computation)" — with animated counter
    - "₱125,000/yr" — "Average compliance penalties"
    - "₱80,000/yr" — "Opportunity cost (delayed strategic HR)"
    - A divider line
    - "₱361,000/yr" — "Total hidden cost per company" — in var(--gold), larger font, bold
  - Bottom note: "Most SMEs don't even realize they're paying this." — small italic text

---

### SECTION 3: THE SOLUTION
**Layout**: Dark background (var(--section-dark-bg)). Content centered.

**Content**:

- Section label: "THE SOLUTION" — small uppercase label with var(--accent) color
- Headline: "One Platform. Complete Payroll Automation." — white, 2.75rem
- Subheadline: "GeNXcript replaces spreadsheets, paper forms, and compliance guesswork with a single cloud platform built specifically for Philippine labor law." — var(--section-dark-text), max-width 700px, centered

Below, a grid of 6 feature cards (3 columns on desktop, 2 on tablet, 1 on mobile). Each card has:
- Semi-transparent background (rgba(255,255,255,0.05)), border (rgba(255,255,255,0.1)), border-radius 16px
- A colored icon circle at top (40px, with the module color as background)
- Feature title in white, 600 weight
- Short description in var(--section-dark-text), 0.95rem

The 6 cards:

1. Icon circle: var(--primary). Title: "Automated Payroll Run". Description: "Compute salaries, deductions, overtime, and net pay for your entire workforce in under 60 seconds. No formulas. No errors."

2. Icon circle: var(--accent). Title: "Government Compliance Engine". Description: "Auto-calculates SSS, PhilHealth, Pag-IBIG, and BIR withholding tax using the latest contribution tables. Generates ready-to-file government reports."

3. Icon circle: var(--gold). Title: "Time & Attendance". Description: "Digital DTR with geolocation clock-in, night differential computation, schedule management, and automated overtime tracking."

4. Icon circle: #ef4444. Title: "Employee Self-Service Portal". Description: "Employees view payslips, file leave requests, check balances, and update personal info — all from their phone. Zero HR intervention."

5. Icon circle: #8b5cf6 (purple). Title: "Supervisor Dashboard". Description: "Team-level visibility into payroll costs, attendance, leave balances, and approval workflows. Real data, real time."

6. Icon circle: #ec4899 (pink). Title: "Analytics & Insights". Description: "Payroll trend analysis, overtime heatmaps, headcount growth, cost breakdowns — the data you need to make smarter workforce decisions."

Below the grid, a centered callout:
- "Zero installation. Zero maintenance. Pure cloud SaaS." — white, 1.1rem, 600 weight, with a subtle underline using var(--accent)

---

### SECTION 4: MARKET OPPORTUNITY
**Layout**: Light background. Full-width section.

**Content**:

- Section label: "MARKET OPPORTUNITY" — small uppercase label with var(--primary) color
- Headline: "A ₱10 Billion Addressable Market" — 2.75rem, var(--dark)
- Subheadline: "The Philippine payroll software market is massively underserved. Most solutions are either too expensive for SMEs or too basic to handle real compliance." — var(--gray-500)

**TAM/SAM/SOM Visual**: Create a set of three concentric circles (pure CSS) representing TAM, SAM, SOM — largest at back, smallest at front. Use layered `border-radius: 50%` divs with different sizes and opacity levels. Colors: TAM = var(--primary) at 15% opacity, SAM = var(--primary) at 30% opacity, SOM = var(--primary) at full opacity.

Each circle has a label positioned on or near it:

- **TAM** (outermost, largest — ~350px): "₱25B" large number + "Total Addressable Market" + "1.1M registered businesses in the Philippines. 400K+ have 10 or more employees needing payroll solutions."

- **SAM** (middle — ~250px): "₱10B" large number + "Serviceable Addressable Market" + "~120,000 SMEs with 10-500 employees actively willing to adopt cloud payroll. At an average of ₱7,000/month."

- **SOM** (innermost — ~150px): "₱42M" large number + "Serviceable Obtainable Market (Year 3)" + "500 companies at ₱7,000 average monthly revenue. Conservative 0.4% market penetration."

To the right of the circles (or below on mobile), show three Year targets as horizontal stat rows:
- Year 1: "50 companies" / "₱4.2M ARR"
- Year 2: "200 companies" / "₱16.8M ARR"
- Year 3: "500 companies" / "₱42M ARR"

Each year row should have a bar that grows to represent relative scale (Year 1 = short bar, Year 3 = full width bar), animated on scroll.

---

### SECTION 5: PRODUCT
**Layout**: Dark background (var(--section-dark-bg)).

**Content**:

- Section label: "THE PRODUCT" — small uppercase label with var(--accent) color
- Headline: "Built for Philippine HR Teams" — white, 2.75rem
- Subheadline: "Every screen designed for speed, clarity, and compliance. Here's what your clients see." — var(--section-dark-text)

**CSS-Only Screen Mockups**: Create 6 "screenshot" mockups using pure CSS (no images). Each mockup is a rounded rectangle (border-radius 12px) with:
- A "browser chrome" bar at top (8px height, three small colored dots: red, yellow, green — each 6px circles)
- A content area below showing a stylized representation of the screen

Display in a 2x3 grid on desktop, 1 column on mobile. Each mockup card has:
- The CSS mockup at top
- A title below
- A one-line description

The 6 mockups:

1. **Company Dashboard**
   - Content area: Show a top row of 4 small metric boxes (colored rectangles with small text placeholders), then below that 2 side-by-side chart placeholders (one bar chart shape, one line chart shape using CSS gradients)
   - Title: "Command Center Dashboard"
   - Description: "Real-time overview of payroll status, headcount, and pending approvals."

2. **Payroll Run**
   - Content area: Show a table-like layout — a header row with 5 column labels (small gray rectangles), then 4-5 data rows with alternating light/slightly-lighter backgrounds. A prominent blue "Run Payroll" button shape at top-right.
   - Title: "One-Click Payroll Processing"
   - Description: "Select period, review, approve. Payroll for 100 employees in under 60 seconds."

3. **Employee Profile (201 File)**
   - Content area: Show a left sidebar with a circle (avatar placeholder) and stacked text lines, and a right content area with tabbed sections (3 tab shapes at top, content blocks below)
   - Title: "Digital 201 File"
   - Description: "Complete employee records with compensation history, documents, and compliance data."

4. **Employee Portal**
   - Content area: Show a mobile-width frame within the mockup. Inside: a greeting text line at top, 3 card-like blocks stacked vertically (representing payslip summary, leave balance, and recent activity)
   - Title: "Employee Self-Service"
   - Description: "Payslips, leave filing, and personal info — accessible from any device."

5. **Supervisor Portal**
   - Content area: Show a 2x2 grid of card shapes (team metrics), then below that a small table shape (team member list)
   - Title: "Supervisor Team View"
   - Description: "Team payroll costs, attendance tracking, and approval queue at a glance."

6. **Analytics Dashboard**
   - Content area: Show a large bar chart shape (5 bars of varying height using CSS), a donut/ring chart (CSS border-radius circle with a cutout), and a small data table
   - Title: "Workforce Analytics"
   - Description: "Payroll trends, overtime patterns, cost breakdowns — data-driven HR decisions."

---

### SECTION 6: MODULAR ARCHITECTURE
**Layout**: Light background.

**Content**:

- Section label: "ARCHITECTURE" — small uppercase label with var(--primary)
- Headline: "Modular by Design. Scalable by Nature." — 2.75rem, var(--dark)
- Subheadline: "Clients start with what they need and expand as they grow. Our plugin architecture drives natural revenue expansion." — var(--gray-500), max-width 650px

**Module Building Blocks Visual**: Display 7 modules as a visual stack/grid of interlocking blocks. Use a layout where the CORE module is a wide base block spanning the full width, and the other 6 modules sit on top in a 3x2 grid arrangement — creating a "building" or "pyramid" visual metaphor.

Each module block:
- Has its designated color as a left border (4px) and a subtle tinted background
- Shows the module name in bold
- Shows 3-4 key features as small bullet text
- Has a small "included in" badge showing which pricing tier includes it

The 7 modules with their colors and content:

1. **CORE** (color: var(--accent), green) — Full-width base block
   - "Always included in every plan"
   - Features: Company Setup, Employee Management, Authentication & Roles, Employee Portal, Preferences & Settings
   - Badge: "All Plans"

2. **PAYROLL ENGINE** (color: var(--primary), blue)
   - Features: Payroll Run & Computation, Gov't Contributions Auto-Calc, Payslip Generation, Gov't Reports, 13th Month Pay
   - Badge: "Essential+"

3. **TIME & ATTENDANCE** (color: var(--gold), amber)
   - Features: Digital DTR, Schedule Management, Geolocation Clock-in, Night Differential, DTR Corrections
   - Badge: "Professional+"

4. **LEAVE & OT MANAGEMENT** (color: #f97316, orange)
   - Features: Leave Requests & Balances, OT Requests & Tracking, Special Leaves (SIL, Maternity, Paternity), Approval Workflows
   - Badge: "Professional+"

5. **SUPERVISOR PORTAL** (color: #ef4444, red)
   - Features: Team Dashboard, Team Payroll View, 201 Cards, Multi-level Approval Workflows
   - Badge: "Enterprise"

6. **ANALYTICS & INSIGHTS** (color: #8b5cf6, purple)
   - Features: Payroll Comparison, Workforce Analytics, OT Heatmap, Break Monitoring
   - Badge: "Enterprise"

7. **COMPLIANCE+** (color: var(--dark), dark)
   - Features: BIR 2316/1604-C Generation, Complete Audit Trail, Holiday Management, Regulatory Updates
   - Badge: "Enterprise"

Below the module blocks, show a "Land and Expand" metric strip:
- Three stats in a row:
  - "2.3" / "Avg modules at signup"
  - "4.7" / "Avg modules by Month 12"
  - "104%" / "Net revenue retention"
- Use animated counters for these numbers.

---

### SECTION 7: BUSINESS MODEL & UNIT ECONOMICS
**Layout**: Dark background (var(--section-dark-bg)).

**Content**:

- Section label: "BUSINESS MODEL" — small uppercase label with var(--gold)
- Headline: "SaaS Economics That Work" — white, 2.75rem
- Subheadline: "Predictable recurring revenue with best-in-class unit economics." — var(--section-dark-text)

**Pricing Tiers**: Display 4 pricing tier cards in a horizontal row (desktop) or stacked (mobile). Each card:
- Semi-transparent background
- Tier name at top
- Price in large font
- "per month" below
- Employee limit
- List of included modules with checkmarks (var(--accent)) for included, dashes (var(--gray-500)) for not included
- The "Professional" tier should be highlighted with a "Most Popular" badge in var(--gold) and a slightly larger card / brighter border

Tiers:

1. **Starter** — ₱2,999/mo — Up to 20 employees — Core only
2. **Essential** — ₱5,999/mo — Up to 50 employees — Core + Payroll Engine
3. **Professional** — ₱9,999/mo — Up to 100 employees — Core + Payroll + Time & Attendance + Leave/OT (MOST POPULAR)
4. **Enterprise** — ₱14,999/mo — Unlimited employees — All 7 modules

Below tiers, note: "+ ₱50-100 per employee/month beyond tier threshold"

**Unit Economics Strip**: Below the pricing cards, display key unit economics as large metric cards in a row:

- "₱7,000-15,000" / "Monthly ARPU" (Average Revenue Per User)
- "₱15,000" / "CAC" (Customer Acquisition Cost)
- "₱504,000" / "LTV" (36-month avg retention x ₱14,000 ARPU)
- "33.6x" / "LTV:CAC Ratio"
- "85%+" / "Gross Margin"

Each metric: large number on top (animated counter, white, JetBrains Mono font), label below (var(--section-dark-text), small uppercase).

**Revenue Streams** below the metrics — a simple 4-item list:
1. SaaS Subscriptions (primary)
2. Per-employee overage fees
3. Onboarding & training fees (₱25,000-50,000 one-time)
4. Custom development & integrations

---

### SECTION 8: COMPETITIVE LANDSCAPE
**Layout**: Light background.

**Content**:

- Section label: "COMPETITION" — small uppercase label with var(--primary)
- Headline: "Enterprise Features at SME Prices" — 2.75rem, var(--dark)
- Subheadline: "We're not the first payroll tool in the Philippines. We're the first one built right for SMEs." — var(--gray-500)

**Comparison Table**: A styled comparison matrix table. Clean design with:
- Header row: Feature column + GeNXcript (highlighted column with var(--primary) background) + Sprout Solutions + PayrollHero + GreatDay HR + Manual (Excel)
- GeNXcript column has a light blue background tint to stand out
- Rows with alternating backgrounds

Comparison rows:

| Feature | GeNXcript | Sprout | PayrollHero | GreatDay HR | Excel |
|---|---|---|---|---|---|
| Monthly Price (50 emp) | ₱9,999 | ₱25,000+ | ₱15,000+ | ₱20,000+ | "Free" |
| Philippine Compliance | Full Auto | Full Auto | Partial | Full Auto | Manual |
| Modular Pricing | Yes | No | No | No | N/A |
| Supervisor Portal | Yes | Limited | No | Limited | No |
| Employee Self-Service | Yes | Yes | Yes | Yes | No |
| Geolocation Clock-in | Yes | Yes | Yes | Yes | No |
| Setup Time | Same day | 2-4 weeks | 1-2 weeks | 2-4 weeks | N/A |
| Custom Reports | Yes | Extra cost | Limited | Extra cost | Manual |

Use checkmark icons (green) for Yes, X icons (red) for No, and tilde/dash for partial/limited. Make GeNXcript's column values bold or accented.

Below the table, a centered positioning statement:
"GeNXcript sits in the sweet spot — enterprise-grade compliance automation at a price point that makes sense for growing Philippine businesses." — styled as a quote/callout with a left border in var(--primary).

---

### SECTION 9: GO-TO-MARKET STRATEGY
**Layout**: Dark background (var(--section-dark-bg)).

**Content**:

- Section label: "GO-TO-MARKET" — small uppercase label with var(--accent)
- Headline: "From Metro Manila to the Entire Archipelago" — white, 2.75rem
- Subheadline: "A phased approach to market penetration, starting where the density is highest." — var(--section-dark-text)

**Three-Phase Timeline**: Display as a horizontal timeline (desktop) or vertical timeline (mobile) with three connected phases. Each phase is a card connected by a line/arrow.

Phase 1: "Foundation" — Months 1-6
- Icon/color: var(--primary)
- "Direct sales to BPOs and tech companies in Metro Manila"
- "Target: 50 pilot customers"
- "Channel: LinkedIn B2B ads, founder-led sales, HR conference sponsorships"
- "Focus on BPO sector — high employee counts, compliance-heavy, tech-forward"

Phase 2: "Expansion" — Months 7-12
- Icon/color: var(--accent)
- "Channel partnerships with accounting firms and HR consultants"
- "Target: 200 total customers"
- "Launch referral program (1 month free per successful referral)"
- "Content marketing: compliance guides, webinars, HR community building"

Phase 3: "Scale" — Year 2+
- Icon/color: var(--gold)
- "Self-serve onboarding with free trial"
- "Regional expansion: Cebu, Davao, Clark, Subic"
- "Target: 500+ customers"
- "Explore integrations: Maya, GCash, major PH banks for payroll disbursement"

Below the timeline, a row of channel icons/labels:
"Key Channels: LinkedIn Ads | HR Conferences | Accounting Firm Partnerships | Referral Program | Content Marketing"

---

### SECTION 10: TRACTION & MILESTONES
**Layout**: Light background.

**Content**:

- Section label: "TRACTION" — small uppercase label with var(--accent)
- Headline: "We've Built the Foundation" — 2.75rem, var(--dark)
- Subheadline: "GeNXcript isn't a concept — it's a working product. Here's where we stand today." — var(--gray-500)

**Completed Milestones** (show as a vertical timeline or checklist with green checkmarks):

1. "MVP Complete" — "All 7 modules built and functional — payroll engine, time & attendance, leave management, supervisor portal, analytics, compliance+"
2. "Multi-Tenant Architecture" — "Single instance serves multiple companies with complete data isolation. Ready to scale to thousands of tenants."
3. "3 Pilot Companies Onboarded" — "Full test data seeded across 3 companies with realistic employee records, payroll history, and compliance data."
4. "Philippine Compliance Engine" — "Complete auto-calculation for SSS, PhilHealth, Pag-IBIG, and BIR withholding tax. Updated to 2026 contribution tables."
5. "25+ Database Tables" — "Production-grade PostgreSQL schema on Supabase. Row-level security. Real-time subscriptions ready."
6. "30+ Government Report Templates" — "BIR 2316, 1604-C, SSS R-3, PhilHealth RF-1, Pag-IBIG remittance — all auto-generated."
7. "Role-Based Access Control" — "5 user roles: Admin, HR Manager, Payroll Officer, Supervisor, Employee. Each with tailored views and permissions."

**Next Milestones** (show as a roadmap with open circles / unfilled checkmarks):

1. "Q2 2026: Beta launch with 10 paying customers"
2. "Q3 2026: Seed round close"
3. "Q4 2026: 50 paying customers, ₱4.2M ARR run rate"
4. "Q1 2027: Accounting firm partnership program launch"
5. "Q2 2027: Self-serve onboarding + regional expansion"

**Tech Stack Badge Row**: Show small "tech badges" (styled like GitHub badges) in a row:
"Python" "Streamlit" "Supabase" "PostgreSQL" "Cloud-Native" "Row-Level Security"

---

### SECTION 11: THE TEAM
**Layout**: Dark background (var(--section-dark-bg)).

**Content**:

- Section label: "THE TEAM" — small uppercase label with var(--gold)
- Headline: "Built by People Who Understand Philippine Payroll" — white, 2.75rem
- Subheadline: "A lean, technical team with deep domain expertise in HR, compliance, and cloud architecture." — var(--section-dark-text)

**Team Cards**: Display 3 team member cards in a row (desktop) or stacked (mobile). Each card:
- Semi-transparent background
- Large circle at top (avatar placeholder — use initials in a colored circle, 80px)
- Name (white, 600 weight, 1.2rem)
- Title (var(--gold), 0.9rem)
- Short bio (var(--section-dark-text), 0.9rem, 3-4 lines)

Team members (placeholder content):

1. Initials: "JD" / Color: var(--primary)
   Name: "[Founder Name]"
   Title: "Founder & CEO"
   Bio: "10+ years in enterprise software development. Deep expertise in Philippine HR systems and labor compliance. Previously built internal payroll systems for mid-size Philippine companies."

2. Initials: "CTO" / Color: var(--accent)
   Name: "[CTO Name]"
   Title: "Chief Technology Officer"
   Bio: "Full-stack architect with experience scaling cloud applications. Expert in Python, PostgreSQL, and modern SaaS architecture. Passionate about building developer-friendly platforms."

3. Initials: "ADV" / Color: var(--gold)
   Name: "[Advisory Board]"
   Title: "Advisors"
   Bio: "Network of advisors spanning HR consulting, Philippine labor law, accounting, and SaaS go-to-market strategy. Active advisory board to be formalized post-seed."

Below the team cards:
"We're hiring. Post-funding, immediate hires include: Sales Lead, Customer Success Manager, and Senior Full-Stack Developer." — small text, centered, var(--section-dark-text)

---

### SECTION 12: FINANCIAL PROJECTIONS
**Layout**: Light background.

**Content**:

- Section label: "FINANCIALS" — small uppercase label with var(--primary)
- Headline: "Path to Profitability in 24 Months" — 2.75rem, var(--dark)
- Subheadline: "Conservative projections based on the Philippine SME market size and our go-to-market timeline." — var(--gray-500)

**3-Year Financial Summary**: Display as a CSS-only bar chart or combined chart showing Revenue vs Expenses vs Profit for each year.

Create a bar chart with 3 groups (Year 1, Year 2, Year 3). Each group has 3 bars:
- Revenue bar (var(--primary))
- Expenses bar (var(--gray-300))
- Profit/Loss bar (var(--accent) for profit, var(--red) for loss)

Data:
- Year 1 (2026): Revenue ₱4.2M / Expenses ₱6.2M / Net -₱2.0M
- Year 2 (2027): Revenue ₱16.8M / Expenses ₱15.0M / Net ₱1.8M
- Year 3 (2028): Revenue ₱42.0M / Expenses ₱27.0M / Net ₱15.0M

Bars should animate from 0 height to final height when scrolled into view. Scale should be relative (₱42M = tallest bar = 100%).

Below the chart, a metric strip showing key Year 3 numbers:
- "₱42M" / "ARR"
- "500" / "Customers"
- "₱15M" / "Net Profit"
- "36%" / "Net Margin"

**Assumptions footnote** (small text, muted):
"Projections based on: ₱7,000 blended ARPU, 5% monthly churn, 15% month-over-month growth in Year 1 tapering to 8% in Year 3. Expenses include team scaling from 3 to 15 FTEs by Year 3."

---

### SECTION 13: THE ASK
**Layout**: Dark gradient background (same as cover slide — `linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)`). This is the climactic section.

**Content**:

- Section label: "THE ASK" — small uppercase label with var(--gold), letter-spacing wide
- Headline: "Join Us in Building the Future of Philippine Payroll" — white, 2.75rem, 800 weight
- Subheadline: "We're raising a seed round to take GeNXcript from MVP to market leader." — var(--section-dark-text), max-width 600px, centered

**Funding Ask**: Large centered display:
- "Seed Round" — var(--gold), uppercase, small
- "₱5M — ₱10M" — white, 3.5rem, JetBrains Mono, 700 weight (animated counter)
- "Target raise to fund 18 months of growth" — var(--section-dark-text)

**Use of Funds**: Display as a CSS donut chart (pure CSS using conic-gradient) with 4 segments:
- 40% — Product Development (var(--primary))
- 25% — Sales & Marketing (var(--accent))
- 20% — Operations & Team (var(--gold))
- 15% — Reserve (var(--gray-500))

Next to the donut chart, list the segments with their percentages, colors, and brief descriptions:
- "40% Product Development" — "Mobile app, API integrations, advanced analytics, AI features"
- "25% Sales & Marketing" — "Sales team, digital marketing, conference presence, partnerships"
- "20% Operations" — "Customer success team, cloud infrastructure scaling, office"
- "15% Reserve" — "Working capital and contingency buffer"

**Key targets post-funding** (3 cards in a row):
- Card 1: "200" (animated counter) / "Paying Customers by Year 2"
- Card 2: "₱16.8M" (animated counter) / "ARR Target"
- Card 3: "18 mo" / "Runway"

---

### SECTION 14: CONTACT & NEXT STEPS
**Layout**: Light background. Centered content. Clean and simple.

**Content**:

- Headline: "Let's Talk" — 2.75rem, var(--dark), centered
- Subheadline: "We'd love to walk you through the product live and discuss how GeNXcript can transform Philippine payroll." — var(--gray-500), centered, max-width 550px

**Next Steps** — 3 items in a row (icon + text):
1. "Schedule a Demo" — "See GeNXcript in action with real Philippine payroll data"
2. "Review the Data Room" — "Financial models, technical architecture, compliance documentation"
3. "Meet the Team" — "We're available for in-person meetings in Metro Manila"

**Contact Card**: Centered card with subtle border, containing:
- "GeNXcript Payroll"
- "Email: invest@genxcript.com" (placeholder)
- "Phone: +63 XXX XXX XXXX" (placeholder)
- "Location: Metro Manila, Philippines"

**QR Code Placeholder**: A CSS-only QR code approximation — a square (120px) with a grid of smaller black and white squares inside (use a grid of tiny divs or a CSS gradient pattern to simulate a QR code). Label below: "Scan for pitch deck PDF"

**Footer**:
- "GeNXcript Payroll | Confidential — For Intended Recipient Only"
- "2026 GeNXcript Technologies. All rights reserved."
- Small text: "This document contains forward-looking statements and projections. Actual results may vary."

---

## FINAL TECHNICAL REQUIREMENTS

1. **Single HTML file** — everything inline. No external resources except the two Google Fonts links.
2. **Semantic HTML** — use `<section>`, `<article>`, `<nav>`, `<header>`, `<footer>`, `<figure>` where appropriate. Each major section should have an `id` attribute for anchor navigation.
3. **CSS Custom Properties** — define all colors and key values as CSS custom properties in `:root`.
4. **Responsive breakpoints**:
   - Desktop: > 1024px
   - Tablet: 768px - 1024px
   - Mobile: < 768px
5. **Performance**: Use `will-change` sparingly. Debounce/throttle scroll handlers. Use passive event listeners where possible.
6. **Accessibility**: Proper heading hierarchy (h1 once for title, h2 for section headlines). Alt text placeholders. Sufficient color contrast. Focus-visible styles for nav dots.
7. **Smooth scrolling**: `html { scroll-behavior: smooth; }` and use `scrollIntoView({ behavior: 'smooth' })` for JS navigation.
8. **Total size target**: Under 50KB for the entire HTML file.
9. **No JavaScript frameworks** — vanilla JS only.
10. **Browser support**: Modern browsers (Chrome, Firefox, Safari, Edge — last 2 versions). No IE11 support needed.
