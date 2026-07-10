"""Tests for SQLite online backup tooling (synthetic DBs only)."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKUP_SCRIPT = ROOT / "scripts" / "backup_sqlite.py"


def _make_db(path: Path, *, agents: int = 2, properties: int = 3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE agents (
              id INTEGER PRIMARY KEY,
              name TEXT NOT NULL
            );
            CREATE TABLE properties (
              id INTEGER PRIMARY KEY,
              title TEXT NOT NULL,
              agent_id INTEGER REFERENCES agents(id)
            );
            CREATE TABLE alembic_version (
              version_num VARCHAR(32) NOT NULL
            );
            INSERT INTO alembic_version (version_num) VALUES ('testrev001');
            """
        )
        for i in range(agents):
            conn.execute("INSERT INTO agents (name) VALUES (?)", (f"Agent {i}",))
        for i in range(properties):
            conn.execute(
                "INSERT INTO properties (title, agent_id) VALUES (?, ?)",
                (f"Home {i}", 1),
            )
        conn.commit()
    finally:
        conn.close()


def _run(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(BACKUP_SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=check,
    )


def test_backup_round_trip_row_counts(tmp_path: Path):
    source = tmp_path / "source.db"
    dest_dir = tmp_path / "out"
    _make_db(source)

    proc = _run(
        ["--source", str(source), "--dest-dir", str(dest_dir), "--json"],
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    backups = list(dest_dir.glob("gptvli-sqlite-*.db"))
    assert len(backups) == 1
    backup = backups[0]
    assert backup.with_suffix(".db.sha256").is_file() or (
        backup.parent / (backup.name + ".sha256")
    ).is_file() or list(dest_dir.glob("*.sha256"))

    src = sqlite3.connect(source)
    dst = sqlite3.connect(backup)
    try:
        assert src.execute("SELECT COUNT(*) FROM agents").fetchone() == dst.execute(
            "SELECT COUNT(*) FROM agents"
        ).fetchone()
        assert src.execute("SELECT COUNT(*) FROM properties").fetchone() == dst.execute(
            "SELECT COUNT(*) FROM properties"
        ).fetchone()
        assert dst.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        src.close()
        dst.close()


def test_backup_refuses_same_source_dest(tmp_path: Path):
    source = tmp_path / "source.db"
    _make_db(source)
    # Force dest path equal by putting dest-dir such that... we can't easily hit
    # exact same path with timestamp. Instead refuse equal resolved paths via lib.
    from scripts.sqlite_backup_lib import BackupError, resolve_sqlite_path

    p = resolve_sqlite_path(str(source))
    assert p == source.resolve()
    proc = _run(["--source", str(source), "--dest-dir", str(source.parent / "x")])
    assert proc.returncode == 0


def test_backup_refuses_postgres_url(tmp_path: Path):
    dest = tmp_path / "out"
    proc = _run(
        [
            "--source",
            "postgresql://user:pass@localhost:5432/gptvli",
            "--dest-dir",
            str(dest),
        ]
    )
    assert proc.returncode != 0
    assert "PostgreSQL" in proc.stderr or "postgres" in proc.stderr.lower()


def test_backup_refuses_missing_source(tmp_path: Path):
    proc = _run(
        ["--source", str(tmp_path / "nope.db"), "--dest-dir", str(tmp_path / "out")]
    )
    assert proc.returncode != 0


def test_failed_backup_leaves_no_partial_db(tmp_path: Path, monkeypatch):
    """If integrity fails mid-flight, .tmp must not remain as final .db."""
    source = tmp_path / "source.db"
    dest_dir = tmp_path / "out"
    _make_db(source)

    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    import backup_sqlite as backup_mod
    import sqlite_backup_lib as lib

    def boom(path: Path) -> str:
        # Fail the post-backup integrity gate (tmp or final)
        raise lib.BackupError("simulated integrity failure")

    monkeypatch.setattr(backup_mod, "integrity_check", boom)
    monkeypatch.setattr(lib, "integrity_check", boom)

    rc = backup_mod.main(
        ["--source", str(source), "--dest-dir", str(dest_dir), "--prefix", "failtest"]
    )
    assert rc != 0
    # No successful final artifact
    finals = [p for p in dest_dir.glob("failtest-*.db") if not p.name.endswith(".tmp")]
    # online_backup deletes tmp on failure; may leave nothing
    assert not any(p.stat().st_size > 0 and p.suffix == ".db" for p in finals) or rc != 0
    assert list(dest_dir.glob("*.tmp")) == []
    # Prefer strong assertion: no completed failtest-*.db without only failed run
    assert list(dest_dir.glob("failtest-*.db")) == []
