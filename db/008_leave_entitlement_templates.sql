-- ============================================================
-- 008_leave_entitlement_templates.sql
--
-- Leave Entitlement Template system:
--   1. leave_entitlement_templates table (employer-defined leave tiers)
--   2. FK column on employees: leave_template_id
--   3. RLS policies for admin and employee access
--
-- Run once in Supabase SQL Editor AFTER 007_leave_ot_requests.sql.
-- ============================================================


-- ── 1. Templates table ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leave_entitlement_templates (
  id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id         UUID         NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name               TEXT         NOT NULL,
  -- Service range in months (e.g. 0–11 = first year, 12–23 = second year, etc.)
  -- max_service_months = NULL means no upper limit (senior staff, etc.)
  min_service_months INTEGER      NOT NULL DEFAULT 0
                     CHECK (min_service_months >= 0),
  max_service_months INTEGER      -- NULL = open-ended / no upper limit
                     CHECK (max_service_months IS NULL OR max_service_months >= min_service_months),
  vl_days            INTEGER      NOT NULL DEFAULT 15 CHECK (vl_days >= 0),
  sl_days            INTEGER      NOT NULL DEFAULT 15 CHECK (sl_days >= 0),
  cl_days            INTEGER      NOT NULL DEFAULT 5  CHECK (cl_days >= 0),
  created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ── 2. FK on employees ────────────────────────────────────────────────────────
ALTER TABLE employees
  ADD COLUMN IF NOT EXISTS leave_template_id UUID
    REFERENCES leave_entitlement_templates(id) ON DELETE SET NULL;


-- ── 3. RLS ────────────────────────────────────────────────────────────────────
ALTER TABLE leave_entitlement_templates ENABLE ROW LEVEL SECURITY;

-- Admin / viewer: full CRUD on their company's templates
CREATE POLICY "let_admin_company" ON leave_entitlement_templates
  FOR ALL USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role IN ('admin', 'viewer')
    )
  );

-- Employee: read-only (so the portal can fetch the assigned template)
CREATE POLICY "let_employee_read" ON leave_entitlement_templates
  FOR SELECT USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid()
    )
  );
