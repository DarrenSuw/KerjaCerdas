#!/bin/sh
# Container entrypoint: bring the schema up to date, then serve.
#
# `create_all()` at startup can only create missing TABLES — it can never add a
# COLUMN to a table that already exists. Without this step, an existing
# PostgreSQL deployment silently keeps its old schema and then 500s on the
# first query touching a v2 column (users.email_verified, jobs.public_code,
# applications.skill_snapshot, ...). Alembic is the only supported migration
# path for PostgreSQL (see CLAUDE.md).
#
# Failing here is deliberate: a container that cannot migrate must not start
# serving against a half-migrated database.
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "[entrypoint] alembic upgrade head"
    cd /app/backend && alembic upgrade head && cd /app
else
    echo "[entrypoint] RUN_MIGRATIONS=false — skipping alembic upgrade"
fi

exec "$@"
