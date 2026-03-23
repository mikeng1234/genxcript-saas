-- Enable RLS on audit_logs (fixes Supabase security advisory)
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own company audit logs"
  ON public.audit_logs FOR SELECT
  USING (company_id IN (SELECT get_user_company_ids()));

CREATE POLICY "Users can insert own company audit logs"
  ON public.audit_logs FOR INSERT
  WITH CHECK (company_id IN (SELECT get_user_company_ids()));
