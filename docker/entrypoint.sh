#!/bin/sh
set -e

echo "[entrypoint] FLASK_ENV=${FLASK_ENV:-production}"

# Normalize postgres URL for SQLAlchemy if needed
if [ -n "$DATABASE_URL" ]; then
  case "$DATABASE_URL" in
    postgres://*)
      export DATABASE_URL="postgresql://${DATABASE_URL#postgres://}"
      echo "[entrypoint] Normalized DATABASE_URL scheme to postgresql://"
      ;;
  esac
fi

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "[entrypoint] Running database migrations..."
  export FLASK_APP=app.py
  # Bounded retry for transient DB readiness, then fail closed.
  attempts="${MIGRATION_RETRIES:-10}"
  delay="${MIGRATION_RETRY_DELAY:-3}"
  i=1
  while [ "$i" -le "$attempts" ]; do
    if flask db upgrade heads; then
      echo "[entrypoint] Migrations complete"
      break
    fi
    if [ "$i" -eq "$attempts" ]; then
      echo "[entrypoint] ERROR: flask db upgrade failed after ${attempts} attempt(s); refusing to start"
      exit 1
    fi
    echo "[entrypoint] Migration attempt ${i}/${attempts} failed; retrying in ${delay}s..."
    sleep "$delay"
    i=$((i + 1))
  done
else
  echo "[entrypoint] RUN_MIGRATIONS=0 — skipping migrations (operator-managed schema)"
fi

# Ensure upload directory exists and is writable
mkdir -p /app/static/uploads /app/instance 2>/dev/null || true

echo "[entrypoint] Starting: $*"
exec "$@"
