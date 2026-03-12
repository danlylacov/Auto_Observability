#!/bin/bash
set -e

if [ -z "$DATABASE_URL" ]; then
    POSTGRES_HOST=${POSTGRES_HOST:-postgres}
    POSTGRES_PORT=${POSTGRES_PORT:-5432}
    POSTGRES_USER=${POSTGRES_USER:-postgres}
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
    POSTGRES_DB=${POSTGRES_DB:-auto_observability}
    
    export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
fi

echo "Waiting for PostgreSQL to be ready..."
echo "Database URL: postgresql://${POSTGRES_USER:-postgres}:***@${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-auto_observability}"

RETRIES=30
until python3 -c "import psycopg2; psycopg2.connect('${DATABASE_URL}')" 2>/dev/null || [ $RETRIES -eq 0 ]; do
  echo "PostgreSQL is unavailable - sleeping (retries left: $RETRIES)"
  RETRIES=$((RETRIES-1))
  sleep 2
done

if [ $RETRIES -eq 0 ]; then
  echo "Failed to connect to PostgreSQL after 60 seconds"
  exit 1
fi

echo "PostgreSQL is up!"

if [[ "$1" != "celery" ]]; then
    echo "Initializing database..."
    python3 -m app.db.postgres.init_db
    echo "Database initialized successfully!"
else
    echo "Skipping database initialization for Celery worker/beat"
fi

echo "Starting application..."
exec "$@"

