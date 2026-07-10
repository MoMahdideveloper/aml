"""Shared helpers for SQLite backup/restore/verify (Track A, disposable only)."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

# Reject destinations that look like production host data dirs (defense in depth).
_PROD_PATH_MARKERS = (
    "/var/lib/postgresql",
    "\\var\\lib\\postgresql",
    "/data/postgres",
    "production",
    "prod-db",
    "rds.amazonaws.com",
)


class BackupError(Exception):
    """Operational failure for backup/restore tooling."""


def resolve_sqlite_path(url_or_path: str) -> Path:
    """Resolve a SQLite file path from a filesystem path or sqlite URL."""
    raw = (url_or_path or "").strip()
    if not raw:
        raise BackupError("Empty SQLite path or URL")

    lower = raw.lower()
    if lower.startswith("postgres://") or lower.startswith("postgresql://"):
        raise BackupError("PostgreSQL URL refused; use Postgres backup tooling instead")

    if lower.startswith("sqlite:"):
        # sqlite:///relative or sqlite:////absolute or sqlite:///:memory:
        if ":memory:" in lower:
            raise BackupError("In-memory SQLite cannot be backed up to a file")
        # Strip scheme
        rest = raw.split("sqlite:", 1)[1]
        if rest.startswith("///"):
            # sqlite:///path or sqlite:////abs
            path_part = rest[3:]  # after ///
            if path_part.startswith("/") and len(path_part) > 1 and path_part[1] != "/":
                # Unix absolute: /tmp/x from sqlite:////tmp/x is ////tmp -> ///tmp after [3:]
                pass
            path_part = unquote(path_part)
            # Windows: sqlite:///C:/foo -> C:/foo
            p = Path(path_part)
            if not p.is_absolute() and not (len(path_part) > 1 and path_part[1] == ":"):
                p = Path.cwd() / p
            return p.resolve()
        if rest.startswith("//"):
            # sqlite://hostname/path — uncommon; treat host empty
            parsed = urlparse(raw)
            path_part = unquote(parsed.path or "")
            if path_part.startswith("/") and len(path_part) > 2 and path_part[2] == ":":
                path_part = path_part.lstrip("/")
            p = Path(path_part)
            return p.resolve() if p.is_absolute() else (Path.cwd() / p).resolve()
        raise BackupError(f"Unrecognized SQLite URL: {raw!r}")

    p = Path(raw).expanduser()
    return p.resolve() if p.is_absolute() else (Path.cwd() / p).resolve()


def refuse_prod_looking_path(path: Path, *, label: str) -> None:
    text = str(path).replace("\\", "/").lower()
    for marker in _PROD_PATH_MARKERS:
        if marker.lower().replace("\\", "/") in text:
            raise BackupError(
                f"{label} path looks production-like ({marker!r}); "
                "use an explicit disposable path under a local backups/ or temp directory"
            )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_checksum_sidecar(path: Path) -> Path:
    digest = sha256_file(path)
    side = path.with_suffix(path.suffix + ".sha256")
    side.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return side


def verify_checksum_sidecar(path: Path) -> str:
    side = path.with_suffix(path.suffix + ".sha256")
    if not side.is_file():
        raise BackupError(f"Missing checksum sidecar: {side}")
    line = side.read_text(encoding="utf-8").strip().split()
    if not line:
        raise BackupError(f"Empty checksum sidecar: {side}")
    expected = line[0].lower()
    actual = sha256_file(path).lower()
    if expected != actual:
        raise BackupError("Checksum mismatch: file may be corrupt or tampered")
    return actual


def integrity_check(db_path: Path) -> str:
    if not db_path.is_file() or db_path.stat().st_size == 0:
        raise BackupError(f"Database missing or empty: {db_path}")
    uri = db_path.resolve().as_uri()
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        result = (row[0] if row else "") or ""
        if result.lower() != "ok":
            raise BackupError(f"integrity_check failed for {db_path}: {result}")
        return result
    finally:
        conn.close()


def user_table_row_counts(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        counts: dict[str, int] = {}
        for name in tables:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                continue
            counts[name] = int(conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0])
        return counts
    finally:
        conn.close()


def alembic_revision(db_path: Path) -> str | None:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        ).fetchone()
        if not row:
            return None
        ver = conn.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
        return ver[0] if ver else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def online_backup(source: Path, dest: Path) -> None:
    """Copy source -> dest using SQLite online backup API (consistent snapshot)."""
    if not source.is_file():
        raise BackupError(f"Source database not found: {source}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Atomic: write temp then replace
    tmp = dest.with_name(dest.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    try:
        src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        try:
            dst = sqlite3.connect(tmp)
            try:
                src.backup(dst)
                dst.commit()
            finally:
                dst.close()
        finally:
            src.close()

        integrity_check(tmp)
        # Replace destination only after success
        if dest.exists():
            dest.unlink()
        tmp.replace(dest)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def foreign_key_violations(db_path: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        rows = conn.execute("PRAGMA foreign_key_check").fetchall()
        # table, rowid, parent, fkid
        return [
            {"table": r[0], "rowid": r[1], "parent": r[2], "fkid": r[3]} for r in rows
        ]
    finally:
        conn.close()


def list_user_tables(db_path: Path) -> list[str]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
    finally:
        conn.close()
