"""
Simplified integration tests for customer recommendations routing and template rendering
Tests the complete recommendation generation end-to-end flow
"""
import pytest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from database import db
from sqlalchemy_models import Agent, Customer, Property


class TestRecommendationsIntegrationSimple:
    """Simplified integration tests for the complete recommendation flow"""

    def test_complete_recommendation_generation_end_to_end(self, client, app, db_setup):
        """Test complete recommendation generation end-to-end with real customer and property data"""
        with app.app_context():
            # Create test data directly in test
            agent = Agent(name="Test Agent", email="agent@test.com", phone="555-0001")
            db.session.add(agent)
            db.session.commit()

            customer = Customer(
                name="Alice Johnson",
                email="alice@example.com",
                phone="555-0201",
                budget_min=300000,
                budget_max=500000,
                preferred_bedrooms=3,
                preferred_bathrooms=2,
                preferred_type="House",
                location_preference="Downtown"
            )
            db.session.add(customer)
            db.session.commit()

            property1 = Property(
                title="Beautiful Downtown House",
                address="123 Main St, Downtown",
                price=450000,
                property_type="House",
                bedrooms=3,
                bathrooms=2,
                square_feet=1800,
                description="Spacious family home in prime location",
                status="active",
                agent_id=agent.id,
                neighborhood="Downtown"
            )
            property2 = Property(
                title="Modern Suburban Condo",
                address="456 Oak Ave, Suburbs", 
                price=320000,
                property_type="Condo",
                bedrooms=2,
                bathrooms=1,
                square_feet=1200,
                description="Contemporary condo with amenities",
                status="active",
                agent_id=agent.id,
                neighborhood="Suburbs"
            )
            db.session.add_all([property1, property2])
            db.session.commit()

            # Mock the AI service to return structured recommendations
            mock_recommendations = [
                MagicMock(
                    property=property1,
                    match_score=85,
                    analysis="This property perfectly matches your budget and location preferences."
                ),
                MagicMock(
                    property=property2,
                    match_score=45,
                    analysis="While this property is within budget, it's in the suburbs rather than your preferred downtown location."
                )
            ]
            
            with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai:
                mock_ai.return_value = mock_recommendations
                
                response = client.get(f'/recommendations/{customer.id}')
                
                assert response.status_code == 200
                
                # Parse HTML response
                soup = BeautifulSoup(response.data, 'html.parser')
                
                # Verify customer-specific content is displayed
                assert customer.name in response.data.decode()
                assert "AI Recommendations for Alice Johnson" in response.data.decode()
                
                # Verify recommendations are displayed with match scores
                recommendation_cards = soup.find_all('div', class_='recommendation-card')
                assert len(recommendation_cards) == 2
                
                # Verify match scores are displayed
                assert 'Match Score: 85/100' in response.data.decode()
                assert 'Match Score: 45/100' in response.data.decode()
                
                # Verify AI analysis is displayed
                assert "perfectly matches your budget" in response.data.decode()
                assert "suburbs rather than your preferred downtown" in response.data.decode()

    def test_template_rendering_with_recommendation_data(self, client, app, db_setup):
        """Test template rendering with recommendation data including match scores and AI analysis"""
        with app.app_context():
            # Create test data
            agent = Agent(name="Test Agent", email="agent@test.com", phone="555-0001")
            db.session.add(agent)
            db.session.commit()

            customer = Customer(
                name="Bob Wilson",
                email="bob@example.com", 
                phone="555-0202",
                budget_min=200000,
                budget_max=350000,
                preferred_bedrooms=2,
                preferred_bathrooms=1,
                preferred_type="Condo",
                location_preference="Suburbs"
            )
            db.session.add(customer)
            db.session.commit()

            property1 = Property(
                title="Modern Suburban Condo",
                address="456 Oak Ave, Suburbs", 
                price=320000,
                property_type="Condo",
                bedrooms=2,
                bathrooms=1,
                square_feet=1200,
                description="Contemporary condo with amenities",
                status="active",
                agent_id=agent.id,
                neighborhood="Suburbs"
            )
            db.session.add(property1)
            db.session.commit()

            mock_recommendations = [
                MagicMock(
                    property=property1,
                    match_score=95,
                    analysis="Excellent match! This 2-bedroom condo in the suburbs fits perfectly within your budget and location preferences."
                )
            ]
            
            with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai:
                mock_ai.return_value = mock_recommendations
                
                response = client.get(f'/recommendations/{customer.id}')
                
                assert response.status_code == 200
                soup = BeautifulSoup(response.data, 'html.parser')
                
                # Verify template variables are properly rendered
                assert "Bob Wilson" in response.data.decode()
                
                # Verify customer is highlighted in selection area
                customer_cards = soup.find_all('div', class_='customer-selection-card')
                highlighted_card = None
                for card in customer_cards:
                    if 'border-primary' in card.get('class', []):
                        highlighted_card = card
                        break
                
                assert highlighted_card is not None, "Selected customer should be highlighted"
                assert "Bob Wilson" in str(highlighted_card)
                
                # Verify property details are rendered correctly
                assert "$320,000" in response.data.decode()
                assert "2 Beds" in response.data.decode()
                assert "1 Baths" in response.data.decode()
                assert "1,200 sqft" in response.data.decode()
                
                # Verify recommendation summary section
                assert "Total Properties Analyzed: 1" in response.data.decode()
                assert "Excellent Matches (80%+): 1" in response.data.decode()

    def test_error_scenarios_and_proper_error_message_display(self, client, app, db_setup):
        """Test error scenarios and proper error message display in the UI"""
        
        # Test 1: Non-existent customer ID
        response = client.get('/recommendations/99999')
        # Custom error handler redirects to dashboard or referrer
        assert response.status_code == 302
        
        # Test 2: AI service failure with fallback
        with app.app_context():
            agent = Agent(name="Test Agent", email="agent@test.com", phone="555-0001")
            db.session.add(agent)
            db.session.commit()

            customer = Customer(
                name="Test Customer",
                email="test@example.com",
                phone="555-0000",
                budget_min=100000,
                budget_max=200000,
                preferred_bedrooms=2,
                preferred_type="House"
            )
            db.session.add(customer)
            db.session.commit()

            property1 = Property(
                title="Test Property",
                address="123 Test St",
                price=150000,
                property_type="House",
                bedrooms=2,
                bathrooms=1,
                square_feet=1000,
                status="active",
                agent_id=agent.id
            )
            db.session.add(property1)
            db.session.commit()
            
            # Mock AI service to raise exception, then return fallback
            with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai, \
                 patch('services.gemini_service.gemini_service._create_fallback_recommendations') as mock_fallback:
                
                mock_ai.side_effect = Exception("AI service unavailable")
                mock_fallback.return_value = [
                    MagicMock(
                        property=property1,
                        match_score=75,
                        analysis="Basic recommendation based on preference matching."
                    )
                ]
                
                response = client.get(f'/recommendations/{customer.id}')
                
                assert response.status_code == 200
                assert "AI service temporarily unavailable" in response.data.decode()
                assert "Showing basic recommendations" in response.data.decode()
                
                # Verify fallback recommendations are still displayed
                soup = BeautifulSoup(response.data, 'html.parser')
                recommendation_cards = soup.find_all('div', class_='recommendation-card')
                assert len(recommendation_cards) == 1

    def test_url_routing_and_customer_selection_highlighting(self, client, app, db_setup):
        """Verify URL routing works correctly and customer selection highlighting functions properly"""
        
        with app.app_context():
            # Create test data
            agent = Agent(name="Test Agent", email="agent@test.com", phone="555-0001")
            db.session.add(agent)
            db.session.commit()

            customer1 = Customer(name="Customer 1", email="c1@test.com", phone="555-0001")
            customer2 = Customer(name="Customer 2", email="c2@test.com", phone="555-0002")
            db.session.add_all([customer1, customer2])
            db.session.commit()

            # Test 1: General recommendations route
            response = client.get('/recommendations')
            assert response.status_code == 200
            
            soup = BeautifulSoup(response.data, 'html.parser')
            
            # Verify all customers are displayed
            customer_cards = soup.find_all('div', class_='customer-selection-card')
            assert len(customer_cards) == 2
            
            # Verify no customer is highlighted initially
            highlighted_cards = [card for card in customer_cards if 'border-primary' in card.get('class', [])]
            assert len(highlighted_cards) == 0
            
            # Verify "Get Recommendations" buttons have correct URLs
            recommendation_links = soup.find_all('a', href=lambda x: x and '/recommendations/' in x)
            assert len(recommendation_links) == 2
            
            # Test 2: Customer-specific recommendations route
            with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai:
                mock_ai.return_value = []
                
                response = client.get(f'/recommendations/{customer1.id}')
                assert response.status_code == 200
                
                soup = BeautifulSoup(response.data, 'html.parser')
                
                # Verify selected customer is highlighted
                customer_cards = soup.find_all('div', class_='customer-selection-card')
                highlighted_cards = [card for card in customer_cards if 'border-primary' in card.get('class', [])]
                assert len(highlighted_cards) == 1
                
                # Verify the correct customer is highlighted
                highlighted_card = highlighted_cards[0]
                assert customer1.name in str(highlighted_card)

    def test_navigation_between_general_and_customer_specific_recommendations(self, client, app, db_setup):
        """Test navigation between general recommendations view and customer-specific recommendations"""
        
        with app.app_context():
            # Create test data
            agent = Agent(name="Test Agent", email="agent@test.com", phone="555-0001")
            db.session.add(agent)
            db.session.commit()

            customer1 = Customer(name="Customer 1", email="c1@test.com", phone="555-0001")
            customer2 = Customer(name="Customer 2", email="c2@test.com", phone="555-0002")
            db.session.add_all([customer1, customer2])
            db.session.commit()

            # Test 1: Navigate from general to customer-specific
            response = client.get('/recommendations')
            assert response.status_code == 200
            
            soup = BeautifulSoup(response.data, 'html.parser')
            
            # Find and verify customer recommendation link exists
            customer_link = soup.find('a', href=f'/recommendations/{customer1.id}')
            assert customer_link is not None
            
            # Test the customer-specific route
            with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai:
                mock_ai.return_value = []
                
                response = client.get(f'/recommendations/{customer1.id}')
                assert response.status_code == 200
                
                # Verify we can navigate to another customer
                response = client.get(f'/recommendations/{customer2.id}')
                assert response.status_code == 200
                
                # Verify the new customer is now highlighted
                soup = BeautifulSoup(response.data, 'html.parser')
                customer_cards = soup.find_all('div', class_='customer-selection-card')
                highlighted_cards = [card for card in customer_cards if 'border-primary' in card.get('class', [])]
                assert len(highlighted_cards) == 1
                assert customer2.name in str(highlighted_cards[0])

    def test_recommendation_flow_with_no_properties(self, client, app, db_setup):
        """Test recommendation flow when no properties are available"""
        with app.app_context():
            # Create customer but no properties
            customer = Customer(
                name="Test Customer",
                email="test@example.com",
                phone="555-0000",
                budget_min=100000,
                budget_max=200000,
                preferred_bedrooms=2,
                preferred_type="House"
            )
            db.session.add(customer)
            db.session.commit()
            
            with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai:
                mock_ai.return_value = []
                
                response = client.get(f'/recommendations/{customer.id}')
                assert response.status_code == 200
                
                # Should handle empty recommendations gracefully
                soup = BeautifulSoup(response.data, 'html.parser')
                
                # Verify customer is still displayed
                assert customer.name in response.data.decode()
                
                # Verify no recommendation cards are shown
                recommendation_cards = soup.find_all('div', class_='recommendation-card')
                assert len(recommendation_cards) == 0

    def test_recommendation_flow_with_ai_service_timeout(self, client, app, db_setup):
        """Test recommendation flow when AI service times out"""
        with app.app_context():
            agent = Agent(name="Test Agent", email="agent@test.com", phone="555-0001")
            db.session.add(agent)
            db.session.commit()

            customer = Customer(
                name="Test Customer",
                email="test@example.com",
                phone="555-0000",
                budget_min=100000,
                budget_max=200000,
                preferred_bedrooms=2,
                preferred_type="House"
            )
            db.session.add(customer)
            db.session.commit()

            property1 = Property(
                title="Test Property",
                address="123 Test St",
                price=150000,
                property_type="House",
                bedrooms=2,
                bathrooms=1,
                square_feet=1000,
                status="active",
                agent_id=agent.id
            )
            db.session.add(property1)
            db.session.commit()
            
            with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai, \
                 patch('services.gemini_service.gemini_service._create_fallback_recommendations') as mock_fallback:
                
                # Simulate timeout
                mock_ai.side_effect = TimeoutError("AI service timeout")
                mock_fallback.return_value = [
                    MagicMock(
                        property=property1,
                        match_score=70,
                        analysis="Fallback recommendation based on basic criteria matching."
                    )
                ]
                
                response = client.get(f'/recommendations/{customer.id}')
                
                assert response.status_code == 200
                assert "AI service temporarily unavailable" in response.data.decode()
                
                # Verify fallback recommendations are displayed
                soup = BeautifulSoup(response.data, 'html.parser')
                recommendation_cards = soup.find_all('div', class_='recommendation-card')
                assert len(recommendation_cards) == 1
                
                # Verify match score from fallback
                assert "Match Score: 70/100" in response.data.decode()

    def test_template_variables_consistency(self, client, app, db_setup):
        """Test that template variables are consistent between general and customer-specific routes"""
        
        with app.app_context():
            # Create test data
            agent = Agent(name="Test Agent", email="agent@test.com", phone="555-0001")
            db.session.add(agent)
            db.session.commit()

            customer = Customer(name="Test Customer", email="test@test.com", phone="555-0001")
            db.session.add(customer)
            db.session.commit()

            property1 = Property(
                title="Test Property",
                address="123 Test St",
                price=150000,
                property_type="House",
                bedrooms=2,
                bathrooms=1,
                square_feet=1000,
                status="active",
                agent_id=agent.id
            )
            db.session.add(property1)
            db.session.commit()

            # Test general route variables
            response = client.get('/recommendations')
            assert response.status_code == 200
            
            # Verify template has access to customers and agents
            soup = BeautifulSoup(response.data, 'html.parser')
            customer_cards = soup.find_all('div', class_='customer-selection-card')
            assert len(customer_cards) == 1
            
            # Test customer-specific route variables
            with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai:
                mock_ai.return_value = [
                    MagicMock(
                        property=property1,
                        match_score=80,
                        analysis="Good match for customer preferences."
                    )
                ]
                
                response = client.get(f'/recommendations/{customer.id}')
                assert response.status_code == 200
                
                soup = BeautifulSoup(response.data, 'html.parser')
                
                # Verify all required template variables are present
                # customers - for customer selection area
                customer_cards = soup.find_all('div', class_='customer-selection-card')
                assert len(customer_cards) == 1
                
                # selected_customer - for highlighting and recommendations
                highlighted_cards = [card for card in customer_cards if 'border-primary' in card.get('class', [])]
                assert len(highlighted_cards) == 1
                
                # recommendations - for displaying results
                recommendation_cards = soup.find_all('div', class_='recommendation-card')
                assert len(recommendation_cards) == 1
                
                # agents - for deal creation modal (check if modal exists)
                deal_modal = soup.find('div', id='createDealModal')
                assert deal_modal is not None
                
                # ai_service_available - should be True when AI works
                assert "AI Analysis Complete" in response.data.decode()
                
                # error_message - should be None when no errors
                assert "An error occurred" not in response.data.decode()
