"""Liveness vs readiness probe semantics."""

from unittest.mock import patch

import pytest


def test_healthz_is_liveness_independent_of_db(client, app, db_setup):
    with app.app_context():
        resp = client.get("/healthz")
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["status"] == "ok"
        assert "env" in payload


def test_readyz_ok_when_db_available(client, app, db_setup):
    with app.app_context():
        resp = client.get("/readyz")
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["status"] == "ready"
        assert payload["components"]["database"]["status"] == "ok"


def test_readyz_503_sanitized_when_db_fails(client, app, db_setup):
    with app.app_context():
        with patch(
            "utils.observability.check_database",
            return_value={"status": "error", "detail": "unavailable"},
        ):
            with patch(
                "app.check_database",
                return_value={"status": "error", "detail": "unavailable"},
            ):
                resp = client.get("/readyz")
        assert resp.status_code == 503
        payload = resp.get_json()
        assert payload["status"] == "not_ready"
        assert payload["components"]["database"]["status"] == "error"
        # Must not echo internal exception text / connection secrets
        body = resp.get_data(as_text=True)
        assert "secret connection string" not in body
        assert "RuntimeError" not in body
        assert "postgresql://" not in body


def test_healthz_still_ok_when_db_execute_would_fail(client, app, db_setup):
    """Liveness must not depend on database connectivity."""
    with app.app_context():
        with patch("database.db.session.execute", side_effect=RuntimeError("db down")):
            resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
