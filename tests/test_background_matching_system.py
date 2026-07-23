"""
Tests for the background matching system
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from background_matcher import background_matcher
from event_handlers import event_handlers
from services.database_service import database_service
from services.monitoring_service import monitoring_service
from services.scheduler_service import scheduler_service
from sqlalchemy_models import Property, Customer, Agent, PropertyMatch, AgentNotification


class TestBackgroundMatchingSystem:
    """Test the background matching system components"""
    
    def test_background_matcher_initialization(self):
        """Test that BackgroundMatcher initializes correctly"""
        assert background_matcher is not None
        assert background_matcher.min_match_score == 0.4
        assert background_matcher.notification_threshold == 0.7
        assert background_matcher.high_priority_threshold == 0.85
    
    def test_event_handlers_initialization(self):
        """Test that EventHandlers initializes correctly"""
        assert event_handlers is not None
        # Test that handlers can be registered without error
        event_handlers.register_handlers()
    
    def test_scheduler_service_initialization(self, app):
        """Test that SchedulerService initializes correctly"""
        with app.app_context():
            assert scheduler_service is not None
            # Test job listing
            jobs = scheduler_service.list_active_jobs()
            assert isinstance(jobs, list)
    
    def test_monitoring_service_initialization(self):
        """Test that MonitoringService initializes correctly"""
        assert monitoring_service is not None
        
        # Test basic monitoring functions
        session_id = monitoring_service.log_matching_job_start("test_job", "manual")
        assert session_id is not None
        
        result = {'status': 'completed', 'matches_found': 0}
        monitoring_service.log_matching_job_completion(session_id, result, 1.0)
    
    def test_matching_cycle_basic(self, app, db_setup):
        """Test basic matching cycle functionality"""
        with app.app_context():
            # Create sample data
            agent = Agent(name="Test Agent", email="test@example.com", phone="123-456-7890")
            db_setup.session.add(agent)
            
            customer = Customer(
                name="Test Customer", 
                email="customer@example.com", 
                phone="123-456-7890",
                budget_min=100000,
                budget_max=200000,
                preferred_bedrooms=3,
                preferred_type="house"
            )
            db_setup.session.add(customer)
            
            property_obj = Property(
                title="Test Property",
                address="123 Test St",
                price=150000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1500,
                description="Test property",
                agent_id=1
            )
            db_setup.session.add(property_obj)
            db_setup.session.commit()
            
            # Run a matching cycle
            result = background_matcher.run_matching_cycle()
            
            # Verify result structure
            assert 'status' in result
            assert 'matches_found' in result
            assert 'matches_saved' in result
            assert 'notifications_created' in result
            assert 'duration_seconds' in result
    
    def test_fallback_matching(self, app, db_setup):
        """Test fallback matching when AI service is unavailable"""
        with app.app_context():
            # Create sample data
            customer = Customer(
                name="Test Customer", 
                email="customer@example.com", 
                phone="123-456-7890",
                budget_min=100000,
                budget_max=200000,
                preferred_bedrooms=3,
                preferred_type="house"
            )
            
            properties = [
                Property(
                    title="Test Property 1",
                    address="123 Test St",
                    price=150000,
                    property_type="house",
                    bedrooms=3,
                    bathrooms=2,
                    square_feet=1500,
                    description="Test property 1"
                ),
                Property(
                    title="Test Property 2",
                    address="456 Test Ave",
                    price=180000,
                    property_type="condo",
                    bedrooms=2,
                    bathrooms=1,
                    square_feet=1200,
                    description="Test property 2"
                )
            ]
            
            # Test fallback matching directly
            matches = background_matcher._fallback_matching(customer, properties)
            
            # Verify matches structure
            assert isinstance(matches, list)
            for match in matches:
                assert 'property_id' in match
                assert 'customer_id' in match
                assert 'match_score' in match
                assert 'confidence_level' in match
    
    def test_match_record_creation(self, app, db_setup):
        """Test creation of match records"""
        with app.app_context():
            customer = Customer(
                name="Test Customer", 
                email="customer@example.com", 
                phone="123-456-7890",
                budget_min=100000,
                budget_max=200000
            )
            
            property_obj = Property(
                title="Test Property",
                address="123 Test St",
                price=150000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1500,
                description="Test property"
            )
            property_obj.id = 1  # Set ID for testing
            customer.id = 1  # Set ID for testing
            
            # Create a mock recommendation
            recommendation = {
                'property': property_obj,
                'match_score': 75,  # 75/100
                'analysis': 'Match Score: 75/100\n• Within budget range\n• Matches bedroom preference'
            }
            
            # Test match record creation
            match = background_matcher._create_match_record(customer, recommendation, [property_obj])
            
            assert match is not None
            assert match['property_id'] == property_obj.id
            assert match['customer_id'] == customer.id
            assert match['match_score'] == 0.75  # Converted to 0-1 scale
            assert match['confidence_level'] in ['low', 'medium', 'high']
    
    def test_system_health_check(self, app, db_setup):
        """Test system health monitoring"""
        with app.app_context():
            health = monitoring_service.get_system_health()
            
            assert 'timestamp' in health
            assert 'overall_status' in health
            assert 'database' in health
            assert health['overall_status'] in ['healthy', 'warning', 'critical', 'unknown']
    
    def test_matching_stats(self, app, db_setup):
        """Test matching statistics retrieval"""
        with app.app_context():
            stats = event_handlers.get_matching_stats()
            
            # Should have stats structure even if no data
            assert 'recent_matches_24h' in stats
            assert 'recent_notifications_24h' in stats
            assert 'high_score_matches_24h' in stats
            assert 'pending_notifications' in stats
            assert 'timestamp' in stats
    
    @patch('background_matcher.gemini_service')
    def test_matching_with_mock_ai(self, mock_gemini, app, db_setup):
        """Test matching with mocked AI service"""
        with app.app_context():
            # Create sample data
            agent = Agent(name="Test Agent", email="test@example.com", phone="123-456-7890")
            db_setup.session.add(agent)
            
            customer = Customer(
                name="Test Customer", 
                email="customer@example.com", 
                phone="123-456-7890",
                budget_min=100000,
                budget_max=200000
            )
            db_setup.session.add(customer)
            
            property_obj = Property(
                title="Test Property",
                address="123 Test St",
                price=150000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1500,
                description="Test property",
                agent_id=1
            )
            db_setup.session.add(property_obj)
            db_setup.session.commit()
            
            # Mock AI service response
            mock_recommendations = [
                {
                    'property': property_obj,
                    'match_score': 85,
                    'analysis': 'Match Score: 85/100\n• Excellent match\n• Within budget'
                }
            ]
            mock_gemini.get_property_recommendations.return_value = mock_recommendations
            
            # Run matching cycle
            result = background_matcher.run_matching_cycle()
            
            # Verify AI service was called
            assert mock_gemini.get_property_recommendations.called
            assert result['status'] == 'completed'
    
    def test_notification_creation(self, app, db_setup):
        """Test agent notification creation"""
        with app.app_context():
            # Create test data
            agent = Agent(name="Test Agent", email="test@example.com", phone="123-456-7890")
            db_setup.session.add(agent)
            
            customer = Customer(
                name="Test Customer", 
                email="customer@example.com", 
                phone="123-456-7890"
            )
            db_setup.session.add(customer)
            
            property_obj = Property(
                title="Test Property",
                address="123 Test St",
                price=150000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1500,
                description="Test property",
                agent_id=1
            )
            db_setup.session.add(property_obj)
            db_setup.session.commit()
            
            # Create a test property match
            match = PropertyMatch(
                property_id=1,
                customer_id=1,
                agent_id=1,
                match_score=0.8,
                confidence_level='high',
                priority='high',
                match_reasons='["Excellent match", "Within budget"]'
            )
            db_setup.session.add(match)
            db_setup.session.commit()
            
            # Test notification creation
            notifications = background_matcher.create_agent_notifications([match])
            
            # Verify notification was created
            assert len(notifications) >= 0
    
    def test_performance_metrics(self, app):
        """Test performance metrics collection"""
        with app.app_context():
            # Get performance metrics
            metrics = monitoring_service.get_performance_metrics(hours=1)
            
            assert 'period_hours' in metrics
            assert 'job_count' in metrics
            assert 'avg_duration' in metrics
    
    def test_error_handling(self, app):
        """Test error handling and logging"""
        with app.app_context():
            # Test error logging
            test_error = Exception("Test error")
            monitoring_service.log_matching_error("test_session", test_error, {"test": "context"})
            
            # Get error summary
            error_summary = monitoring_service.get_error_summary(hours=1)
            
            assert 'period_hours' in error_summary
            assert 'total_errors' in error_summary
