#!/usr/bin/env sh
set -eu

db_host="${DB_HOST:-db}"
db_port="${DB_PORT:-5432}"
db_user="${POSTGRES_USER:-libraryos}"
db_name="${POSTGRES_DB:-libraryos}"

echo "Waiting for PostgreSQL at ${db_host}:${db_port}..."
until pg_isready -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" >/dev/null 2>&1; do
    sleep 1
done

echo "Applying database migrations..."
alembic upgrade head

echo "Running deterministic seed..."
python -m app.seed

echo "Starting LibraryOS API..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
