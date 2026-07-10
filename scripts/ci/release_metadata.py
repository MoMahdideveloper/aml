#!/usr/bin/env python3
"""Generate immutable release metadata JSON for Track A artifacts.

Does not include secrets or customer data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _git(*args: str) -> str:
    try:
        out = subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="replace").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _alembic_heads() -> list[str]:
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config()
        cfg.set_main_option("script_location", str(ROOT / "migrations"))
        return list(ScriptDirectory.from_config(cfg).get_heads())
    except Exception:
        return []


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--image-tag", default="")
    args = parser.parse_args()

    sha = _git("rev-parse", "HEAD") or os.environ.get("GITHUB_SHA", "unknown")
    short = sha[:12] if sha != "unknown" else "unknown"
    meta = {
        "schema_version": 1,
        "track": "A",
        "product": "platinum-heritage-crm",
        "git_sha": sha,
        "git_sha_short": short,
        "git_ref": _git("rev-parse", "--abbrev-ref", "HEAD")
        or os.environ.get("GITHUB_REF", ""),
        "built_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python_requires": "3.11",
        "node_requires": "20",
        "migration_heads": _alembic_heads(),
        "requirements_sha256": _file_sha256(ROOT / "requirements.txt"),
        "package_lock_sha256": _file_sha256(ROOT / "package-lock.json"),
        "image_tag": args.image_tag or f"gptvli-web:{short}",
        "ci_run_url": os.environ.get("GITHUB_SERVER_URL", "")
        + (
            f"/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
            if os.environ.get("GITHUB_RUN_ID")
            else ""
        ),
        "notes": "Immutable metadata only — no secrets or customer data.",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"wrote={args.out}")
    print(f"git_sha={short}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
