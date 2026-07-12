"""Admin console password policy (separate from CRM User model)."""

from __future__ import annotations

import os
from typing import Tuple

# Never use these in production without explicit override.
WEAK_ADMIN_PASSWORDS = frozenset(
    {
        "admin123",
        "admin",
        "password",
        "password123",
        "123456",
        "changeme",
        "",
    }
)


def get_admin_password() -> str:
    """Return configured admin password (default only for non-production)."""
    return os.environ.get("ADMIN_PASSWORD", "admin123")


def admin_password_is_acceptable(*, is_production: bool | None = None) -> Tuple[bool, str]:
    """
    Return (ok, reason).

    Production refuses empty/weak defaults unless ALLOW_WEAK_ADMIN_PASSWORD=1.
    """
    if is_production is None:
        env = (os.environ.get("FLASK_ENV") or os.environ.get("ENV") or "").lower()
        is_production = env in ("production", "prod")

    password = get_admin_password()
    allow_weak = os.environ.get("ALLOW_WEAK_ADMIN_PASSWORD", "0").strip() == "1"

    if not password:
        return False, "ADMIN_PASSWORD is empty"
    if is_production and password in WEAK_ADMIN_PASSWORDS and not allow_weak:
        return (
            False,
            "ADMIN_PASSWORD is a known weak default; set a strong value "
            "or ALLOW_WEAK_ADMIN_PASSWORD=1 to override",
        )
    if is_production and len(password) < 12 and not allow_weak:
        return False, "ADMIN_PASSWORD must be at least 12 characters in production"
    return True, "ok"


def verify_admin_password(candidate: str) -> bool:
    """Constant-time-ish compare against configured password."""
    expected = get_admin_password()
    if not candidate or not expected:
        return False
    # Avoid short-circuit length leak of content; still fine for local admin gate.
    if len(candidate) != len(expected):
        # Still compare to reduce trivial timing; use secrets if available
        try:
            import hmac

            return hmac.compare_digest(candidate, expected)
        except Exception:
            return False
    try:
        import hmac

        return hmac.compare_digest(candidate, expected)
    except Exception:
        return candidate == expected
