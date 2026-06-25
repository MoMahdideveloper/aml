import pytest
from bs4 import BeautifulSoup


class TestRootAndDashboardRoutes:
    """Test cases for root route and dashboard route"""

    def test_root_route_serves_code_html(self, client):
        """Test that root route serves valid HTML from code.html"""
        # Act
        response = client.get('/')

        # Assert
        assert response.status_code == 200
        assert response.mimetype == 'text/html'

        # Parse HTML content
        soup = BeautifulSoup(response.data, 'html.parser')

        # Validate HTML structure
        assert soup.html is not None
        assert soup.html.name == 'html'
        assert soup.find('title').text.strip() == 'Luxe Estate - Dashboard'
        html_tag = soup.html
        assert html_tag.get('lang') == 'en'
        assert soup.find('meta', attrs={'charset': 'utf-8'}) is not None
        assert soup.find('meta', attrs={'name': 'viewport'}) is not None

        # Check for key content elements
        assert soup.find('h1', string='Performance Overview') is not None
        assert soup.find('p', string='Track your real estate portfolio\'s growth and daily operations.') is not None

        # Check for key stats elements
        assert soup.find('span', string='Total Properties') is not None
        assert soup.find('span', string='Active Deals') is not None
        assert soup.find('span', string='Monthly Revenue') is not None
        assert soup.find('span', string='Pending Inquiries') is not None

    def test_dashboard_route_accessibility(self, client, db_setup):
        """Test that dashboard route is accessible and returns 200 status"""
        # Act
        response = client.get('/dashboard')

        # Assert
        assert response.status_code == 200
        assert response.mimetype == 'text/html'

        # Parse HTML content
        soup = BeautifulSoup(response.data, 'html.parser')

        # Validate basic HTML structure
        assert soup.html is not None
        assert soup.html.name == 'html'
        assert soup.find('html').get('lang') == 'en'
        assert soup.find('title').text.strip() == 'Dashboard - Real Estate CRM'

    def test_root_and_dashboard_return_different_content(self, client, db_setup):
        """Test that root route and dashboard route return different content when both are successful"""
        # Act
        root_response = client.get('/')
        dashboard_response = client.get('/dashboard')

        # Assert both routes are accessible
        assert root_response.status_code == 200
        assert dashboard_response.status_code == 200

        # Assert they return different content
        assert root_response.data != dashboard_response.data

        # Parse HTML content
        root_soup = BeautifulSoup(root_response.data, 'html.parser')
        dashboard_soup = BeautifulSoup(dashboard_response.data, 'html.parser')

        # Root should contain Performance Overview
        assert root_soup.find('h1', string='Performance Overview') is not None

        # Dashboard should contain different content
        assert dashboard_soup.find('h1', string='Performance Overview') is None

        # Check for specific content differences
        root_text = root_response.data.decode('utf-8')
        dashboard_text = dashboard_response.data.decode('utf-8')

        assert 'Performance Overview' in root_text
        assert 'Performance Overview' not in dashboard_text
        assert 'Dashboard' in dashboard_text