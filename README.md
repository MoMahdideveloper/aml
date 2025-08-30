# Real Estate CRM (Flask)

[![CI](https://github.com/OWNER/REPO/actions/workflows/tests.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/tests.yml)

A lightweight CRM-style web app built with Flask, SQLAlchemy, and Jinja templates. Includes property, agent, customer, deal, and task management, with optional vector search and AI extraction services.

## Quick Start
- Install deps (minimal): `python -m pip install flask flask-sqlalchemy flask-migrate sqlalchemy`
- Dev server: `python main.py` (http://0.0.0.0:5000)
- Tests: `python -m pip install pytest && pytest -q`

## Docs
- Contributor guide: see `AGENTS.md` for structure, style, and workflows.
- CI: `.github/workflows/tests.yml` runs pytest on push/PR.

Note: Replace `OWNER/REPO` in the badge URL with your GitHub repo path.

