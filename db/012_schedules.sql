-- ============================================================
-- Migration 012: Shift Schedules (Phase 4A)
-- ============================================================
-- 1. schedules          — company-defined shift profiles
-- 2. employees          — schedule_id FK (which shift an employee follows)
-- 3. schedule_overrides — single-day exceptions per employee
--
-- Run once in Supabase SQL Editor AFTER 011_leave_balance_policy.sql.
-- ============================================================


-- ── 1. Schedules table ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS schedules (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

  name            TEXT        NOT NULL,                  -- e.g. "Morning 8–5", "Night Shift"
  start_time      TIME        NOT NULL,                  -- e.g. 08:00
  end_time        TIME        NOT NULL,                  -- e.g. 17:00  (or 06:00 for night)

  -- Break duration deducted when computing hours worked
  break_minutes   INTEGER     NOT NULL DEFAULT 60
                  CHECK (break_minutes >= 0 AND break_minutes < 480),

  -- Working days: subset of {'Mon','Tue','Wed','Thu','Fri','Sat','Sun'}
  -- Stored as Postgres TEXT array for readability and easy filtering
  work_days       TEXT[]      NOT NULL DEFAULT ARRAY['Mon','Tue','Wed','Thu','Fri'],

  -- TRUE when the shift crosses midnight (end_time < start_time).
  -- Used by the DTR engine to correctly compute hours for overnight shifts.
  is_overnight    BOOLEAN     NOT NULL DEFAULT FALSE,

  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Names must be unique within a company
  UNIQUE (company_id, name)
);

CREATE INDEX IF NOT EXISTS idx_schedules_company ON schedules (company_id);


-- ── 2. Assign a default schedule to each employee ────────────────────────────

ALTER TABLE employees
  ADD COLUMN IF NOT EXISTS schedule_id UUID REFERENCES schedules(id) ON DELETE SET NULL;


-- ── 3. Schedule overrides — single-day exceptions ────────────────────────────
-- An override can:
--   a) Swap to a different shift  (schedule_id IS NOT NULL)
--   b) Mark as a rest/off day     (schedule_id IS NULL + is_rest_day = TRUE)

CREATE TABLE IF NOT EXISTS schedule_overrides (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id    UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  employee_id   UUID        NOT NULL REFERENCES employees(id) ON DELETE CASCADE,

  override_date DATE        NOT NULL,
  schedule_id   UUID        REFERENCES schedules(id) ON DELETE SET NULL,
  is_rest_day   BOOLEAN     NOT NULL DEFAULT FALSE,
  reason        TEXT,

  created_by    UUID        REFERENCES auth.users(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Only one override per employee per day
  UNIQUE (employee_id, override_date)
);

CREATE INDEX IF NOT EXISTS idx_sched_overrides_employee ON schedule_overrides (employee_id);
CREATE INDEX IF NOT EXISTS idx_sched_overrides_date     ON schedule_overrides (employee_id, override_date);


-- ── 4. RLS ────────────────────────────────────────────────────────────────────

ALTER TABLE schedules          ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedule_overrides ENABLE ROW LEVEL SECURITY;

-- Schedules: admin/viewer full access; employees read-only (portal can fetch their shift)
CREATE POLICY "sched_admin" ON schedules
  FOR ALL USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role IN ('admin', 'viewer')
    )
  );

CREATE POLICY "sched_employee_read" ON schedules
  FOR SELECT USING (
    company_id IN (SELECT get_user_company_ids())
  );

-- Schedule overrides: admin full access; employees read own
CREATE POLICY "sched_ov_admin" ON schedule_overrides
  FOR ALL USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role IN ('admin', 'viewer')
    )
  );

CREATE POLICY "sched_ov_employee_read" ON schedule_overrides
  FOR SELECT USING (
    employee_id IN (
      SELECT id FROM employees WHERE user_id = auth.uid()
    )
  );
