#!/usr/bin/env python3
"""Post-deploy verification for Track A (synthetic checks only).

Env:
  BASE_URL   base URL (default http://127.0.0.1:8000)
  VERIFY_TIMEOUT_SECONDS  total timeout (default 60)

Exit 0 when all required checks pass.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def _get(url: str, timeout: float = 5.0) -> tuple[int, str, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "gptvli-post-deploy-verify/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, body, headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body, {}
    except Exception as e:
        return 0, f"{type(e).__name__}", {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("VERIFY_TIMEOUT_SECONDS", "60")),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    deadline = time.time() + args.timeout
    results: dict = {"base_url": base, "checks": {}}

    # Poll readiness until timeout
    ready_ok = False
    last_ready = ""
    while time.time() < deadline:
        code, body, _ = _get(f"{base}/readyz", timeout=3.0)
        last_ready = body[:200]
        if code == 200 and "ready" in body:
            ready_ok = True
            break
        time.sleep(2)

    results["checks"]["readyz"] = {"ok": ready_ok, "sample": last_ready}

    code, body, _ = _get(f"{base}/healthz", timeout=3.0)
    results["checks"]["healthz"] = {"ok": code == 200 and "ok" in body, "status": code}

    code, body, headers = _get(f"{base}/auth/login", timeout=5.0)
    css_ok = True  # soft: login page loads
    results["checks"]["login_page"] = {
        "ok": code in (200, 302),
        "status": code,
        "has_request_id_header": "x-request-id" in {k.lower() for k in headers},
    }

    # Static production CSS when served
    code, _, _ = _get(f"{base}/static/css/tailwind-ph.css", timeout=5.0)
    # 200 or 404 if not mounted in some test servers — soft when 404
    results["checks"]["static_css"] = {"ok": code in (200, 404), "status": code}

    metrics_code, metrics_body, _ = _get(f"{base}/metrics", timeout=5.0)
    results["checks"]["metrics"] = {
        "ok": metrics_code in (200, 404),  # optional if older image
        "status": metrics_code,
        "has_http_counter": "http_requests_total" in metrics_body if metrics_code == 200 else None,
    }

    all_required = (
        results["checks"]["readyz"]["ok"]
        and results["checks"]["healthz"]["ok"]
        and results["checks"]["login_page"]["ok"]
    )
    results["ok"] = all_required

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for name, data in results["checks"].items():
            print(f"{name}: {'PASS' if data.get('ok') else 'FAIL'} {data}")
        print(f"overall: {'PASS' if all_required else 'FAIL'}")

    return 0 if all_required else 1


if __name__ == "__main__":
    sys.exit(main())
