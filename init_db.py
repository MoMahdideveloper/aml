"""
Database initialization script with sample data seeding
"""

from datetime import datetime, timedelta
from app import app
from database import db
from sqlalchemy_models import Property, Agent, Customer, Deal, Task


def create_tables():
    """Create all database tables"""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")


def seed_data():
    """Seed the database with sample data"""
    with app.app_context():
        if Agent.query.first():
            print("Database already has data, skipping seeding")
            return

        agents = [
            Agent(
                name="Sarah Johnson",
                email="sarah.johnson@realestate.com",
                phone="+1-555-0101",
                specialization="Luxury Homes",
                bio="High-end residential properties",
            ),
            Agent(
                name="Mike Chen",
                email="mike.chen@realestate.com",
                phone="+1-555-0102",
                specialization="Commercial Properties",
                bio="Commercial and investments",
            ),
            Agent(
                name="Lisa Rodriguez",
                email="lisa.rodriguez@realestate.com",
                phone="+1-555-0103",
                specialization="First-Time Buyers",
                bio="Guiding first-time buyers",
            ),
        ]
        db.session.add_all(agents)
        db.session.commit()
        print("Sample agents created")

        properties = [
            Property(
                title="Modern Downtown Condo",
                address="123 Main St, Downtown",
                price=450000,
                property_type="Condo",
                bedrooms=2,
                bathrooms=2,
                square_feet=1200,
                description="Modern condo with city views",
                status="active",
                agent_id=1,
                year_built=2018,
                parking_spaces=1,
                floors=1,
                units=1,
                property_condition="excellent",
                heating_type="Central Air",
                cooling_type="Central Air",
                property_features="Granite Countertops, Hardwood Floors, City Views, Balcony",
                neighborhood="Downtown",
                property_category="residential",
                listing_type="sale",
            ),
            Property(
                title="Suburban Family Home",
                address="456 Oak Avenue, Suburbia",
                price=650000,
                property_type="House",
                bedrooms=4,
                bathrooms=3,
                square_feet=2800,
                description="Spacious family home",
                status="active",
                agent_id=1,
                year_built=2010,
                parking_spaces=3,
                floors=2,
                units=1,
                property_condition="good",
                heating_type="Gas",
                cooling_type="Central Air",
                property_features="Updated Kitchen, Large Backyard, 3-Car Garage, Walk-in Closets",
                neighborhood="Suburbia",
                property_category="residential",
                listing_type="sale",
            ),
            Property(
                title="Urban Loft - Iranian Rental",
                address="321 Industrial Blvd, Arts District",
                price=0,
                property_type="Loft",
                bedrooms=1,
                bathrooms=1,
                square_feet=950,
                description="Converted industrial loft",
                status="active",
                agent_id=2,
                year_built=1995,
                parking_spaces=1,
                floors=1,
                units=1,
                property_condition="good",
                heating_type="Electric",
                cooling_type="Window Units",
                property_features="Exposed Brick, High Ceilings, Industrial Design, Artist Space",
                neighborhood="Arts District",
                property_category="residential",
                listing_type="rental",
                rahn=400000000,
                ejare=2500000,
            ),
        ]
        db.session.add_all(properties)
        db.session.commit()
        print("Sample properties created")

        customers = [
            Customer(
                name="John Smith",
                email="john.smith@email.com",
                phone="+1-555-1001",
                budget_min=300000,
                budget_max=500000,
                preferred_bedrooms=3,
                preferred_bathrooms=2,
                preferred_type="House",
                location_preference="Suburbia",
            ),
            Customer(
                name="Emma Wilson",
                email="emma.wilson@email.com",
                phone="+1-555-1002",
                budget_min=800000,
                budget_max=1500000,
                preferred_bedrooms=4,
                preferred_bathrooms=3,
                preferred_type="House",
                location_preference="Waterfront",
            ),
        ]
        db.session.add_all(customers)
        db.session.commit()
        print("Sample customers created")

        deals = [
            Deal(property_id=1, customer_id=1, agent_id=1, status="qualified", offer_amount=625000),
            Deal(property_id=2, customer_id=2, agent_id=1, status="proposal", offer_amount=1200000),
        ]
        db.session.add_all(deals)
        db.session.commit()
        print("Sample deals created")

        tasks = [
            Task(
                title="Follow up with John Smith",
                description="Call about property showing",
                agent_id=1,
                priority="high",
                due_date=datetime.utcnow() + timedelta(days=1),
            ),
            Task(
                title="Prepare market analysis",
                description="Create CMA for listing",
                agent_id=1,
                priority="medium",
                due_date=datetime.utcnow() + timedelta(days=3),
            ),
        ]
        db.session.add_all(tasks)
        db.session.commit()
        print("Sample tasks created")

        print("Database seeded successfully with sample data")


def init_database():
    """Initialize database with tables and sample data"""
    print("Initializing database...")
    create_tables()
    seed_data()
    print("Database initialization complete!")


if __name__ == "__main__":
    init_database()
