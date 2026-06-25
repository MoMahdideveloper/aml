import logging
from app import create_app
from database import db
from services.database_service import database_service
from services.gemini_service import gemini_service
from sqlalchemy_models import Customer, Property

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_recommendations():
    app = create_app()
    with app.app_context():
        # Ensure schema exists when this script-style test is run standalone.
        db.create_all()

        # Create a test customer
        customer_data = {
            "name": "Test Buyer",
            "email": "testbuyer@example.com",
            "phone": "555-0100",
            "budget_min": 300000,
            "budget_max": 600000,
            "preferred_type": "house",
            "preferred_bedrooms": 3,
            "preferred_bathrooms": 2,
            "location_preference": "Downtown"
        }
        
        # Check if customer exists or create new
        customer = None
        existing_customers = database_service.get_customers()
        for c in existing_customers:
            if c.email == customer_data["email"]:
                customer = c
                break
        
        if not customer:
            customer = database_service.add_customer(**customer_data)
            logger.info(f"Created test customer: {customer.name}")
        else:
            logger.info(f"Using existing customer: {customer.name}")
            
        # Ensure we have some properties
        properties = database_service.get_properties()
        if not properties:
            logger.info("Creating test properties...")
            database_service.add_property(
                title="Modern Downtown Condo",
                address="123 Main St",
                price=450000,
                property_type="condo",
                bedrooms=2,
                bathrooms=2,
                square_feet=1200,
                description="Beautiful condo in the heart of downtown.",
                neighborhood="Downtown"
            )
            database_service.add_property(
                title="Suburban Family Home",
                address="456 Oak Ln",
                price=550000,
                property_type="house",
                bedrooms=3,
                bathrooms=2.5,
                square_feet=2000,
                description="Spacious family home with a large backyard.",
                neighborhood="Suburbs"
            )
            properties = database_service.get_properties()
            
        logger.info(f"Found {len(properties)} properties.")
        
        # Test recommendations
        logger.info("Testing AI recommendations...")
        recommendations = gemini_service.get_property_recommendations(customer, properties)
        
        logger.info(f"Received {len(recommendations)} recommendations.")
        for i, rec in enumerate(recommendations):
            prop = rec['property']
            score = rec['match_score']
            analysis = rec['analysis']
            logger.info(f"Rec #{i+1}: {prop.title} (Score: {score})")
            logger.info(f"Analysis: {analysis[:100]}...")

if __name__ == "__main__":
    test_recommendations()
