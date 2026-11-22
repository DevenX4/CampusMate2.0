#!/bin/sh
# Runs once, when the database volume is first created: the same low-privilege role and
# databases as a native install (backend/scripts/create_local_db.sql). The role's password comes
# from the environment and is never written to a file.
set -eu
psql --username "$POSTGRES_USER" --dbname postgres -v ON_ERROR_STOP=1 \
     -v app_password="$CAMPUSMATE_DB_PASSWORD" -f /campusmate/create_local_db.sql
