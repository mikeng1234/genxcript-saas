-- ============================================================
-- 007_leave_ot_requests.sql
--
-- Adds leave & overtime request tracking:
--   1. Leave entitlement + replenishment config on companies
--   2. leave_requests table
--   3. overtime_requests table
--   4. RLS policies for employee + admin access
--
-- Run once in Supabase SQL Editor.
-- ============================================================


-- ── 1. Leave configuration on companies ──────────────────────────────────────
ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS leave_vl_days        INTEGER NOT NULL DEFAULT 15,
  ADD COLUMN IF NOT EXISTS leave_sl_days        INTEGER NOT NULL DEFAULT 15,
  ADD COLUMN IF NOT EXISTS leave_cl_days        INTEGER NOT NULL DEFAULT 5,
  -- replenishment_policy: 'annual' (Jan 1) or 'anniversary' (hire date)
  ADD COLUMN IF NOT EXISTS leave_replenishment  TEXT    NOT NULL DEFAULT 'annual'
    CHECK (leave_replenishment IN ('annual', 'anniversary'));


-- ── 2. Leave requests ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leave_requests (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id    UUID         NOT NULL REFERENCES companies(id)  ON DELETE CASCADE,
  employee_id   UUID         NOT NULL REFERENCES employees(id)  ON DELETE CASCADE,
  leave_type    TEXT         NOT NULL CHECK (leave_type IN ('VL', 'SL', 'CL')),
  start_date    DATE         NOT NULL,
  end_date      DATE         NOT NULL,
  days          NUMERIC(4,1) NOT NULL DEFAULT 1,
  reason        TEXT,
  status        TEXT         NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'approved', 'rejected')),
  reviewed_by   UUID         REFERENCES auth.users(id),
  reviewed_at   TIMESTAMPTZ,
  admin_notes   TEXT,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ── 3. Overtime requests ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS overtime_requests (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id    UUID         NOT NULL REFERENCES companies(id)  ON DELETE CASCADE,
  employee_id   UUID         NOT NULL REFERENCES employees(id)  ON DELETE CASCADE,
  ot_date       DATE         NOT NULL,
  start_time    TIME         NOT NULL,
  end_time      TIME         NOT NULL,
  hours         NUMERIC(4,1) NOT NULL,
  reason        TEXT,
  status        TEXT         NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'approved', 'rejected')),
  reviewed_by   UUID         REFERENCES auth.users(id),
  reviewed_at   TIMESTAMPTZ,
  admin_notes   TEXT,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ── 4. RLS ────────────────────────────────────────────────────────────────────
ALTER TABLE leave_requests    ENABLE ROW LEVEL SECURITY;
ALTER TABLE overtime_requests ENABLE ROW LEVEL SECURITY;

-- Employees: full CRUD on their own requests
CREATE POLICY "lr_employee_own" ON leave_requests
  FOR ALL USING (
    employee_id IN (
      SELECT id FROM employees WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "otr_employee_own" ON overtime_requests
  FOR ALL USING (
    employee_id IN (
      SELECT id FROM employees WHERE user_id = auth.uid()
    )
  );

-- Admin / viewer: see + update all requests for their company
CREATE POLICY "lr_admin_company" ON leave_requests
  FOR ALL USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role IN ('admin', 'viewer')
    )
  );

CREATE POLICY "otr_admin_company" ON overtime_requests
  FOR ALL USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role IN ('admin', 'viewer')
    )
  );
