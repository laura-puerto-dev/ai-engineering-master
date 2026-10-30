-- Application role without administrative privileges
CREATE ROLE municipal_app
    WITH LOGIN
    NOSUPERUSER
    NOBYPASSRLS;

-- Allow the application role to access the public schema
GRANT USAGE ON SCHEMA public TO municipal_app;

-- Allow reading incidents without modifying them
GRANT SELECT ON TABLE incidents TO municipal_app;

-- Enable row-level security for incidents
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;

-- Restrict application queries to the current department
CREATE POLICY incidents_department_select
ON incidents
FOR SELECT
TO municipal_app
USING (
    department_id = NULLIF(
        current_setting('app.department_id', true),
        ''
    )::integer
);
