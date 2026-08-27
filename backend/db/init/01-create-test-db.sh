#!/usr/bin/env bash
set -euo pipefail

if [[ "${POSTGRES_DB}" == "${POSTGRES_TEST_DB}" ]]; then
    exit 0
fi

if ! psql \
    --username "${POSTGRES_USER}" \
    --dbname "${POSTGRES_DB}" \
    --tuples-only \
    --no-align \
    --set=test_database="${POSTGRES_TEST_DB}" \
    --command="SELECT 1 FROM pg_database WHERE datname = :'test_database';" | grep -q '^1$'; then
    # The database name comes from the Compose environment. Double quotes are
    # escaped before use as an identifier for a safe local override.
    quoted_test_db="${POSTGRES_TEST_DB//\"/\"\"}"
    psql \
        --username "${POSTGRES_USER}" \
        --dbname "${POSTGRES_DB}" \
        --command "CREATE DATABASE \"${quoted_test_db}\";"
fi
