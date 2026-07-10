#!/usr/bin/env python3
"""Static checks on GitHub workflow YAML for Track A safety rules.

Fails if:
  - production deploy triggered on plain push
  - hardcoded private keys / cloud tokens appear
  - workflow_dispatch missing for promote/rollback
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WF = ROOT / ".github" / "workflows"

# High-signal secret shapes (values never printed)
FORBIDDEN = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----"),
    re.compile(r"ghp_[0-9A-Za-z]{20,}"),
    re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
]


def main() -> int:
    if not WF.is_dir():
        print("no workflows dir")
        return 1
    errors: list[str] = []
    for path in sorted(WF.glob("*.yml")) + sorted(WF.glob("*.yaml")):
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        for rx in FORBIDDEN:
            if rx.search(text):
                errors.append(f"{rel}: forbidden credential pattern {rx.pattern}")

        lower = text.lower()
        # Production promote / rollback must not run on push
        if path.name in ("deploy-production.yml", "rollback.yml", "deploy-staging.yml"):
            if re.search(r"(?m)^on:\s*$", text) or "on:" in text:
                # crude: if 'push:' appears under on without only tags
                if re.search(r"(?m)^\s+push:\s*$", text) or re.search(
                    r"(?m)^\s+push:\s*\[", text
                ):
                    # allow push to tags only if tags: filter present on same block — simplify ban push
                    if "tags:" not in text.split("push:", 1)[-1][:200]:
                        errors.append(f"{rel}: deploy workflow must not use unrestricted push trigger")
            if "workflow_dispatch" not in text:
                errors.append(f"{rel}: must support workflow_dispatch")

        if "password:" in lower and "ci_" not in lower and "postgres_password" in lower:
            # CI synthetic passwords are OK when clearly ci_
            pass

    if errors:
        print("WORKFLOW_SAFETY_FAIL")
        for e in errors:
            print(f"  {e}")
        return 1
    print("WORKFLOW_SAFETY_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
