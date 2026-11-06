-- Row-Level Security for documents and chunks, enforced in PostgreSQL so
-- authorization never depends solely on Python-side filtering or on
-- instructions given to an LLM.
--
-- app.country and app.role are authorization context, not authentication:
-- the backend must set them per-transaction from an already-authenticated
-- identity, and must never let end users or an LLM execute arbitrary SQL
-- through policy_app. policy_consultant_admin is a superuser in this
-- local Docker setup (POSTGRES_USER) and therefore always bypasses RLS —
-- that holds regardless of table ownership, and FORCE ROW LEVEL SECURITY
-- would not change it. Only policy_app, which is neither superuser nor
-- the tables' owner, is actually constrained by the policies below.
--
-- policy_app's password is deliberately not set here as a literal: roles
-- are cluster-wide, not per-database, so this migration only ever creates
-- the role once (the IF NOT EXISTS guard matters because test runs reset
-- the public schema but never the role itself). The password comes from
-- app.policy_app_bootstrap_password, a session-level setting the caller
-- (scripts/apply_migrations.py, tests/conftest.py) establishes from the
-- POLICY_APP_PASSWORD environment variable before applying migrations,
-- which itself validates that the value is non-empty before ever reaching
-- SQL. Because it is only read inside the IF NOT EXISTS branch, re-running
-- migrations — including every test run — never changes an
-- already-created role's password. If POLICY_APP_PASSWORD in .env changes
-- afterwards, the role's actual password does not change with it; update
-- it manually with `ALTER ROLE policy_app WITH PASSWORD '...';`.
DO $$
DECLARE
    bootstrap_password text := current_setting('app.policy_app_bootstrap_password', true);
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'policy_app') THEN
        IF bootstrap_password IS NULL OR bootstrap_password = '' THEN
            RAISE EXCEPTION
                'app.policy_app_bootstrap_password must be set (non-empty) before creating policy_app';
        END IF;
        EXECUTE format(
            'CREATE ROLE policy_app LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD %L',
            bootstrap_password
        );
    END IF;
END
$$;

-- Guards against silently trusting a pre-existing policy_app role (e.g.
-- created by hand, or left over from something unrelated) that happens to
-- carry attributes or ownership defeating every policy defined below.
-- Scope is deliberately narrow: it checks policy_app's own direct role
-- attributes and its ownership of the two protected tables. It does not
-- walk role membership/inheritance chains (e.g. policy_app being granted
-- membership in some other, more privileged role) or audit any other
-- grants policy_app might already hold — a full audit of that kind is a
-- separate, more general concern this migration does not try to solve.
DO $$
DECLARE
    is_dangerous boolean;
BEGIN
    SELECT rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole
    INTO is_dangerous
    FROM pg_roles
    WHERE rolname = 'policy_app';

    IF is_dangerous THEN
        RAISE EXCEPTION
            'policy_app has SUPERUSER, BYPASSRLS, CREATEDB, or CREATEROLE — refusing to '
            'proceed with a role that could bypass the access control this migration builds';
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename IN ('documents', 'chunks')
          AND tableowner = 'policy_app'
    ) THEN
        RAISE EXCEPTION
            'policy_app owns documents or chunks — table owners bypass row-level '
            'security by default, which defeats this migration''s purpose';
    END IF;
END
$$;

-- Postgres 15+ already grants only USAGE (not CREATE) to PUBLIC on the
-- public schema by default; revoking it explicitly keeps this auditable
-- without depending on that default.
REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO policy_app;

-- Read-only: policy_app never gets INSERT/UPDATE/DELETE, and gets nothing
-- at all on index_metadata or schema_migrations — there is no functional
-- need for the application role to read either.
GRANT SELECT ON documents, chunks TO policy_app;

-- These two literal arrays are a deliberate, narrow exception to the
-- project's usual rule that country/role vocabulary lives only in
-- config/access-model.yaml (see corpus_manifest.py), not duplicated into
-- SQL. The set of valid *user* countries is a security-relevant subset
-- of that vocabulary (it excludes 'global', see below), and hardcoding
-- it here is a small, explicit, auditable trade-off for simplicity —
-- not a pattern to extend to the rest of the schema. If this list starts
-- changing often, revisit with a small reference table instead; no
-- concrete need for that exists yet.
--
-- 'global' is deliberately excluded from the valid user countries below:
-- it is a document scope (config/access-model.yaml's fourth country
-- value), not something a real user is "from". A context claiming
-- country='global' must be denied, exactly like any other unrecognized
-- value — see documents_select, which still grants global documents to
-- any validly-scoped user via its own separate OR clause.
CREATE FUNCTION access_context_is_set() RETURNS boolean
LANGUAGE sql STABLE AS $$
    SELECT COALESCE(current_setting('app.country', true), '')
               = ANY (ARRAY['spain', 'mexico', 'england'])
       AND COALESCE(current_setting('app.role', true), '')
               = ANY (ARRAY['employee', 'manager', 'hr'])
$$;

REVOKE EXECUTE ON FUNCTION access_context_is_set() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION access_context_is_set() TO policy_app;

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- 'global' is a literal value of the country column (one of the four
-- real values in config/access-model.yaml), not a special Postgres
-- construct — a global document is visible to any authorized role,
-- regardless of the requester's own country.
CREATE POLICY documents_select ON documents
FOR SELECT TO policy_app
USING (
    access_context_is_set()
    AND (country = current_setting('app.country', true) OR country = 'global')
    AND current_setting('app.role', true) = ANY(allowed_roles)
);

ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

-- Deliberately delegates entirely to documents_select instead of
-- repeating its country/role predicate here: policy_app is itself bound
-- by documents' RLS (it is neither the owner nor a BYPASSRLS role), so
-- this subquery is filtered by documents_select too — a chunk is visible
-- exactly when its document is. Verified directly against PostgreSQL,
-- not assumed (see tests/test_security.py).
CREATE POLICY chunks_select ON chunks
FOR SELECT TO policy_app
USING (
    EXISTS (SELECT 1 FROM documents d WHERE d.document_id = chunks.document_id)
);
