-- 016_manager_hierarchy.sql
-- Adds reporting-line (manager) to the employees table
-- Enables the org chart hierarchy: who reports to whom

ALTER TABLE employees
  ADD COLUMN IF NOT EXISTS manager_id UUID REFERENCES employees(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_employees_manager ON employees (manager_id);

-- Note: No RLS changes needed — manager_id follows the same
-- company-scoped access rules already applied to the employees table.
