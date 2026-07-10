"""Track A production observability: correlation, structured logs, bounded metrics.

Never log secrets, cookies, tokens, full bodies, prompts, or customer record contents.
Never use high-cardinality metric labels (user ids, raw URLs, request ids, emails).
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

logger = logging.getLogger("observability")

# ── Correlation ──────────────────────────────────────────────────────────────

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

_REDACT_KEYS = re.compile(
    r"(password|passwd|secret|token|cookie|authorization|api[_-]?key|session|"
    r"prompt|response_text|body|ssn|credit.?card)",
    re.I,
)

PROVIDER_ALLOWLIST = frozenset(
    {"gemini", "kie", "nominatim", "melipayamak", "redis", "postgres", "sqlite", "unknown"}
)
OPERATION_ALLOWLIST = frozenset(
    {
        "generate",
        "extract",
        "embed",
        "geocode",
        "sms",
        "chat",
        "query",
        "ping",
        "unknown",
    }
)
JOB_TYPE_ALLOWLIST = frozenset(
    {
        "matching",
        "rematch_queue",
        "notification_digest",
        "sms_queue",
        "overdue_tasks",
        "scoring",
        "cleanup",
        "backup",
        "generic",
    }
)
ERROR_CATEGORIES = frozenset(
    {"timeout", "dependency", "validation", "auth", "internal", "unknown"}
)


def normalize_request_id(raw: Optional[str]) -> str:
    """Accept a valid inbound request id or generate a new UUID hex."""
    if raw:
        candidate = raw.strip()[:64]
        if _REQUEST_ID_RE.match(candidate):
            return candidate
    return uuid.uuid4().hex


def get_request_id() -> Optional[str]:
    try:
        from flask import g, has_request_context

        if has_request_context():
            return getattr(g, "request_id", None)
    except Exception:
        return None
    return None


def set_request_id(value: str) -> None:
    try:
        from flask import g, has_request_context

        if has_request_context():
            g.request_id = value
    except Exception:
        pass


def status_class(status_code: int) -> str:
    if status_code < 200:
        return "1xx"
    if status_code < 300:
        return "2xx"
    if status_code < 400:
        return "3xx"
    if status_code < 500:
        return "4xx"
    return "5xx"


def normalize_route(endpoint: Optional[str], path: Optional[str] = None) -> str:
    """Prefer Flask rule template; fall back to low-cardinality path class."""
    try:
        from flask import has_request_context, request

        if has_request_context() and request.url_rule is not None:
            return request.url_rule.rule or "unknown"
    except Exception:
        pass
    if endpoint:
        return f"endpoint:{endpoint}"
    if not path:
        return "unknown"
    # Collapse digits to avoid high-cardinality raw URLs as last resort
    collapsed = re.sub(r"/\d+", "/:id", path.split("?", 1)[0])
    if len(collapsed) > 80:
        return "unknown"
    return collapsed


def _redact_value(key: str, value: Any) -> Any:
    if _REDACT_KEYS.search(key or ""):
        return "[REDACTED]"
    if isinstance(value, str) and len(value) > 200:
        return value[:200] + "…"
    return value


def log_event(event: str, **fields: Any) -> None:
    """Emit one JSON structured observability event (stdout-friendly)."""
    rid = fields.pop("request_id", None) or get_request_id()
    payload: Dict[str, Any] = {"event": event}
    if rid:
        payload["request_id"] = rid
    for k, v in fields.items():
        if v is None:
            continue
        payload[k] = _redact_value(k, v)
    # Prefer JSON for production parsers; single line.
    try:
        line = json.dumps(payload, default=str, separators=(",", ":"), sort_keys=True)
    except Exception:
        line = f'{{"event":"{event}","error_category":"internal"}}'
    logger.info(line)


# ── Metrics (in-process, Prometheus text) ────────────────────────────────────


@dataclass
class _Hist:
    counts: List[int] = field(default_factory=lambda: [0] * 12)
    sum: float = 0.0
    count: int = 0


# Fixed latency buckets (seconds) for p50/p95/p99 style queries
_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf"))


class MetricsRegistry:
    """Thread-safe counters and histograms with bounded label sets."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = defaultdict(float)
        self._histograms: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], _Hist] = {}

    def _labels(self, labels: Optional[Dict[str, str]]) -> Tuple[Tuple[str, str], ...]:
        if not labels:
            return ()
        # Drop forbidden high-cardinality keys if accidentally passed
        forbidden = {"user_id", "request_id", "email", "url", "path", "error", "message"}
        cleaned = {
            str(k): str(v)[:64]
            for k, v in labels.items()
            if k not in forbidden and v is not None
        }
        return tuple(sorted(cleaned.items()))

    def inc(self, name: str, amount: float = 1.0, **labels: str) -> None:
        key = (name, self._labels(labels))
        with self._lock:
            self._counters[key] += amount

    def observe(self, name: str, value: float, **labels: str) -> None:
        key = (name, self._labels(labels))
        with self._lock:
            hist = self._histograms.get(key)
            if hist is None:
                hist = _Hist()
                self._histograms[key] = hist
            hist.count += 1
            hist.sum += value
            for i, bound in enumerate(_BUCKETS):
                if value <= bound:
                    hist.counts[i] += 1
                    break

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._histograms.clear()

    def render_prometheus(self) -> str:
        lines: List[str] = []
        with self._lock:
            for (name, labels), value in sorted(self._counters.items()):
                lines.append(f"{name}{_fmt_labels(labels)} {value}")
            for (name, labels), hist in sorted(self._histograms.items()):
                cumulative = 0
                for i, bound in enumerate(_BUCKETS):
                    cumulative += hist.counts[i]
                    b = "+Inf" if bound == float("inf") else str(bound)
                    lab = list(labels) + [("le", b)]
                    lines.append(f"{name}_bucket{_fmt_labels(tuple(lab))} {cumulative}")
                lines.append(f"{name}_sum{_fmt_labels(labels)} {hist.sum}")
                lines.append(f"{name}_count{_fmt_labels(labels)} {hist.count}")
        lines.append("")
        return "\n".join(lines)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counters": {
                    f"{n}|{dict(l)}": v for (n, l), v in self._counters.items()
                },
                "histograms": {
                    f"{n}|{dict(l)}": {
                        "count": h.count,
                        "sum": h.sum,
                        "buckets": h.counts[:],
                    }
                    for (n, l), h in self._histograms.items()
                },
            }


def _fmt_labels(labels: Tuple[Tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{k}="{v}"' for k, v in labels)
    return "{" + inner + "}"


METRICS = MetricsRegistry()


def record_http_request(
    *,
    route: str,
    method: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    sc = status_class(status_code)
    method_u = (method or "GET").upper()
    route_n = route or "unknown"
    METRICS.inc(
        "http_requests_total",
        route=route_n,
        method=method_u,
        status_class=sc,
    )
    METRICS.observe(
        "http_request_duration_seconds",
        duration_seconds,
        route=route_n,
        method=method_u,
        status_class=sc,
    )


def record_provider_call(
    *,
    provider: str,
    operation: str,
    duration_seconds: float,
    outcome: str,
) -> None:
    p = provider if provider in PROVIDER_ALLOWLIST else "unknown"
    op = operation if operation in OPERATION_ALLOWLIST else "unknown"
    out = outcome if outcome in ("ok", "error", "timeout") else "error"
    METRICS.inc(
        "external_provider_calls_total",
        provider=p,
        operation=op,
        outcome=out,
    )
    METRICS.observe(
        "external_provider_duration_seconds",
        duration_seconds,
        provider=p,
        operation=op,
        outcome=out,
    )


def record_job_event(
    *,
    job_type: str,
    outcome: str,
    duration_seconds: Optional[float] = None,
) -> None:
    jt = job_type if job_type in JOB_TYPE_ALLOWLIST else "generic"
    out = outcome if outcome in ("started", "ok", "error", "retry", "skipped") else "error"
    METRICS.inc("job_events_total", job_type=jt, outcome=out)
    if duration_seconds is not None and out in ("ok", "error", "skipped"):
        METRICS.observe(
            "job_duration_seconds",
            duration_seconds,
            job_type=jt,
            outcome=out if out != "started" else "ok",
        )


def record_business_counter(name: str, **labels: str) -> None:
    """Aggregate-only business health counters (no entity ids)."""
    allowed = {
        "crm_mutations_total",
        "recommendation_outcomes_total",
        "notification_outcomes_total",
        "dashboard_snapshot_failures_total",
    }
    if name not in allowed:
        name = "crm_mutations_total"
    # scrub labels to allowlist keys only
    safe = {}
    for k, v in labels.items():
        if k in ("domain", "outcome", "channel") and v:
            safe[k] = str(v)[:32]
    METRICS.inc(name, **safe)


# ── Timed helpers ────────────────────────────────────────────────────────────


@contextmanager
def timed_provider(provider: str, operation: str) -> Iterator[Dict[str, Any]]:
    """Context manager that records provider latency/outcome without storing payloads."""
    state: Dict[str, Any] = {"outcome": "ok", "error_category": None}
    start = time.perf_counter()
    try:
        yield state
    except TimeoutError:
        state["outcome"] = "timeout"
        state["error_category"] = "timeout"
        raise
    except Exception:
        if state.get("outcome") == "ok":
            state["outcome"] = "error"
            state["error_category"] = state.get("error_category") or "dependency"
        raise
    finally:
        dur = time.perf_counter() - start
        record_provider_call(
            provider=provider,
            operation=operation,
            duration_seconds=dur,
            outcome=str(state.get("outcome") or "error"),
        )
        log_event(
            "provider_call",
            component="provider",
            provider=provider if provider in PROVIDER_ALLOWLIST else "unknown",
            operation=operation if operation in OPERATION_ALLOWLIST else "unknown",
            duration_ms=int(dur * 1000),
            outcome=state.get("outcome"),
            error_category=state.get("error_category"),
        )


@contextmanager
def timed_job(job_type: str, *, attempt: int = 1, request_id: Optional[str] = None) -> Iterator[Dict[str, Any]]:
    jt = job_type if job_type in JOB_TYPE_ALLOWLIST else "generic"
    rid = request_id or get_request_id() or uuid.uuid4().hex
    state: Dict[str, Any] = {
        "outcome": "ok",
        "error_category": None,
        "request_id": rid,
        "attempt": attempt,
    }
    start = time.perf_counter()
    record_job_event(job_type=jt, outcome="started")
    log_event(
        "job_started",
        component="job",
        job_type=jt,
        attempt=attempt,
        request_id=rid,
    )
    try:
        yield state
        outcome = str(state.get("outcome") or "ok")
        if outcome == "skipped":
            record_job_event(job_type=jt, outcome="skipped", duration_seconds=time.perf_counter() - start)
            log_event(
                "job_skipped",
                component="job",
                job_type=jt,
                attempt=attempt,
                duration_ms=int((time.perf_counter() - start) * 1000),
                request_id=rid,
            )
        elif outcome == "retry":
            record_job_event(job_type=jt, outcome="retry")
            log_event(
                "job_retried",
                component="job",
                job_type=jt,
                attempt=attempt,
                error_category=state.get("error_category") or "unknown",
                request_id=rid,
            )
        else:
            dur = time.perf_counter() - start
            record_job_event(job_type=jt, outcome="ok", duration_seconds=dur)
            log_event(
                "job_succeeded",
                component="job",
                job_type=jt,
                attempt=attempt,
                duration_ms=int(dur * 1000),
                request_id=rid,
            )
    except Exception:
        dur = time.perf_counter() - start
        cat = state.get("error_category") if state.get("error_category") in ERROR_CATEGORIES else "internal"
        record_job_event(job_type=jt, outcome="error", duration_seconds=dur)
        log_event(
            "job_failed",
            component="job",
            job_type=jt,
            attempt=attempt,
            duration_ms=int(dur * 1000),
            error_category=cat,
            request_id=rid,
        )
        raise


def check_redis(timeout: float = 0.5) -> Dict[str, Any]:
    """Best-effort Redis ping; never returns connection strings."""
    url = os.environ.get("REDIS_URL") or os.environ.get("CELERY_BROKER_URL")
    if not url:
        return {"status": "skipped", "detail": "not_configured"}
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(url, socket_connect_timeout=timeout, socket_timeout=timeout)
        client.ping()
        return {"status": "ok"}
    except Exception:
        return {"status": "error", "detail": "unavailable"}


def check_database(timeout_note: str = "strict") -> Dict[str, Any]:
    try:
        from database import db
        from sqlalchemy import text

        db.session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return {"status": "error", "detail": "unavailable"}
