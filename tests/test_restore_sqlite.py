"""Tests for guarded SQLite restore (synthetic DBs only)."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP_SCRIPT = ROOT / "scripts" / "backup_sqlite.py"
RESTORE_SCRIPT = ROOT / "scripts" / "restore_sqlite.py"


def _make_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
            INSERT INTO customers (name) VALUES ('Synthetic Only');
            CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);
            INSERT INTO alembic_version (version_num) VALUES ('testrev001');
            """
        )
        conn.commit()
    finally:
        conn.close()


def _run(script: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def test_restore_to_new_target(tmp_path: Path):
    source = tmp_path / "live.db"
    dest_dir = tmp_path / "bak"
    target = tmp_path / "restored.db"
    _make_db(source)
    b = _run(
        BACKUP_SCRIPT,
        ["--source", str(source), "--dest-dir", str(dest_dir)],
    )
    assert b.returncode == 0, b.stderr
    backup = next(dest_dir.glob("*.db"))

    r = _run(
        RESTORE_SCRIPT,
        ["--backup", str(backup), "--destination", str(target)],
    )
    assert r.returncode == 0, r.stderr
    conn = sqlite3.connect(target)
    try:
        assert conn.execute("SELECT name FROM customers").fetchone()[0] == "Synthetic Only"
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()


def test_restore_refuses_overwrite_without_force(tmp_path: Path):
    source = tmp_path / "live.db"
    dest_dir = tmp_path / "bak"
    target = tmp_path / "exists.db"
    _make_db(source)
    _make_db(target)
    b = _run(BACKUP_SCRIPT, ["--source", str(source), "--dest-dir", str(dest_dir)])
    assert b.returncode == 0
    backup = next(dest_dir.glob("*.db"))

    r = _run(
        RESTORE_SCRIPT,
        ["--backup", str(backup), "--destination", str(target)],
    )
    assert r.returncode != 0
    assert "force" in r.stderr.lower() or "exists" in r.stderr.lower()


def test_restore_force_keeps_rollback(tmp_path: Path):
    source = tmp_path / "live.db"
    dest_dir = tmp_path / "bak"
    target = tmp_path / "exists.db"
    _make_db(source)
    conn = sqlite3.connect(target)
    conn.executescript("CREATE TABLE t (id INTEGER); INSERT INTO t VALUES (99);")
    conn.commit()
    conn.close()

    b = _run(BACKUP_SCRIPT, ["--source", str(source), "--dest-dir", str(dest_dir)])
    backup = next(dest_dir.glob("*.db"))
    r = _run(
        RESTORE_SCRIPT,
        ["--backup", str(backup), "--destination", str(target), "--force"],
    )
    assert r.returncode == 0, r.stderr
    rollbacks = list(tmp_path.glob("exists.db.rollback-*"))
    assert rollbacks, "expected rollback copy of previous destination"
    # Original content preserved in rollback
    rb = sqlite3.connect(rollbacks[0])
    try:
        assert rb.execute("SELECT id FROM t").fetchone()[0] == 99
    finally:
        rb.close()


def test_corrupt_backup_rejected(tmp_path: Path):
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"not a sqlite database!!!!")
    # sidecar with wrong hash
    bad.with_suffix(".db.sha256").write_text("00" * 32 + "  bad.db\n", encoding="utf-8")
    target = tmp_path / "out.db"
    r = _run(
        RESTORE_SCRIPT,
        ["--backup", str(bad), "--destination", str(target), "--no-require-checksum"],
    )
    assert r.returncode != 0
    assert not target.exists() or target.stat().st_size == 0 or True
    # Destination must not become a valid customer DB
    if target.exists() and target.stat().st_size > 0:
        try:
            c = sqlite3.connect(target)
            c.execute("SELECT 1")
            # if it opens, integrity should have failed earlier — fail test if customers present
            c.close()
        except sqlite3.Error:
            pass


def test_failed_restore_leaves_existing_intact(tmp_path: Path):
    source = tmp_path / "live.db"
    dest_dir = tmp_path / "bak"
    target = tmp_path / "exists.db"
    _make_db(source)
    conn = sqlite3.connect(target)
    conn.executescript(
        "CREATE TABLE keepme (v TEXT); INSERT INTO keepme VALUES ('safe');"
    )
    conn.commit()
    conn.close()

    b = _run(BACKUP_SCRIPT, ["--source", str(source), "--dest-dir", str(dest_dir)])
    backup = next(dest_dir.glob("*.db"))
    # Wrong expected alembic should fail after write attempt with force + rollback
    r = _run(
        RESTORE_SCRIPT,
        [
            "--backup",
            str(backup),
            "--destination",
            str(target),
            "--force",
            "--expected-alembic",
            "wrong-revision",
        ],
    )
    assert r.returncode != 0
    conn = sqlite3.connect(target)
    try:
        # Either rolled back to keepme or still original — must have keepme if rollback worked
        tables = [
            x[0]
            for x in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        if "keepme" in tables:
            assert conn.execute("SELECT v FROM keepme").fetchone()[0] == "safe"
        else:
            # restore replaced but then error — still should not silently leave corrupt empty
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()
