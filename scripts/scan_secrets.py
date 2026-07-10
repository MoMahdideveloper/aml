#!/usr/bin/env python3
"""
Scan tracked text files for credential-like patterns.

NEVER prints secret values — only path, line number, and pattern name.
Exit 1 if high-severity findings are present (override with --allow-high).

Usage:
  python scripts/scan_secrets.py
  python scripts/scan_secrets.py --json --out artifacts/SECRET_SCAN.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Pattern name → compiled regex (value capture group is never printed)
PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "high",
        "private_key_block",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "high",
        "aws_access_key_id",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "high",
        "generic_api_key_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)\b\s*[=:]\s*['\"][^'\"]{12,}['\"]"
        ),
    ),
    (
        "high",
        "password_assignment_literal",
        re.compile(
            r"(?i)\b(password|passwd|pwd)\b\s*[=:]\s*['\"][^'\"]{6,}['\"]"
        ),
    ),
    (
        "medium",
        "bearer_token_literal",
        re.compile(r"(?i)bearer\s+[a-z0-9_\-\.]{20,}"),
    ),
    (
        "medium",
        "connection_string_password",
        re.compile(r"(?i)(postgres|mysql|mongodb|redis)://[^:\s]+:[^@\s]{4,}@"),
    ),
    (
        "medium",
        "slack_or_github_token_prefix",
        re.compile(r"\b(xox[baprs]-[0-9A-Za-z-]{10,}|ghp_[0-9A-Za-z]{20,})\b"),
    ),
    (
        "low",
        "default_admin_password_hint",
        re.compile(r"(?i)admin123|changeme|password123|dev-secret-key-change-in-production"),
    ),
]

# Paths relative to repo root — never scan generated/vendor noise
SKIP_DIR_PARTS = {
    ".git",
    "node_modules",
    "chroma_db",
    "graphify-out",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "platinum-heritage-runnable",
    "api/node_modules",
    "matcher/node_modules",
    ".pytest_cache",
    "backups",
    "instance",
    "uploads",
}

SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".bin",
    ".pyc",
    ".woff",
    ".woff2",
    ".map",
    ".mp4",
    ".lock",
}

# Known synthetic / documented placeholders — pattern still reported as low if matched
ALLOWLIST_PATH_SUBSTRINGS = (
    "tests/",
    "test_",
    "artifacts/",
    "docs/",
    ".env.example",
    "HELP.md",
    "scripts/scan_secrets.py",
    "deep_think/",
    "specs/",
    "sessionfixbugs.md",
)


def _git_ls_files(root: Path) -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "-z"],
            cwd=root,
            stderr=subprocess.DEVNULL,
        )
        rels = [p for p in out.decode("utf-8", errors="replace").split("\0") if p]
        return [root / p for p in rels]
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: walk source-ish tree
        files: list[Path] = []
        for p in root.rglob("*"):
            if p.is_file():
                files.append(p)
        return files


def _should_skip(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return True
    parts = set(rel.split("/"))
    if parts & SKIP_DIR_PARTS:
        return True
    for skip in SKIP_DIR_PARTS:
        if f"/{skip}/" in f"/{rel}/" or rel.startswith(f"{skip}/"):
            return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    # size guard
    try:
        if path.stat().st_size > 1_500_000:
            return True
    except OSError:
        return True
    return False


def _is_allowlisted(rel: str) -> bool:
    rel_l = rel.replace("\\", "/")
    return any(a in rel_l for a in ALLOWLIST_PATH_SUBSTRINGS)


def scan(root: Path) -> list[dict]:
    findings: list[dict] = []
    for path in _git_ls_files(root):
        if _should_skip(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        allow = _is_allowlisted(rel)
        for i, line in enumerate(text.splitlines(), 1):
            # skip obvious comments about patterns in docs-heavy lines already allowlisted
            for severity, name, rx in PATTERNS:
                if not rx.search(line):
                    continue
                sev = severity
                if allow and severity == "high":
                    sev = "medium"  # demote high hits in tests/docs to medium
                if allow and severity == "medium":
                    sev = "low"
                findings.append(
                    {
                        "severity": sev,
                        "pattern": name,
                        "path": rel,
                        "line": i,
                        # intentionally NO matched text / secret value
                    }
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--out", type=Path, help="Write JSON report to path")
    parser.add_argument(
        "--allow-high",
        action="store_true",
        help="Exit 0 even when high findings exist",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    findings = scan(root)

    summary = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        summary[f["severity"]] = summary.get(f["severity"], 0) + 1

    report = {
        "root": str(root),
        "finding_count": len(findings),
        "summary": summary,
        "findings": findings,
        "note": "Values never included. Rotate any real high findings in process env / secret store.",
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Secret scan: {len(findings)} finding(s)  high={summary['high']} medium={summary['medium']} low={summary['low']}")
        for f in findings:
            if f["severity"] == "high":
                print(f"  [HIGH] {f['path']}:{f['line']}  pattern={f['pattern']}")
        if summary["high"] == 0:
            print("  (no high-severity findings)")
        print("  Full list: use --json or --out artifacts/SECRET_SCAN.json")

    if summary["high"] and not args.allow_high:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
