-- One-time local setup: a dedicated low-privilege role plus two databases for CampusMate.
--   campusmate       development data
--   campusmate_test  used only by pytest (tests drop and rebuild its schema)
--
-- Run as the postgres superuser (the ONLY time the superuser is needed), e.g. from the repo root in Git Bash:
--
--   psql -U postgres -h localhost -p 5432 \
--        -v app_password="$(grep '^DB_PASSWORD=' .env | cut -d= -f2-)" \
--        -f backend/scripts/create_local_db.sql
--
-- The password is passed on the command line (-v) so it is never stored in this file.

\set ON_ERROR_STOP on

-- A login role that cannot create roles or databases and is not a superuser.
CREATE ROLE campusmate_app LOGIN PASSWORD :'app_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE;

-- The role OWNS only these two databases, so migrations can create tables inside them,
-- but it has no rights on any other database on this server.
CREATE DATABASE campusmate      OWNER campusmate_app ENCODING 'UTF8' TEMPLATE template0;
CREATE DATABASE campusmate_test OWNER campusmate_app ENCODING 'UTF8' TEMPLATE template0;

-- Other roles on the server may not connect to them.
REVOKE ALL ON DATABASE campusmate      FROM PUBLIC;
REVOKE ALL ON DATABASE campusmate_test FROM PUBLIC;
