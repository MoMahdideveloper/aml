#!/usr/bin/env python3
"""SQLite online backup for Track A CRM (disposable/local only).

Uses sqlite3.Connection.backup (online backup API), not a raw live file copy.
Never commits dumps; write only under an explicit destination directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as `python scripts/backup_sqlite.py` from repo root
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from backup_lock import BackupLock, BackupLockError  # noqa: E402
from sqlite_backup_lib import (  # noqa: E402
    BackupError,
    integrity_check,
    online_backup,
    refuse_prod_looking_path,
    resolve_sqlite_path,
    user_table_row_counts,
    write_checksum_sidecar,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Create a consistent SQLite backup via the online backup API."
    )
    p.add_argument(
        "--source",
        required=True,
        help="Source SQLite file path or sqlite:/// URL (explicit; no hidden defaults).",
    )
    p.add_argument(
        "--dest-dir",
        required=True,
        help="Directory for timestamped backup (e.g. ./backups or a temp dir).",
    )
    p.add_argument(
        "--prefix",
        default="gptvli-sqlite",
        help="Backup filename prefix (default: gptvli-sqlite).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary on success.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        source = resolve_sqlite_path(args.source)
        dest_dir = Path(args.dest_dir).expanduser().resolve()
        refuse_prod_looking_path(source, label="source")
        refuse_prod_looking_path(dest_dir, label="destination directory")

        if not source.is_file():
            raise BackupError(f"Source not found: {source}")

        dest_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = dest_dir / f"{args.prefix}-{stamp}.db"

        if source.resolve() == dest.resolve():
            raise BackupError("Source and destination must differ")

        if dest.exists():
            raise BackupError(f"Destination already exists: {dest}")

        with BackupLock(dest_dir / ".backup_sqlite.lock"):
            src_counts = user_table_row_counts(source)
            online_backup(source, dest)
            integrity_check(dest)
            dest_counts = user_table_row_counts(dest)
            if src_counts != dest_counts:
                dest.unlink(missing_ok=True)
                raise BackupError(
                    "Row counts differ between source and backup; backup discarded"
                )

            checksum_path = write_checksum_sidecar(dest)
        summary = {
            "ok": True,
            "source": str(source),
            "backup": str(dest),
            "checksum_file": str(checksum_path),
            "bytes": dest.stat().st_size,
            "tables": len(src_counts),
            "row_counts_match": True,
            "integrity_check": "ok",
        }
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"OK backup: {dest}")
            print(f"Checksum:  {checksum_path}")
            print(f"Size:      {summary['bytes']} bytes")
            print(f"Tables:    {summary['tables']} (row counts match source)")
        return 0
    except (BackupError, BackupLockError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"ERROR: unexpected failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
