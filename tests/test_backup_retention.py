"""Retention planner tests (temporary directories only)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from backup_retention import main, plan_deletions  # noqa: E402


def test_keep_count_dry_run(tmp_path: Path):
    for i in range(5):
        p = tmp_path / f"gptvli-sqlite-00{i}.db"
        p.write_bytes(b"x")
        # distinct mtimes
        time.sleep(0.02)
        os_utime = p.stat()
        # bump mtime artificially
        Path(p).touch()
        time.sleep(0.01)

    planned = plan_deletions(tmp_path, keep_count=2, max_age_days=None, pattern="gptvli-*.db")
    # newest 2 kept → 3 primaries deleted (+ possible sidecars none)
    primaries = [p for p in planned if p.suffix == ".db"]
    assert len(primaries) == 3

    rc = main(["--dir", str(tmp_path), "--keep-count", "2", "--dry-run", "--json"])
    assert rc == 0
    assert list(tmp_path.glob("gptvli-*.db")).__len__() == 5  # dry-run keeps all


def test_execute_deletes(tmp_path: Path):
    for i in range(4):
        (tmp_path / f"gptvli-sqlite-{i}.db").write_bytes(b"data")
        time.sleep(0.02)
    rc = main(["--dir", str(tmp_path), "--keep-count", "1", "--execute", "--json"])
    assert rc == 0
    left = list(tmp_path.glob("gptvli-*.db"))
    assert len(left) == 1
