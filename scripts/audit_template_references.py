#!/usr/bin/env python3
"""CLI wrapper for the live template reference audit.

Usage (from repo root):
  python scripts/audit_template_references.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from test_template_references import (  # noqa: E402
    collect_direct_render_templates,
    collect_jinja_deps,
    template_path,
)


def main() -> int:
    entries = collect_direct_render_templates()
    print(f"Direct render_template() names: {len(entries)}")
    for name in sorted(entries):
        path = template_path(name)
        status = "OK" if path.is_file() else "MISSING"
        print(f"  [{status}] {name}")

    live = {n for n in entries if "stitch_kpi" not in n and not n.startswith("_archive/")}
    deps = collect_jinja_deps(live)
    print(f"\nJinja dependency closure: {len(deps)}")
    missing = [n for n in sorted(deps) if not template_path(n).is_file()]
    if missing:
        print("MISSING deps:")
        for n in missing:
            print(f"  - {n}")
        return 1
    print("All live template references resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
