"""Admin password policy and production refuse-weak-default."""

import os

import pytest


def test_weak_default_ok_in_development(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    from utils.admin_auth import admin_password_is_acceptable, verify_admin_password

    ok, _ = admin_password_is_acceptable(is_production=False)
    assert ok is True
    assert verify_admin_password("admin123") is True
    assert verify_admin_password("wrong") is False


def test_weak_default_rejected_in_production(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")
    monkeypatch.delenv("ALLOW_WEAK_ADMIN_PASSWORD", raising=False)
    from utils.admin_auth import admin_password_is_acceptable

    ok, reason = admin_password_is_acceptable(is_production=True)
    assert ok is False
    assert "weak" in reason.lower() or "ADMIN_PASSWORD" in reason


def test_production_create_app_rejects_weak_admin(monkeypatch):
    for key in (
        "FLASK_ENV",
        "SESSION_SECRET",
        "ADMIN_PASSWORD",
        "ALLOW_INSECURE_SECRET",
        "ALLOW_WEAK_ADMIN_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "prod-test-secret-not-for-real-use-32chars")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")

    from app import create_app

    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        create_app()


def test_production_create_app_accepts_strong_admin(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "prod-test-secret-not-for-real-use-32chars")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-very-strong-admin-pass-99")
    monkeypatch.delenv("ALLOW_WEAK_ADMIN_PASSWORD", raising=False)

    from app import create_app

    app = create_app()
    assert app is not None
