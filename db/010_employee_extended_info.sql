-- ============================================================
-- Migration 010: Employee Extended Information (Phase 3B)
-- ============================================================
-- Adds fields for:
--   employees       → resignation_date
--   employee_profiles → classification, education, extra contacts, social links
-- ============================================================

-- ---- employees table: track end of employment ----
ALTER TABLE employees
  ADD COLUMN IF NOT EXISTS resignation_date DATE;

-- ---- employee_profiles: professional classification ----
ALTER TABLE employee_profiles
  ADD COLUMN IF NOT EXISTS classification    TEXT;   -- e.g. Accountant, Engineer, Nurse

-- ---- employee_profiles: educational background ----
ALTER TABLE employee_profiles
  ADD COLUMN IF NOT EXISTS education_degree  TEXT,   -- e.g. BS Computer Science, BSBA
  ADD COLUMN IF NOT EXISTS education_school  TEXT,   -- e.g. University of the Philippines
  ADD COLUMN IF NOT EXISTS education_year    INTEGER; -- year graduated, e.g. 2018

-- ---- employee_profiles: additional contact channels ----
ALTER TABLE employee_profiles
  ADD COLUMN IF NOT EXISTS home_phone        TEXT,
  ADD COLUMN IF NOT EXISTS work_phone        TEXT,
  ADD COLUMN IF NOT EXISTS personal_email    TEXT;

-- ---- employee_profiles: social / online presence ----
ALTER TABLE employee_profiles
  ADD COLUMN IF NOT EXISTS facebook          TEXT,   -- profile URL or username
  ADD COLUMN IF NOT EXISTS linkedin          TEXT;   -- profile URL or username
