-- Least-privilege roles for monitoring (run once per environment as an admin role).
-- Same PostgreSQL server as the identity service, but its own schema: the service can neither read nor change
-- other services' tables. Alembic runs as monitoring_owner; the API as monitoring_rw.

CREATE ROLE monitoring_owner LOGIN PASSWORD :'owner_password';
CREATE ROLE monitoring_rw LOGIN PASSWORD :'app_password';

GRANT CONNECT ON DATABASE app TO monitoring_owner, monitoring_rw;

CREATE SCHEMA IF NOT EXISTS monitoring AUTHORIZATION monitoring_owner;
REVOKE ALL ON SCHEMA monitoring FROM PUBLIC;
GRANT USAGE ON SCHEMA monitoring TO monitoring_rw;

ALTER DEFAULT PRIVILEGES FOR ROLE monitoring_owner IN SCHEMA monitoring
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO monitoring_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE monitoring_owner IN SCHEMA monitoring
  GRANT USAGE, SELECT ON SEQUENCES TO monitoring_rw;

-- Keep other services' schemas closed to these roles (public is the identity service's schema).
REVOKE ALL ON SCHEMA public FROM monitoring_owner, monitoring_rw;

-- Secret keys: DB_USERNAME=monitoring_rw, MIGRATION_DB_USERNAME=monitoring_owner.
