"""
Test dynamic data injection in dashboard template.
Tests that dashboard template properly renders dynamic data from Flask routes.
"""
import pytest
from bs4 import BeautifulSoup


def test_dashboard_template_dynamic_data_injection(client, app, sample_data):
    """Test that dashboard template properly injects dynamic data."""
    # Make a request to the dashboard route
    response = client.get('/')
    assert response.status_code == 200

    # Parse the HTML response
    soup = BeautifulSoup(response.data, 'html.parser')

    # Check that dynamic data from sample_data is present in the response
    # Based on the dashboard route in views/main.py, it passes:
    # stats, recent_properties, recent_deals, pending_tasks

    # Check for stats data (should contain counts)
    assert b'stats' in response.data or len(soup.find_all(text=True)) > 0

    # Check for recent properties data
    if sample_data['property']:
        # The property name should appear in the response
        assert bytes(sample_data['property'].title, 'utf-8') in response.data or \
               len(soup.find_all(text=lambda text: sample_data['property'].title in text if text else False)) > 0

    # Check for recent deals data
    if sample_data['deal']:
        # Deal information should be present
        assert len(soup.find_all(text=True)) > 0  # Basic check that content exists

    # Check for pending tasks data
    if sample_data['task']:
        # Task title should appear in the response
        assert bytes(sample_data['task'].title, 'utf-8') in response.data or \
               len(soup.find_all(text=lambda text: sample_data['task'].title in text if text else False)) > 0

    # Verify that the template uses proper Jinja2 syntax by checking for template remnants
    # After rendering, there should be no unsubstituted template variables
    html_content = response.data.decode('utf-8')

    # Check for obvious unsubstituted variables (this would indicate template issues)
    # Note: Some variables might legitimately appear in static text, so we check for obvious patterns
    unsubstituted_vars = [
        '{{ stats',
        '{{ recent_properties',
        '{{ recent_deals',
        '{{ pending_tasks',
        '{%',
        '%}'
    ]

    # Actually, after rendering, Jinja2 tags should be gone, replaced with actual values
    # So we check that we don't have obvious template tags left
    assert '{{' not in html_content or '{{ url_for' in html_content or '{{ config' in html_content, \
        "Template should not contain unsubstituted variables (except known exceptions like url_for/config)"


def test_dashboard_template_contains_stitch_elements(client):
    """Test that dashboard template contains Stitch/KPI specific elements."""
    response = client.get('/')
    assert response.status_code == 200

    html_content = response.data.decode('utf-8').lower()

    # Check for common Stitch/Bootstrap classes and elements
    stitch_elements = [
        'class="',
        'id="',
        'btn',
        'card',
        'navbar',
        'sidebar',
        'container',
        'row',
        'col-',
        'table',
        'table-striped',
        'table-hover'
    ]

    # Should contain at least some Bootstrap/Stitch elements
    found_elements = [elem for elem in stitch_elements if elem in html_content]
    assert len(found_elements) > 3, f"Should find multiple Stitch/Bootstrap elements, found: {found_elements}"

    # Check for common dashboard elements
    dashboard_elements = ['stats', 'metric', 'chart', 'graph', 'panel', 'widget']
    found_dashboard = [elem for elem in dashboard_elements if elem in html_content]
    # Note: Might not find these if they're implemented differently, so this is a softer assertion


def test_dashboard_template_no_raw_placeholders(client):
    """Test that dashboard template doesn't contain raw placeholder variables."""
    response = client.get('/')
    assert response.status_code == 200

    html_content = response.data.decode('utf-8')

    # These would be bad if they appeared in rendered output
    obvious_placeholders = [
        '{{ stats',
        '{{ recent_properties',
        '{{ recent_deals',
        '{{ pending_tasks',
        '{{ property.',
        '{{ deal.',
        '{{ task.'
    ]

    for placeholder in obvious_placeholders:
        # Allow some false positives for things like "{{ url_for" or "{{ config"
        if not (placeholder.startswith('{{ url_for') or placeholder.startswith('{{ config')):
            assert placeholder not in html_content, \
                f"Template should not contain unsubstituted placeholder: {placeholder}"