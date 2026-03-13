-- ============================================================
-- GenXcript Payroll SaaS — Complete Supabase Schema
-- Philippine SME Payroll System
-- ============================================================
-- All monetary values stored as INTEGER in centavos
-- (e.g. ₱1,500.00 = 150000) to avoid floating-point errors.
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- COMPANIES
-- ============================================================
CREATE TABLE companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    address         TEXT,
    region          TEXT NOT NULL DEFAULT 'NCR',  -- affects minimum wage
    bir_tin         TEXT,
    sss_employer_no TEXT,
    philhealth_employer_no TEXT,
    pagibig_employer_no    TEXT,
    pay_frequency   TEXT NOT NULL DEFAULT 'semi-monthly'
                    CHECK (pay_frequency IN ('monthly', 'semi-monthly', 'weekly')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_companies_name ON companies (name);

-- ============================================================
-- EMPLOYEES
-- ============================================================
CREATE TABLE employees (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    employee_no     TEXT NOT NULL,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    position        TEXT,
    employment_type TEXT NOT NULL DEFAULT 'regular'
                    CHECK (employment_type IN ('regular', 'probationary', 'contractual')),
    date_hired      DATE NOT NULL DEFAULT CURRENT_DATE,
    basic_salary    INTEGER NOT NULL,  -- centavos
    salary_type     TEXT NOT NULL DEFAULT 'monthly'
                    CHECK (salary_type IN ('monthly', 'daily', 'hourly')),
    tax_status      TEXT NOT NULL DEFAULT 'S'
                    CHECK (tax_status IN ('S', 'ME', 'S1', 'S2', 'S3', 'ME1', 'ME2', 'ME3', 'ME4')),
    sss_no          TEXT,
    philhealth_no   TEXT,
    pagibig_no      TEXT,
    bir_tin         TEXT,
    bank_account    TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (company_id, employee_no)
);

CREATE INDEX idx_employees_company ON employees (company_id);
CREATE INDEX idx_employees_active  ON employees (company_id, is_active);

-- ============================================================
-- PAY_PERIODS
-- ============================================================
CREATE TABLE pay_periods (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    payment_date    DATE NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'finalized', 'paid')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (company_id, period_start, period_end)
);

CREATE INDEX idx_pay_periods_company ON pay_periods (company_id);
CREATE INDEX idx_pay_periods_status  ON pay_periods (company_id, status);

-- ============================================================
-- PAYROLL_ENTRIES (one row per employee per pay period)
-- ============================================================
CREATE TABLE payroll_entries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pay_period_id   UUID NOT NULL REFERENCES pay_periods(id) ON DELETE CASCADE,
    employee_id     UUID NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,

    -- Earnings (all in centavos)
    basic_pay               INTEGER NOT NULL DEFAULT 0,
    overtime_pay            INTEGER NOT NULL DEFAULT 0,
    holiday_pay             INTEGER NOT NULL DEFAULT 0,
    night_differential      INTEGER NOT NULL DEFAULT 0,
    allowances_nontaxable   INTEGER NOT NULL DEFAULT 0,
    allowances_taxable      INTEGER NOT NULL DEFAULT 0,
    commission              INTEGER NOT NULL DEFAULT 0,
    thirteenth_month_accrual INTEGER NOT NULL DEFAULT 0,
    gross_pay               INTEGER NOT NULL DEFAULT 0,  -- computed

    -- Government contributions — Employee share
    sss_employee            INTEGER NOT NULL DEFAULT 0,
    philhealth_employee     INTEGER NOT NULL DEFAULT 0,
    pagibig_employee        INTEGER NOT NULL DEFAULT 0,

    -- Government contributions — Employer share
    sss_employer            INTEGER NOT NULL DEFAULT 0,
    philhealth_employer     INTEGER NOT NULL DEFAULT 0,
    pagibig_employer        INTEGER NOT NULL DEFAULT 0,

    -- Tax
    withholding_tax         INTEGER NOT NULL DEFAULT 0,

    -- Other deductions
    sss_loan                INTEGER NOT NULL DEFAULT 0,
    pagibig_loan            INTEGER NOT NULL DEFAULT 0,
    cash_advance            INTEGER NOT NULL DEFAULT 0,
    other_deductions        INTEGER NOT NULL DEFAULT 0,

    -- Totals
    total_deductions        INTEGER NOT NULL DEFAULT 0,  -- computed
    net_pay                 INTEGER NOT NULL DEFAULT 0,  -- computed

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (pay_period_id, employee_id)
);

CREATE INDEX idx_payroll_entries_period   ON payroll_entries (pay_period_id);
CREATE INDEX idx_payroll_entries_employee ON payroll_entries (employee_id);

-- ============================================================
-- DEDUCTION_TYPES (custom deductions per company)
-- ============================================================
CREATE TABLE deduction_types (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    is_recurring    BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (company_id, name)
);

CREATE INDEX idx_deduction_types_company ON deduction_types (company_id);

-- ============================================================
-- GOVERNMENT_RATES (updatable reference table, no hardcoding)
-- ============================================================
CREATE TABLE government_rates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agency          TEXT NOT NULL
                    CHECK (agency IN ('SSS', 'PhilHealth', 'PagIBIG', 'BIR')),
    rate_type       TEXT NOT NULL,   -- e.g. 'employee_rate', 'bracket_1', etc.
    value           JSONB NOT NULL,  -- flexible: can hold numbers, ranges, brackets
    effective_date  DATE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_gov_rates_agency ON government_rates (agency, effective_date DESC);
CREATE INDEX idx_gov_rates_type   ON government_rates (agency, rate_type, effective_date DESC);

-- ============================================================
-- SYNC_QUEUE (future offline-first capability)
-- ============================================================
CREATE TABLE sync_queue (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name      TEXT NOT NULL,
    record_id       UUID NOT NULL,
    operation       TEXT NOT NULL
                    CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    payload         JSONB NOT NULL DEFAULT '{}',
    synced_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sync_queue_pending ON sync_queue (synced_at) WHERE synced_at IS NULL;

-- ============================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================
-- Enable RLS on all tenant-scoped tables.
-- Supabase Auth provides auth.uid() which maps to the logged-in user.
-- We use a helper table to map auth users to companies.

CREATE TABLE user_company_access (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL,  -- references auth.users(id)
    company_id  UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'admin'
                CHECK (role IN ('admin', 'viewer')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (user_id, company_id)
);

CREATE INDEX idx_user_company_access_user ON user_company_access (user_id);

-- Helper function: returns all company_ids the current user can access
CREATE OR REPLACE FUNCTION get_user_company_ids()
RETURNS SETOF UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT company_id
    FROM user_company_access
    WHERE user_id = auth.uid();
$$;

-- ---- COMPANIES ----
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;

CREATE POLICY companies_select ON companies
    FOR SELECT USING (id IN (SELECT get_user_company_ids()));

CREATE POLICY companies_insert ON companies
    FOR INSERT WITH CHECK (true);  -- anyone can create a company (signup flow)

CREATE POLICY companies_update ON companies
    FOR UPDATE USING (id IN (SELECT get_user_company_ids()));

CREATE POLICY companies_delete ON companies
    FOR DELETE USING (id IN (
        SELECT company_id FROM user_company_access
        WHERE user_id = auth.uid() AND role = 'admin'
    ));

-- ---- EMPLOYEES ----
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;

CREATE POLICY employees_select ON employees
    FOR SELECT USING (company_id IN (SELECT get_user_company_ids()));

CREATE POLICY employees_insert ON employees
    FOR INSERT WITH CHECK (company_id IN (SELECT get_user_company_ids()));

CREATE POLICY employees_update ON employees
    FOR UPDATE USING (company_id IN (SELECT get_user_company_ids()));

CREATE POLICY employees_delete ON employees
    FOR DELETE USING (company_id IN (
        SELECT company_id FROM user_company_access
        WHERE user_id = auth.uid() AND role = 'admin'
    ));

-- ---- PAY_PERIODS ----
ALTER TABLE pay_periods ENABLE ROW LEVEL SECURITY;

CREATE POLICY pay_periods_select ON pay_periods
    FOR SELECT USING (company_id IN (SELECT get_user_company_ids()));

CREATE POLICY pay_periods_insert ON pay_periods
    FOR INSERT WITH CHECK (company_id IN (SELECT get_user_company_ids()));

CREATE POLICY pay_periods_update ON pay_periods
    FOR UPDATE USING (company_id IN (SELECT get_user_company_ids()));

CREATE POLICY pay_periods_delete ON pay_periods
    FOR DELETE USING (company_id IN (
        SELECT company_id FROM user_company_access
        WHERE user_id = auth.uid() AND role = 'admin'
    ));

-- ---- PAYROLL_ENTRIES ----
ALTER TABLE payroll_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY payroll_entries_select ON payroll_entries
    FOR SELECT USING (
        pay_period_id IN (
            SELECT pp.id FROM pay_periods pp
            WHERE pp.company_id IN (SELECT get_user_company_ids())
        )
    );

CREATE POLICY payroll_entries_insert ON payroll_entries
    FOR INSERT WITH CHECK (
        pay_period_id IN (
            SELECT pp.id FROM pay_periods pp
            WHERE pp.company_id IN (SELECT get_user_company_ids())
        )
    );

CREATE POLICY payroll_entries_update ON payroll_entries
    FOR UPDATE USING (
        pay_period_id IN (
            SELECT pp.id FROM pay_periods pp
            WHERE pp.company_id IN (SELECT get_user_company_ids())
        )
    );

CREATE POLICY payroll_entries_delete ON payroll_entries
    FOR DELETE USING (
        pay_period_id IN (
            SELECT pp.id FROM pay_periods pp
            WHERE pp.company_id IN (
                SELECT company_id FROM user_company_access
                WHERE user_id = auth.uid() AND role = 'admin'
            )
        )
    );

-- ---- DEDUCTION_TYPES ----
ALTER TABLE deduction_types ENABLE ROW LEVEL SECURITY;

CREATE POLICY deduction_types_select ON deduction_types
    FOR SELECT USING (company_id IN (SELECT get_user_company_ids()));

CREATE POLICY deduction_types_insert ON deduction_types
    FOR INSERT WITH CHECK (company_id IN (SELECT get_user_company_ids()));

CREATE POLICY deduction_types_update ON deduction_types
    FOR UPDATE USING (company_id IN (SELECT get_user_company_ids()));

CREATE POLICY deduction_types_delete ON deduction_types
    FOR DELETE USING (company_id IN (
        SELECT company_id FROM user_company_access
        WHERE user_id = auth.uid() AND role = 'admin'
    ));

-- ---- USER_COMPANY_ACCESS ----
ALTER TABLE user_company_access ENABLE ROW LEVEL SECURITY;

CREATE POLICY uca_select ON user_company_access
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY uca_insert ON user_company_access
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY uca_delete ON user_company_access
    FOR DELETE USING (user_id = auth.uid());

-- ---- GOVERNMENT_RATES (readable by all authenticated users) ----
ALTER TABLE government_rates ENABLE ROW LEVEL SECURITY;

CREATE POLICY gov_rates_select ON government_rates
    FOR SELECT USING (auth.uid() IS NOT NULL);

-- Only service_role can insert/update government rates (admin operation)
-- No insert/update/delete policies = denied by default for regular users

-- ---- SYNC_QUEUE ----
ALTER TABLE sync_queue ENABLE ROW LEVEL SECURITY;
-- sync_queue is managed server-side only, no user policies needed
