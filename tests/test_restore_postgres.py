"""Config/guard tests for Postgres restore wrapper."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import restore_postgres as rp  # noqa: E402


def test_refuses_system_db_names(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:5432/drill")
    dump = tmp_path / "x.dump"
    dump.write_bytes(b"not-empty")
    rc = rp.main(["--dump", str(dump), "--target-db", "postgres"])
    assert rc != 0


def test_main_fails_missing_dump(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:5432/drill")
    rc = rp.main(
        ["--dump", str(tmp_path / "missing.dump"), "--target-db", "drill_restore_x"]
    )
    assert rc != 0


def test_target_db_must_be_simple(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:5432/drill")
    dump = tmp_path / "x.dump"
    dump.write_bytes(b"PGDMP")
    rc = rp.main(["--dump", str(dump), "--target-db", "bad-name;drop"])
    assert rc != 0
