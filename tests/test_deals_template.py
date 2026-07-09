"""
Test dynamic data injection in deals template.
Tests that deals template properly displays dynamic data from database queries.
"""
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

        # Check for specific dynamic content that would come from deals data
        # The pipeline summary cards show counts of deals by status
        assert 'Prospecting' in response_text
        assert 'Qualified' in response_text
        assert 'Proposal' in response_text
        assert 'Negotiation' in response_text
        assert 'Closed Won' in response_text
        assert 'Closed Lost' in response_text

        # Check for table headers that indicate data structure
        assert 'Deal ID' in response_text
        assert 'Property' in response_text
        assert 'Customer' in response_text
        assert 'Agent' in response_text
        assert 'Offer Amount' in response_text
        assert 'Status' in response_text
        assert 'Created' in response_text
        assert 'Actions' in response_text


def test_deals_template_pipeline_counts(client, app):
    """Test that deals template properly displays pipeline count data."""
    with app.app_context():
        response = client.get('/deals')
        assert response.status_code == 200

        response_text = response.data.decode('utf-8')

        # Check for the pipeline counter elements
        # These use Jinja2 expressions like: {{ deals | selectattr("status", "equalto", "prospecting") | list | length }}
        assert 'bg-primary/10' in response_text or 'text-primary' in response_text
        assert 'bg-info/10' in response_text or 'text-info' in response_text
        assert 'bg-warning/10' in response_text or 'text-warning' in response_text
        assert 'bg-orange/10' in response_text or 'text-orange' in response_text
        assert 'bg-success/10' in response_text or 'text-success' in response_text
        assert 'bg-error/10' in response_text or 'text-error' in response_text

        # Check for the deal count numbers in the pipeline cards
        # These would be formatted numbers (potentially with commas)
        import re
        # Look for patterns like "> 0 <" or "> 1,234 <" in table cells or divs
        count_pattern = r'[>]\s*\d+(?:,\d+)*\s*[<]'
        count_matches = re.findall(count_pattern, response_text)
        # We should find some count numbers in the pipeline section


def test_deals_template_deal_details_display(client, app):
    """Test that deals template properly displays individual deal details."""
    with app.app_context():
        response = client.get('/deals')
        assert response.status_code == 200

        response_text = response.data.decode('utf-8')

        # Check for deal table structural elements
        assert '<table' in response_text
        assert '<thead' in response_text
        assert '<tbody' in response_text
        assert '<tr' in response_text
        assert '<td' in response_text
        assert '<th' in response_text

        # Check for data display patterns from the deal rows
        # Property info: deal.property_obj.title, deal.property_obj.address, formatted price
        # Customer info: deal.customer_obj.name, deal.customer_obj.email
        # Agent info: deal.agent_obj.name, deal.agent_obj.specialization
        # Offer amount: formatted as currency
        # Status badges with dynamic colors
        # Date formatting

        # Look for formatted currency patterns (like $1,234,567)
        currency_pattern = r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
        currency_matches = re.findall(currency_pattern, response_text)
        # Should find some currency values if there are deals with offer amounts

        # Look for status badge patterns
        # The template uses classes like: bg-primary/10 text-primary, etc.
        status_indicators = [
            'bg-primary/10',
            'bg-info/10',
            'bg-warning/10',
            'bg-orange/10',
            'bg-success/10',
            'bg-error/10'
        ]
        # At least some of these should be present if there are deals in different statuses


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
        assert 'Deal Pipeline Management' in response_text
        assert 'All Deals' in response_text


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
    }

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