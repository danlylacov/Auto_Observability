#!/usr/bin/env bash
set -e

if [ -z "$DATABASE_URL" ]; then
    POSTGRES_HOST=${POSTGRES_HOST:-postgres}
    POSTGRES_PORT=${POSTGRES_PORT:-5432}
    POSTGRES_USER=${POSTGRES_USER:-postgres}
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
    POSTGRES_DB=${POSTGRES_DB:-auto_observability}
    export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
fi

echo "Waiting for PostgreSQL..."
RETRIES=30
until python3 -c "import psycopg2; psycopg2.connect('${DATABASE_URL}')" 2>/dev/null || [ $RETRIES -eq 0 ]; do
  echo "PostgreSQL unavailable ($RETRIES retries left)"
  RETRIES=$((RETRIES-1))
  sleep 2
done
if [ $RETRIES -eq 0 ]; then
  echo "Failed to connect to PostgreSQL"
  exit 1
fi

exec "$@"
