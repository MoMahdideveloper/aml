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
  # Non-fatal if DB not ready yet — compose healthcheck/retry handles DB
  if flask db upgrade; then
    echo "[entrypoint] Migrations complete"
  else
    echo "[entrypoint] WARNING: flask db upgrade failed (will still start app)"
  fi
fi

# Ensure upload directory exists and is writable
mkdir -p /app/static/uploads /app/instance 2>/dev/null || true

echo "[entrypoint] Starting: $*"
exec "$@"
