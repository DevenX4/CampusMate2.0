#!/bin/sh
# Every start first brings the schema to the version this image was built for, then runs the
# command (the API by default; or e.g. "python -m app.seed" via docker compose run).
set -eu
alembic upgrade head
exec "$@"
