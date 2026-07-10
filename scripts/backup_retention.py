#!/usr/bin/env python3
"""Retention cleanup for local backup directories (dry-run by default).

Does not enable any OS scheduler. Safe to run with --dry-run to list actions.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply age/count retention to a backup directory.")
    p.add_argument("--dir", required=True, help="Backup directory (e.g. ./backups)")
    p.add_argument(
        "--keep-count",
        type=int,
        default=7,
        help="Keep the newest N backup files matching --glob (default 7).",
    )
    p.add_argument(
        "--max-age-days",
        type=float,
        default=None,
        help="Also delete files older than this many days (optional).",
    )
    p.add_argument(
        "--glob",
        default="gptvli-*.db",
        help="Glob for primary backup files (default: gptvli-*.db).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="List actions without deleting (default: true).",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete files (turns off dry-run).",
    )
    p.add_argument("--json", action="store_true")
    return p.parse_args(argv)


def plan_deletions(
    directory: Path,
    *,
    keep_count: int,
    max_age_days: float | None,
    pattern: str,
) -> list[Path]:
    if keep_count < 0:
        raise ValueError("keep-count must be >= 0")
    files = sorted(
        [p for p in directory.glob(pattern) if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    to_delete: set[Path] = set()
    if keep_count < len(files):
        to_delete.update(files[keep_count:])
    if max_age_days is not None:
        cutoff = time.time() - (max_age_days * 86400)
        for p in files:
            if p.stat().st_mtime < cutoff:
                to_delete.add(p)
    # Also drop sidecar checksum/meta for deleted primaries
    sidecars: list[Path] = []
    for p in sorted(to_delete):
        for side in (
            p.with_suffix(p.suffix + ".sha256"),
            Path(str(p) + ".sha256"),
            p.with_suffix(".meta.json")
            if p.suffix != ".dump"
            else p.with_name(p.name.replace(".dump", ".meta.json")),
        ):
            if side.is_file():
                sidecars.append(side)
        # meta next to dump: name.dump → name.meta.json pattern used by postgres script
        if p.suffix == ".dump":
            meta = p.with_name(p.name[: -len(".dump")] + ".meta.json")
            if meta.is_file():
                sidecars.append(meta)
        sha = Path(str(p) + ".sha256")
        if sha.is_file():
            sidecars.append(sha)
    return sorted(set(to_delete) | set(sidecars), key=lambda p: str(p))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    dry = not args.execute
    try:
        directory = Path(args.dir).expanduser().resolve()
        if not directory.is_dir():
            print(f"ERROR: not a directory: {directory}", file=sys.stderr)
            return 1
        planned = plan_deletions(
            directory,
            keep_count=args.keep_count,
            max_age_days=args.max_age_days,
            pattern=args.glob,
        )
        actions = []
        for path in planned:
            actions.append({"path": str(path), "action": "delete" if not dry else "would_delete"})
            if not dry:
                path.unlink(missing_ok=True)

        summary = {
            "ok": True,
            "dry_run": dry,
            "dir": str(directory),
            "keep_count": args.keep_count,
            "max_age_days": args.max_age_days,
            "glob": args.glob,
            "actions": actions,
            "count": len(actions),
        }
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            mode = "DRY-RUN" if dry else "EXECUTE"
            print(f"{mode}: {len(actions)} file(s) under {directory}")
            for a in actions:
                print(f"  {a['action']}: {a['path']}")
            if dry and actions:
                print("Re-run with --execute to delete.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
