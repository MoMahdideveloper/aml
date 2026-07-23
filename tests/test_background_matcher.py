import os
import sys
import json
from unittest.mock import patch, Mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from background_matcher import BackgroundMatcher
from sqlalchemy_models import Customer, Property, PropertyMatch, MatchingJobRun

class MockProperty:
    def __init__(self, id, price=None, bedrooms=None, bathrooms=None, property_type=None, rahn=None, agent_id=1):
        self.id = id
        self.price = price
        self.bedrooms = bedrooms
        self.bathrooms = bathrooms
        self.property_type = property_type
        self.rahn = rahn
        self.agent_id = agent_id

def test_prefilter_candidate_properties_zero_price():
    """Test that zero-price properties are correctly filtered by minimum budget."""
    matcher = BackgroundMatcher()

    # Customer with min_budget=1000, max_budget=5000
    customer = Customer()
    customer.budget_min = 1000
    customer.budget_max = 5000

    # Property with zero price
    properties = [MockProperty(1, 0)]

    # Should filter out when min_budget > 0
    result = matcher._prefilter_candidate_properties(customer, properties)
    assert len(result) == 0  # Zero price should not pass min_budget=1000

    # Should pass when min_budget = 0
    customer.budget_min = 0
    result = matcher._prefilter_candidate_properties(customer, properties)
    assert len(result) == 1  # Zero price should pass min_budget=0


def test_calculate_basic_match_score_missing_factors():
    """Test scoring when some factors are missing - should not inflate score."""
    matcher = BackgroundMatcher()

    # Customer with full criteria
    customer = Customer()
    customer.budget_min = 250000
    customer.budget_max = 350000
    customer.preferred_bedrooms = 3
    customer.preferred_bathrooms = 2
    customer.preferred_type = 'house'

    # Property with only price match (missing other attributes)
    property_obj = Property()
    property_obj.price = 300000
    property_obj.bedrooms = None
    property_obj.bathrooms = None
    property_obj.property_type = None

    score = matcher._calculate_basic_match_score(customer, property_obj)
    # Price match: 300k within 250k-350k range = 1.0 (full)
    # Other factors missing = 0.0 each
    # Total should be 1.0/4 = 0.25
    assert 0.24 <= score <= 0.26  # Allow small floating point variance


def test_find_property_matches_deduplicates_per_customer():
    """Test that duplicate properties in candidate list for same customer are deduplicated."""
    matcher = BackgroundMatcher()

    # Setup customer
    customer = Customer()
    customer.id = 10
    customer.budget_min = 0
    customer.budget_max = 1000000

    # Create properties with duplicate ID (same property appears twice)
    prop1 = Property()
    prop1.id = 1
    prop1.price = 500000

    prop2 = Property()
    prop2.id = 1  # Duplicate ID
    prop2.price = 500000

    prop3 = Property()
    prop3.id = 2
    prop3.price = 600000

    properties = [prop1, prop2, prop3]  # Contains duplicate ID=1

    # Mock the lower-level methods to return our test data
    with patch.object(matcher, '_get_properties_for_matching', return_value=properties), \
         patch.object(matcher, '_get_customers_for_matching', return_value=[customer]):

        # We'll capture the arguments passed to _process_customer_candidates
        captured_candidates = []

        def capture_candidates(cust, candidates):
            captured_candidates.append((cust.id, [p.id for p in candidates]))
            return []  # Return empty matches to avoid further processing

        with patch.object(matcher, '_process_customer_candidates', side_effect=capture_candidates):
            matcher.find_property_matches()

            # Should have been called once for our customer
            assert len(captured_candidates) == 1
            cust_id, candidate_ids = captured_candidates[0]
            assert cust_id == 10
            # Should have deduplicated to unique IDs: 1 and 2 (duplicate ID=1 removed once)
            assert set(candidate_ids) == {1, 2}
            assert len(candidate_ids) == 2  # Two unique properties


def test_begin_matching_run_retry_after_failure():
    """Test that failed jobs can be retried within the same hour."""
    from background_matcher import BackgroundMatcher
    from unittest.mock import Mock, patch

    matcher = BackgroundMatcher()

    # Mock job that failed previously
    with patch('background_matcher.db.session') as mock_session, \
         patch('background_matcher.MatchingJobRun') as mock_job_run:

        # Simulate a job that failed in the current hour
        mock_job = Mock()
        mock_job.status = 'failed'
        mock_job.id = 123

        mock_session.query.return_value.filter.return_value.first.return_value = mock_job

        # Should allow retry since job failed
        # Note: the _begin_matching_run method is an instance method, so we call it on the matcher
        result = matcher._begin_matching_run(
            idempotency_key="test_key",
            trigger_source="test",
            property_ids=[1, 2],
            customer_ids=[10, 20]
        )
        assert result is not None  # Should return job ID or similar


def test_create_agent_notifications_handles_monitoring_failure():
    """Test that notification creation continues even if monitoring service fails."""
    matcher = BackgroundMatcher()

    # Mock saved matches that should create notifications
    saved_matches = [
        Mock(id=1, match_score=0.8, agent_id=101, property_match_id=1, _notify_kind="new"),
        Mock(id=2, match_score=0.9, agent_id=102, property_match_id=2, _notify_kind="new")
    ]

    with patch('background_matcher.db.session') as mock_session, \
         patch('background_matcher.monitoring_service') as mock_monitoring, \
         patch.object(matcher, '_create_match_notification') as mock_create_notif:

        # Mock notification creation to succeed
        mock_notif1 = Mock(id=10)
        mock_notif2 = Mock(id=20)
        mock_notif1.property_match_id = 1
        mock_notif2.property_match_id = 2
        mock_create_notif.side_effect = [mock_notif1, mock_notif2]  # Two notifications

        # No existing unread notifications for these mocked matches.
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Mock monitoring service to fail on first call, succeed on second
        mock_monitoring.log_notification_activity.side_effect = [
            Exception("Monitoring service down"),  # First call fails
            None  # Second call succeeds
        ]

        # Function should still return notifications despite monitoring failure
        notifications = matcher.create_agent_notifications(saved_matches)

        # Should have created 2 notifications despite first monitoring failure
        assert len(notifications) == 2

        # Monitoring service should have been called twice (once failed, once succeeded)
        assert mock_monitoring.log_notification_activity.call_count == 2


def test_prefilter_candidate_properties_invalid_input():
    """Test handling of invalid/negative input values."""
    matcher = BackgroundMatcher()

    # Customer with min_budget=0, max_budget=5000
    customer = Customer()
    customer.budget_min = 0
    customer.budget_max = 5000

    # Test with negative prices
    properties = [MockProperty(1, -1000, 3, 2, 'house')]
    result = matcher._prefilter_candidate_properties(customer, properties)
    assert len(result) == 0  # Negative price should be filtered out

    # Test with None values
    properties = [MockProperty(1, None, 3, 2, 'house')]
    result = matcher._prefilter_candidate_properties(customer, properties)
    assert len(result) == 1  # None price treated as 0

    # Test with empty list
    result = matcher._prefilter_candidate_properties(customer, [])
    assert len(result) == 0

    # Test with None input
    result = matcher._prefilter_candidate_properties(customer, None)
    assert len(result) == 0

    # Test with invalid limit parameter (this tests the vector search path which we can't easily unit test without mocking)
    # But we can at least verify the function doesn't crash
    properties = [MockProperty(1, 1000, 3, 2, 'house')]
    result = matcher._prefilter_candidate_properties(customer, properties)
    assert len(result) == 1  # Should work normally


def test_build_idempotency_key():
    """Test that idempotency key is built correctly."""
    matcher = BackgroundMatcher()

    # Test with None inputs
    key = matcher._build_idempotency_key(None, None, "test")
    assert isinstance(key, str)
    assert len(key) == 32

    # Test with actual values
    key = matcher._build_idempotency_key([1, 2, 3], [4, 5], "scheduled")
    assert isinstance(key, str)
    assert len(key) == 32

    # Test that sorting works (order shouldn't matter)
    key1 = matcher._build_idempotency_key([3, 1, 2], [5, 4], "scheduled")
    key2 = matcher._build_idempotency_key([1, 2, 3], [4, 5], "scheduled")
    assert key1 == key2


def test_calculate_basic_match_score_edge_cases():
    """Test edge cases in basic match score calculation."""
    matcher = BackgroundMatcher()

    customer = Customer()
    customer.budget_min = 200000
    customer.budget_max = 300000
    customer.preferred_bedrooms = 3
    customer.preferred_bathrooms = 2
    customer.preferred_type = 'house'

    # Test exact match on all factors
    property_obj = Property()
    property_obj.price = 250000
    property_obj.bedrooms = 3
    property_obj.bathrooms = 2
    property_obj.property_type = 'house'

    score = matcher._calculate_basic_match_score(customer, property_obj)
    assert abs(score - 1.0) < 0.001  # Should be perfect match

    # Test budget slightly above max (should get 0.5)
    property_obj.price = 330000  # 10% above 300000
    score = matcher._calculate_basic_match_score(customer, property_obj)
    # Budget: 0.5, bedrooms: 1.0, bathrooms: 1.0, type: 1.0 = 3.5/4 = 0.875
    assert abs(score - 0.875) < 0.001

    # Test budget way above max (should get 0.0)
    property_obj.price = 500000
    score = matcher._calculate_basic_match_score(customer, property_obj)
    # Budget: 0.0, bedrooms: 1.0, bathrooms: 1.0, type: 1.0 = 3.0/4 = 0.75
    assert abs(score - 0.75) < 0.001

    # Test missing preferred values
    customer.preferred_bedrooms = None
    customer.preferred_bathrooms = None
    customer.preferred_type = None
    property_obj.price = 250000
    property_obj.bedrooms = 3
    property_obj.bathrooms = 2
    property_obj.property_type = 'house'

    score = matcher._calculate_basic_match_score(customer, property_obj)
    # Budget: 1.0, bedrooms: 0.0, bathrooms: 0.0, type: 0.0 = 1.0/4 = 0.25
    assert abs(score - 0.25) < 0.001


def test_save_matches_to_database():
    """Test saving matches to database."""
    matcher = BackgroundMatcher()

    # Create mock matches
    match_data = {
        "property_id": 1,
        "customer_id": 10,
        "agent_id": 5,
        "match_score": 0.8,
        "confidence_level": "high",
        "priority": "high",
        "match_reasons": json.dumps(["Great location", "Good price"]),
        "property": MockProperty(1, 250000, 3, 2, 'house'),
        "customer": Customer()
    }

    with patch('background_matcher.db.session') as mock_session:
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        saved_matches = matcher.save_matches_to_database([match_data])

        assert len(saved_matches) == 1
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


if __name__ == '__main__':
    test_prefilter_candidate_properties_zero_price()
    test_calculate_basic_match_score_missing_factors()
    test_find_property_matches_deduplicates_per_customer()
    test_begin_matching_run_retry_after_failure()
    test_create_agent_notifications_handles_monitoring_failure()
    test_prefilter_candidate_properties_invalid_input()
    test_build_idempotency_key()
    test_calculate_basic_match_score_edge_cases()
    test_save_matches_to_database()
    print("All tests passed!")