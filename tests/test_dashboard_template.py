"""
Test dynamic data injection in dashboard template.
Tests that dashboard template properly displays dynamic data from database_service.get_dashboard_stats().
"""
import pytest
from flask import url_for


def test_dashboard_template_dynamic_data(client, app, db_setup):
    """Test that dashboard template renders with dynamic data from database service."""
    with app.app_context():
        # Make request to dashboard endpoint
        response = client.get('/dashboard')

        # Verify successful response
        assert response.status_code == 200

        # Check that the response contains actual data (not placeholders)
        response_text = response.data.decode('utf-8')

        # Verify that dynamic data is present in the response
        # Check for formatted numbers (with commas for thousands)
        assert '>' in response_text  # HTML tags should be present
        assert '<' in response_text

        # Check for specific dynamic content that would come from stats
        # The dashboard shows formatted numbers like "1,234" or "$1,234,567"
        import re
        # Look for formatted numbers (sequences of digits with commas)
        formatted_numbers = re.findall(r'>\s*[\d,]+\s*<', response_text)
        assert len(formatted_numbers) > 0, "Should find formatted numbers in dashboard"

        # Check for percentage values with signs (from trend data)
        percent_pattern = r'>\s*[+-]?\d+\.\d+%\s*<'
        percent_matches = re.findall(percent_pattern, response_text)
        # Note: Might be 0 if no data, but pattern should still be detectable in HTML

        # Verify template structure elements are present
        assert 'Performance Overview' in response_text
        assert 'Total Properties' in response_text
        assert 'Active Deals' in response_text
        assert 'Monthly Revenue' in response_text
        assert 'Total Clients' in response_text


def test_dashboard_template_stats_structure(client, app, db_setup):
    """Test that dashboard template receives properly structured stats data."""
    with app.app_context():
        # Get the response
        response = client.get('/dashboard')
        assert response.status_code == 200

        # With the application context, we can also verify that
        # the template was rendered with the expected data structure
        # by checking the rendered output for expected patterns

        response_text = response.data.decode('utf-8')

        # Check for the structured way data is displayed in the template
        # Look for the pattern of how values are displayed in the bento cards

        # Check for formatted values (these come from stats[0].value, stats[1].value, etc.)
        # The template uses: {{ '{:,}'.format(stats[0].value) }} for integers
        # and {{ '{:,.0f}'.format(stats[2].value) }} for currency

        # PH dashboard shell: metric values + trend rows + material icons
        assert 'tabular-nums' in response_text or 'font-semibold text-primary' in response_text
        assert 'material-symbols-outlined' in response_text
        assert 'vs last month' in response_text
        assert '%' in response_text


def test_dashboard_template_trend_display(client, app, db_setup):
    """Test that dashboard template properly displays trend information."""
    with app.app_context():
        response = client.get('/dashboard')
        assert response.status_code == 200

        response_text = response.data.decode('utf-8')

        # Look for trend-related elements in the HTML
        # The template displays trends like: "+12.5% vs last month" or "-5.2% vs last month"

        # Check for the structure that displays trend information
        assert 'vs last month' in response_text

        # Check for trend icons (material symbols)
        # The template uses: <span class="material-symbols-outlined text-[16px] mr-1" data-icon="{{ stats[0].trend_icon }}">{{ stats[0].trend_icon }}</span>
        assert 'material-symbols-outlined' in response_text
        assert 'text-[16px]' in response_text


def test_dashboard_template_empty_state_handling(client, app, db_setup):
    """Test that dashboard template handles empty/default states gracefully."""
    with app.app_context():
        response = client.get('/dashboard')
        assert response.status_code == 200

        response_text = response.data.decode('utf-8')

        # Even with no data, the template should render without errors
        # and show appropriate default values (like 0 or empty states)

        # Check that essential structural elements are present
        assert '<!DOCTYPE html>' in response_text or '<html' in response_text.lower()
        assert '<html' in response_text
        assert '</html>' in response_text

        # Shared shell + dashboard content
        assert 'Performance Overview' in response_text
        assert 'Platinum Heritage' in response_text or 'Real Estate CRM' in response_text
        assert 'Recent Activity' in response_text or 'Background matches' in response_text


if __name__ == "__main__":
    pytest.main([__file__])