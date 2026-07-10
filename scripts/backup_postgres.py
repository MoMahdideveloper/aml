#!/usr/bin/env python3
"""PostgreSQL logical backup wrapper (custom format) for Track A CRM.

Connection settings come from the environment only (DATABASE_URL or PG*).
Passwords are never placed on the process command line by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse


class BackupError(Exception):
    pass


_PROD_MARKERS = (
    "rds.amazonaws.com",
    "azure.com",
    "cloudsql",
    "production",
    "prod-db",
)


def _redact_url(url: str) -> str:
    try:
        p = urlparse(url)
        host = p.hostname or ""
        db = (p.path or "").lstrip("/")
        return f"{p.scheme}://{p.username or ''}:***@{host}:{p.port or ''}/{db}"
    except Exception:
        return "(unparseable)"


def parse_database_url(url: str) -> dict[str, str]:
    raw = (url or "").strip()
    if not raw:
        raise BackupError("DATABASE_URL is empty")
    lower = raw.lower()
    if lower.startswith("sqlite:"):
        raise BackupError("SQLite URL refused; use scripts/backup_sqlite.py")
    if not (lower.startswith("postgres://") or lower.startswith("postgresql://")):
        raise BackupError("DATABASE_URL must be a postgresql:// URL")

    # Normalize postgres:// → postgresql:// for urlparse
    if lower.startswith("postgres://"):
        raw = "postgresql://" + raw.split("://", 1)[1]

    p = urlparse(raw)
    if not p.hostname:
        raise BackupError("DATABASE_URL missing host")
    db = unquote((p.path or "").lstrip("/"))
    if not db:
        raise BackupError("DATABASE_URL missing database name")

    host_l = (p.hostname or "").lower()
    for marker in _PROD_MARKERS:
        if marker in host_l or marker in db.lower():
            if os.environ.get("ALLOW_PROD_BACKUP", "").strip() != "1":
                raise BackupError(
                    f"Host/db looks production-like ({marker!r}). "
                    "Set ALLOW_PROD_BACKUP=1 only for intentional authorized backups."
                )

    env = {
        "PGHOST": p.hostname,
        "PGPORT": str(p.port or 5432),
        "PGUSER": unquote(p.username or ""),
        "PGDATABASE": db,
    }
    if p.password is not None:
        env["PGPASSWORD"] = unquote(p.password)
    return env


def build_pg_env() -> dict[str, str]:
    """Build env for pg_dump/pg_restore without putting secrets on argv."""
    base = os.environ.copy()
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        pg = parse_database_url(url)
        base.update(pg)
        return base
    # Fall back to PG* already in environment
    required = ("PGHOST", "PGUSER", "PGDATABASE")
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise BackupError(
            "Set DATABASE_URL or PGHOST/PGUSER/PGDATABASE (and PGPASSWORD if needed). "
            f"Missing: {', '.join(missing)}"
        )
    return base


def require_bin(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise BackupError(f"Required binary not found on PATH: {name}")
    return path


def tool_version(bin_path: str) -> str:
    try:
        out = subprocess.run(
            [bin_path, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        return (out.stdout or out.stderr or "").strip().splitlines()[0] if (out.stdout or out.stderr) else "unknown"
    except Exception as exc:  # noqa: BLE001
        return f"unknown ({exc})"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="pg_dump -Fc wrapper; connection from env only."
    )
    parser.add_argument(
        "--dest-dir",
        required=True,
        help="Explicit output directory for dump + metadata (e.g. ./backups).",
    )
    parser.add_argument(
        "--prefix",
        default="gptvli-postgres",
        help="Filename prefix (default: gptvli-postgres).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable summary (no secrets).",
    )
    args = parser.parse_args(argv)

    try:
        dest_dir = Path(args.dest_dir).expanduser().resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)

        dump_bin = require_bin("pg_dump")
        restore_bin = require_bin("pg_restore")
        env = build_pg_env()

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dump_path = dest_dir / f"{args.prefix}-{stamp}.dump"
        meta_path = dest_dir / f"{args.prefix}-{stamp}.meta.json"
        tmp_path = dump_path.with_suffix(dump_path.suffix + ".tmp")

        if dump_path.exists():
            raise BackupError(f"Refusing to overwrite existing file: {dump_path}")

        # Command line: no password, no full URL
        cmd = [
            dump_bin,
            "-Fc",
            "--no-password",
            "-f",
            str(tmp_path),
        ]
        # Optional: pin database via env only (PGDATABASE already set)

        proc = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )
        if proc.returncode != 0:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            # Never echo env; stderr may occasionally contain host — still avoid password
            err = (proc.stderr or proc.stdout or "").strip()
            err = err.replace(env.get("PGPASSWORD", ""), "***") if env.get("PGPASSWORD") else err
            raise BackupError(f"pg_dump failed (exit {proc.returncode}): {err[:500]}")

        if not tmp_path.is_file() or tmp_path.stat().st_size == 0:
            tmp_path.unlink(missing_ok=True)
            raise BackupError("pg_dump produced empty output")

        # Verify archive listing
        list_proc = subprocess.run(
            [restore_bin, "--list", str(tmp_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if list_proc.returncode != 0:
            tmp_path.unlink(missing_ok=True)
            raise BackupError(
                f"pg_restore --list failed (exit {list_proc.returncode}); backup discarded"
            )
        list_lines = [
            ln for ln in (list_proc.stdout or "").splitlines() if ln.strip() and not ln.startswith(";")
        ]
        if len(list_lines) < 1:
            tmp_path.unlink(missing_ok=True)
            raise BackupError("pg_restore --list returned no TOC entries; backup discarded")

        tmp_path.replace(dump_path)
        digest = sha256_file(dump_path)
        side = dump_path.with_suffix(dump_path.suffix + ".sha256")
        side.write_text(f"{digest}  {dump_path.name}\n", encoding="utf-8")

        meta = {
            "ok": True,
            "created_at_utc": stamp,
            "format": "custom",
            "pg_dump": tool_version(dump_bin),
            "pg_restore": tool_version(restore_bin),
            "dump_file": str(dump_path),
            "checksum_sha256": digest,
            "bytes": dump_path.stat().st_size,
            "toc_entries_listed": len(list_lines),
            "connection": {
                "host": env.get("PGHOST"),
                "port": env.get("PGPORT"),
                "user": env.get("PGUSER"),
                "database": env.get("PGDATABASE"),
                # password never recorded
            },
            "database_url_redacted": _redact_url(os.environ.get("DATABASE_URL", ""))
            if os.environ.get("DATABASE_URL")
            else None,
        }
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

        if args.json:
            print(json.dumps(meta, indent=2))
        else:
            print(f"OK backup: {dump_path}")
            print(f"Checksum:  {side}")
            print(f"Metadata:  {meta_path}")
            print(f"TOC items: {len(list_lines)}")
            print(f"Size:      {meta['bytes']} bytes")
        return 0
    except BackupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: unexpected failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
