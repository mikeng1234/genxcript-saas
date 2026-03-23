-- Add photo_url to employee_profiles for profile pictures
ALTER TABLE public.employee_profiles ADD COLUMN IF NOT EXISTS photo_url TEXT;

-- Storage bucket: employee-photos (create manually in Supabase Dashboard)
-- Storage > New bucket > name: employee-photos > Public = ON
