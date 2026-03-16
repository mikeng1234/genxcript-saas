-- ============================================================
-- Migration 011: Leave Balance & Year-End Policy
-- ============================================================
-- 1. Adds year-end policy columns to leave_entitlement_templates:
--      carry_over_cap      — max unused days rolled to next year per leave type
--      convertible_to_cash — whether remaining days (beyond carry-over) can be paid out
--      conversion_rate     — cash payout multiplier (1.00 = 1 day = 1 day's pay)
--
-- 2. Creates leave_balance table:
--      Stores the opening balance override per employee / year / leave type.
--      Populated by the year-end processing action (Phase 5).
--      When a row exists, it REPLACES the template default for that year
--      (it already includes the template allocation + any carried-over days).
--
-- Run once in Supabase SQL Editor AFTER 010_employee_extended_info.sql.
-- ============================================================


-- ── 1. Policy columns on leave_entitlement_templates ─────────────────────────

ALTER TABLE leave_entitlement_templates
  ADD COLUMN IF NOT EXISTS carry_over_cap      INTEGER   NOT NULL DEFAULT 0
    CHECK (carry_over_cap >= 0),          -- 0 = no carry-over
  ADD COLUMN IF NOT EXISTS convertible_to_cash BOOLEAN   NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS conversion_rate     NUMERIC(4,2) NOT NULL DEFAULT 1.00
    CHECK (conversion_rate > 0);          -- 1.00 = 1 day = 1 day's pay


-- ── 2. leave_balance table ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS leave_balance (
  id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID         NOT NULL REFERENCES companies(id)  ON DELETE CASCADE,
  employee_id     UUID         NOT NULL REFERENCES employees(id)  ON DELETE CASCADE,

  -- Calendar year this balance applies to (e.g. 2025, 2026)
  year            INTEGER      NOT NULL,

  -- Leave type matches leave_requests.leave_type
  leave_type      TEXT         NOT NULL CHECK (leave_type IN ('VL', 'SL', 'CL')),

  -- Full opening balance for the year:
  --   = template allocation + carried-over days from previous year.
  -- Written by the year-end processing action; may also be set manually by HR.
  opening_balance NUMERIC(5,1) NOT NULL DEFAULT 0,

  notes           TEXT,        -- optional HR note (e.g. "Includes 3 VL days carried from 2024")
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

  UNIQUE (employee_id, year, leave_type)
);

CREATE INDEX IF NOT EXISTS idx_leave_balance_employee ON leave_balance (employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_balance_company  ON leave_balance (company_id, year);


-- ── 3. RLS ────────────────────────────────────────────────────────────────────

ALTER TABLE leave_balance ENABLE ROW LEVEL SECURITY;

-- Admin / viewer: full CRUD on their company's balance records
CREATE POLICY "lb_admin" ON leave_balance
  FOR ALL USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role IN ('admin', 'viewer')
    )
  );

-- Employee: read-only access to their own balance rows
CREATE POLICY "lb_employee_read" ON leave_balance
  FOR SELECT USING (
    employee_id IN (
      SELECT id FROM employees WHERE user_id = auth.uid()
    )
  );
