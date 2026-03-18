-- ============================================================
-- Migration 020: NSD Hours + Break Tracking in time_logs
-- ============================================================
-- Adds:
--   nsd_hours        — hours worked in NSD window (10PM–6AM), for payroll NSD premium
--   break_out        — time employee went on break (clock-out for break)
--   break_out_at     — full timestamp of break clock-out
--   break_in         — time employee returned from break
--   break_in_at      — full timestamp of break return
--   actual_break_minutes — computed actual break duration (break_in - break_out)
--   overbreak_minutes    — actual_break - scheduled_break, floor at 0
--
-- Run once in Supabase SQL Editor AFTER 019_holiday_observed.sql.
-- ============================================================

ALTER TABLE time_logs
  ADD COLUMN IF NOT EXISTS nsd_hours             NUMERIC(5,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS break_out             TIME,
  ADD COLUMN IF NOT EXISTS break_out_at          TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS break_in              TIME,
  ADD COLUMN IF NOT EXISTS break_in_at           TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS actual_break_minutes  INTEGER,
  ADD COLUMN IF NOT EXISTS overbreak_minutes     INTEGER      NOT NULL DEFAULT 0;
