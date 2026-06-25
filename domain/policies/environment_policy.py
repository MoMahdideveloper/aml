"""
Environment variable authorization policies.
"""

from typing import Optional
from flask import session


def is_admin_authenticated() -> bool:
    """Check if the current user is authenticated as admin."""
    return session.get('admin_authenticated', False)


def get_current_admin_user() -> Optional[str]:
    """Get the current authenticated admin user."""
    return session.get('admin_user')


def can_administer_environment() -> bool:
    """Policy: Only authenticated admins can administer environment variables."""
    return is_admin_authenticated()


def can_create_environment_variable() -> bool:
    """Policy: Check if user can create environment variables."""
    return can_administer_environment()


def can_update_environment_variable() -> bool:
    """Policy: Check if user can update environment variables."""
    return can_administer_environment()


def can_delete_environment_variable() -> bool:
    """Policy: Check if user can delete environment variables."""
    return can_administer_environment()


def can_view_environment_variables() -> bool:
    """Policy: Check if user can view environment variables."""
    return can_administer_environment()