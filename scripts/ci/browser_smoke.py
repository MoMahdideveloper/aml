#!/usr/bin/env python3
"""HTTP browser-style smoke for Track A (no pixel assertions).

Boots nothing — targets BASE_URL (Flask already running). Uses urllib only.
Records failed status codes; optional JSON report.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# Core routes: unauthenticated expectations under AUTH_DEFAULT_DENY off/on.
ROUTES = [
    ("/healthz", {200}),
    ("/readyz", {200, 503}),  # 503 if deps missing
    ("/auth/login", {200, 302}),
    ("/", {200, 302}),
    ("/properties", {200, 302}),
    ("/customers", {200, 302}),
    ("/deals", {200, 302}),
    ("/tasks", {200, 302}),
    ("/recommendations", {200, 302}),
    ("/metrics", {200, 404}),
]


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "gptvli-browser-smoke/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read(2000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, type(e).__name__


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    failures = []
    results = []
    for path, allowed in ROUTES:
        code, snippet = fetch(base + path)
        ok = code in allowed
        results.append({"path": path, "status": code, "ok": ok})
        print(f"{'PASS' if ok else 'FAIL'} {path} -> {code}")
        if not ok:
            failures.append(path)
        # Console-error proxy: HTML 500 body markers
        if code >= 500:
            failures.append(path)

    report = {"base_url": base, "results": results, "ok": not failures}
    if args.json_out:
        Path = __import__("pathlib").Path
        p = Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
