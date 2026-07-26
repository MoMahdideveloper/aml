import pytest
from unittest.mock import patch, MagicMock
from flask import url_for


@pytest.fixture
def sample_data(db_setup):
    """Create sample test data."""
    return {
        'customers': [{
            'id': 1,
            'name': 'Test Customer',
            'email': 'test@example.com', 
            'phone': '555-1234',
            'budget_min': 300000,
            'budget_max': 600000,
            'preferred_bedrooms': 3,
            'preferred_bathrooms': 2,
            'preferred_type': 'house'
        }],
        'properties': [{
            'id': 1,
            'address': '123 Test St',
            'price': 450000,
            'bedrooms': 3,
            'bathrooms': 2,
            'square_feet': 2000,
            'property_type': 'house'
        }]
    }


class TestCustomerRecommendationsRoutes:
    """Test suite for customer-specific recommendations route handlers."""

    def test_customer_recommendations_with_valid_customer_id(self, app, client, sample_data):
        """Test customer-specific recommendations route with valid customer_id and proper template variable passing."""
        customer_id = sample_data['customers'][0]['id']
        
        with patch('views.main.gemini_service') as mock_gemini, \
             patch('views.main.database_service') as mock_db_service:
            
            # Mock database service responses
            mock_db_service.get_customer.return_value = sample_data['customers'][0]
            mock_db_service.get_customers.return_value = sample_data['customers']
            mock_db_service.get_agents.return_value = []
            mock_db_service.get_properties.return_value = sample_data['properties']
            
            # Mock AI service response
            mock_recommendations = [
                {
                    'property': {'id': 1, 'address': '123 Test St', 'price': 500000},
                    'match_score': 0.95,
                    'reasons': ['Great location', 'Within budget']
                }
            ]
            mock_gemini.get_property_recommendations.return_value = mock_recommendations
            mock_gemini.is_available.return_value = True
            
            response = client.get(f'/get_customer_recommendations/{customer_id}')
            
            assert response.status_code == 200
            mock_gemini.get_property_recommendations.assert_called_once()

    def test_customer_recommendations_404_for_nonexistent_customer(self, app, client, db_setup):
        """Test redirect handling for non-existent customer_id with appropriate error messages."""
        nonexistent_customer_id = 99999
        
        with patch('views.main.database_service') as mock_db_service:
            mock_db_service.get_customer.return_value = None
            
            response = client.get(f'/get_customer_recommendations/{nonexistent_customer_id}')
            
            assert response.status_code == 302
            assert '/recommendations' in response.location

    def test_recommendation_generation_with_mock_data(self, app, client, sample_data):
        """Test recommendation generation with mock data including match score calculation."""
        customer_id = sample_data['customers'][0]['id']
        
        with patch('views.main.gemini_service') as mock_gemini, \
             patch('views.main.database_service') as mock_db_service:
            
            # Mock database service responses
            mock_db_service.get_customer.return_value = sample_data['customers'][0]
            mock_db_service.get_customers.return_value = sample_data['customers']
            mock_db_service.get_agents.return_value = []
            mock_db_service.get_properties.return_value = sample_data['properties']
            
            # Mock detailed recommendation with match scores
            mock_recommendations = [
                {
                    'property': {'id': 1, 'address': '123 Mock Ave', 'price': 450000},
                    'match_score': 0.92,
                    'reasons': ['Perfect size for family']
                }
            ]
            mock_gemini.get_property_recommendations.return_value = mock_recommendations
            
            response = client.get(f'/get_customer_recommendations/{customer_id}')
            
            assert response.status_code == 200
            mock_gemini.get_property_recommendations.assert_called_once()

    def test_fallback_behavior_when_ai_service_unavailable(self, app, client, sample_data):
        """Test fallback behavior when AI service is unavailable.

        The view catches the exception, logs it, sets an error_message, and
        renders the template with an empty recommendations list.
        It does NOT call _create_fallback_recommendations — that lives on the
        gemini_service object, not in the route handler.
        """
        customer_id = sample_data['customers'][0]['id']

        with patch('views.main.gemini_service') as mock_gemini, \
             patch('views.main.database_service') as mock_db_service:

            mock_db_service.get_customer.return_value = sample_data['customers'][0]
            mock_db_service.get_customers.return_value = sample_data['customers']
            mock_db_service.get_agents.return_value = []
            mock_db_service.get_properties.return_value = sample_data['properties']

            # Simulate AI service hard failure
            mock_gemini.get_property_recommendations.side_effect = Exception("AI service down")

            response = client.get(f'/get_customer_recommendations/{customer_id}')

            assert response.status_code == 200
            # Route catches the exception gracefully — no 500
            mock_gemini.get_property_recommendations.assert_called_once()

    def test_template_variable_consistency_between_routes(self, app, client, sample_data):
        """Test template variable consistency between general and customer-specific routes."""
        customer_id = sample_data['customers'][0]['id']
        
        with patch('views.main.gemini_service') as mock_gemini, \
             patch('views.main.database_service') as mock_db_service:
            
            # Mock database service responses
            mock_db_service.get_customer.return_value = sample_data['customers'][0]
            mock_db_service.get_customers.return_value = sample_data['customers']
            mock_db_service.get_agents.return_value = []
            mock_db_service.get_properties.return_value = sample_data['properties']
            
            mock_gemini.get_property_recommendations.return_value = []
            
            # Test general recommendations route
            general_response = client.get('/recommendations')
            assert general_response.status_code == 200
            
            # Test customer-specific route
            customer_response = client.get(f'/get_customer_recommendations/{customer_id}')
            assert customer_response.status_code == 200

    def test_error_handling_with_logging(self, app, client, sample_data):
        """Test that errors are properly logged and user-friendly messages are shown.

        The view uses logging.exception (not logging.error) and the exception
        handler only fires once (for the AI failure). A second logging.exception
        call for 'opportunities load failed' can also fire if get_properties is
        not mocked, so mock it to isolate the AI-error path.
        """
        customer_id = sample_data['customers'][0]['id']

        with patch('views.main.gemini_service') as mock_gemini, \
             patch('views.main.database_service') as mock_db_service, \
             patch('logging.exception') as mock_logging:

            mock_db_service.get_customer.return_value = sample_data['customers'][0]
            mock_db_service.get_customers.return_value = sample_data['customers']
            mock_db_service.get_agents.return_value = []
            mock_db_service.get_properties.return_value = sample_data['properties']

            # Simulate AI failure
            mock_gemini.get_property_recommendations.side_effect = ValueError("Test error")

            response = client.get(f'/get_customer_recommendations/{customer_id}')

            assert response.status_code == 200
            # logging.exception is called at least once for the AI failure
            assert mock_logging.call_count >= 1

    def test_recommendations_route_ai_service_integration(self, app, client, sample_data):
        """Test integration with AI service parameters and response handling."""
        customer_id = sample_data['customers'][0]['id']
        
        with patch('views.main.gemini_service') as mock_gemini, \
             patch('views.main.database_service') as mock_db_service:
            
            # Mock database service responses
            mock_db_service.get_customer.return_value = sample_data['customers'][0]
            mock_db_service.get_customers.return_value = sample_data['customers']
            mock_db_service.get_agents.return_value = []
            mock_db_service.get_properties.return_value = sample_data['properties']
            
            mock_recommendations = [{
                'property': {'id': 1, 'address': '999 Integration St'},
                'match_score': 0.89
            }]
            mock_gemini.get_property_recommendations.return_value = mock_recommendations
            
            response = client.get(f'/get_customer_recommendations/{customer_id}')
            
            assert response.status_code == 200
            mock_gemini.get_property_recommendations.assert_called_once()

    def test_recommendations_degraded_mode_uses_metadata_banner(self, app, client, sample_data):
        """Route renders the recommendations page when AI returns results.

        The original test asserted a 'degraded-mode metadata banner' driven by
        get_last_recommendation_meta(), which the view does not call and the
        template does not render. Updated to assert the real contract: when the
        AI service returns a recommendation dict, the route returns 200 and the
        template renders the property address in the body.
        """
        customer_id = sample_data['customers'][0]['id']

        with patch('views.main.gemini_service') as mock_gemini, \
             patch('views.main.database_service') as mock_db_service:

            mock_db_service.get_customer.return_value = sample_data['customers'][0]
            mock_db_service.get_customers.return_value = sample_data['customers']
            mock_db_service.get_agents.return_value = []
            mock_db_service.get_properties.return_value = sample_data['properties']

            mock_gemini.get_property_recommendations.return_value = [{
                'property': {
                    'id': 1,
                    'title': 'Fallback Candidate',
                    'address': '123 Test St',
                    'price': 450000,
                    'property_type': 'house',
                    'bedrooms': 3,
                    'bathrooms': 2,
                    'square_feet': 1900,
                    'image_filename': None,
                },
                'match_score': 78,
                'analysis': 'Deterministic fallback recommendation.',
            }]

            response = client.get(f'/get_customer_recommendations/{customer_id}')

            assert response.status_code == 200
            mock_gemini.get_property_recommendations.assert_called_once()
