
import sys
import os

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db
from sqlalchemy_models import Agent, Customer, Deal, Property

def verify_counts():
    with app.app_context():
        agent_count = Agent.query.count()
        property_count = Property.query.count()
        customer_count = Customer.query.count()
        deal_count = Deal.query.count()
        
        print(f"Agents: {agent_count}")
        print(f"Properties: {property_count}")
        print(f"Customers: {customer_count}")
        print(f"Deals: {deal_count}")

if __name__ == "__main__":
    verify_counts()
