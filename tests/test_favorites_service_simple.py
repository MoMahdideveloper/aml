"""
Simplified unit tests for FavoritesService
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from database import db
from sqlalchemy_models import Property, PropertyFavorite, Agent
from services.favorites_service import FavoritesService


class TestFavoritesServiceSimple:
    """Test FavoritesService functionality with simplified approach"""

    @pytest.fixture
    def favorites_service(self):
        """Create FavoritesService instance"""
        return FavoritesService()

    def create_test_property(self):
        """Helper to create a test property within current context"""
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
        db.session.flush()
        return property

    def test_add_favorite_success(self, app, db_setup, favorites_service):
        """Test successfully adding a favorite"""
        with app.app_context():
            property = self.create_test_property()
            
            favorite = favorites_service.add_favorite(
                property_id=property.id,
                user_id=1,
                category="potential_buy",
                notes="Great location"
            )

            assert favorite.id is not None
            assert favorite.property_id == property.id
            assert favorite.user_id == 1
            assert favorite.category == "potential_buy"
            assert favorite.notes == "Great location"
            assert favorite.created_at is not None

    def test_add_favorite_nonexistent_property(self, app, db_setup, favorites_service):
        """Test adding favorite for non-existent property"""
        with app.app_context():
            with pytest.raises(ValueError, match="Property with ID 99999 not found"):
                favorites_service.add_favorite(property_id=99999, user_id=1)

    def test_add_favorite_duplicate(self, app, db_setup, favorites_service):
        """Test adding duplicate favorite"""
        with app.app_context():
            property = self.create_test_property()
            
            # Add first favorite
            favorites_service.add_favorite(property_id=property.id, user_id=1)
            
            # Try to add duplicate
            with pytest.raises(ValueError, match="already favorited"):
                favorites_service.add_favorite(property_id=property.id, user_id=1)

    def test_add_favorite_without_user_id(self, app, db_setup, favorites_service):
        """Test adding favorite without user_id"""
        with app.app_context():
            property = self.create_test_property()
            
            favorite = favorites_service.add_favorite(
                property_id=property.id,
                category="watch_list"
            )

            assert favorite.user_id is None
            assert favorite.category == "watch_list"

    def test_remove_favorite_by_property_and_user(self, app, db_setup, favorites_service):
        """Test removing favorite by property_id and user_id"""
        with app.app_context():
            property = self.create_test_property()
            
            # Add favorite first
            favorite = favorites_service.add_favorite(property_id=property.id, user_id=1)
            
            # Remove favorite
            result = favorites_service.remove_favorite(property_id=property.id, user_id=1)
            
            assert result is True
            assert db.session.get(PropertyFavorite, favorite.id) is None

    def test_remove_favorite_by_id(self, app, db_setup, favorites_service):
        """Test removing favorite by favorite_id"""
        with app.app_context():
            property = self.create_test_property()
            
            # Add favorite first
            favorite = favorites_service.add_favorite(property_id=property.id, user_id=1)
            
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

    def test_get_user_favorites_basic(self, app, db_setup, favorites_service):
        """Test getting user favorites"""
        with app.app_context():
            property1 = self.create_test_property()
            
            # Create another property
            agent2 = Agent(name="Agent 2", email="agent2@test.com", phone="123-456-7891")
            db.session.add(agent2)
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
                agent_id=agent2.id
            )
            db.session.add(property2)
            db.session.flush()
            
            # Add favorites
            favorites_service.add_favorite(property_id=property1.id, user_id=1, category="potential_buy")
            favorites_service.add_favorite(property_id=property2.id, user_id=1, category="investment")
            
            # Get user favorites
            favorites = favorites_service.get_user_favorites(user_id=1)
            
            assert len(favorites) == 2
            assert all(fav.user_id == 1 for fav in favorites)

    def test_is_favorited_true(self, app, db_setup, favorites_service):
        """Test is_favorited returns True when property is favorited"""
        with app.app_context():
            property = self.create_test_property()
            favorites_service.add_favorite(property_id=property.id, user_id=1)
            
            result = favorites_service.is_favorited(property_id=property.id, user_id=1)
            assert result is True

    def test_is_favorited_false(self, app, db_setup, favorites_service):
        """Test is_favorited returns False when property is not favorited"""
        with app.app_context():
            property = self.create_test_property()
            result = favorites_service.is_favorited(property_id=property.id, user_id=1)
            assert result is False

    def test_get_favorites_count_for_property(self, app, db_setup, favorites_service):
        """Test getting favorites count for a property"""
        with app.app_context():
            property = self.create_test_property()
            
            # Add multiple favorites for same property
            favorites_service.add_favorite(property_id=property.id, user_id=1)
            favorites_service.add_favorite(property_id=property.id, user_id=2)
            favorites_service.add_favorite(property_id=property.id, user_id=3)
            
            count = favorites_service.get_favorites_count(property_id=property.id)
            assert count == 3

    def test_get_favorite_by_id(self, app, db_setup, favorites_service):
        """Test getting favorite by ID"""
        with app.app_context():
            property = self.create_test_property()
            favorite = favorites_service.add_favorite(property_id=property.id, user_id=1)
            
            retrieved = favorites_service.get_favorite_by_id(favorite.id)
            
            assert retrieved is not None
            assert retrieved.id == favorite.id
            assert retrieved.property_id == property.id

    def test_update_favorite(self, app, db_setup, favorites_service):
        """Test updating favorite category and notes"""
        with app.app_context():
            property = self.create_test_property()
            favorite = favorites_service.add_favorite(
                property_id=property.id,
                user_id=1,
                category="potential_buy",
                notes="Original notes"
            )
            
            original_updated_at = favorite.updated_at
            
            updated = favorites_service.update_favorite(
                favorite_id=favorite.id,
                category="investment",
                notes="Updated notes"
            )
            
            assert updated.category == "investment"
            assert updated.notes == "Updated notes"
            assert updated.updated_at >= original_updated_at

    def test_get_popular_properties(self, app, db_setup, favorites_service):
        """Test getting popular properties"""
        with app.app_context():
            property = self.create_test_property()
            
            # Add multiple favorites for the property
            favorites_service.add_favorite(property_id=property.id, user_id=1)
            favorites_service.add_favorite(property_id=property.id, user_id=2)
            favorites_service.add_favorite(property_id=property.id, user_id=3)
            
            popular = favorites_service.get_popular_properties(limit=5, min_favorites=2)
            
            assert len(popular) == 1
            assert popular[0]['property'].id == property.id
            assert popular[0]['favorites_count'] == 3

    def test_bulk_remove_favorites(self, app, db_setup, favorites_service):
        """Test bulk removing favorites"""
        with app.app_context():
            property1 = self.create_test_property()
            
            # Create another property
            agent2 = Agent(name="Agent 2", email="agent2@test.com", phone="123-456-7891")
            db.session.add(agent2)
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
                agent_id=agent2.id
            )
            db.session.add(property2)
            db.session.flush()
            
            # Add favorites
            fav1 = favorites_service.add_favorite(property_id=property1.id, user_id=1)
            fav2 = favorites_service.add_favorite(property_id=property2.id, user_id=1)
            
            # Bulk remove
            results = favorites_service.bulk_remove_favorites([fav1.id, fav2.id], user_id=1)
            
            assert results['total_removed'] == 2
            assert results['total_failed'] == 0
            assert len(results['removed']) == 2

    def test_get_favorites_statistics(self, app, db_setup, favorites_service):
        """Test getting favorites statistics"""
        with app.app_context():
            property = self.create_test_property()
            favorites_service.add_favorite(
                property_id=property.id,
                user_id=1,
                category="potential_buy"
            )
            
            stats = favorites_service.get_favorites_statistics(user_id=1)
            
            assert stats['total_favorites'] == 1
            assert 'potential_buy' in stats['categories']
            assert stats['categories']['potential_buy'] == 1
            assert stats['most_recent'] is not None
            assert stats['oldest'] is not None

    def test_error_handling_database_error(self, app, db_setup, favorites_service):
        """Test error handling when database errors occur"""
        with app.app_context():
            with patch.object(favorites_service.logger, 'error') as mock_error:
                with patch('services.favorites_service.db.session.get', side_effect=Exception("Database error")):
                    result = favorites_service.get_favorite_by_id(1)
                    
                    assert result is None
                    mock_error.assert_called_once()
