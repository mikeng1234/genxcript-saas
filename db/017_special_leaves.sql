-- ============================================================
-- Migration 017: Philippine Special Leave Requests
-- ============================================================
-- Covers statutory special leaves:
--   ML  — Maternity Leave   (RA 11210) — 105 days / 60 days
--   PL  — Paternity Leave   (RA 8187)  — 7 days (first 4 deliveries)
--   SPL — Solo Parent Leave (RA 8972)  — 7 days per year
--
-- Only employees who file qualify — no pre-allocated balance.
-- Run once in Supabase SQL Editor AFTER 016_manager_hierarchy.sql.
-- ============================================================


CREATE TABLE IF NOT EXISTS special_leave_requests (
  id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id    UUID         NOT NULL REFERENCES companies(id)  ON DELETE CASCADE,
  employee_id   UUID         NOT NULL REFERENCES employees(id)  ON DELETE CASCADE,

  -- ML | PL | SPL
  leave_type    TEXT         NOT NULL
                CHECK (leave_type IN ('ML', 'PL', 'SPL')),

  -- ML only: governs how many days are granted (105 vs 60)
  delivery_type TEXT
                CHECK (delivery_type IN (
                  'normal', 'caesarean', 'miscarriage', 'emergency_termination'
                )),

  -- Delivery date (actual or expected)
  delivery_date DATE,

  -- PL only: spouse / partner name on the birth certificate
  partner_name  TEXT,

  -- SPL only: DSWD-issued Solo Parent ID card number
  solo_parent_id TEXT,

  start_date    DATE         NOT NULL,
  end_date      DATE         NOT NULL,

  -- Days requested (computed by front-end, validated by HR on review)
  days          NUMERIC(5,1) NOT NULL CHECK (days > 0),

  reason        TEXT,

  -- Notes about supporting documents handed to HR
  supporting_docs_note TEXT,

  status        TEXT         NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'approved', 'rejected')),

  reviewed_by   UUID         REFERENCES auth.users(id),
  reviewed_at   TIMESTAMPTZ,
  admin_notes   TEXT,

  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_slr_company  ON special_leave_requests (company_id, status);
CREATE INDEX IF NOT EXISTS idx_slr_employee ON special_leave_requests (employee_id);
CREATE INDEX IF NOT EXISTS idx_slr_type     ON special_leave_requests (company_id, leave_type);


-- ── RLS ───────────────────────────────────────────────────────────────────────

ALTER TABLE special_leave_requests ENABLE ROW LEVEL SECURITY;

-- Admin / viewer: full CRUD on all company special leave requests
CREATE POLICY "slr_admin" ON special_leave_requests
  FOR ALL USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role IN ('admin', 'viewer')
    )
  );

-- Employee: read their own records
CREATE POLICY "slr_employee_read" ON special_leave_requests
  FOR SELECT USING (
    employee_id IN (SELECT id FROM employees WHERE user_id = auth.uid())
  );

-- Employee: file (insert) their own requests
CREATE POLICY "slr_employee_insert" ON special_leave_requests
  FOR INSERT WITH CHECK (
    employee_id IN (SELECT id FROM employees WHERE user_id = auth.uid())
  );
