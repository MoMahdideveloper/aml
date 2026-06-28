"""
Test dashboard template basic structure.
Tests that dashboard template renders and contains placeholder content.
"""
import pytest


def test_dashboard_template_exists(client):
    """Test that dashboard template renders without error."""
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b'PLACEHOLDER_DASHBOARD_CONTENT' in response.data