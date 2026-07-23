"""Regression: explicit test_config must win over the AUTH_DEFAULT_DENY_ENABLED env var."""

import os

from app import create_app


def test_test_config_auth_flag_overrides_env(monkeypatch):
    """create_app(test_config) with an explicit auth flag must not be overwritten by env."""
    # Env says "deny enabled", but explicit config says disabled — config must win.
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "1")
    monkeypatch.setenv("EVENT_HANDLERS_ENABLED", "0")

    app = create_app(
        {
            "TESTING": True,
            "AUTH_DEFAULT_DENY_ENABLED": False,
            "WTF_CSRF_ENABLED": False,
        }
    )

    assert app.config["AUTH_DEFAULT_DENY_ENABLED"] is False


def test_env_still_controls_auth_when_config_silent(monkeypatch):
    """When test_config does not mention the flag, the env var still governs."""
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "1")
    monkeypatch.setenv("EVENT_HANDLERS_ENABLED", "0")

    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})

    assert app.config["AUTH_DEFAULT_DENY_ENABLED"] is True
