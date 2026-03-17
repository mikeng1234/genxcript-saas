-- ============================================================
-- Migration 014 — remittance_records
--
-- Tracks when each agency's monthly remittance has been filed
-- and paid.  One row per company × agency × calendar month.
--
-- Agencies: 'SSS' | 'PhilHealth' | 'Pag-IBIG' | 'BIR'
-- Forms:    'R3 / R5' | 'RF-1' | 'MCRF' | '1601-C'
-- ============================================================

CREATE TABLE IF NOT EXISTS remittance_records (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id      UUID          NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

  -- Which agency + statutory form
  agency          TEXT          NOT NULL,   -- 'SSS' | 'PhilHealth' | 'Pag-IBIG' | 'BIR'
  form            TEXT          NOT NULL,   -- 'R3 / R5' | 'RF-1' | 'MCRF' | '1601-C'

  -- Reporting period (calendar month contributions relate to)
  period_year     INTEGER       NOT NULL,   -- e.g. 2025
  period_month    INTEGER       NOT NULL    -- 1 = January … 12 = December
      CHECK (period_month BETWEEN 1 AND 12),

  -- Payment details
  remitted_date   DATE          NOT NULL,   -- actual date HR submitted / paid
  reference_no    TEXT,                     -- ORN / Batch No. / TRA number
  amount_centavos BIGINT,                   -- total amount remitted (centavos)
  notes           TEXT,

  -- Audit
  remitted_by     UUID          REFERENCES auth.users(id),
  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

  -- Only one record per company × agency × month
  UNIQUE (company_id, agency, period_year, period_month)
);

CREATE INDEX IF NOT EXISTS idx_remit_company_period
    ON remittance_records (company_id, period_year, period_month);

CREATE INDEX IF NOT EXISTS idx_remit_company_agency
    ON remittance_records (company_id, agency);

-- ── Row Level Security ────────────────────────────────────────
ALTER TABLE remittance_records ENABLE ROW LEVEL SECURITY;

-- All company members: read access
CREATE POLICY "remit_select" ON remittance_records
    FOR SELECT
    TO authenticated
    USING (company_id IN (SELECT get_user_company_ids()));

-- All company members: insert / update
CREATE POLICY "remit_insert" ON remittance_records
    FOR INSERT
    TO authenticated
    WITH CHECK (company_id IN (SELECT get_user_company_ids()));

CREATE POLICY "remit_update" ON remittance_records
    FOR UPDATE
    TO authenticated
    USING  (company_id IN (SELECT get_user_company_ids()))
    WITH CHECK (company_id IN (SELECT get_user_company_ids()));

-- Admins only: delete
CREATE POLICY "remit_delete" ON remittance_records
    FOR DELETE
    TO authenticated
    USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid()
              AND role = 'admin'
        )
    );

-- Employees with no company access: no access (covered by absence from user_company_access)
