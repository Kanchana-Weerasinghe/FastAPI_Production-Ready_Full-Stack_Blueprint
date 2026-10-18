-- Least-privilege database roles (run once per environment as a superuser / admin role).
-- The app runs as app_rw (DML only); Alembic runs as app_owner (owns the schema).
-- Passwords come from the secrets manager; rotate them by creating a second login role and switching.

CREATE ROLE app_owner LOGIN PASSWORD :'owner_password';
CREATE ROLE app_rw LOGIN PASSWORD :'app_password';

-- The owner creates and alters tables (migrations).
GRANT CONNECT, CREATE ON DATABASE app TO app_owner;
ALTER SCHEMA public OWNER TO app_owner;

-- The application can read and write data but cannot change the schema.
GRANT CONNECT ON DATABASE app TO app_rw;
GRANT USAGE ON SCHEMA public TO app_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_rw;

-- Tables created by future migrations get the same grants automatically.
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO app_rw;

-- The audit trail is append-only for the application.
-- (Run after the audit_logs table exists.)
-- REVOKE UPDATE, DELETE ON audit_logs FROM app_rw;

-- Configure the app with DB_USERNAME=app_rw and Alembic with MIGRATION_DB_USERNAME=app_owner.
