-- RegulAI database init — runs on first postgres start
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'regulai_app') THEN
        CREATE ROLE regulai_app LOGIN;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE regulai TO regulai_app;
GRANT USAGE ON SCHEMA public TO regulai_app;
