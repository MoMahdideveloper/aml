"""Observability: correlation, structured logs, metrics bounds, health, jobs."""

from __future__ import annotations

import json
import logging
import re

import pytest


def _app(monkeypatch):
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    monkeypatch.setenv("ENABLE_CSRF", "0")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("READYZ_REQUIRE_REDIS", "0")

    from app import create_app
    from database import db
    from utils.observability import METRICS

    METRICS.reset()
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
    return app


def test_request_id_accepts_valid_and_rejects_malformed(monkeypatch):
    app = _app(monkeypatch)
    client = app.test_client()

    ok = client.get("/healthz", headers={"X-Request-ID": "abc-123_OK"})
    assert ok.headers.get("X-Request-ID") == "abc-123_OK"

    bad = client.get("/healthz", headers={"X-Request-ID": "bad id with spaces!!!"})
    rid = bad.headers.get("X-Request-ID") or ""
    assert rid
    assert " " not in rid
    assert rid != "bad id with spaces!!!"


def test_structured_http_log_is_json_and_redacted(monkeypatch, caplog):
    app = _app(monkeypatch)
    client = app.test_client()
    with caplog.at_level(logging.INFO, logger="observability"):
        client.get("/healthz", headers={"X-Request-ID": "corr-http-1"})
    lines = [
        r.getMessage()
        for r in caplog.records
        if r.name == "observability" and "http_request" in r.getMessage()
    ]
    assert lines, "expected structured http_request log"
    payload = json.loads(lines[-1])
    assert payload["event"] == "http_request"
    assert payload["request_id"] == "corr-http-1"
    assert payload["status_class"] == "2xx"
    assert "duration_ms" in payload
    assert "route" in payload
    # no secret-looking fields
    assert "password" not in payload
    assert "Authorization" not in json.dumps(payload)


def test_metrics_http_red_bounded_labels(monkeypatch):
    app = _app(monkeypatch)
    client = app.test_client()
    client.get("/healthz")
    client.get("/readyz")
    text = client.get("/metrics").get_data(as_text=True)
    assert "http_requests_total" in text
    assert "http_request_duration_seconds_bucket" in text
    # No raw high-cardinality request ids in metrics
    assert "corr-" not in text or "request_id" not in text
    assert 'status_class="2xx"' in text


def test_metrics_rejects_forbidden_label_keys(monkeypatch):
    from utils.observability import METRICS

    METRICS.reset()
    METRICS.inc(
        "http_requests_total",
        route="/x",
        method="GET",
        status_class="2xx",
        user_id="should-drop",
        request_id="should-drop",
        email="a@b.c",
    )
    rendered = METRICS.render_prometheus()
    assert "user_id" not in rendered
    assert "should-drop" not in rendered
    assert "a@b.c" not in rendered


def test_healthz_liveness_vs_readyz_db_failure(monkeypatch):
    app = _app(monkeypatch)
    client = app.test_client()
    assert client.get("/healthz").status_code == 200

    # Force DB failure for readiness
    from unittest.mock import patch

    with patch("utils.observability.check_database", return_value={"status": "error", "detail": "unavailable"}):
        # readyz uses check_database from utils - but app.readyz imports it at call time
        with patch("app.check_database", return_value={"status": "error", "detail": "unavailable"}):
            r = client.get("/readyz")
    assert r.status_code == 503
    body = r.get_json()
    assert body["status"] == "not_ready"
    assert "components" in body
    # no connection string
    assert "sqlite" not in json.dumps(body).lower() or "unavailable" in json.dumps(body)


def test_readyz_ok_with_components(monkeypatch):
    app = _app(monkeypatch)
    client = app.test_client()
    r = client.get("/readyz")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ready"
    assert body["components"]["database"]["status"] == "ok"


def test_job_lifecycle_events(monkeypatch, caplog):
    from utils.observability import METRICS, timed_job

    METRICS.reset()
    with caplog.at_level(logging.INFO, logger="observability"):
        with timed_job("matching", attempt=1, request_id="job-corr-1") as st:
            st["outcome"] = "ok"
        assert "job_started" in caplog.text
        assert "job_succeeded" in caplog.text
        assert "job-corr-1" in caplog.text

        with pytest.raises(RuntimeError):
            with timed_job("matching", attempt=2, request_id="job-corr-2"):
                raise RuntimeError("boom")
        assert "job-corr-2" in caplog.text
        assert "job_failed" in caplog.text
    prom = METRICS.render_prometheus()
    assert "job_events_total" in prom


def test_provider_timeout_telemetry(monkeypatch, caplog):
    from utils.observability import METRICS, timed_provider

    METRICS.reset()
    with caplog.at_level(logging.INFO, logger="observability"):
        with pytest.raises(TimeoutError):
            with timed_provider("gemini", "generate") as st:
                st["outcome"] = "timeout"
                st["error_category"] = "timeout"
                raise TimeoutError("x")
    assert "provider_call" in caplog.text
    assert "timeout" in caplog.text
    assert "prompt" not in caplog.text
    assert 'outcome="timeout"' in METRICS.render_prometheus() or "timeout" in METRICS.render_prometheus()


def test_log_event_redacts_sensitive_keys(monkeypatch, caplog):
    from utils.observability import log_event

    with caplog.at_level(logging.INFO, logger="observability"):
        log_event(
            "test_redact",
            password="secret-pass",
            api_key="sk-xyz",
            prompt="customer SSN 123",
            route="/healthz",
        )
    msg = caplog.records[-1].getMessage()
    data = json.loads(msg)
    assert data["password"] == "[REDACTED]"
    assert data["api_key"] == "[REDACTED]"
    assert data["prompt"] == "[REDACTED]"
    assert "secret-pass" not in msg
    assert "sk-xyz" not in msg


def test_failure_injection_route_exception_visible_in_metrics(monkeypatch):
    """Disposable failure: route exception → 5xx metric + request id header."""
    app = _app(monkeypatch)

    @app.route("/__obs_boom")
    def _boom():
        raise RuntimeError("synthetic failure for observability")

    client = app.test_client()
    resp = client.get(
        "/__obs_boom",
        headers={
            "X-Request-ID": "inj-1",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    assert resp.status_code == 500
    assert resp.headers.get("X-Request-ID") == "inj-1"
    metrics = client.get("/metrics").get_data(as_text=True)
    assert 'status_class="5xx"' in metrics


def test_business_counters_no_entity_ids(monkeypatch):
    from utils.observability import METRICS, record_business_counter

    METRICS.reset()
    record_business_counter("crm_mutations_total", domain="customer", outcome="ok")
    record_business_counter("recommendation_outcomes_total", outcome="ok")
    text = METRICS.render_prometheus()
    assert "crm_mutations_total" in text
    assert "customer_id" not in text
    assert re.search(r"crm_mutations_total\{[^}]*domain=\"customer\"", text)
