# Platinum Heritage CRM — common developer / deploy targets
# Usage: make <target>
# On Windows, use Git Bash / WSL, or run the equivalent commands from docs/PRODUCTION.md

.PHONY: help install css test test-core ci-local migrate up-prod down-prod logs-prod build-prod health redis-up always-on worker beat

help:
	@echo "Targets:"
	@echo "  install     - Python + npm install"
	@echo "  css         - Build production Tailwind CSS"
	@echo "  test-core   - Core CI pytest suite"
	@echo "  test        - Full pytest"
	@echo "  ci-local    - CSS build + core tests (mirrors GitHub Actions gate)"
	@echo "  migrate     - flask db upgrade"
	@echo "  redis-up    - start Redis (compose profile crm)"
	@echo "  worker      - Celery worker (always-on rematch)"
	@echo "  beat        - Celery beat scheduler"
	@echo "  always-on   - print how to run full local stack (see scripts/dev-always-on.ps1 on Windows)"
	@echo "  build-prod  - docker compose build (prod profile)"
	@echo "  up-prod     - docker compose up prod stack"
	@echo "  down-prod   - docker compose down prod stack"
	@echo "  logs-prod   - follow web logs"
	@echo "  health      - curl healthz/readyz on :8000"

install:
	python -m pip install -U pip
	pip install -r requirements.txt
	pip install pytest
	npm ci || npm install

css:
	npm run build:css

test-core:
	pytest -q \
	  tests/test_platinum_heritage_ui.py \
	  tests/test_app_smoke.py \
	  tests/test_simple.py \
	  tests/test_template_replacement.py \
	  --tb=short

test:
	pytest -q --tb=line

ci-local: css test-core
	@echo "CI local gate OK"

migrate:
	FLASK_APP=app.py flask db upgrade

build-prod:
	docker compose --profile prod build

up-prod:
	@test -n "$$SESSION_SECRET" || (echo "Set SESSION_SECRET first (export SESSION_SECRET=...)"; exit 1)
	docker compose --profile prod up -d --build

down-prod:
	docker compose --profile prod down

logs-prod:
	docker compose --profile prod logs -f web

health:
	curl -fsS http://127.0.0.1:8000/healthz && echo
	curl -fsS http://127.0.0.1:8000/readyz && echo

redis-up:
	docker compose --profile crm up -d redis

worker:
	celery -A celery_app.celery_app worker -l info

beat:
	celery -A celery_app.celery_app beat -l info

always-on:
	@echo "Windows (recommended):  .\\scripts\\dev-always-on.ps1"
	@echo "Unix-style terminals:"
	@echo "  1) make redis-up"
	@echo "  2) python main.py          # http://127.0.0.1:55555"
	@echo "  3) make worker             # separate terminal"
	@echo "  4) make beat               # separate terminal"
	@echo "Requires REDIS_URL=redis://localhost:6379/0 in .env"
