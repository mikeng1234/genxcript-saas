-- ============================================================
-- Migration 018: Company HR Policy Columns
-- ============================================================
-- Adds two HR policy columns to the `companies` table:
--
--   probationary_months — how many months before an employee
--                         is eligible for regularization.
--                         Displayed as a reminder in HR views.
--                         Default: 6 months (PH Labor Code standard).
--
--   ot_min_hours        — minimum hours worked beyond scheduled
--                         end time before overtime is auto-computed
--                         by the DTR engine.
--                         Default: 1.00 hour  (DOLE practice).
--
-- Run once in Supabase SQL Editor AFTER 017_special_leaves.sql.
-- ============================================================

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS probationary_months  INTEGER NOT NULL DEFAULT 6
    CHECK (probationary_months >= 0 AND probationary_months <= 24),
  ADD COLUMN IF NOT EXISTS ot_min_hours         NUMERIC(4,2) NOT NULL DEFAULT 1.00
    CHECK (ot_min_hours >= 0 AND ot_min_hours <= 4);
