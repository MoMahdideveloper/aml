
import random
from datetime import datetime, timedelta
from faker import Faker
import sys
import os

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db
from sqlalchemy_models import Agent, Customer, Deal, Property, Task, PropertyMatch, PropertyFavorite

fake = Faker()

def create_agents(count=10):
    agents = []
    print(f"Creating {count} agents...")
    for _ in range(count):
        agent = Agent(
            name=fake.name(),
            email=fake.unique.email(),
            phone=fake.phone_number()[:20],
            specialization=random.choice(["Luxury Homes", "Commercial", "Residential", "Rentals", "Urban Lofts"]),
            bio=fake.text(max_nb_chars=200),
            total_sales=random.randint(0, 100),
            active_listings=random.randint(0, 20),
            created_at=fake.date_time_between(start_date='-2y', end_date='now')
        )
        agents.append(agent)
    
    db.session.add_all(agents)
    db.session.commit()
    print(f"Created {len(agents)} agents.")
    return agents

def create_properties(agents, count=500):
    properties = []
    print(f"Creating {count} properties...")
    
    property_types = ["House", "Condo", "Apartment", "Townhouse", "Villa", "Loft"]
    statuses = ["active", "pending", "sold", "rented"]
    
    for _ in range(count):
        agent = random.choice(agents)
        listing_type = random.choice(["sale", "rental"])
        
        price = 0
        rahn = 0
        ejare = 0
        
        if listing_type == "sale":
            price = random.randint(100000, 5000000)
        else:
            rahn = random.randint(10000000, 1000000000)
            ejare = random.randint(1000000, 50000000)
            
        prop = Property(
            title=fake.catch_phrase(),
            address=fake.address(),
            price=price,
            property_type=random.choice(property_types),
            bedrooms=random.randint(1, 6),
            bathrooms=random.randint(1, 4),
            square_feet=random.randint(500, 5000),
            description=fake.text(),
            status=random.choice(statuses),
            agent_id=agent.id,
            year_built=random.randint(1950, 2024),
            parking_spaces=random.randint(0, 3),
            floors=random.randint(1, 3),
            units=random.randint(1, 4),
            property_condition=random.choice(["new", "excellent", "good", "fair", "needs work"]),
            heating_type=random.choice(["Gas", "Electric", "Solar", "None"]),
            cooling_type=random.choice(["Central Air", "Window Units", "None"]),
            rental_price=ejare if listing_type == "rental" else None,
            property_features=", ".join(fake.words(nb=5)),
            neighborhood=fake.city(),
            property_category="residential",
            listing_type=listing_type,
            rahn=rahn if listing_type == "rental" else None,
            ejare=ejare if listing_type == "rental" else None,
            image_filename=f"house_{random.randint(1, 5)}.jpg", # Assuming some placeholder images exist or will be handled
            latitude=float(fake.latitude()),
            longitude=float(fake.longitude()),
            created_at=fake.date_time_between(start_date='-1y', end_date='now')
        )
        properties.append(prop)
        
        # Commit in batches of 100
        if len(properties) % 100 == 0:
            db.session.add_all(properties)
            db.session.commit()
            properties = []
            print(f"Committed batch of 100 properties...")

    if properties:
        db.session.add_all(properties)
        db.session.commit()
    
    print("Finished creating properties.")

def create_customers(count=200):
    customers = []
    print(f"Creating {count} customers...")
    for _ in range(count):
        budget_min = random.randint(100000, 500000)
        budget_max = budget_min + random.randint(50000, 1000000)
        
        customer = Customer(
            name=fake.name(),
            email=fake.unique.email(),
            phone=fake.phone_number()[:20],
            budget_min=budget_min,
            budget_max=budget_max,
            preferred_bedrooms=random.randint(1, 5),
            preferred_bathrooms=random.randint(1, 3),
            preferred_type=random.choice(["House", "Condo", "Apartment"]),
            location_preference=fake.city(),
            status=random.choice(["active", "inactive", "lead"]),
            created_at=fake.date_time_between(start_date='-1y', end_date='now')
        )
        customers.append(customer)
        
        if len(customers) % 100 == 0:
            db.session.add_all(customers)
            db.session.commit()
            customers = []

    if customers:
        db.session.add_all(customers)
        db.session.commit()
    print("Finished creating customers.")

def create_deals(count=100):
    print(f"Creating {count} deals...")
    # Fetch IDs to avoid loading all objects
    property_ids = [p[0] for p in db.session.query(Property.id).all()]
    customer_ids = [c[0] for c in db.session.query(Customer.id).all()]
    agent_ids = [a[0] for a in db.session.query(Agent.id).all()]
    
    if not property_ids or not customer_ids or not agent_ids:
        print("Not enough data to create deals.")
        return

    deals = []
    for _ in range(count):
        deal = Deal(
            property_id=random.choice(property_ids),
            customer_id=random.choice(customer_ids),
            agent_id=random.choice(agent_ids),
            status=random.choice(["prospecting", "negotiation", "closed", "lost"]),
            offer_amount=random.randint(100000, 1000000),
            notes=fake.sentence(),
            created_at=fake.date_time_between(start_date='-6m', end_date='now')
        )
        deals.append(deal)

    db.session.add_all(deals)
    db.session.commit()
    print("Finished creating deals.")

def seed_large_data():
    with app.app_context():
        print("Starting data seeding...")
        agents = create_agents(10)
        create_properties(agents, 500)
        create_customers(200)
        create_deals(100)
        print("Data seeding completed successfully!")

if __name__ == "__main__":
    seed_large_data()
