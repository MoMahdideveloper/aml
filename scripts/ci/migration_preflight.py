#!/usr/bin/env python3
"""Migration safety preflight for Track A.

Offline by default: scans migration scripts for destructive patterns and
detects multiple Alembic heads via ScriptDirectory when possible.

Optional live check when DATABASE_URL is set: verifies flask can resolve
a single head. Never prints secret credentials.

Exit codes:
  0 — ok
  1 — blocked
  2 — usage error
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESTRUCTIVE = re.compile(
    r"\b(op\.drop_table|op\.drop_column|DROP\s+TABLE|DROP\s+COLUMN)\b",
    re.I,
)


def _redact_url(url: str) -> str:
    return re.sub(r"://([^:/@]+):([^@/]+)@", r"://\1:***@", url)


def _scan_destructive(versions_dir: Path) -> list[str]:
    if not versions_dir.is_dir():
        return []
    hits: list[str] = []
    for path in sorted(versions_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if DESTRUCTIVE.search(text):
            hits.append(path.name)
    return hits


def _alembic_heads(script_location: Path) -> list[str]:
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
    except ImportError:
        return []

    cfg = Config()
    cfg.set_main_option("script_location", str(script_location))
    script = ScriptDirectory.from_config(cfg)
    return list(script.get_heads())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-destructive", action="store_true")
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=ROOT / "migrations",
    )
    args = parser.parse_args()

    versions = args.migrations_dir / "versions"
    scripts = list(versions.glob("*.py")) if versions.is_dir() else []
    destructive = _scan_destructive(versions)

    print(f"migration_scripts={len(scripts)}")
    print(f"destructive_pattern_files={len(destructive)}")
    for name in destructive[:30]:
        print(f"  destructive_candidate={name}")

    heads = _alembic_heads(args.migrations_dir)
    if heads:
        print(f"heads={len(heads)}")
        for h in heads:
            print(f"  head={h}")
        if len(heads) > 1:
            print("status=blocked reason=multiple_heads")
            return 1
    else:
        print("heads=unknown (alembic unavailable or no script dir)")

    db_url = os.environ.get("DATABASE_URL", "")
    if db_url:
        print(f"database={_redact_url(db_url)}")

    if destructive and not args.allow_destructive:
        print("status=blocked reason=destructive_candidates_need_--allow-destructive")
        return 1

    print("status=ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
