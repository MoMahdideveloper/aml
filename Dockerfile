# Platinum Heritage CRM — multi-stage production image
# Stage 1: build Tailwind CSS
FROM node:20-alpine AS css
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY tailwind.config.js ./
COPY static/css/tailwind-input.css ./static/css/tailwind-input.css
COPY templates ./templates
COPY static/js ./static/js
RUN npm run build:css

# Stage 2: Python runtime
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    USE_TAILWIND_CDN=0 \
    ENABLE_CSRF=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg2 / builds
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install "psycopg2-binary>=2.9.9"

# Application source (context filtered by .dockerignore — no .env, tests, Track B, DBs)
COPY . .
# Overwrite with production CSS from build stage
COPY --from=css /build/static/css/tailwind-ph.css ./static/css/tailwind-ph.css

# Fail image build if production CSS missing or tiny
RUN test -f /app/static/css/tailwind-ph.css \
    && test "$(wc -c < /app/static/css/tailwind-ph.css)" -gt 10000

RUN chmod +x /app/docker/entrypoint.sh \
    && mkdir -p /app/static/uploads /app/instance \
    && useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "main:app"]
