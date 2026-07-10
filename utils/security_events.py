"""Structured security event logging with redaction.

Never log passwords, tokens, cookies, Authorization headers, or full PII blobs.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("security.events")

_REDACT_KEYS = re.compile(
    r"(password|passwd|secret|token|cookie|authorization|api[_-]?key|session)",
    re.I,
)


def _redact_value(key: str, value: Any) -> Any:
    if _REDACT_KEYS.search(key or ""):
        return "[REDACTED]"
    if isinstance(value, str) and len(value) > 200:
        return value[:200] + "…"
    return value


def _correlation_id() -> str | None:
    try:
        from flask import g, has_request_context

        if has_request_context():
            return getattr(g, "request_id", None)
    except Exception:
        return None
    return None


def log_security_event(event: str, **fields: Any) -> None:
    """Emit a single-line structured security event.

    Example fields: outcome, username, path, reason, user_id (ok), ip (ok).
    Automatically attaches request_id when available on flask.g.
    """
    rid = fields.pop("request_id", None) or _correlation_id()
    if rid is not None:
        fields = {**fields, "request_id": rid}

    safe = {k: _redact_value(k, v) for k, v in fields.items() if v is not None}
    parts = [f"event={event}"]
    for k in sorted(safe.keys()):
        parts.append(f"{k}={safe[k]!s}")
    logger.info(" ".join(parts))
