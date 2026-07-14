#!/usr/bin/env python3
"""Staging release rehearsal coordinator for Track A.

Thin orchestration layer — does not duplicate backup/restore/migration logic.
All actual work is delegated to existing scripts in scripts/ci/ and scripts/.

Safety contracts:
- Refuses production-looking hosts and DB names.
- Requires explicit opt-in flag before construction.
- Requires explicit --live flag before any subprocess execution.
- dry_run / plan mode requires no external binaries.
- Never includes credentials in output or plan commands.
- Does not automatically clean up or destructively restore.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent

# Runner type: (cmd: list[str], env: dict | None) -> (rc: int, stdout: str, stderr: str)
Runner = Callable[[list[str], dict | None], tuple[int, str, str]]

# Production markers shared with backup_postgres — refuse these in rehearsal too.
_PROD_MARKERS = (
    "rds.amazonaws.com",
    "azure.com",
    "database.azure",
    "cloudsql",
    "production",
    "prod-db",
    "prod_db",
)

_SYSTEM_DB_NAMES = {"postgres", "template0", "template1"}

# Patterns whose VALUES must never appear in output.
_SECRET_PATTERNS = [
    # postgresql://user:PASSWORD@host/db  (also catches pg:// aliases)
    re.compile(r"((?:postgres(?:ql)?|pg)://[^:/@]+:)([^@/\s]+)(@)", re.I),
    # KEY=VALUE for credential-looking env vars
    re.compile(r"((?:PGPASSWORD|PASSWORD|SECRET|API_KEY|GOOGLE_API_KEY|DATABASE_URL\s*=\s*\S+:)[^\s=]*=)(\S+)", re.I),
    # Bare AIza... Google API key shapes
    re.compile(r"(AIza[0-9A-Za-z_-]{35})"),
    # generic password=VALUE
    re.compile(r"(password=)([^\s,;&]+)", re.I),
]


# ---------------------------------------------------------------------------
# Public exceptions
# ---------------------------------------------------------------------------

class RehearsalRefused(Exception):
    """Raised when a safety gate prevents rehearsal from proceeding."""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def is_disposable_target(host: str, db: str) -> bool:
    """Return True only when host+db are clearly local/disposable."""
    host_l = (host or "").lower()
    db_l = (db or "").lower()
    if db_l in _SYSTEM_DB_NAMES:
        return False
    for marker in _PROD_MARKERS:
        if marker in host_l or marker in db_l:
            return False
    return True


def sanitize_output(text: str) -> str:
    """Redact credential-looking values from arbitrary text."""
    result = text
    for pattern in _SECRET_PATTERNS:
        if pattern.groups == 3:
            # URL: replace group 2 (password) with ***
            result = pattern.sub(r"\1***\3", result)
        elif pattern.groups == 2:
            result = pattern.sub(r"\1***", result)
        else:
            # Single group: full match → ***
            result = pattern.sub("***", result)
    return result


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------

@dataclass
class RehearsalConfig:
    target_db: str
    target_host: str
    backup_dest: str
    uploads_source: str
    base_url: str
    opt_in: bool
    dry_run: bool = True
    live: bool = False
    target_port: int = 5432
    allow_destructive_migrations: bool = False
    backup_dump: str = ""
    extra_meta_args: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------

class RehearsalCoordinator:
    """Thin coordinator for staging release rehearsal gates.

    Construction validates safety contracts.
    plan()  → list of step dicts (no subprocess calls).
    run()   → executes gates via injected runner; dry_run returns plan report.
    """

    def __init__(self, config: RehearsalConfig, runner: Runner | None = None) -> None:
        self._cfg = config
        self._runner = runner or _default_runner

        # --- Safety contracts checked at construction time ---

        if not config.opt_in:
            raise RehearsalRefused(
                "Explicit opt-in required. Pass opt_in=True or --opt-in on CLI."
            )

        db_l = config.target_db.lower()
        host_l = config.target_host.lower()

        if config.target_db.lower() in _SYSTEM_DB_NAMES:
            raise RehearsalRefused(
                f"Refusing to use system/template database name: {config.target_db!r}"
            )

        for marker in _PROD_MARKERS:
            if marker in host_l or marker in db_l:
                raise RehearsalRefused(
                    f"Target host/db looks production-like (matched {marker!r}). "
                    "Use a local/disposable target only."
                )

        # Live mode: base_url must be local/disposable
        if config.live and not config.dry_run:
            url_l = (config.base_url or "").lower()
            if not (
                "127.0.0.1" in url_l
                or "localhost" in url_l
                or "0.0.0.0" in url_l
            ):
                raise RehearsalRefused(
                    f"Live mode base_url must point at a local/disposable target. "
                    f"Got: {config.base_url!r}. Use http://127.0.0.1:... or http://localhost:..."
                )

            # Live mode: explicit dump path required — no implicit "latest" selection.
            if not config.backup_dump:
                raise RehearsalRefused(
                    "Live mode requires --backup-dump: explicit path to the pg_dump archive. "
                    "Refusing implicit latest-dump selection."
                )
            dump_path = Path(config.backup_dump)
            if not dump_path.is_file():
                raise RehearsalRefused(
                    f"--backup-dump path does not exist or is not a file: {config.backup_dump!r}"
                )

    # ------------------------------------------------------------------
    # Plan (no subprocess)
    # ------------------------------------------------------------------

    def plan(self) -> list[dict]:
        """Return the ordered gate list with commands. Never calls runner."""
        cfg = self._cfg
        steps: list[dict] = []

        _scripts_ci = ROOT / "scripts" / "ci"
        _scripts = ROOT / "scripts"

        # Gate 1: Workflow safety (offline, no DB)
        steps.append({
            "name": "workflow_safety",
            "description": "Static checks on GitHub workflow YAML for safety rules.",
            "command": [sys.executable, str(_scripts_ci / "assert_workflow_safety.py")],
            "skip": False,
            "mode": "offline",
        })

        # Gate 2: Migration preflight (offline)
        migration_cmd = [sys.executable, str(_scripts_ci / "migration_preflight.py")]
        if cfg.allow_destructive_migrations:
            migration_cmd.append("--allow-destructive")
        steps.append({
            "name": "migration_preflight",
            "description": "Scan migration scripts for destructive patterns; check Alembic heads.",
            "command": migration_cmd,
            "skip": False,
            "mode": "offline",
        })

        # Gate 3: Release metadata (offline, writes to tmp)
        meta_out = str(ROOT / "rehearsal-release-metadata.json")
        steps.append({
            "name": "release_metadata",
            "description": "Generate immutable release metadata JSON (no secrets).",
            "command": [
                sys.executable,
                str(_scripts_ci / "release_metadata.py"),
                "--out", meta_out,
            ],
            "skip": False,
            "mode": "offline",
        })

        # Gate 4: Postgres backup — skip in dry_run (requires live DB + pg_dump)
        backup_cmd = [
            sys.executable,
            str(_scripts / "backup_postgres.py"),
            "--dest-dir", cfg.backup_dest,
            "--json",
        ]
        steps.append({
            "name": "backup_postgres",
            "description": "pg_dump backup of disposable database to backup_dest.",
            "command": backup_cmd,
            "skip": cfg.dry_run,
            "mode": "dry_run" if cfg.dry_run else "live",
            "note": "Skipped in dry_run. Set DATABASE_URL in env before live run.",
        })

        # Gate 5: Uploads backup — skip in dry_run
        uploads_cmd = [
            sys.executable,
            str(_scripts / "backup_uploads.py"),
            "--source-dir", cfg.uploads_source,
            "--dest-dir", cfg.backup_dest,
            "--json",
        ]
        steps.append({
            "name": "backup_uploads",
            "description": "Archive property media uploads.",
            "command": uploads_cmd,
            "skip": cfg.dry_run,
            "mode": "dry_run" if cfg.dry_run else "live",
        })

        # Gate 6: Restore drill — skip in dry_run (requires pg_restore + live DB)
        # Use the explicit --backup-dump path; no implicit "latest" selection.
        dump_arg = cfg.backup_dump if cfg.backup_dump else "<supply --backup-dump in live mode>"
        restore_cmd = [
            sys.executable,
            str(_scripts / "restore_postgres.py"),
            "--dump", dump_arg,
            "--target-db", cfg.target_db,
            "--drop-target-if-exists",
            "--json",
        ]
        steps.append({
            "name": "restore_drill",
            "description": "pg_restore into disposable target_db (not live app DB).",
            "command": restore_cmd,
            "skip": cfg.dry_run,
            "mode": "dry_run" if cfg.dry_run else "live",
            "note": "Skipped in dry_run. Application DATABASE_URL never modified automatically.",
        })

        # Gate 7: Health / readiness smoke — offline mock in dry_run
        smoke_cmd = [
            sys.executable,
            str(_scripts_ci / "browser_smoke.py"),
            "--base-url", cfg.base_url,
        ]
        steps.append({
            "name": "health_smoke",
            "description": "HTTP smoke check of /healthz, /readyz, and key routes.",
            "command": smoke_cmd,
            "skip": cfg.dry_run,
            "mode": "dry_run" if cfg.dry_run else "live",
            "note": "Skipped in dry_run (no running app). Use live mode with local app.",
        })

        return steps

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """Execute the rehearsal gates and return a structured report."""
        cfg = self._cfg

        # Guard: non-dry live execution requires explicit live=True
        if not cfg.dry_run and not cfg.live:
            raise RehearsalRefused(
                "Live execution requires explicit live=True (--live on CLI). "
                "Use dry_run=True for plan-only mode."
            )

        steps = self.plan()
        start = time.monotonic()

        if cfg.dry_run:
            # Plan mode: no subprocess, annotate all steps as planned
            for step in steps:
                step["result"] = "planned"
            return {
                "ok": True,
                "mode": "dry_run",
                "target_db": cfg.target_db,
                "target_host": cfg.target_host,
                "base_url": cfg.base_url,
                "steps": steps,
                "duration_seconds": round(time.monotonic() - start, 3),
                "note": "dry_run: no subprocesses invoked. Switch to live=True for execution.",
            }

        # Live mode: execute non-skipped gates via runner
        overall_ok = True
        for step in steps:
            if step.get("skip"):
                step["result"] = "skipped"
                continue

            rc, stdout, stderr = self._runner(step["command"], None)
            step["rc"] = rc
            step["stdout"] = sanitize_output((stdout or "")[:2000])
            step["stderr"] = sanitize_output((stderr or "")[:500])
            step["result"] = "pass" if rc == 0 else "fail"
            if rc != 0:
                overall_ok = False

        return {
            "ok": overall_ok,
            "mode": "live",
            "target_db": cfg.target_db,
            "target_host": cfg.target_host,
            "base_url": cfg.base_url,
            "steps": steps,
            "duration_seconds": round(time.monotonic() - start, 3),
        }


# ---------------------------------------------------------------------------
# Default runner (real subprocess — only reached in live mode)
# ---------------------------------------------------------------------------

def _default_runner(cmd: list[str], env: dict | None) -> tuple[int, str, str]:
    import subprocess

    try:
        proc = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 1, "", str(exc)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Staging release rehearsal coordinator (Track A). "
                    "Use --plan or --dry-run for safe offline operation."
    )
    p.add_argument("--opt-in", action="store_true",
                   help="Explicit consent that this targets a local/disposable environment.")
    p.add_argument("--target-db", required=True,
                   help="Disposable database name for restore drill.")
    p.add_argument("--target-host", default="127.0.0.1",
                   help="Database host (must be local/disposable, default 127.0.0.1).")
    p.add_argument("--target-port", type=int, default=5432)
    p.add_argument("--backup-dest", required=True,
                   help="Directory for backup artifacts.")
    p.add_argument("--uploads-source", required=True,
                   help="Uploads directory to archive.")
    p.add_argument("--base-url", default="http://127.0.0.1:8000",
                   help="Application base URL for smoke checks.")
    p.add_argument("--plan", action="store_true",
                   help="Print the ordered gate plan as JSON and exit (no execution).")
    p.add_argument("--dry-run", action="store_true",
                   help="Run in dry_run mode: validates config, returns plan report, "
                        "no subprocess calls. Safe; requires no external binaries.")
    p.add_argument("--live", action="store_true",
                   help="Enable live subprocess execution (requires --opt-in and local target).")
    p.add_argument("--backup-dump", default="",
                   help="Path to pg_dump -Fc archive for restore drill "
                        "(required in --live mode; ignored in plan/dry-run).")
    p.add_argument("--allow-destructive-migrations", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Default to dry_run if neither --plan nor --live given
    dry_run = args.dry_run or (not args.live)

    cfg = RehearsalConfig(
        target_db=args.target_db,
        target_host=args.target_host,
        target_port=args.target_port,
        backup_dest=args.backup_dest,
        uploads_source=args.uploads_source,
        base_url=args.base_url,
        opt_in=args.opt_in,
        dry_run=dry_run,
        live=args.live,
        backup_dump=args.backup_dump,
        allow_destructive_migrations=args.allow_destructive_migrations,
    )

    try:
        coord = RehearsalCoordinator(cfg)
    except RehearsalRefused as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.plan:
        steps = coord.plan()
        print(json.dumps({"steps": steps}, indent=2))
        return 0

    try:
        report = coord.run()
    except RehearsalRefused as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
