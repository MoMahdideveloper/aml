"""Validation tests for Postgres backup wrapper (no real prod; skip if no pg_dump)."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import backup_postgres as bp  # noqa: E402


def test_parse_rejects_sqlite():
    with pytest.raises(bp.BackupError, match="SQLite"):
        bp.parse_database_url("sqlite:///foo.db")


def test_parse_requires_db_name():
    with pytest.raises(bp.BackupError):
        bp.parse_database_url("postgresql://u:p@localhost:5432/")


def test_parse_sets_pg_env_without_logging_password():
    env = bp.parse_database_url("postgresql://myuser:s3cret@127.0.0.1:5433/drill_db")
    assert env["PGHOST"] == "127.0.0.1"
    assert env["PGPORT"] == "5433"
    assert env["PGUSER"] == "myuser"
    assert env["PGDATABASE"] == "drill_db"
    assert env["PGPASSWORD"] == "s3cret"
    red = bp._redact_url("postgresql://myuser:s3cret@127.0.0.1:5433/drill_db")
    assert "s3cret" not in red
    assert "***" in red


def test_parse_blocks_prod_looking_host_without_allow(monkeypatch):
    monkeypatch.delenv("ALLOW_PROD_BACKUP", raising=False)
    with pytest.raises(bp.BackupError, match="production-like"):
        bp.parse_database_url(
            "postgresql://u:p@mydb.rds.amazonaws.com:5432/app"
        )


def test_parse_allows_prod_marker_with_flag(monkeypatch):
    monkeypatch.setenv("ALLOW_PROD_BACKUP", "1")
    env = bp.parse_database_url(
        "postgresql://u:p@mydb.rds.amazonaws.com:5432/app"
    )
    assert env["PGHOST"] == "mydb.rds.amazonaws.com"


def test_missing_dest_dir_arg():
    # argparse exits 2
    with pytest.raises(SystemExit) as ei:
        bp.main([])
    assert ei.value.code == 2


def test_fails_when_pg_dump_missing(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://u:p@127.0.0.1:5432/drill_only"
    )
    monkeypatch.setattr(bp.shutil, "which", lambda name: None)
    rc = bp.main(["--dest-dir", str(tmp_path)])
    assert rc != 0


@pytest.mark.skipif(not shutil.which("pg_dump") or not shutil.which("pg_restore"), reason="pg client tools not installed")
@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL for live disposable drill")
def test_live_disposable_pg_dump_if_configured(tmp_path):
    """Optional: TEST_DATABASE_URL=postgresql://...@localhost/... disposable only."""
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
    rc = bp.main(["--dest-dir", str(tmp_path), "--json"])
    assert rc == 0
    dumps = list(tmp_path.glob("*.dump"))
    assert dumps
    assert dumps[0].stat().st_size > 0
