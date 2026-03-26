-- ============================================================
-- Migration 028: User Roles & Access Control (Phase 3E)
--
-- Expands the 3-role model (admin, viewer, employee) to a
-- 5-role model:
--   admin           — full access to everything
--   hr_manager      — employees, attendance, analytics, reports (no payroll run, no company setup edit)
--   payroll_officer — payroll processing, reports, read-only employees
--   supervisor      — team-only view: dashboard, attendance, calendar
--   employee        — portal only (unchanged)
--
-- Also migrates existing 'viewer' rows → 'hr_manager' and
-- creates a recursive supervisor-tree SQL function.
-- ============================================================

-- ---- 1. Expand role CHECK constraint ----
ALTER TABLE user_company_access
    DROP CONSTRAINT IF EXISTS user_company_access_role_check;

ALTER TABLE user_company_access
    ADD CONSTRAINT user_company_access_role_check
    CHECK (role IN ('admin', 'hr_manager', 'payroll_officer', 'supervisor', 'employee'));

-- ---- 2. Migrate existing viewer → hr_manager ----
UPDATE user_company_access
    SET role = 'hr_manager'
    WHERE role = 'viewer';

-- ---- 3. Recursive supervisor tree function ----
-- Given a supervisor's employee_id, returns all employee IDs
-- in their reporting tree (direct + indirect reports via reports_to).
CREATE OR REPLACE FUNCTION get_supervisor_tree(supervisor_employee_id UUID)
RETURNS SETOF UUID
LANGUAGE sql
STABLE
AS $$
    WITH RECURSIVE tree AS (
        SELECT id FROM employees WHERE reports_to = supervisor_employee_id
        UNION ALL
        SELECT e.id FROM employees e INNER JOIN tree t ON e.reports_to = t.id
    )
    SELECT id FROM tree;
$$;

-- ---- 4. Helper: get employee_id for current auth user ----
CREATE OR REPLACE FUNCTION get_employee_id_for_user(uid UUID)
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
    SELECT id FROM employees WHERE user_id = uid LIMIT 1;
$$;

-- ---- 5. Update RLS policies that reference 'viewer' ----
-- These policies need to include the new roles that should have
-- equivalent or broader access than the old 'viewer' role.

-- employee_profiles (migration 006)
DROP POLICY IF EXISTS ep_update ON employee_profiles;
CREATE POLICY ep_update ON employee_profiles
    FOR UPDATE USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager')
        )
        OR employee_id IN (
            SELECT id FROM employees WHERE user_id = auth.uid()
        )
    );

-- leave_requests (migration 007)
DROP POLICY IF EXISTS lr_admin_select ON leave_requests;
CREATE POLICY lr_admin_select ON leave_requests
    FOR SELECT USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager', 'payroll_officer', 'supervisor')
        )
        OR employee_id IN (SELECT id FROM employees WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS lr_admin_update ON leave_requests;
CREATE POLICY lr_admin_update ON leave_requests
    FOR UPDATE USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager', 'supervisor')
        )
    );

-- overtime_requests (migration 007)
DROP POLICY IF EXISTS otr_admin_select ON overtime_requests;
CREATE POLICY otr_admin_select ON overtime_requests
    FOR SELECT USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager', 'payroll_officer', 'supervisor')
        )
        OR employee_id IN (SELECT id FROM employees WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS otr_admin_update ON overtime_requests;
CREATE POLICY otr_admin_update ON overtime_requests
    FOR UPDATE USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager', 'supervisor')
        )
    );

-- leave_entitlement_templates (migration 008)
DROP POLICY IF EXISTS let_admin ON leave_entitlement_templates;
CREATE POLICY let_admin ON leave_entitlement_templates
    FOR ALL USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager')
        )
    );

-- leave_balance (migration 011)
DROP POLICY IF EXISTS lb_admin ON leave_balance;
CREATE POLICY lb_admin ON leave_balance
    FOR ALL USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager', 'payroll_officer')
        )
    );

-- schedules (migration 012)
DROP POLICY IF EXISTS sched_admin ON schedules;
CREATE POLICY sched_admin ON schedules
    FOR ALL USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager')
        )
    );

DROP POLICY IF EXISTS sched_read ON schedules;
CREATE POLICY sched_read ON schedules
    FOR SELECT USING (
        company_id IN (SELECT get_user_company_ids())
    );

-- schedule_overrides (migration 012)
DROP POLICY IF EXISTS so_admin ON schedule_overrides;
CREATE POLICY so_admin ON schedule_overrides
    FOR ALL USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager')
        )
    );

-- company_locations (migration 013)
DROP POLICY IF EXISTS cl_admin ON company_locations;
CREATE POLICY cl_admin ON company_locations
    FOR ALL USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager')
        )
    );

DROP POLICY IF EXISTS cl_read ON company_locations;
CREATE POLICY cl_read ON company_locations
    FOR SELECT USING (
        company_id IN (SELECT get_user_company_ids())
    );

-- time_logs (migration 013)
DROP POLICY IF EXISTS tl_admin ON time_logs;
CREATE POLICY tl_admin ON time_logs
    FOR ALL USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager', 'payroll_officer')
        )
    );

-- dtr_corrections (migration 013)
DROP POLICY IF EXISTS dc_admin ON dtr_corrections;
CREATE POLICY dc_admin ON dtr_corrections
    FOR ALL USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager')
        )
    );

-- special_leave_requests (migration 017)
DROP POLICY IF EXISTS slr_admin ON special_leave_requests;
CREATE POLICY slr_admin ON special_leave_requests
    FOR ALL USING (
        company_id IN (
            SELECT company_id FROM user_company_access
            WHERE user_id = auth.uid() AND role IN ('admin', 'hr_manager')
        )
    );
