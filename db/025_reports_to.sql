-- Add reporting relationship for org chart hierarchy
ALTER TABLE public.employees
  ADD COLUMN reports_to UUID REFERENCES public.employees(id) ON DELETE SET NULL;

CREATE INDEX idx_employees_reports_to ON public.employees(reports_to);

COMMENT ON COLUMN public.employees.reports_to IS
  'Direct supervisor/manager this employee reports to. NULL = top of org chart (CEO/GM).';
