from database import db
from services.database_service import database_service
from sqlalchemy_models import Deal, Property


def test_money_round_trip_stays_integer(app, db_setup):
    with app.app_context():
        agent = database_service.add_agent("Money Agent", "money.agent@example.com", "5551231")
        customer = database_service.add_customer(
            "Money Customer",
            "money.customer@example.com",
            "5551232",
            budget_min=12_345_678_901,
            budget_max=15_000_000_000,
            preferred_bedrooms=2,
            preferred_bathrooms=1,
            preferred_type="house",
            location_preference="north",
        )
        property_obj = database_service.add_property(
            title="Money House",
            address="1 Money St",
            price=13_250_000_000,
            property_type="house",
            bedrooms=2,
            bathrooms=1,
            square_feet=100,
            description="big integer price",
            status="active",
            agent_id=agent.id,
        )
        deal = database_service.add_deal(property_obj.id, customer.id, agent.id, "qualified", 13_100_000_000)

        assert isinstance(property_obj.price, int)
        assert property_obj.price == 13_250_000_000
        assert isinstance(customer.budget_min, int)
        assert customer.budget_min == 12_345_678_901
        assert isinstance(deal.offer_amount, int)
        assert deal.offer_amount == 13_100_000_000


def test_soft_delete_hides_entities_by_default(app, db_setup):
    with app.app_context():
        agent = database_service.add_agent("Delete Agent", "delete.agent@example.com", "5552221")
        property_obj = database_service.add_property(
            title="Delete House",
            address="2 Delete St",
            price=100_000,
            property_type="house",
            bedrooms=2,
            bathrooms=1,
            square_feet=100,
            description="to delete",
            status="active",
            agent_id=agent.id,
        )

        assert database_service.delete_property(property_obj.id) is True
        assert database_service.get_property(property_obj.id) is None

        raw = db.session.get(Property, property_obj.id)
        assert raw is not None
        assert raw.is_deleted is True
        assert raw.deleted_at is not None

        # Legacy success contract is preserved on deal delete path too.
        customer = database_service.add_customer(
            "Delete Customer",
            "delete.customer@example.com",
            "5552222",
            budget_min=50_000,
            budget_max=120_000,
            preferred_bedrooms=1,
            preferred_bathrooms=1,
            preferred_type="house",
            location_preference="north",
        )
        deal = database_service.add_deal(raw.id, customer.id, agent.id, "qualified", 90_000)
        assert database_service.delete_deal(deal.id) is True
        assert database_service.get_deal(deal.id) is None
        assert db.session.get(Deal, deal.id).is_deleted is True

