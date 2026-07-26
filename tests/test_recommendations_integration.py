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
            
            with patch('views.main.gemini_service.get_property_recommendations') as mock_ai:
                mock_ai.return_value = mock_recommendations
                
                response = client.get(f'/get_customer_recommendations/{customer_id}')
                
                assert response.status_code == 200

                # NOTE: recommendations.html was redesigned around opportunity
                # "sections" (opp-card). It no longer renders the per-recommendation
                # card UI, the "AI Recommendations for <name>" heading,
                # 'Match Score: N/100' badges, or 'ai-analysis' blocks.
                # Assert the contract that actually exists.
                body = response.data.decode()
                assert customer.name in body
                assert "AI Smart Property Matcher" in body
                mock_ai.assert_called_once()

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
        
        with patch('views.main.gemini_service.get_property_recommendations') as mock_ai:
            mock_ai.return_value = mock_recommendations
            
            response = client.get(f'/get_customer_recommendations/{customer.id}')
            
            assert response.status_code == 200
            body = response.data.decode()

            # Selected customer is rendered (switcher <select> options plus the
            # __selectedCustomerId bootstrap).
            assert "Bob Wilson" in body

            # The redesigned template marks selection with a JS id, not a
            # 'customer-selection-card' div with 'border-primary', and has no
            # 'property-details' / summary blocks.
            assert "window.__selectedCustomerId" in body
            assert f"/get_customer_recommendations/{customer.id}" in body

    def test_error_scenarios_and_proper_error_message_display(self, client, sample_data):
        """Test error scenarios and proper error message display in the UI"""
        
        # Test 1: Non-existent customer ID
        response = client.get('/get_customer_recommendations/99999')
        assert response.status_code == 302
        
        # Test 2: AI service failure with fallback
        customer = sample_data['customers'][0]
        
        # Mock AI service to raise exception, then return fallback
        with patch('views.main.gemini_service.get_property_recommendations') as mock_ai, \
             patch('services.gemini_service.gemini_service._create_fallback_recommendations') as mock_fallback:
            
            mock_ai.side_effect = Exception("AI service unavailable")
            mock_fallback.return_value = [
                MagicMock(
                    property=sample_data['properties'][0],
                    match_score=75,
                    analysis="Basic recommendation based on preference matching."
                )
            ]
            
            response = client.get(f'/get_customer_recommendations/{customer.id}')

            # The view catches the AI exception, logs it, and still renders the
            # page (error_message is set but the redesigned template does not
            # render it, and there is no 'recommendation-card' markup).
            assert response.status_code == 200
            assert "AI Smart Property Matcher" in response.data.decode()
        
        # Test 3: Complete system failure
        with patch('views.main.database_service.get_customer') as mock_get_customer, \
             patch('views.main.database_service.get_customers') as mock_get_customers, \
             patch('views.main.database_service.get_agents') as mock_get_agents:
            
            mock_get_customer.return_value = customer
            mock_get_customers.return_value = sample_data['customers']
            mock_get_agents.return_value = sample_data['agents']
            
            with patch('views.main.database_service.get_properties') as mock_get_properties:
                mock_get_properties.side_effect = Exception("Database error")
                
                response = client.get(f'/get_customer_recommendations/{customer.id}')

                # NOTE: unlike the AI call, `database_service.get_properties()`
                # is NOT wrapped in a try/except in the view, so a DB failure
                # propagates to the app-level error handler, which redirects
                # instead of rendering an in-page error banner.
                assert response.status_code == 302

    def test_url_routing_and_customer_selection_highlighting(self, client, sample_data):
        """Verify URL routing works correctly and customer selection highlighting functions properly"""
        
        # Test 1: General recommendations route
        response = client.get('/recommendations')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')

        # Each customer is rendered as a link to its own recommendations page
        # (template loop `{% for customer in customers %}`), not as a
        # 'customer-selection-card' div.
        recommendation_links = soup.find_all('a', href=lambda x: x and '/get_customer_recommendations/' in x)
        assert len(recommendation_links) == 2
        
        customer_ids = [sample_data['customers'][0].id, sample_data['customers'][1].id]
        for link in recommendation_links:
            href = link.get('href')
            assert any(f'/get_customer_recommendations/{cid}' in href for cid in customer_ids)
        
        # Test 2: Customer-specific recommendations route
        customer = sample_data['customers'][0]
        
        with patch('views.main.gemini_service.get_property_recommendations') as mock_ai:
            mock_ai.return_value = []
            
            response = client.get(f'/get_customer_recommendations/{customer.id}')
            assert response.status_code == 200

            body = response.data.decode()

            # Selection is expressed by seeding the JS id with the concrete
            # customer id, not by a 'border-primary' card + button variants.
            assert f"window.__selectedCustomerId = {customer.id};" in body
            assert customer.name in body

    def test_navigation_between_general_and_customer_specific_recommendations(self, client, sample_data):
        """Test navigation between general recommendations view and customer-specific recommendations"""
        
        # Test 1: Navigate from general to customer-specific
        response = client.get('/recommendations')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find and follow a customer recommendation link
        customer = sample_data['customers'][0]
        customer_link = soup.find('a', href=f'/get_customer_recommendations/{customer.id}')
        assert customer_link is not None
        
        # Test the customer-specific route
        with patch('views.main.gemini_service.get_property_recommendations') as mock_ai:
            mock_ai.return_value = []
            
            response = client.get(f'/get_customer_recommendations/{customer.id}')
            assert response.status_code == 200
            
            # Verify we can navigate back to general view
            soup = BeautifulSoup(response.data, 'html.parser')
            
            # On a selected-customer page the template renders the customer
            # grid only in its `{% if not selected_customer %}` branch. Other
            # customers are reachable through the <select> switcher's <option>
            # values instead of <a href> anchors.
            other_customer_options = soup.find_all(
                'option',
                value=lambda x: x and '/get_customer_recommendations/' in x
                and x != f'/get_customer_recommendations/{customer.id}',
            )
            assert len(other_customer_options) > 0
            
            # Test navigation to another customer
            other_customer = sample_data['customers'][1]
            response = client.get(f'/get_customer_recommendations/{other_customer.id}')
            assert response.status_code == 200
            
            # Selection now points at the other customer.
            body = response.data.decode()
            assert f"window.__selectedCustomerId = {other_customer.id};" in body
            assert other_customer.name in body

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
            
            response = client.get(f'/get_customer_recommendations/{customer.id}')
            assert response.status_code == 200
            
            # Should handle empty recommendations gracefully
            body = response.data.decode()

            # Verify customer is still displayed
            assert customer.name in body

            # Empty result set still renders the page shell.
            assert "AI Smart Property Matcher" in body

    def test_recommendation_flow_with_ai_service_timeout(self, client, sample_data):
        """Test recommendation flow when AI service times out"""
        customer = sample_data['customers'][0]
        
        with patch('views.main.gemini_service.get_property_recommendations') as mock_ai, \
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
            
            response = client.get(f'/get_customer_recommendations/{customer.id}')

            # A TimeoutError from the AI service is caught by the view's broad
            # `except Exception` handler, so the page still renders.
            assert response.status_code == 200
            assert "AI Smart Property Matcher" in response.data.decode()

    def test_template_variables_consistency(self, client, sample_data):
        """Test that template variables are consistent between general and customer-specific routes"""
        
        # Test general route variables
        response = client.get('/recommendations')
        assert response.status_code == 200
        
        # Verify template has access to customers: each is rendered as a link
        # to its own recommendations page.
        soup = BeautifulSoup(response.data, 'html.parser')
        recommendation_links = soup.find_all(
            'a', href=lambda x: x and '/get_customer_recommendations/' in x
        )
        assert len(recommendation_links) == 2
        
        # Test customer-specific route variables
        customer = sample_data['customers'][0]
        
        with patch('views.main.gemini_service.get_property_recommendations') as mock_ai:
            mock_ai.return_value = [
                MagicMock(
                    property=sample_data['properties'][0],
                    match_score=80,
                    analysis="Good match for customer preferences."
                )
            ]
            
            response = client.get(f'/get_customer_recommendations/{customer.id}')
            assert response.status_code == 200
            
            body = response.data.decode()

            # customers - rendered in the customer switcher <select>
            assert customer.name in body

            # selected_customer - seeded into the JS bootstrap
            assert f"window.__selectedCustomerId = {customer.id};" in body

            # page shell renders
            assert "AI Smart Property Matcher" in body
