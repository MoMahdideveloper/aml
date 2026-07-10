"""Uploads archive helper tests."""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "backup_uploads.py"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def test_empty_uploads_ok(tmp_path: Path):
    src = tmp_path / "uploads"
    src.mkdir()
    dest = tmp_path / "out"
    proc = _run(["--source-dir", str(src), "--dest-dir", str(dest), "--json"])
    assert proc.returncode == 0, proc.stderr
    zips = list(dest.glob("gptvli-uploads-*.zip"))
    assert len(zips) == 1


def test_archives_files(tmp_path: Path):
    src = tmp_path / "uploads"
    src.mkdir()
    (src / "a.txt").write_text("hello", encoding="utf-8")
    sub = src / "nested"
    sub.mkdir()
    (sub / "b.bin").write_bytes(b"\x00\x01")
    dest = tmp_path / "out"
    proc = _run(["--source-dir", str(src), "--dest-dir", str(dest)])
    assert proc.returncode == 0, proc.stderr
    zpath = next(dest.glob("*.zip"))
    with zipfile.ZipFile(zpath) as zf:
        names = set(zf.namelist())
    assert "a.txt" in names
    assert "nested/b.bin" in names
    assert list(dest.glob("*.sha256")) or Path(str(zpath) + ".sha256").is_file()
