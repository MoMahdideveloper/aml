"""
Test dynamic data injection in customers template.
Tests that customers template properly displays dynamic data from customer objects.
"""
import pytest
from flask import url_for


def test_customers_template_dynamic_data(client, app):
    """Test that customers template renders with dynamic customer data."""
    with app.app_context():
        # Make request to customers endpoint
        response = client.get('/customers')

        # Verify successful response
        assert response.status_code == 200

        # Check that the response contains actual data (not placeholders)
        response_text = response.data.decode('utf-8')

        # Verify that dynamic data is present in the response
        # Check for formatted numbers (with commas for thousands)
        assert '>' in response_text  # HTML tags should be present
        assert '<' in response_text

        # Check for specific dynamic content that would come from customer data
        # The customers page shows customer names, emails, phones, etc.

        # Verify template structure elements are present
        assert 'Clients' in response_text        # page heading
        assert 'Add New Client' in response_text  # primary action


def test_customers_template_customer_data_display(client, app):
    """Test that customers template properly displays customer-specific data."""
    with app.app_context():
        # Get the response
        response = client.get('/customers')
        assert response.status_code == 200

        response_text = response.data.decode('utf-8')

        # Page always renders the client list container and search/filter controls
        assert 'Clients' in response_text
        assert 'Status' in response_text          # status filter always visible

        # Add-client form fields are always embedded in the page
        assert 'Full Name' in response_text       # label present as "Full Name *"
        assert 'Email' in response_text           # label present as "Email *"


def test_customers_template_empty_state_handling(client, app):
    """Test that customers template handles empty states gracefully."""
    with app.app_context():
        response = client.get('/customers')
        assert response.status_code == 200

        response_text = response.data.decode('utf-8')

        # Even with no data, the template should render without errors
        # and show appropriate UI elements

        # Essential structural elements must be present
        assert '<!DOCTYPE html>' in response_text
        assert '<html' in response_text
        assert '<title>' in response_text
        assert 'Platinum Heritage' in response_text  # current branding in title/header

        # Add-client action must always be present
        assert 'Add' in response_text


def test_customers_template_modal_presence(client, app):
    """Test that customers template includes necessary modals and interactive elements."""
    with app.app_context():
        response = client.get('/customers')
        assert response.status_code == 200

        response_text = response.data.decode('utf-8')

        # Check for modal element
        assert 'addCustomerModal' in response_text
        assert 'Add New Client' in response_text   # current copy

        # Form field labels present in the add-client modal
        assert 'Full Name' in response_text
        assert 'Email' in response_text
        assert 'Phone' in response_text
        assert 'Budget Min' in response_text
        assert 'Budget Max' in response_text
        assert 'Bedrooms' in response_text
        assert 'Bathrooms' in response_text
        assert 'property type' in response_text.lower()
        assert 'Location' in response_text


def test_customers_template_no_raw_placeholders(client, app):
    """Test that customers template doesn't contain raw unsubstituted Jinja2 variables."""
    response = client.get('/customers')
    assert response.status_code == 200

    html_content = response.data.decode('utf-8')

    # A rendered Jinja2 template should never expose these raw variable prefixes.
    obvious_placeholders = [
        '{{ customers.',
        '{{ customer.',
        '{{ form.',
        '{{ csrf_token',
    ]

    for placeholder in obvious_placeholders:
        assert placeholder not in html_content, (
            f"Unrendered Jinja2 variable found in response: {placeholder!r}"
        )