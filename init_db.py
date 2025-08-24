"""
Database initialization script with sample data seeding
"""
import os
from datetime import datetime, timedelta
from app import app
from database import db
from sqlalchemy_models import Property, Agent, Customer, Deal, Task

def create_tables():
    """Create all database tables"""
    with app.app_context():
        db.create_all()
        print("✓ Database tables created successfully")

def seed_data():
    """Seed the database with sample data"""
    with app.app_context():
        # Check if data already exists
        if Agent.query.first():
            print("✓ Database already has data, skipping seeding")
            return
        
        # Create sample agents
        agents = [
            Agent(
                name="Sarah Johnson",
                email="sarah.johnson@realestate.com",
                phone="+1-555-0101",
                specialization="Luxury Homes",
                bio="Specializing in high-end residential properties with 10+ years experience"
            ),
            Agent(
                name="Mike Chen",
                email="mike.chen@realestate.com", 
                phone="+1-555-0102",
                specialization="Commercial Properties",
                bio="Expert in commercial real estate and investment properties"
            ),
            Agent(
                name="Lisa Rodriguez",
                email="lisa.rodriguez@realestate.com",
                phone="+1-555-0103", 
                specialization="First-Time Buyers",
                bio="Dedicated to helping first-time homebuyers navigate the market"
            )
        ]
        
        for agent in agents:
            db.session.add(agent)
        
        db.session.commit()
        print("✓ Sample agents created")
        
        # Create sample properties
        properties = [
            Property(
                title="Modern Downtown Condo",
                address="123 Main St, Downtown",
                price=450000,
                property_type="Condo",
                bedrooms=2,
                bathrooms=2,
                square_feet=1200,
                description="Beautiful modern condo with city views, granite countertops, and hardwood floors",
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
                listing_type="sale"
            ),
            Property(
                title="Suburban Family Home",
                address="456 Oak Avenue, Suburbia",
                price=650000,
                property_type="House",
                bedrooms=4,
                bathrooms=3,
                square_feet=2800,
                description="Spacious family home with large backyard, updated kitchen, and 3-car garage",
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
                listing_type="sale"
            ),
            Property(
                title="Luxury Waterfront Estate",
                address="789 Lake Drive, Waterfront",
                price=1250000,
                property_type="House",
                bedrooms=5,
                bathrooms=4,
                square_feet=4500,
                description="Stunning waterfront estate with private dock, infinity pool, and panoramic lake views",
                status="active",
                agent_id=1,
                year_built=2015,
                parking_spaces=4,
                floors=3,
                units=1,
                property_condition="excellent",
                heating_type="Radiant Floor",
                cooling_type="Central Air",
                property_features="Private Dock, Infinity Pool, Lake Views, Wine Cellar, Smart Home",
                neighborhood="Waterfront",
                property_category="residential",
                listing_type="sale"
            ),
            Property(
                title="Urban Loft - Iranian Rental",
                address="321 Industrial Blvd, Arts District",
                price=0,
                property_type="Loft",
                bedrooms=1,
                bathrooms=1,
                square_feet=950,
                description="Converted industrial loft with exposed brick, high ceilings, and modern amenities",
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
                rahn=400000000,  # 400 million toman deposit
                ejare=2500000    # 2.5 million toman monthly rent
            ),
            Property(
                title="Starter Home",
                address="654 Pine Street, Neighborhood",
                price=285000,
                property_type="House",
                bedrooms=3,
                bathrooms=2,
                square_feet=1450,
                description="Perfect starter home with updated appliances, new roof, and fenced yard",
                status="active",
                agent_id=3,
                year_built=2005,
                parking_spaces=2,
                floors=1,
                units=1,
                property_condition="good",
                heating_type="Gas",
                cooling_type="Central Air",
                property_features="Updated Appliances, New Roof, Fenced Yard, Quiet Street",
                neighborhood="Neighborhood",
                property_category="residential",
                listing_type="sale"
            )
        ]
        
        for property_obj in properties:
            db.session.add(property_obj)
        
        db.session.commit()
        print("✓ Sample properties created")
        
        # Create sample customers
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
                location_preference="Suburbia"
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
                location_preference="Waterfront"
            ),
            Customer(
                name="David Brown",
                email="david.brown@email.com",
                phone="+1-555-1003",
                budget_min=200000,
                budget_max=350000,
                preferred_bedrooms=2,
                preferred_bathrooms=1,
                preferred_type="Condo",
                location_preference="Downtown"
            )
        ]
        
        for customer in customers:
            db.session.add(customer)
        
        db.session.commit()
        print("✓ Sample customers created")
        
        # Create sample deals
        deals = [
            Deal(
                property_id=1,
                customer_id=3,
                agent_id=1,
                status="negotiation",
                offer_amount=435000
            ),
            Deal(
                property_id=2,
                customer_id=1,
                agent_id=1,
                status="qualified",
                offer_amount=625000
            ),
            Deal(
                property_id=3,
                customer_id=2,
                agent_id=1,
                status="proposal",
                offer_amount=1200000
            )
        ]
        
        for deal in deals:
            db.session.add(deal)
        
        db.session.commit()
        print("✓ Sample deals created")
        
        # Create sample tasks
        tasks = [
            Task(
                title="Follow up with John Smith",
                description="Call John about the Oak Avenue property showing",
                agent_id=1,
                priority="high",
                due_date=datetime.utcnow() + timedelta(days=1)
            ),
            Task(
                title="Prepare market analysis",
                description="Create CMA for the Waterfront Estate listing",
                agent_id=1,
                priority="medium",
                due_date=datetime.utcnow() + timedelta(days=3)
            ),
            Task(
                title="Schedule property photos",
                description="Book photographer for new downtown listing",
                agent_id=2,
                priority="medium",
                due_date=datetime.utcnow() + timedelta(days=2)
            )
        ]
        
        for task in tasks:
            db.session.add(task)
        
        db.session.commit()
        print("✓ Sample tasks created")
        
        print("✓ Database seeded successfully with sample data")

def init_database():
    """Initialize database with tables and sample data"""
    print("Initializing database...")
    create_tables()
    seed_data()
    print("Database initialization complete!")

if __name__ == "__main__":
    init_database()