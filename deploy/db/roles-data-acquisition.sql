-- Least-privilege roles for data-acquisition (run once per environment as an admin role).
-- Same PostgreSQL server as the identity service, but its own schema: the service can neither read nor change
-- other services' tables. Alembic runs as data_acquisition_owner; the API as data_acquisition_rw.

CREATE ROLE data_acquisition_owner LOGIN PASSWORD :'owner_password';
CREATE ROLE data_acquisition_rw LOGIN PASSWORD :'app_password';

GRANT CONNECT ON DATABASE app TO data_acquisition_owner, data_acquisition_rw;

CREATE SCHEMA IF NOT EXISTS data_acquisition AUTHORIZATION data_acquisition_owner;
REVOKE ALL ON SCHEMA data_acquisition FROM PUBLIC;
GRANT USAGE ON SCHEMA data_acquisition TO data_acquisition_rw;

ALTER DEFAULT PRIVILEGES FOR ROLE data_acquisition_owner IN SCHEMA data_acquisition
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO data_acquisition_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE data_acquisition_owner IN SCHEMA data_acquisition
  GRANT USAGE, SELECT ON SEQUENCES TO data_acquisition_rw;

-- Keep other services' schemas closed to these roles (public is the identity service's schema).
REVOKE ALL ON SCHEMA public FROM data_acquisition_owner, data_acquisition_rw;

-- Secret keys: DB_USERNAME=data_acquisition_rw, MIGRATION_DB_USERNAME=data_acquisition_owner.
