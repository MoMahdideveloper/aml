#!/usr/bin/env python3
"""Export Track A Flask URL map to a security authorization matrix (markdown).

Does not guess multi-tenancy — records endpoints for human/security agent review.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def classify_endpoint(endpoint: str, rule: str, methods: list[str]) -> dict:
    mutating = any(m in methods for m in ("POST", "PUT", "PATCH", "DELETE"))
    admin = rule.startswith("/admin") or endpoint.startswith("admin_")
    auth = rule.startswith("/auth") or endpoint.startswith("auth.")
    api = "/api/" in rule or rule.startswith("/api")
    health = rule in ("/healthz", "/readyz") or endpoint in ("healthz", "readyz")

    # Expected auth — inferred from code patterns, must be verified by security agent
    if health:
        expected_auth = "public"
    elif admin:
        expected_auth = "admin_session (require_admin_auth)"
    elif auth and "logout" not in endpoint and "login" not in endpoint and "register" not in endpoint:
        expected_auth = "session optional / login for writes"
    elif auth:
        expected_auth = "public (login/register) or session (logout/profile writes)"
    else:
        # Core CRM currently serves many pages without forced login in app factory
        expected_auth = "VERIFY: often public-read in current code; confirm product intent"

    csrf = "required when ENABLE_CSRF=1" if mutating else "n/a (safe method)"
    sensitivity = "high" if admin or "delete" in endpoint or "environment" in endpoint else (
        "medium" if mutating or api else "low-medium"
    )
    return {
        "expected_auth": expected_auth,
        "csrf": csrf,
        "sensitivity": sensitivity,
        "mutating": mutating,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="docs/SECURITY_ROUTE_MATRIX.md",
        help="Output markdown path",
    )
    args = parser.parse_args()

    from app import create_app

    app = create_app()
    rows = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        methods = sorted(m for m in (rule.methods or []) if m not in ("HEAD", "OPTIONS"))
        meta = classify_endpoint(rule.endpoint, rule.rule, methods)
        rows.append(
            {
                "methods": ",".join(methods),
                "rule": rule.rule,
                "endpoint": rule.endpoint,
                **meta,
            }
        )
    rows.sort(key=lambda r: (r["rule"], r["methods"]))

    out = Path(args.out)
    lines = [
        "# Track A Security Route Matrix",
        "",
        "Auto-generated from Flask `url_map`. **Expected auth is a starting hypothesis** —",
        "confirm against `views/` and product policy before hardening.",
        "",
        f"Total non-static endpoints: **{len(rows)}**",
        "",
        "| Methods | Path | Endpoint | Expected auth (verify) | CSRF | Sensitivity |",
        "|---------|------|----------|------------------------|------|-------------|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['methods']}` | `{r['rule']}` | `{r['endpoint']}` | "
            f"{r['expected_auth']} | {r['csrf']} | {r['sensitivity']} |"
        )
    lines.extend(
        [
            "",
            "## Access model notes (from code inspection, 2026-07-10)",
            "",
            "- Session keys: `session['user_id']`, `session['user_role']` (`views/auth.py`).",
            "- Admin environment routes use `require_admin_auth` (`views/admin_environment.py`).",
            "- Many CRM list/detail routes appear reachable without login today — "
            "**product may be single-tenant office tool**; security plan must not invent multi-tenancy.",
            "- CSRF enabled when `ENABLE_CSRF=1` or production default (`app.py`).",
            "",
            "## Findings seed (for security agent)",
            "",
            "| ID | Severity | Finding |",
            "|----|----------|---------|",
            "| F1 | high | Confirm which CRM routes must reject anonymous users server-side |",
            "| F2 | high | Object-level authorization (IDOR) may be absent if all staff share data |",
            "| F3 | medium | Dual endpoint aliases (blueprint + bare) increase CSRF/test surface |",
            "| F4 | medium | Admin JSON/API routes need same controls as HTML |",
            "",
            "Regenerate: `python scripts/export_security_route_matrix.py`",
            "",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(rows)} routes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
