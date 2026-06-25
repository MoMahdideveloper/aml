"""
Integration tests for customer recommendations routing and template rendering
Tests the complete recommendation generation end-to-end flow
"""
import pytest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
from types import SimpleNamespace

from database import db
from sqlalchemy_models import Agent, Customer, Property


class TestRecommendationsIntegration:
    """Integration tests for the complete recommendation flow"""

    @pytest.fixture
    def sample_data(self, app, db_setup):
        """Create sample data for integration tests"""
        with app.app_context():
            # Create agents
            agent1 = Agent(
                name="John Smith", 
                email="john@example.com", 
                phone="555-0101",
                specialization="Residential"
            )
            agent2 = Agent(
                name="Jane Doe", 
                email="jane@example.com", 
                phone="555-0102",
                specialization="Commercial"
            )
            db.session.add_all([agent1, agent2])
            db.session.commit()

            # Create customers with different preferences
            customer1 = Customer(
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
            customer2 = Customer(
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
            db.session.add_all([customer1, customer2])
            db.session.commit()

            # Create properties with varying characteristics
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
                agent_id=agent1.id,
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
                agent_id=agent2.id,
                neighborhood="Suburbs"
            )
            property3 = Property(
                title="Luxury Penthouse",
                address="789 High St, Downtown",
                price=800000,
                property_type="Condo",
                bedrooms=4,
                bathrooms=3,
                square_feet=2500,
                description="Premium penthouse with city views",
                status="active",
                agent_id=agent1.id,
                neighborhood="Downtown"
            )
            db.session.add_all([property1, property2, property3])
            db.session.commit()

            # Store IDs to avoid detached instance errors
            return {
                'agent_ids': [agent1.id, agent2.id],
                'customer_ids': [customer1.id, customer2.id],
                'property_ids': [property1.id, property2.id, property3.id],
                # Lightweight snapshots for tests that only need attribute access.
                'agents': [
                    SimpleNamespace(id=agent1.id, name=agent1.name, email=agent1.email, phone=agent1.phone, specialization=agent1.specialization),
                    SimpleNamespace(id=agent2.id, name=agent2.name, email=agent2.email, phone=agent2.phone, specialization=agent2.specialization),
                ],
                'customers': [
                    SimpleNamespace(
                        id=customer1.id,
                        name=customer1.name,
                        email=customer1.email,
                        phone=customer1.phone,
                        budget_min=customer1.budget_min,
                        budget_max=customer1.budget_max,
                        preferred_bedrooms=customer1.preferred_bedrooms,
                        preferred_bathrooms=customer1.preferred_bathrooms,
                        preferred_type=customer1.preferred_type,
                        location_preference=customer1.location_preference,
                    ),
                    SimpleNamespace(
                        id=customer2.id,
                        name=customer2.name,
                        email=customer2.email,
                        phone=customer2.phone,
                        budget_min=customer2.budget_min,
                        budget_max=customer2.budget_max,
                        preferred_bedrooms=customer2.preferred_bedrooms,
                        preferred_bathrooms=customer2.preferred_bathrooms,
                        preferred_type=customer2.preferred_type,
                        location_preference=customer2.location_preference,
                    ),
                ],
                'properties': [
                    SimpleNamespace(
                        id=property1.id,
                        title=property1.title,
                        address=property1.address,
                        price=property1.price,
                        property_type=property1.property_type,
                        bedrooms=property1.bedrooms,
                        bathrooms=property1.bathrooms,
                        square_feet=property1.square_feet,
                        description=property1.description,
                        image_filename=getattr(property1, "image_filename", None),
                        neighborhood=property1.neighborhood,
                    ),
                    SimpleNamespace(
                        id=property2.id,
                        title=property2.title,
                        address=property2.address,
                        price=property2.price,
                        property_type=property2.property_type,
                        bedrooms=property2.bedrooms,
                        bathrooms=property2.bathrooms,
                        square_feet=property2.square_feet,
                        description=property2.description,
                        image_filename=getattr(property2, "image_filename", None),
                        neighborhood=property2.neighborhood,
                    ),
                    SimpleNamespace(
                        id=property3.id,
                        title=property3.title,
                        address=property3.address,
                        price=property3.price,
                        property_type=property3.property_type,
                        bedrooms=property3.bedrooms,
                        bathrooms=property3.bathrooms,
                        square_feet=property3.square_feet,
                        description=property3.description,
                        image_filename=getattr(property3, "image_filename", None),
                        neighborhood=property3.neighborhood,
                    ),
                ],
            }

    def get_fresh_objects(self, sample_data):
        """Helper method to get fresh objects from database"""
        customers = [Customer.query.get(cid) for cid in sample_data['customer_ids']]
        properties = [Property.query.get(pid) for pid in sample_data['property_ids']]
        agents = [Agent.query.get(aid) for aid in sample_data['agent_ids']]
        return customers, properties, agents

    def test_complete_recommendation_generation_end_to_end(self, client, sample_data, app):
        """Test complete recommendation generation end-to-end with real customer and property data"""
        customer_id = sample_data['customer_ids'][0]  # Alice Johnson
        
        with app.app_context():
            customers, properties, agents = self.get_fresh_objects(sample_data)
            customer = customers[0]  # Alice Johnson
            property1 = properties[0]  # Downtown House
            property2 = properties[1]  # Suburban Condo
            
            # Mock the AI service to return structured recommendations
            mock_recommendations = [
                MagicMock(
                    property=property1,  # Downtown House - should be high match
                    match_score=85,
                    analysis="This property perfectly matches your budget and location preferences. The 3-bedroom house in Downtown offers excellent value and meets all your criteria."
                ),
                MagicMock(
                    property=property2,  # Suburban Condo - lower match
                    match_score=45,
                    analysis="While this property is within budget, it's in the suburbs rather than your preferred downtown location and has fewer bedrooms than requested."
                )
            ]
            
            with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai:
                mock_ai.return_value = mock_recommendations
                
                response = client.get(f'/recommendations/{customer_id}')
                
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
                match_score_badges = soup.find_all('span', string=lambda text: text and 'Match Score:' in text)
                assert len(match_score_badges) == 2
                assert 'Match Score: 85/100' in str(match_score_badges[0])
                assert 'Match Score: 45/100' in str(match_score_badges[1])
                
                # Verify AI analysis is displayed
                analysis_sections = soup.find_all('div', class_='ai-analysis')
                assert len(analysis_sections) == 2
                assert "perfectly matches your budget" in response.data.decode()
                assert "fewer bedrooms than requested" in response.data.decode()

    def test_template_rendering_with_recommendation_data(self, client, sample_data):
        """Test template rendering with recommendation data including match scores and AI analysis"""
        customer = sample_data['customers'][1]  # Bob Wilson
        
        mock_recommendations = [
            MagicMock(
                property=sample_data['properties'][1],  # Suburban Condo - perfect match
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
            
            # Verify customer preferences are displayed
            customer_cards = soup.find_all('div', class_='customer-selection-card')
            highlighted_card = None
            for card in customer_cards:
                if 'border-primary' in card.get('class', []):
                    highlighted_card = card
                    break
            
            assert highlighted_card is not None, "Selected customer should be highlighted"
            assert "Bob Wilson" in str(highlighted_card)
            
            # Verify property details are rendered correctly
            property_details = soup.find_all('div', class_='property-details')
            assert len(property_details) == 1
            
            # Check for price, bedrooms, bathrooms, square feet
            assert "$320,000" in response.data.decode()
            assert "2 Beds" in response.data.decode()
            assert "1 Baths" in response.data.decode()
            assert "1,200 sqft" in response.data.decode()
            
            # Verify recommendation summary section
            summary_section = soup.find('div', class_='bg-light rounded')
            assert summary_section is not None
            assert "Total Properties Analyzed: 1" in response.data.decode()
            assert "Excellent Matches (80%+): 1" in response.data.decode()

    def test_error_scenarios_and_proper_error_message_display(self, client, sample_data):
        """Test error scenarios and proper error message display in the UI"""
        
        # Test 1: Non-existent customer ID
        response = client.get('/recommendations/99999')
        assert response.status_code == 302
        
        # Test 2: AI service failure with fallback
        customer = sample_data['customers'][0]
        
        # Mock AI service to raise exception, then return fallback
        with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai, \
             patch('services.gemini_service.gemini_service._create_fallback_recommendations') as mock_fallback:
            
            mock_ai.side_effect = Exception("AI service unavailable")
            mock_fallback.return_value = [
                MagicMock(
                    property=sample_data['properties'][0],
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
        
        # Test 3: Complete system failure
        with patch('views.main.database_service.get_customer') as mock_get_customer, \
             patch('views.main.database_service.get_customers') as mock_get_customers, \
             patch('views.main.database_service.get_agents') as mock_get_agents:
            
            mock_get_customer.return_value = customer
            mock_get_customers.return_value = sample_data['customers']
            mock_get_agents.return_value = sample_data['agents']
            
            with patch('views.main.database_service.get_properties') as mock_get_properties:
                mock_get_properties.side_effect = Exception("Database error")
                
                response = client.get(f'/recommendations/{customer.id}')
                
                assert response.status_code == 200
                assert "An error occurred while generating recommendations" in response.data.decode()
                assert "Please try again" in response.data.decode()

    def test_url_routing_and_customer_selection_highlighting(self, client, sample_data):
        """Verify URL routing works correctly and customer selection highlighting functions properly"""
        
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
        
        customer_ids = [sample_data['customers'][0].id, sample_data['customers'][1].id]
        for link in recommendation_links:
            href = link.get('href')
            assert any(f'/recommendations/{cid}' in href for cid in customer_ids)
        
        # Test 2: Customer-specific recommendations route
        customer = sample_data['customers'][0]
        
        with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai:
            mock_ai.return_value = []
            
            response = client.get(f'/recommendations/{customer.id}')
            assert response.status_code == 200
            
            soup = BeautifulSoup(response.data, 'html.parser')
            
            # Verify selected customer is highlighted
            customer_cards = soup.find_all('div', class_='customer-selection-card')
            highlighted_cards = [card for card in customer_cards if 'border-primary' in card.get('class', [])]
            assert len(highlighted_cards) == 1
            
            # Verify the correct customer is highlighted
            highlighted_card = highlighted_cards[0]
            assert customer.name in str(highlighted_card)
            
            # Verify the highlighted customer's button shows different styling
            highlighted_button = highlighted_card.find('a', class_='btn-primary')
            assert highlighted_button is not None
            
            # Verify other customers have outline buttons
            non_highlighted_cards = [card for card in customer_cards if 'border-primary' not in card.get('class', [])]
            for card in non_highlighted_cards:
                outline_button = card.find('a', class_='btn-outline-primary')
                assert outline_button is not None

    def test_navigation_between_general_and_customer_specific_recommendations(self, client, sample_data):
        """Test navigation between general recommendations view and customer-specific recommendations"""
        
        # Test 1: Navigate from general to customer-specific
        response = client.get('/recommendations')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find and follow a customer recommendation link
        customer = sample_data['customers'][0]
        customer_link = soup.find('a', href=f'/recommendations/{customer.id}')
        assert customer_link is not None
        
        # Test the customer-specific route
        with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai:
            mock_ai.return_value = []
            
            response = client.get(f'/recommendations/{customer.id}')
            assert response.status_code == 200
            
            # Verify we can navigate back to general view
            soup = BeautifulSoup(response.data, 'html.parser')
            
            # Look for other customer links (navigation back to general view)
            other_customer_links = soup.find_all('a', href=lambda x: x and '/recommendations/' in x and x != f'/recommendations/{customer.id}')
            assert len(other_customer_links) > 0
            
            # Test navigation to another customer
            other_customer = sample_data['customers'][1]
            response = client.get(f'/recommendations/{other_customer.id}')
            assert response.status_code == 200
            
            # Verify the new customer is now highlighted
            soup = BeautifulSoup(response.data, 'html.parser')
            customer_cards = soup.find_all('div', class_='customer-selection-card')
            highlighted_cards = [card for card in customer_cards if 'border-primary' in card.get('class', [])]
            assert len(highlighted_cards) == 1
            assert other_customer.name in str(highlighted_cards[0])

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
            
            response = client.get(f'/recommendations/{customer.id}')
            assert response.status_code == 200
            
            # Should handle empty recommendations gracefully
            soup = BeautifulSoup(response.data, 'html.parser')
            
            # Verify customer is still displayed
            assert customer.name in response.data.decode()
            
            # Verify no recommendation cards are shown
            recommendation_cards = soup.find_all('div', class_='recommendation-card')
            assert len(recommendation_cards) == 0

    def test_recommendation_flow_with_ai_service_timeout(self, client, sample_data):
        """Test recommendation flow when AI service times out"""
        customer = sample_data['customers'][0]
        
        with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai, \
             patch('services.gemini_service.gemini_service._create_fallback_recommendations') as mock_fallback:
            
            # Simulate timeout
            mock_ai.side_effect = TimeoutError("AI service timeout")
            mock_fallback.return_value = [
                MagicMock(
                    property=sample_data['properties'][0],
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

    def test_template_variables_consistency(self, client, sample_data):
        """Test that template variables are consistent between general and customer-specific routes"""
        
        # Test general route variables
        response = client.get('/recommendations')
        assert response.status_code == 200
        
        # Verify template has access to customers and agents
        soup = BeautifulSoup(response.data, 'html.parser')
        customer_cards = soup.find_all('div', class_='customer-selection-card')
        assert len(customer_cards) == 2
        
        # Test customer-specific route variables
        customer = sample_data['customers'][0]
        
        with patch('services.gemini_service.gemini_service.get_property_recommendations') as mock_ai:
            mock_ai.return_value = [
                MagicMock(
                    property=sample_data['properties'][0],
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
            assert len(customer_cards) == 2
            
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
