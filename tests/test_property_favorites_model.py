"""
Unit tests for PropertyFavorite model and related functionality
"""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from database import db
from sqlalchemy_models import Property, PropertyFavorite, Agent


class TestPropertyFavoriteModel:
    """Test PropertyFavorite model functionality"""

    def test_create_property_favorite(self, app, db_setup):
        """Test creating a property favorite"""
        with app.app_context():
            # Create a test property first
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

            # Create favorite
            favorite = PropertyFavorite(
                property_id=property.id,
                user_id=1,
                category="potential_buy",
                notes="Great location"
            )
            db.session.add(favorite)
            db.session.commit()

            # Verify favorite was created
            assert favorite.id is not None
            assert favorite.property_id == property.id
            assert favorite.user_id == 1
            assert favorite.category == "potential_buy"
            assert favorite.notes == "Great location"
            assert favorite.created_at is not None
            assert favorite.updated_at is not None

    def test_property_favorite_relationship(self, app, db_setup):
        """Test relationship between Property and PropertyFavorite"""
        with app.app_context():
            # Create test data
            agent = Agent(
                name="Test Agent",
                email="test2@example.com",
                phone="123-456-7891"
            )
            db.session.add(agent)
            db.session.flush()

            property = Property(
                title="Test Property 2",
                address="456 Test Ave",
                price=200000,
                property_type="condo",
                bedrooms=2,
                bathrooms=1,
                square_feet=1000,
                description="Test condo",
                agent_id=agent.id
            )
            db.session.add(property)
            db.session.flush()

            favorite = PropertyFavorite(
                property_id=property.id,
                user_id=2
            )
            db.session.add(favorite)
            db.session.commit()

            # Test relationship
            assert favorite.property == property
            assert favorite in property.favorites

    def test_property_favorite_without_user_id(self, app, db_setup):
        """Test creating favorite without user_id (for future user system)"""
        with app.app_context():
            agent = Agent(
                name="Test Agent 3",
                email="test3@example.com",
                phone="123-456-7892"
            )
            db.session.add(agent)
            db.session.flush()

            property = Property(
                title="Test Property 3",
                address="789 Test Blvd",
                price=150000,
                property_type="apartment",
                bedrooms=1,
                bathrooms=1,
                square_feet=800,
                description="Test apartment",
                agent_id=agent.id
            )
            db.session.add(property)
            db.session.flush()

            favorite = PropertyFavorite(
                property_id=property.id,
                # user_id is None by default
                category="watch_list"
            )
            db.session.add(favorite)
            db.session.commit()

            assert favorite.user_id is None
            assert favorite.category == "watch_list"

    def test_property_favorite_to_dict(self, app, db_setup):
        """Test PropertyFavorite to_dict method"""
        with app.app_context():
            agent = Agent(
                name="Test Agent 4",
                email="test4@example.com",
                phone="123-456-7893"
            )
            db.session.add(agent)
            db.session.flush()

            property = Property(
                title="Test Property 4",
                address="321 Test Dr",
                price=300000,
                property_type="house",
                bedrooms=4,
                bathrooms=3,
                square_feet=2000,
                description="Large house",
                agent_id=agent.id
            )
            db.session.add(property)
            db.session.flush()

            favorite = PropertyFavorite(
                property_id=property.id,
                user_id=3,
                category="dream_home",
                notes="Perfect family home"
            )
            db.session.add(favorite)
            db.session.commit()

            favorite_dict = favorite.to_dict()

            assert favorite_dict["id"] == favorite.id
            assert favorite_dict["property_id"] == property.id
            assert favorite_dict["user_id"] == 3
            assert favorite_dict["category"] == "dream_home"
            assert favorite_dict["notes"] == "Perfect family home"
            assert "created_at" in favorite_dict
            assert "updated_at" in favorite_dict

    def test_property_favorite_foreign_key_constraint(self, app, db_setup):
        """Test foreign key constraint for property_id"""
        with app.app_context():
            # Enable foreign key constraints for SQLite
            db.session.execute(db.text("PRAGMA foreign_keys=ON"))
            
            # Try to create favorite with non-existent property
            favorite = PropertyFavorite(
                property_id=99999,  # Non-existent property
                user_id=1
            )
            db.session.add(favorite)
            
            with pytest.raises(IntegrityError):
                db.session.commit()

    def test_multiple_favorites_same_property(self, app, db_setup):
        """Test multiple users can favorite the same property"""
        with app.app_context():
            agent = Agent(
                name="Test Agent 5",
                email="test5@example.com",
                phone="123-456-7894"
            )
            db.session.add(agent)
            db.session.flush()

            property = Property(
                title="Popular Property",
                address="555 Popular St",
                price=250000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1800,
                description="Very popular property",
                agent_id=agent.id
            )
            db.session.add(property)
            db.session.flush()

            # Create multiple favorites for same property
            favorite1 = PropertyFavorite(
                property_id=property.id,
                user_id=1,
                category="potential_buy"
            )
            favorite2 = PropertyFavorite(
                property_id=property.id,
                user_id=2,
                category="investment"
            )
            favorite3 = PropertyFavorite(
                property_id=property.id,
                user_id=3,
                category="watch_list"
            )

            db.session.add_all([favorite1, favorite2, favorite3])
            db.session.commit()

            # Verify all favorites exist
            assert len(property.favorites) == 3
            assert property.favorites_count == 3

    def test_property_favorites_count_property(self, app, db_setup):
        """Test favorites_count property on Property model"""
        with app.app_context():
            agent = Agent(
                name="Test Agent 6",
                email="test6@example.com",
                phone="123-456-7895"
            )
            db.session.add(agent)
            db.session.flush()

            property = Property(
                title="Count Test Property",
                address="777 Count Ave",
                price=180000,
                property_type="condo",
                bedrooms=2,
                bathrooms=2,
                square_feet=1200,
                description="Property for count testing",
                agent_id=agent.id
            )
            db.session.add(property)
            db.session.flush()

            # Initially no favorites
            assert property.favorites_count == 0

            # Add favorites
            for i in range(5):
                favorite = PropertyFavorite(
                    property_id=property.id,
                    user_id=i + 1
                )
                db.session.add(favorite)

            db.session.commit()

            # Check count
            assert property.favorites_count == 5

    def test_property_is_favorited_by_user(self, app, db_setup):
        """Test is_favorited_by_user method on Property model"""
        with app.app_context():
            agent = Agent(
                name="Test Agent 7",
                email="test7@example.com",
                phone="123-456-7896"
            )
            db.session.add(agent)
            db.session.flush()

            property = Property(
                title="Favorited Test Property",
                address="888 Favorited Rd",
                price=220000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1600,
                description="Property for favorited testing",
                agent_id=agent.id
            )
            db.session.add(property)
            db.session.flush()

            # Initially not favorited
            assert not property.is_favorited_by_user(1)
            assert not property.is_favorited_by_user(None)

            # Add favorite for user 1
            favorite = PropertyFavorite(
                property_id=property.id,
                user_id=1
            )
            db.session.add(favorite)
            db.session.commit()

            # Check favorited status
            assert property.is_favorited_by_user(1)
            assert not property.is_favorited_by_user(2)
            assert property.is_favorited_by_user(None)  # Any favorites exist

    def test_property_favorite_updated_at_timestamp(self, app, db_setup):
        """Test that updated_at timestamp changes on update"""
        with app.app_context():
            agent = Agent(
                name="Test Agent 8",
                email="test8@example.com",
                phone="123-456-7897"
            )
            db.session.add(agent)
            db.session.flush()

            property = Property(
                title="Update Test Property",
                address="999 Update St",
                price=190000,
                property_type="townhouse",
                bedrooms=2,
                bathrooms=2,
                square_feet=1400,
                description="Property for update testing",
                agent_id=agent.id
            )
            db.session.add(property)
            db.session.flush()

            favorite = PropertyFavorite(
                property_id=property.id,
                user_id=1,
                notes="Initial notes"
            )
            db.session.add(favorite)
            db.session.commit()

            original_updated_at = favorite.updated_at

            # Update the favorite
            favorite.notes = "Updated notes"
            db.session.commit()

            # Verify updated_at changed
            assert favorite.updated_at > original_updated_at

    def test_property_favorite_categories(self, app, db_setup):
        """Test different favorite categories"""
        with app.app_context():
            agent = Agent(
                name="Test Agent 9",
                email="test9@example.com",
                phone="123-456-7898"
            )
            db.session.add(agent)
            db.session.flush()

            property = Property(
                title="Category Test Property",
                address="111 Category Ln",
                price=160000,
                property_type="house",
                bedrooms=3,
                bathrooms=1,
                square_feet=1300,
                description="Property for category testing",
                agent_id=agent.id
            )
            db.session.add(property)
            db.session.flush()

            categories = ["potential_buy", "investment", "watch_list", "dream_home", "comparison"]
            
            for i, category in enumerate(categories):
                favorite = PropertyFavorite(
                    property_id=property.id,
                    user_id=i + 1,
                    category=category
                )
                db.session.add(favorite)

            db.session.commit()

            # Verify all categories were saved
            for favorite in property.favorites:
                assert favorite.category in categories
