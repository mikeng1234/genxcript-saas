-- ============================================================
-- Migration 006: Employee Self-Service
-- - Add email + user_id to employees (for portal login link)
-- - Add 'employee' role to user_company_access
-- - Create employee_profiles table (personal details filled by employee)
-- ============================================================

-- ---- Add email and user_id to employees ----
ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS email   TEXT,
    ADD COLUMN IF NOT EXISTS user_id UUID;  -- references auth.users(id)

CREATE INDEX IF NOT EXISTS idx_employees_email   ON employees (email);
CREATE INDEX IF NOT EXISTS idx_employees_user_id ON employees (user_id);

-- ---- Expand role options on user_company_access ----
ALTER TABLE user_company_access
    DROP CONSTRAINT IF EXISTS user_company_access_role_check;

ALTER TABLE user_company_access
    ADD CONSTRAINT user_company_access_role_check
    CHECK (role IN ('admin', 'viewer', 'employee'));

-- ============================================================
-- EMPLOYEE_PROFILES
-- Personal/demographic details filled in by the employee via
-- the self-service portal.  Kept separate from the employees
-- table so payroll-critical fields (salary, tax status, etc.)
-- are never touched by employee-role users.
-- ============================================================

CREATE TABLE IF NOT EXISTS employee_profiles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id     UUID NOT NULL UNIQUE REFERENCES employees(id) ON DELETE CASCADE,
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- Personal
    middle_name             TEXT,
    suffix                  TEXT,       -- Jr., Sr., III, etc.
    date_of_birth           DATE,
    place_of_birth          TEXT,
    sex                     TEXT CHECK (sex IN ('Male', 'Female', 'Prefer not to say')),
    civil_status            TEXT CHECK (civil_status IN ('Single', 'Married', 'Widowed', 'Separated', 'Divorced')),
    nationality             TEXT DEFAULT 'Filipino',
    religion                TEXT,
    mobile_no               TEXT,

    -- Present Address
    present_address_street      TEXT,
    present_address_barangay    TEXT,
    present_address_city        TEXT,
    present_address_province    TEXT,
    present_address_zip         TEXT,

    -- Permanent Address (can be same as present)
    perm_address_same           BOOLEAN DEFAULT true,
    perm_address_street         TEXT,
    perm_address_barangay       TEXT,
    perm_address_city           TEXT,
    perm_address_province       TEXT,
    perm_address_zip            TEXT,

    -- Additional Government IDs
    philsys_no      TEXT,
    umid_no         TEXT,

    -- Bank
    bank_name       TEXT,

    -- Emergency Contact
    emergency_name          TEXT,
    emergency_relationship  TEXT,
    emergency_phone         TEXT,
    emergency_address       TEXT,

    -- Spouse (applicable if married)
    spouse_name             TEXT,
    spouse_occupation       TEXT,
    spouse_employer         TEXT,
    spouse_contact          TEXT,

    -- Employment details (admin-viewable extras)
    department              TEXT,
    regularization_date     DATE,

    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_employee_profiles_employee ON employee_profiles (employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_profiles_company  ON employee_profiles (company_id);

-- ============================================================
-- RLS for employee_profiles
-- Admins/viewers can read all profiles in their company.
-- Employees can only read and update their own profile.
-- ============================================================

ALTER TABLE employee_profiles ENABLE ROW LEVEL SECURITY;

-- Admins and viewers: full read access within their company
CREATE POLICY ep_select_admin ON employee_profiles
    FOR SELECT USING (company_id IN (SELECT get_user_company_ids()));

-- Anyone in the company can insert (admin creating stub, or employee filling theirs)
CREATE POLICY ep_insert ON employee_profiles
    FOR INSERT WITH CHECK (company_id IN (SELECT get_user_company_ids()));

-- Admins can update any profile; employees can only update their own
CREATE POLICY ep_update ON employee_profiles
    FOR UPDATE USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'viewer')
        )
        OR
        employee_id IN (
            SELECT id FROM employees WHERE user_id = auth.uid()
        )
    );
