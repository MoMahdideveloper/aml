import os
import sys
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from background_matcher import BackgroundMatcher
from sqlalchemy_models import Customer, Property

class MockProperty:
    def __init__(self, id, price=None, bedrooms=None, bathrooms=None, property_type=None, rahn=None):
        self.id = id
        self.price = price
        self.bedrooms = bedrooms
        self.bathrooms = bathrooms
        self.property_type = property_type
        self.rahn = rahn

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


if __name__ == '__main__':
    test_prefilter_candidate_properties_zero_price()
    test_calculate_basic_match_score_missing_factors()
    test_find_property_matches_deduplicates_per_customer()
    print("All tests passed!")