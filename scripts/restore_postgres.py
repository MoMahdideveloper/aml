#!/usr/bin/env python3
"""Guarded PostgreSQL restore into a disposable database.

Connection settings from environment only (never password on argv).
Restores into a *new* database name by default; refuses production-looking
hosts unless ALLOW_PROD_BACKUP=1 (same gate as backup).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

# Reuse backup_postgres helpers
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import backup_postgres as bp  # noqa: E402


class RestoreError(Exception):
    pass


def _require_bin(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RestoreError(f"Required binary not found: {name}")
    return path


def _admin_env(base_env: dict[str, str], maintenance_db: str = "postgres") -> dict[str, str]:
    env = dict(base_env)
    env["PGDATABASE"] = maintenance_db
    return env


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="pg_restore into a fresh disposable database (env credentials only)."
    )
    p.add_argument("--dump", required=True, help="Path to pg_dump -Fc archive")
    p.add_argument(
        "--target-db",
        required=True,
        help="Name of NEW database to create and restore into (not the live app DB name casually).",
    )
    p.add_argument(
        "--maintenance-db",
        default="postgres",
        help="Existing DB used to run CREATE DATABASE (default: postgres).",
    )
    p.add_argument(
        "--drop-target-if-exists",
        action="store_true",
        help="DROP target DB if it already exists (disposable drills only).",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    try:
        dump = Path(args.dump).expanduser().resolve()
        if not dump.is_file() or dump.stat().st_size == 0:
            raise RestoreError(f"Dump missing or empty: {dump}")

        target = (args.target_db or "").strip()
        if not target or not target.replace("_", "").isalnum():
            raise RestoreError("target-db must be a simple identifier (letters/digits/underscore)")
        if target.lower() in {"postgres", "template0", "template1"}:
            raise RestoreError("Refusing to restore into a template/system database name")

        restore_bin = _require_bin("pg_restore")
        psql_bin = _require_bin("psql")
        env = bp.build_pg_env()

        # List archive first
        list_proc = subprocess.run(
            [restore_bin, "--list", str(dump)],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if list_proc.returncode != 0:
            raise RestoreError(f"pg_restore --list failed: {(list_proc.stderr or '')[:400]}")

        admin = _admin_env(env, args.maintenance_db)

        if args.drop_target_if_exists:
            subprocess.run(
                [psql_bin, "-v", "ON_ERROR_STOP=1", "-c", f'DROP DATABASE IF EXISTS "{target}";'],
                env=admin,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

        create = subprocess.run(
            [psql_bin, "-v", "ON_ERROR_STOP=1", "-c", f'CREATE DATABASE "{target}";'],
            env=admin,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if create.returncode != 0:
            err = (create.stderr or create.stdout or "").replace(env.get("PGPASSWORD", ""), "***")
            raise RestoreError(f"CREATE DATABASE failed: {err[:400]}")

        # Restore into new DB (password via env)
        target_env = dict(env)
        target_env["PGDATABASE"] = target
        rest = subprocess.run(
            [
                restore_bin,
                "--no-password",
                "--verbose",
                "-d",
                target,  # database name only, not URL
                str(dump),
            ],
            env=target_env,
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )
        # pg_restore may return 1 with warnings; treat only hard fail
        if rest.returncode not in (0, 1):
            err = (rest.stderr or rest.stdout or "").replace(env.get("PGPASSWORD", ""), "***")
            raise RestoreError(f"pg_restore failed (exit {rest.returncode}): {err[:500]}")

        # Simple connectivity check
        check = subprocess.run(
            [psql_bin, "-d", target, "-v", "ON_ERROR_STOP=1", "-c", "SELECT 1;"],
            env=target_env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if check.returncode != 0:
            raise RestoreError("Post-restore SELECT 1 failed")

        summary = {
            "ok": True,
            "dump": str(dump),
            "target_db": target,
            "host": env.get("PGHOST"),
            "port": env.get("PGPORT"),
            "note": "Application DATABASE_URL not modified; switch only after human approval.",
        }
        if args.json:
            import json

            print(json.dumps(summary, indent=2))
        else:
            print(f"OK restore into database {target!r} on {env.get('PGHOST')}")
            print("Switch application DATABASE_URL only after approval.")
        return 0
    except (RestoreError, bp.BackupError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: unexpected: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
