"""
Unit tests for FavoritesService
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from database import db
from sqlalchemy_models import Property, PropertyFavorite, Agent
from services.favorites_service import FavoritesService


class TestFavoritesService:
    """Test FavoritesService functionality"""

    @pytest.fixture
    def favorites_service(self):
        """Create FavoritesService instance"""
        return FavoritesService()

    @pytest.fixture
    def sample_property(self, app, db_setup):
        """Create a sample property for testing"""
        with app.app_context():
            agent = Agent(
                name="Test Agent",
                email="test@example.com",
                phone="123-456-7890"
            )
            db.session.add(agent)
            db.session.flush()

            property = Property(
                title="Test Property",
                address="123 Test St",
                price=100000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1500,
                description="Test property",
                agent_id=agent.id
            )
            db.session.add(property)
            db.session.commit()
            
            return SimpleNamespace(id=property.id)

    def test_add_favorite_success(self, app, db_setup, favorites_service, sample_property):
        """Test successfully adding a favorite"""
        with app.app_context():
            favorite = favorites_service.add_favorite(
                property_id=sample_property.id,
                user_id=1,
                category="potential_buy",
                notes="Great location"
            )

            assert favorite.id is not None
            assert favorite.property_id == sample_property.id
            assert favorite.user_id == 1
            assert favorite.category == "potential_buy"
            assert favorite.notes == "Great location"
            assert favorite.created_at is not None

    def test_add_favorite_nonexistent_property(self, app, db_setup, favorites_service):
        """Test adding favorite for non-existent property"""
        with app.app_context():
            with pytest.raises(ValueError, match="Property with ID 99999 not found"):
                favorites_service.add_favorite(property_id=99999, user_id=1)

    def test_add_favorite_duplicate(self, app, db_setup, favorites_service, sample_property):
        """Test adding duplicate favorite"""
        with app.app_context():
            # Add first favorite
            favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            
            # Try to add duplicate
            with pytest.raises(ValueError, match="already favorited"):
                favorites_service.add_favorite(property_id=sample_property.id, user_id=1)

    def test_add_favorite_without_user_id(self, app, db_setup, favorites_service, sample_property):
        """Test adding favorite without user_id"""
        with app.app_context():
            favorite = favorites_service.add_favorite(
                property_id=sample_property.id,
                category="watch_list"
            )

            assert favorite.user_id is None
            assert favorite.category == "watch_list"

    def test_add_favorite_invalid_category_warning(self, app, db_setup, favorites_service, sample_property):
        """Test adding favorite with invalid category logs warning"""
        with app.app_context():
            with patch.object(favorites_service.logger, 'warning') as mock_warning:
                favorite = favorites_service.add_favorite(
                    property_id=sample_property.id,
                    user_id=1,
                    category="invalid_category"
                )
                
                assert favorite.category == "invalid_category"
                mock_warning.assert_called_once()

    def test_remove_favorite_by_property_and_user(self, app, db_setup, favorites_service, sample_property):
        """Test removing favorite by property_id and user_id"""
        with app.app_context():
            # Add favorite first
            favorite = favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            
            # Remove favorite
            result = favorites_service.remove_favorite(property_id=sample_property.id, user_id=1)
            
            assert result is True
            assert db.session.get(PropertyFavorite, favorite.id) is None

    def test_remove_favorite_by_id(self, app, db_setup, favorites_service, sample_property):
        """Test removing favorite by favorite_id"""
        with app.app_context():
            # Add favorite first
            favorite = favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            
            # Remove favorite by ID
            result = favorites_service.remove_favorite(favorite_id=favorite.id)
            
            assert result is True
            assert db.session.get(PropertyFavorite, favorite.id) is None

    def test_remove_favorite_not_found(self, app, db_setup, favorites_service):
        """Test removing non-existent favorite"""
        with app.app_context():
            result = favorites_service.remove_favorite(property_id=99999, user_id=1)
            assert result is False

    def test_remove_favorite_no_parameters(self, app, db_setup, favorites_service):
        """Test removing favorite without required parameters"""
        with app.app_context():
            with pytest.raises(ValueError, match="Either favorite_id or property_id must be provided"):
                favorites_service.remove_favorite()

    def test_get_user_favorites_basic(self, app, db_setup, favorites_service, sample_property):
        """Test getting user favorites"""
        with app.app_context():
            # Add multiple favorites
            favorites_service.add_favorite(property_id=sample_property.id, user_id=1, category="potential_buy")
            
            # Create another property and favorite
            agent = Agent(name="Agent 2", email="agent2@test.com", phone="123-456-7891")
            db.session.add(agent)
            db.session.flush()
            
            property2 = Property(
                title="Property 2",
                address="456 Test Ave",
                price=200000,
                property_type="condo",
                bedrooms=2,
                bathrooms=1,
                square_feet=1000,
                description="Test condo",
                agent_id=agent.id
            )
            db.session.add(property2)
            db.session.flush()
            
            favorites_service.add_favorite(property_id=property2.id, user_id=1, category="investment")
            
            # Get user favorites
            favorites = favorites_service.get_user_favorites(user_id=1)
            
            assert len(favorites) == 2
            assert all(fav.user_id == 1 for fav in favorites)

    def test_get_user_favorites_with_category_filter(self, app, db_setup, favorites_service, sample_property):
        """Test getting user favorites filtered by category"""
        with app.app_context():
            favorites_service.add_favorite(property_id=sample_property.id, user_id=1, category="potential_buy")
            
            # Get favorites by category
            favorites = favorites_service.get_user_favorites(user_id=1, category="potential_buy")
            
            assert len(favorites) == 1
            assert favorites[0].category == "potential_buy"

    def test_get_user_favorites_with_sorting(self, app, db_setup, favorites_service, sample_property):
        """Test getting user favorites with sorting"""
        with app.app_context():
            # Add favorite and wait a bit
            fav1 = favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            
            # Create another property and add to favorites
            agent = Agent(name="Agent 2", email="agent2@test.com", phone="123-456-7891")
            db.session.add(agent)
            db.session.flush()
            
            property2 = Property(
                title="Another Property",
                address="456 Test Ave",
                price=200000,
                property_type="condo",
                bedrooms=2,
                bathrooms=1,
                square_feet=1000,
                description="Test condo",
                agent_id=agent.id
            )
            db.session.add(property2)
            db.session.flush()
            
            # Manually set different created_at times
            fav1.created_at = datetime.utcnow() - timedelta(hours=1)
            db.session.commit()
            
            fav2 = favorites_service.add_favorite(property_id=property2.id, user_id=1)
            
            # Get favorites sorted by created_at desc (newest first)
            favorites = favorites_service.get_user_favorites(user_id=1, sort_by="created_at", sort_order="desc")
            
            assert len(favorites) == 2
            assert favorites[0].created_at > favorites[1].created_at

    def test_get_user_favorites_with_limit(self, app, db_setup, favorites_service, sample_property):
        """Test getting user favorites with limit"""
        with app.app_context():
            favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            
            # Create another property and favorite
            agent = Agent(name="Agent 2", email="agent2@test.com", phone="123-456-7891")
            db.session.add(agent)
            db.session.flush()
            
            property2 = Property(
                title="Property 2",
                address="456 Test Ave",
                price=200000,
                property_type="condo",
                bedrooms=2,
                bathrooms=1,
                square_feet=1000,
                description="Test condo",
                agent_id=agent.id
            )
            db.session.add(property2)
            db.session.flush()
            
            favorites_service.add_favorite(property_id=property2.id, user_id=1)
            
            # Get favorites with limit
            favorites = favorites_service.get_user_favorites(user_id=1, limit=1)
            
            assert len(favorites) == 1

    def test_is_favorited_true(self, app, db_setup, favorites_service, sample_property):
        """Test is_favorited returns True when property is favorited"""
        with app.app_context():
            favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            
            result = favorites_service.is_favorited(property_id=sample_property.id, user_id=1)
            assert result is True

    def test_is_favorited_false(self, app, db_setup, favorites_service, sample_property):
        """Test is_favorited returns False when property is not favorited"""
        with app.app_context():
            result = favorites_service.is_favorited(property_id=sample_property.id, user_id=1)
            assert result is False

    def test_is_favorited_any_user(self, app, db_setup, favorites_service, sample_property):
        """Test is_favorited with user_id=None checks any favorites"""
        with app.app_context():
            favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            
            result = favorites_service.is_favorited(property_id=sample_property.id, user_id=None)
            assert result is True

    def test_get_favorites_count_for_property(self, app, db_setup, favorites_service, sample_property):
        """Test getting favorites count for a property"""
        with app.app_context():
            # Add multiple favorites for same property
            favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            favorites_service.add_favorite(property_id=sample_property.id, user_id=2)
            favorites_service.add_favorite(property_id=sample_property.id, user_id=3)
            
            count = favorites_service.get_favorites_count(property_id=sample_property.id)
            assert count == 3

    def test_get_favorites_count_for_user(self, app, db_setup, favorites_service, sample_property):
        """Test getting favorites count for a user"""
        with app.app_context():
            favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            
            # Create another property and favorite
            agent = Agent(name="Agent 2", email="agent2@test.com", phone="123-456-7891")
            db.session.add(agent)
            db.session.flush()
            
            property2 = Property(
                title="Property 2",
                address="456 Test Ave",
                price=200000,
                property_type="condo",
                bedrooms=2,
                bathrooms=1,
                square_feet=1000,
                description="Test condo",
                agent_id=agent.id
            )
            db.session.add(property2)
            db.session.flush()
            
            favorites_service.add_favorite(property_id=property2.id, user_id=1)
            
            count = favorites_service.get_favorites_count(user_id=1)
            assert count == 2

    def test_get_favorite_by_id(self, app, db_setup, favorites_service, sample_property):
        """Test getting favorite by ID"""
        with app.app_context():
            favorite = favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            
            retrieved = favorites_service.get_favorite_by_id(favorite.id)
            
            assert retrieved is not None
            assert retrieved.id == favorite.id
            assert retrieved.property_id == sample_property.id

    def test_get_favorite_by_id_not_found(self, app, db_setup, favorites_service):
        """Test getting non-existent favorite by ID"""
        with app.app_context():
            result = favorites_service.get_favorite_by_id(99999)
            assert result is None

    def test_update_favorite(self, app, db_setup, favorites_service, sample_property):
        """Test updating favorite category and notes"""
        with app.app_context():
            favorite = favorites_service.add_favorite(
                property_id=sample_property.id,
                user_id=1,
                category="potential_buy",
                notes="Original notes"
            )
            
            updated = favorites_service.update_favorite(
                favorite_id=favorite.id,
                category="investment",
                notes="Updated notes"
            )
            
            assert updated.category == "investment"
            assert updated.notes == "Updated notes"
            assert updated.updated_at > updated.created_at

    def test_update_favorite_not_found(self, app, db_setup, favorites_service):
        """Test updating non-existent favorite"""
        with app.app_context():
            with pytest.raises(ValueError, match="Favorite with ID 99999 not found"):
                favorites_service.update_favorite(favorite_id=99999, category="investment")

    def test_get_favorites_by_category(self, app, db_setup, favorites_service, sample_property):
        """Test getting favorites by category"""
        with app.app_context():
            favorites_service.add_favorite(
                property_id=sample_property.id,
                user_id=1,
                category="potential_buy"
            )
            
            favorites = favorites_service.get_favorites_by_category(category="potential_buy", user_id=1)
            
            assert len(favorites) == 1
            assert favorites[0].category == "potential_buy"

    def test_get_popular_properties(self, app, db_setup, favorites_service, sample_property):
        """Test getting popular properties"""
        with app.app_context():
            # Add multiple favorites for the property
            favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            favorites_service.add_favorite(property_id=sample_property.id, user_id=2)
            favorites_service.add_favorite(property_id=sample_property.id, user_id=3)
            
            popular = favorites_service.get_popular_properties(limit=5, min_favorites=2)
            
            assert len(popular) == 1
            assert popular[0]['property'].id == sample_property.id
            assert popular[0]['favorites_count'] == 3

    def test_bulk_remove_favorites(self, app, db_setup, favorites_service, sample_property):
        """Test bulk removing favorites"""
        with app.app_context():
            # Add multiple favorites
            fav1 = favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            
            # Create another property and favorite
            agent = Agent(name="Agent 2", email="agent2@test.com", phone="123-456-7891")
            db.session.add(agent)
            db.session.flush()
            
            property2 = Property(
                title="Property 2",
                address="456 Test Ave",
                price=200000,
                property_type="condo",
                bedrooms=2,
                bathrooms=1,
                square_feet=1000,
                description="Test condo",
                agent_id=agent.id
            )
            db.session.add(property2)
            db.session.flush()
            
            fav2 = favorites_service.add_favorite(property_id=property2.id, user_id=1)
            
            # Bulk remove
            results = favorites_service.bulk_remove_favorites([fav1.id, fav2.id], user_id=1)
            
            assert results['total_removed'] == 2
            assert results['total_failed'] == 0
            assert len(results['removed']) == 2

    def test_bulk_remove_favorites_with_failures(self, app, db_setup, favorites_service, sample_property):
        """Test bulk removing favorites with some failures"""
        with app.app_context():
            fav1 = favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
            
            # Try to remove one valid and one invalid ID
            results = favorites_service.bulk_remove_favorites([fav1.id, 99999], user_id=1)
            
            assert results['total_removed'] == 1
            assert results['total_failed'] == 1
            assert len(results['removed']) == 1
            assert len(results['failed']) == 1

    def test_get_user_favorite_categories(self, app, db_setup, favorites_service, sample_property):
        """Test getting user favorite categories with counts"""
        with app.app_context():
            # Add favorites with different categories
            favorites_service.add_favorite(property_id=sample_property.id, user_id=1, category="potential_buy")
            
            # Create another property
            agent = Agent(name="Agent 2", email="agent2@test.com", phone="123-456-7891")
            db.session.add(agent)
            db.session.flush()
            
            property2 = Property(
                title="Property 2",
                address="456 Test Ave",
                price=200000,
                property_type="condo",
                bedrooms=2,
                bathrooms=1,
                square_feet=1000,
                description="Test condo",
                agent_id=agent.id
            )
            db.session.add(property2)
            db.session.flush()
            
            favorites_service.add_favorite(property_id=property2.id, user_id=1, category="potential_buy")
            favorites_service.add_favorite(property_id=property2.id, user_id=2, category="investment")
            
            categories = favorites_service.get_user_favorite_categories(user_id=1)
            
            assert len(categories) == 1
            assert categories[0]['category'] == "potential_buy"
            assert categories[0]['count'] == 2

    def test_get_favorites_statistics(self, app, db_setup, favorites_service, sample_property):
        """Test getting favorites statistics"""
        with app.app_context():
            favorites_service.add_favorite(
                property_id=sample_property.id,
                user_id=1,
                category="potential_buy"
            )
            
            stats = favorites_service.get_favorites_statistics(user_id=1)
            
            assert stats['total_favorites'] == 1
            assert 'potential_buy' in stats['categories']
            assert stats['categories']['potential_buy'] == 1
            assert stats['most_recent'] is not None
            assert stats['oldest'] is not None

    def test_get_favorites_statistics_empty(self, app, db_setup, favorites_service):
        """Test getting statistics when no favorites exist"""
        with app.app_context():
            stats = favorites_service.get_favorites_statistics(user_id=1)
            
            assert stats['total_favorites'] == 0
            assert stats['categories'] == {}
            assert stats['most_recent'] is None

    def test_error_handling_database_error(self, app, db_setup, favorites_service):
        """Test error handling when database errors occur"""
        with app.app_context():
            with patch.object(favorites_service.logger, 'error') as mock_error:
                with patch('services.favorites_service.db.session.get', side_effect=Exception("Database error")):
                    result = favorites_service.get_favorite_by_id(1)
                    
                    assert result is None
                    mock_error.assert_called_once()

    def test_transaction_rollback_on_error(self, app, db_setup, favorites_service, sample_property):
        """Test that transactions are rolled back on errors"""
        with app.app_context():
            with patch('services.favorites_service.db.session.add', side_effect=Exception("Database error")):
                with pytest.raises(Exception):
                    favorites_service.add_favorite(property_id=sample_property.id, user_id=1)
                
                # Verify no favorite was created
                count = favorites_service.get_favorites_count(property_id=sample_property.id)
                assert count == 0
