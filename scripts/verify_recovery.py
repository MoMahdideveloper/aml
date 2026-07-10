#!/usr/bin/env python3
"""Machine-readable recovery verification for a SQLite CRM database.

Does not print customer PII — only structural metrics and status codes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
_ROOT = _SCRIPTS.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlite_backup_lib import (  # noqa: E402
    BackupError,
    alembic_revision,
    foreign_key_violations,
    integrity_check,
    list_user_tables,
    refuse_prod_looking_path,
    resolve_sqlite_path,
    user_table_row_counts,
)

# Core Track A tables expected after a full schema is present.
REQUIRED_TABLES = frozenset(
    {
        "properties",
        "agents",
        "customers",
        "deals",
        "tasks",
        "property_images",
        "dashboard_stat_snapshots",
    }
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verify a restored SQLite CRM database.")
    p.add_argument("--database", required=True, help="Path or sqlite:/// URL to check")
    p.add_argument(
        "--expected-alembic",
        default=None,
        help="Fail if alembic_version != this revision (when table exists).",
    )
    p.add_argument(
        "--min-tables",
        type=int,
        default=1,
        help="Minimum user tables required (default 1).",
    )
    p.add_argument(
        "--check-readyz",
        action="store_true",
        help="Boot app against this DB and GET /readyz (synthetic env only).",
    )
    p.add_argument("--json", action="store_true", default=True)
    return p.parse_args(argv)


def verify(database: str, *, expected_alembic: str | None = None, min_tables: int = 1) -> dict:
    path = resolve_sqlite_path(database)
    refuse_prod_looking_path(path, label="database")
    result: dict = {
        "ok": True,
        "database": str(path),
        "errors": [],
        "warnings": [],
        "alembic_revision": None,
        "tables": [],
        "row_counts": {},
        "foreign_key_violations": 0,
        "dashboard_snapshot_dup_days": 0,
        "required_tables_missing": [],
    }

    try:
        integrity_check(path)
        result["integrity_check"] = "ok"
    except BackupError as exc:
        result["ok"] = False
        result["errors"].append(str(exc))
        result["integrity_check"] = "failed"
        return result

    tables = list_user_tables(path)
    result["tables"] = tables
    if len(tables) < min_tables:
        result["ok"] = False
        result["errors"].append(f"Expected at least {min_tables} tables, found {len(tables)}")

    missing = sorted(REQUIRED_TABLES - set(tables))
    # Only hard-fail required tables if alembic present (migrated schema)
    rev = alembic_revision(path)
    result["alembic_revision"] = rev
    if rev:
        result["required_tables_missing"] = missing
        if missing:
            result["ok"] = False
            result["errors"].append(f"Missing required tables: {', '.join(missing)}")
    elif missing:
        result["warnings"].append(
            f"Alembic revision missing; skipped required-table hard fail. Missing if expected: {missing}"
        )

    if expected_alembic:
        if rev != expected_alembic:
            result["ok"] = False
            result["errors"].append(
                f"Alembic mismatch: got {rev!r}, expected {expected_alembic!r}"
            )

    counts = user_table_row_counts(path)
    # Never include row contents — counts only
    result["row_counts"] = counts

    fks = foreign_key_violations(path)
    result["foreign_key_violations"] = len(fks)
    if fks:
        result["ok"] = False
        # Do not include rowids that might map to sensitive rows in free text logs — count only
        result["errors"].append(f"Foreign key violations: {len(fks)}")

    # Dashboard snapshot uniqueness by calendar day (timestamp date part)
    if "dashboard_stat_snapshots" in counts:
        import sqlite3

        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            dup = conn.execute(
                """
                SELECT COUNT(*) FROM (
                  SELECT date(timestamp) AS d, COUNT(*) AS c
                  FROM dashboard_stat_snapshots
                  GROUP BY date(timestamp)
                  HAVING c > 1
                )
                """
            ).fetchone()[0]
            result["dashboard_snapshot_dup_days"] = int(dup)
            if dup:
                result["warnings"].append(
                    f"dashboard_stat_snapshots has {dup} day(s) with multiple rows"
                )
        except sqlite3.Error as exc:
            result["warnings"].append(f"snapshot uniqueness check skipped: {exc}")
        finally:
            conn.close()

    return result


def check_readyz(database_path: Path) -> dict:
    """Boot Flask against disposable DB; report readiness only."""
    os.environ["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    os.environ.setdefault("SESSION_SECRET", "verify-recovery-disposable-secret-not-prod")
    os.environ.setdefault("FLASK_ENV", "testing")
    os.environ.setdefault("ENABLE_CSRF", "0")
    # Import after env set
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    hz = client.get("/healthz")
    rz = client.get("/readyz")
    return {
        "healthz_status": hz.status_code,
        "readyz_status": rz.status_code,
        "readyz_ok": rz.status_code == 200,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = verify(
            args.database,
            expected_alembic=args.expected_alembic,
            min_tables=args.min_tables,
        )
        if args.check_readyz and report.get("integrity_check") == "ok":
            path = resolve_sqlite_path(args.database)
            try:
                report["app_probe"] = check_readyz(path)
                if not report["app_probe"].get("readyz_ok"):
                    report["ok"] = False
                    report["errors"].append("/readyz did not return 200")
            except Exception as exc:  # noqa: BLE001
                report["ok"] = False
                report["errors"].append(f"app probe failed: {exc}")

        print(json.dumps(report, indent=2))
        return 0 if report.get("ok") else 1
    except BackupError as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "errors": [f"unexpected: {exc}"]}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
