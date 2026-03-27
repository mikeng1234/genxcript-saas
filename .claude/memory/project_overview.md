---
name: GeNXcript Payroll SaaS Overview
description: Philippine SME payroll SaaS — stack, architecture, team roles, and MVP priorities
type: project
---

Two-person team: vibe coder (frontend/design) + data engineer (backend/DB).
Building payroll SaaS for Philippine SMEs (1–30 employees).

Stack: Python backend, Streamlit MVP frontend (React later), self-hosted Supabase on Ubuntu i5 server, PostgreSQL.
All monetary values stored as integers in centavos to avoid floating-point errors.
Government rates stored in DB (government_rates table), never hardcoded.
Multi-tenant with RLS via user_company_access mapping table.

MVP priority: schema → employee master → payroll run → payslips → dashboard → gov reports → auth.
