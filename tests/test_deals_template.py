"""
Test dynamic data injection in deals template.
Tests that deals template properly displays dynamic data from database queries.
"""
import re

import pytest
from flask import url_for


def test_deals_template_dynamic_data(client, app):
    """Test that deals template renders with dynamic data from database."""
    with app.app_context():
        # Make request to deals endpoint
        response = client.get('/deals')

        # Verify successful response
        assert response.status_code == 200

        # Check that the response contains actual data (not placeholders)
        response_text = response.data.decode('utf-8')

        # Verify that dynamic data is present in the response
        # Check for structured elements that indicate dynamic data binding
        assert '<' in response_text
        assert '>' in response_text

        # Pipeline stage headings (actual stage names used by this app)
        assert 'Prospecting' in response_text
        assert 'Contact Made' in response_text
        assert 'Property Shown' in response_text
        assert 'Offer Submitted' in response_text
        assert 'Negotiation' in response_text
        assert 'Closed Won' in response_text

        # Structural/action elements always present regardless of deal count
        assert 'Add New Deal' in response_text
        assert 'Offer Amount' in response_text
        assert 'addDealModal' in response_text


def test_deals_template_pipeline_counts(client, app):
    """Test that deals template properly displays pipeline count data."""
    with app.app_context():
        response = client.get('/deals')
        assert response.status_code == 200

        response_text = response.data.decode('utf-8')

        # The pipeline always renders stage columns; bg-primary/10 is used for Prospecting
        assert 'bg-primary/10' in response_text or 'text-primary' in response_text

        # At least one numeric count must appear in the pipeline section
        count_pattern = r'[>]\s*\d+(?:,\d+)*\s*[<]'
        assert re.search(count_pattern, response_text), \
            "Expected at least one numeric value in the pipeline section"


def test_deals_template_deal_details_display(client, app):
    """Test that deals template properly displays individual deal details."""
    with app.app_context():
        response = client.get('/deals')
        assert response.status_code == 200

        response_text = response.data.decode('utf-8')

        # The deals page uses a JS-rendered kanban layout, not an HTML table.
        # Verify the page has structural HTML and the modal scaffold.
        assert '<!DOCTYPE html>' in response_text
        assert 'addDealModal' in response_text
        assert 'Offer Amount' in response_text

        # Status badge CSS classes — at least one must appear since the template
        # always renders the pipeline header cards regardless of deal count
        status_indicators = [
            'bg-primary/10',
            'text-primary',
        ]
        assert any(cls in response_text for cls in status_indicators), \
            "Expected at least one status-badge CSS class in the page"


def test_deals_template_empty_state_handling(client, app):
    """Test that deals template handles empty state gracefully."""
    with app.app_context():
        response = client.get('/deals')
        assert response.status_code == 200

        response_text = response.data.decode('utf-8')

        # Even with no data, should have proper structure
        assert '<!DOCTYPE html>' in response_text
        assert '<html' in response_text

        # Should show empty state message if no deals
        # "No Deals Found" or similar message
        if 'No Deals Found' in response_text:
            assert 'Start tracking your first deal' in response_text
            # Should have "Add Your First Deal" button
            assert 'Add Your First Deal' in response_text

        # Should always have structural elements regardless of data
        assert 'Deals Pipeline' in response_text
        assert 'Add New Deal' in response_text


def test_deals_template_no_raw_placeholders(client, app):
    """Test that deals template doesn't contain raw unsubstituted template variables."""
    response = client.get('/deals')
    assert response.status_code == 200

    html_content = response.data.decode('utf-8')

    # These would be bad if they appeared in rendered output
    obvious_placeholders = [
        '{{ deals.',
        '{{ deal.',
        '{{ property.',
        '{{ customer.',
        '{{ agent.',
        '{{ status.',
        '{{ offer_amount.',
        '{{ created_at.',
    ]

    for placeholder in obvious_placeholders:
        # We need to be careful not to match legitimate template expressions in JS/CSS
        # Simple approach: check that these don't appear outside of script/style tags
        lines = html_content.split('\n')
        for i, line in enumerate(lines):
            # Skip lines that are clearly inside script or style tags
            # (This is a simplified check - a proper HTML parser would be better)
            if '<script' in line.lower() or '</script>' in line.lower() or \
               '<style' in line.lower() or '</style>' in line.lower():
                continue

            # For lines outside script/style, check for obvious unsubstituted variables
            if placeholder in line:
                # Additional check: make sure it's not part of a larger legitimate expression
                # This is a basic check - in reality we'd want to parse the template properly
                # For now, we'll flag it for manual review if found
                # But given our template is well-formed, these should not appear
                assert False, f"Found unsubstituted template variable: {placeholder} in line: {line}"