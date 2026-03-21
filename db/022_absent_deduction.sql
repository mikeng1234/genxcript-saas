-- Migration 022: Add absent_deduction column to payroll_entries
-- Tracks absent day deductions computed from DTR (daily rate × absent days)

ALTER TABLE payroll_entries
  ADD COLUMN IF NOT EXISTS absent_deduction INTEGER NOT NULL DEFAULT 0;
