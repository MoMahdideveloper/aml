#!/usr/bin/env python3
"""Archive property media uploads for Track A (separate from DB dumps).

Never walks chroma_db, graphify-out, node_modules, or Stitch export trees.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from backup_lock import BackupLock, BackupLockError  # noqa: E402


class UploadsBackupError(Exception):
    pass


_BLOCKED_PARTS = {
    "chroma_db",
    "graphify-out",
    "node_modules",
    "stitch_kpi_performance_dashboard",
    ".git",
}


def _assert_safe_tree(root: Path) -> None:
    resolved = root.resolve()
    for part in resolved.parts:
        if part in _BLOCKED_PARTS:
            raise UploadsBackupError(f"Refusing to archive blocked path component: {part}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Backup static uploads directory.")
    p.add_argument(
        "--source-dir",
        required=True,
        help="Uploads root (e.g. ./static/uploads).",
    )
    p.add_argument(
        "--dest-dir",
        required=True,
        help="Output directory for archive (e.g. ./backups).",
    )
    p.add_argument(
        "--format",
        choices=("zip", "tar.gz"),
        default="zip",
        help="Archive format (default zip).",
    )
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    try:
        source = Path(args.source_dir).expanduser().resolve()
        dest_dir = Path(args.dest_dir).expanduser().resolve()
        _assert_safe_tree(source)
        _assert_safe_tree(dest_dir)

        if source.exists() and not source.is_dir():
            raise UploadsBackupError(f"Source is not a directory: {source}")

        dest_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        suffix = "zip" if args.format == "zip" else "tar.gz"
        out = dest_dir / f"gptvli-uploads-{stamp}.{suffix}"
        tmp = out.with_suffix(out.suffix + ".tmp")
        if tmp.exists():
            tmp.unlink()

        file_count = 0
        with BackupLock(dest_dir / ".backup_uploads.lock"):
            if not source.exists() or not any(source.rglob("*")):
                # Empty archive is success
                if args.format == "zip":
                    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr("README.txt", "Empty uploads directory at backup time.\n")
                else:
                    with tarfile.open(tmp, "w:gz") as tf:
                        pass
                file_count = 0
            else:
                if args.format == "zip":
                    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        for path in source.rglob("*"):
                            if path.is_file():
                                # skip blocked subpaths if any
                                if any(part in _BLOCKED_PARTS for part in path.parts):
                                    continue
                                arc = path.relative_to(source).as_posix()
                                zf.write(path, arcname=arc)
                                file_count += 1
                else:
                    with tarfile.open(tmp, "w:gz") as tf:
                        for path in source.rglob("*"):
                            if path.is_file() and not any(
                                part in _BLOCKED_PARTS for part in path.parts
                            ):
                                tf.add(path, arcname=path.relative_to(source).as_posix())
                                file_count += 1

            if not tmp.is_file():
                raise UploadsBackupError("Archive not created")
            tmp.replace(out)
            digest = _sha256(out)
            side = Path(str(out) + ".sha256")
            side.write_text(f"{digest}  {out.name}\n", encoding="utf-8")

        summary = {
            "ok": True,
            "source_dir": str(source),
            "archive": str(out),
            "checksum_file": str(side),
            "files_archived": file_count,
            "bytes": out.stat().st_size,
            "note": "Restore uploads after DB restore; pair artifacts by timestamp.",
        }
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"OK uploads backup: {out}")
            print(f"Files: {file_count}, size: {summary['bytes']}")
        return 0
    except (UploadsBackupError, BackupLockError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: unexpected: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
