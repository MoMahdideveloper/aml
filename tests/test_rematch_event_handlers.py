"""Regression tests for automatic rematch event registration."""

from database import db
from sqlalchemy_models import Customer, Property, RematchQueue


def test_app_factory_registers_property_rematch_handler(app, db_setup):
    """Creating an active property through the normal app must enqueue rematching."""
    with app.app_context():
        property_obj = Property(
            title="Test Property",
            address="123 Main Street",
            price=150000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1200,
            description="Test listing",
            status="active",
        )
        db.session.add(property_obj)
        db.session.commit()

        rows = RematchQueue.query.filter_by(
            entity_type="property",
            entity_id=property_obj.id,
            status="pending",
        ).all()

        assert len(rows) == 1
        assert rows[0].dedupe_key == f"property:{property_obj.id}"
        assert rows[0].reason == "property_created"


def test_app_factory_registers_customer_rematch_handler(app, db_setup):
    """Creating a matchable customer through the normal app must enqueue rematching."""
    with app.app_context():
        customer = Customer(
            name="Test Customer",
            email="customer-rematch@example.com",
            phone="+10000000000",
            budget_min=100000,
            budget_max=200000,
            preferred_bedrooms=3,
            status="active",
        )
        db.session.add(customer)
        db.session.commit()

        rows = RematchQueue.query.filter_by(
            entity_type="customer",
            entity_id=customer.id,
            status="pending",
        ).all()

        assert len(rows) == 1
        assert rows[0].dedupe_key == f"customer:{customer.id}"
        assert rows[0].reason == "customer_created"
