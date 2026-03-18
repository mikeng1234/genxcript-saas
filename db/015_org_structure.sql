-- 015_org_structure.sql
-- Hierarchical department/organization structure

-- ── departments ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS departments (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id    UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name          TEXT        NOT NULL,
  code          TEXT,                          -- optional short code e.g. "FIN", "HR"
  parent_id     UUID        REFERENCES departments(id) ON DELETE SET NULL,
  color         TEXT        DEFAULT '#6366f1', -- hex accent color for UI
  description   TEXT,
  sort_order    INTEGER     NOT NULL DEFAULT 0,
  is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (company_id, name)
);

CREATE INDEX IF NOT EXISTS idx_departments_company    ON departments (company_id);
CREATE INDEX IF NOT EXISTS idx_departments_parent     ON departments (parent_id);
CREATE INDEX IF NOT EXISTS idx_departments_active     ON departments (company_id, is_active);

-- Add department_id FK to employee_profiles
ALTER TABLE employee_profiles
  ADD COLUMN IF NOT EXISTS department_id UUID REFERENCES departments(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_ep_department_id ON employee_profiles (department_id);

-- ── RLS ────────────────────────────────────────────────────────────────────
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;

-- All authenticated users can read departments for any company they belong to
-- (uses the existing get_user_company_ids() helper from 001_schema.sql)
CREATE POLICY dept_select ON departments
  FOR SELECT
  TO authenticated
  USING (company_id IN (SELECT get_user_company_ids()));

-- Only admins can insert/update/delete departments for their company
CREATE POLICY dept_insert ON departments
  FOR INSERT
  TO authenticated
  WITH CHECK (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY dept_update ON departments
  FOR UPDATE
  TO authenticated
  USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY dept_delete ON departments
  FOR DELETE
  TO authenticated
  USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role = 'admin'
    )
  );
