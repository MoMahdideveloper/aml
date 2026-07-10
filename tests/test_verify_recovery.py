"""Tests for recovery verifier (structural metrics only, no PII dump)."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts" / "verify_recovery.py"


def _make_ok_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE properties (id INTEGER PRIMARY KEY, title TEXT);
            CREATE TABLE agents (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE deals (id INTEGER PRIMARY KEY);
            CREATE TABLE tasks (id INTEGER PRIMARY KEY);
            CREATE TABLE property_images (id INTEGER PRIMARY KEY);
            CREATE TABLE dashboard_stat_snapshots (
              id INTEGER PRIMARY KEY,
              timestamp TEXT
            );
            CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);
            INSERT INTO alembic_version VALUES ('k6l7m8n9o0p1');
            INSERT INTO properties (title) VALUES ('Synthetic');
            INSERT INTO dashboard_stat_snapshots (timestamp) VALUES ('2026-07-10 00:00:00');
            """
        )
        conn.commit()
    finally:
        conn.close()


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VERIFY), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def test_verify_ok_database(tmp_path: Path):
    db = tmp_path / "ok.db"
    _make_ok_db(db)
    proc = _run(["--database", str(db), "--expected-alembic", "k6l7m8n9o0p1"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(proc.stdout)
    assert data["ok"] is True
    assert data["integrity_check"] == "ok"
    assert data["alembic_revision"] == "k6l7m8n9o0p1"
    assert "Synthetic" not in proc.stdout  # no row content leakage
    assert data["row_counts"].get("properties") == 1


def test_verify_fails_corrupt(tmp_path: Path):
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"garbage-not-sqlite")
    proc = _run(["--database", str(bad)])
    assert proc.returncode != 0
    data = json.loads(proc.stdout)
    assert data["ok"] is False


def test_verify_fails_alembic_mismatch(tmp_path: Path):
    db = tmp_path / "ok.db"
    _make_ok_db(db)
    proc = _run(["--database", str(db), "--expected-alembic", "other"])
    assert proc.returncode != 0
    data = json.loads(proc.stdout)
    assert data["ok"] is False
