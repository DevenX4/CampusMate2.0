-- One-time local setup: dedicated low-privilege role + database for CampusMate.
-- Run as the postgres superuser (it is the ONLY thing that should use the superuser):
--
--   psql -U postgres -h localhost -p 5432 -v app_password='<same value as DB_PASSWORD in .env>' -f backend/scripts/create_local_db.sql
--
-- The password is passed on the command line (-v) so it is never stored in this file.

-- A login role that cannot create roles, cannot create databases and is not a superuser.
CREATE ROLE campusmate_app LOGIN PASSWORD :'app_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE;

-- The role owns only its own database, so migrations (Phase 2) can create tables there,
-- but it has no rights on any other database on this server.
CREATE DATABASE campusmate OWNER campusmate_app ENCODING 'UTF8' TEMPLATE template0;

-- Other roles on the server should not be able to connect to it.
REVOKE ALL ON DATABASE campusmate FROM PUBLIC;
