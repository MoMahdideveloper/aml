#!/usr/bin/env python3
"""Guarded SQLite restore for Track A CRM (disposable targets by default)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from sqlite_backup_lib import (  # noqa: E402
    BackupError,
    alembic_revision,
    integrity_check,
    online_backup,
    refuse_prod_looking_path,
    resolve_sqlite_path,
    user_table_row_counts,
    verify_checksum_sidecar,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Restore a SQLite backup into a new target (overwrite only with --force)."
    )
    p.add_argument("--backup", required=True, help="Path to backup .db file")
    p.add_argument(
        "--destination",
        required=True,
        help="Destination database path (prefer a new disposable path).",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Allow replacing an existing destination (keeps .rollback copy first).",
    )
    p.add_argument(
        "--require-checksum",
        action="store_true",
        default=True,
        help="Require matching .sha256 sidecar (default: true).",
    )
    p.add_argument(
        "--no-require-checksum",
        action="store_false",
        dest="require_checksum",
        help="Skip checksum sidecar verification.",
    )
    p.add_argument(
        "--expected-alembic",
        default=None,
        help="If set, fail when restored alembic_version != this revision.",
    )
    p.add_argument("--json", action="store_true", help="Machine-readable summary.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    rollback_path: Path | None = None
    try:
        backup = resolve_sqlite_path(args.backup)
        dest = resolve_sqlite_path(args.destination)
        refuse_prod_looking_path(backup, label="backup")
        refuse_prod_looking_path(dest, label="destination")

        if not backup.is_file() or backup.stat().st_size == 0:
            raise BackupError("Backup missing or empty")
        if backup.resolve() == dest.resolve():
            raise BackupError("Backup and destination must differ")

        if args.require_checksum:
            verify_checksum_sidecar(backup)
        integrity_check(backup)

        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if not args.force:
                raise BackupError(
                    f"Destination exists: {dest}. Use a new path or pass --force "
                    "(creates a .rollback copy first)."
                )
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            rollback_path = dest.with_name(dest.name + f".rollback-{stamp}")
            shutil.copy2(dest, rollback_path)

        # Restore via online backup into temp then replace
        online_backup(backup, dest)
        integrity_check(dest)

        rev = alembic_revision(dest)
        if args.expected_alembic and rev != args.expected_alembic:
            # Roll back destination if we had a previous file
            if rollback_path and rollback_path.is_file():
                dest.unlink(missing_ok=True)
                shutil.copy2(rollback_path, dest)
            raise BackupError(
                f"Alembic revision mismatch: got {rev!r}, expected {args.expected_alembic!r}"
            )

        counts = user_table_row_counts(dest)
        summary = {
            "ok": True,
            "backup": str(backup),
            "destination": str(dest),
            "rollback_copy": str(rollback_path) if rollback_path else None,
            "alembic_revision": rev,
            "tables": len(counts),
            "integrity_check": "ok",
        }
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"OK restore: {dest}")
            if rollback_path:
                print(f"Rollback copy: {rollback_path}")
            print(f"Alembic: {rev or '(none)'}")
            print(f"Tables: {len(counts)}")
        return 0
    except BackupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: unexpected failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
