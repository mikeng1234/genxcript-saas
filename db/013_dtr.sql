-- ============================================================
-- Migration 013: DTR / Attendance (Phase 4B)
-- ============================================================
-- 1. company_locations  — named GPS sites for geofencing
-- 2. time_logs          — one row per employee per day (time-in/out + computed)
-- 3. dtr_corrections    — employee-submitted correction requests
--
-- Run once in Supabase SQL Editor AFTER 012_schedules.sql.
-- ============================================================


-- ── 1. Company Locations (geofencing) ────────────────────────────────────────
-- HR defines named office/site coordinates; radius_m is the allowed check-in
-- radius. Employees clocking in via the portal have their distance computed
-- against the nearest active location.

CREATE TABLE IF NOT EXISTS company_locations (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id  UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

  name        TEXT        NOT NULL,           -- "Main Office", "Laguna Plant"
  address     TEXT,                           -- Human-readable, display only

  latitude    NUMERIC(10, 7) NOT NULL,
  longitude   NUMERIC(10, 7) NOT NULL,
  radius_m    INTEGER     NOT NULL DEFAULT 100
              CHECK (radius_m > 0 AND radius_m <= 50000),

  is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (company_id, name)
);

CREATE INDEX IF NOT EXISTS idx_locations_company ON company_locations (company_id);


-- ── 2. Time Logs ─────────────────────────────────────────────────────────────
-- One row per employee per calendar day.
-- Schedule fields are snapshotted at save time so future schedule edits
-- do not corrupt historical attendance records.
-- Computed columns (late_minutes, gross_hours, etc.) are populated by
-- backend/dtr.py every time the row is saved — they are never trusted
-- as authoritative source-of-truth without the raw time_in / time_out.

CREATE TABLE IF NOT EXISTS time_logs (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  employee_id     UUID        NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  work_date       DATE        NOT NULL,

  -- ── Schedule snapshot ─────────────────────────────────────────────────────
  schedule_id         UUID    REFERENCES schedules(id) ON DELETE SET NULL,
  expected_start      TIME,
  expected_end        TIME,
  expected_hours      NUMERIC(5, 2),

  -- ── Time-in ───────────────────────────────────────────────────────────────
  time_in             TIME,
  time_in_at          TIMESTAMPTZ,            -- full timestamp for audit
  time_in_method      TEXT    DEFAULT 'manual',  -- 'manual' | 'portal'
  time_in_lat         NUMERIC(10, 7),
  time_in_lng         NUMERIC(10, 7),
  time_in_distance_m  INTEGER,               -- distance from nearest approved location
  time_in_location_id UUID    REFERENCES company_locations(id) ON DELETE SET NULL,
  time_in_snapshot_url TEXT,                 -- face photo from camera API

  -- ── Time-out ──────────────────────────────────────────────────────────────
  time_out            TIME,
  time_out_at         TIMESTAMPTZ,
  time_out_method     TEXT    DEFAULT 'manual',
  time_out_lat        NUMERIC(10, 7),
  time_out_lng        NUMERIC(10, 7),
  time_out_distance_m INTEGER,
  time_out_snapshot_url TEXT,

  -- ── Computed attendance fields ─────────────────────────────────────────────
  -- Re-computed by backend/dtr.py on every save. Never manually edited.
  gross_hours         NUMERIC(5, 2),
  late_minutes        INTEGER     NOT NULL DEFAULT 0,
  undertime_minutes   INTEGER     NOT NULL DEFAULT 0,
  ot_hours            NUMERIC(5, 2) NOT NULL DEFAULT 0,

  -- ── Status & flags ────────────────────────────────────────────────────────
  -- present | absent | half_day | on_leave | holiday | rest_day | no_schedule
  status          TEXT        NOT NULL DEFAULT 'present',
  is_out_of_range BOOLEAN     NOT NULL DEFAULT FALSE,

  notes           TEXT,
  created_by      UUID        REFERENCES auth.users(id),
  updated_by      UUID        REFERENCES auth.users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Only one log per employee per day
  UNIQUE (employee_id, work_date)
);

CREATE INDEX IF NOT EXISTS idx_time_logs_company_date ON time_logs (company_id, work_date);
CREATE INDEX IF NOT EXISTS idx_time_logs_employee     ON time_logs (employee_id, work_date);


-- ── 3. DTR Corrections ───────────────────────────────────────────────────────
-- Employees submit correction requests when their clock-in record is wrong
-- (forgot to punch out, system error, working remotely, etc.).
-- Admin reviews, approves (updates the time_log) or rejects with notes.

CREATE TABLE IF NOT EXISTS dtr_corrections (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  employee_id     UUID        NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  time_log_id     UUID        REFERENCES time_logs(id) ON DELETE SET NULL,
  work_date       DATE        NOT NULL,

  requested_time_in   TIME,
  requested_time_out  TIME,
  reason          TEXT        NOT NULL,

  -- pending | approved | rejected
  status          TEXT        NOT NULL DEFAULT 'pending',
  admin_notes     TEXT,
  reviewed_by     UUID        REFERENCES auth.users(id),
  reviewed_at     TIMESTAMPTZ,

  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dtr_corr_company  ON dtr_corrections (company_id, status);
CREATE INDEX IF NOT EXISTS idx_dtr_corr_employee ON dtr_corrections (employee_id);


-- ── 4. RLS ────────────────────────────────────────────────────────────────────

ALTER TABLE company_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_logs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE dtr_corrections   ENABLE ROW LEVEL SECURITY;

-- ── company_locations ────────────────────────────────────────────────────────
-- Admin/viewer: full CRUD
-- Employee: read all active locations for their company (needed for geofencing check)

DROP POLICY IF EXISTS "loc_admin"          ON company_locations;
DROP POLICY IF EXISTS "loc_employee_read"  ON company_locations;

CREATE POLICY "loc_admin" ON company_locations
  FOR ALL USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role IN ('admin', 'viewer')
    )
  );

CREATE POLICY "loc_employee_read" ON company_locations
  FOR SELECT USING (
    is_active = TRUE
    AND company_id IN (SELECT get_user_company_ids())
  );


-- ── time_logs ─────────────────────────────────────────────────────────────────
-- Admin/viewer: full CRUD for all employees in their company
-- Employee: SELECT own rows only (to view their own DTR)

DROP POLICY IF EXISTS "tlog_admin"           ON time_logs;
DROP POLICY IF EXISTS "tlog_employee_read"   ON time_logs;
DROP POLICY IF EXISTS "tlog_employee_write"  ON time_logs;
DROP POLICY IF EXISTS "tlog_employee_update" ON time_logs;

CREATE POLICY "tlog_admin" ON time_logs
  FOR ALL USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role IN ('admin', 'viewer')
    )
  );

CREATE POLICY "tlog_employee_read" ON time_logs
  FOR SELECT USING (
    employee_id IN (
      SELECT id FROM employees WHERE user_id = auth.uid()
    )
  );

-- Employees can INSERT/UPDATE their own row (portal clock-in/out)
CREATE POLICY "tlog_employee_write" ON time_logs
  FOR INSERT WITH CHECK (
    employee_id IN (
      SELECT id FROM employees WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "tlog_employee_update" ON time_logs
  FOR UPDATE USING (
    employee_id IN (
      SELECT id FROM employees WHERE user_id = auth.uid()
    )
  );


-- ── dtr_corrections ───────────────────────────────────────────────────────────
-- Admin/viewer: full access (review + approve/reject)
-- Employee: SELECT + INSERT own records only

DROP POLICY IF EXISTS "dtrcorr_admin"           ON dtr_corrections;
DROP POLICY IF EXISTS "dtrcorr_employee_read"   ON dtr_corrections;
DROP POLICY IF EXISTS "dtrcorr_employee_insert" ON dtr_corrections;

CREATE POLICY "dtrcorr_admin" ON dtr_corrections
  FOR ALL USING (
    company_id IN (
      SELECT company_id FROM user_company_access
      WHERE user_id = auth.uid() AND role IN ('admin', 'viewer')
    )
  );

CREATE POLICY "dtrcorr_employee_read" ON dtr_corrections
  FOR SELECT USING (
    employee_id IN (
      SELECT id FROM employees WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "dtrcorr_employee_insert" ON dtr_corrections
  FOR INSERT WITH CHECK (
    employee_id IN (
      SELECT id FROM employees WHERE user_id = auth.uid()
    )
  );
