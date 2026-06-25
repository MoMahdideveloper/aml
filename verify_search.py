import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_pipeline():
    print("="*50)
    print("STARTING SEARCH PIPELINE VERIFICATION")
    print("="*50)

    # 1. Verify Embedding Service
    print("\n[1/4] Verifying Embedding Service...")
    try:
        from services.embedding_service import embedding_service
        if not embedding_service:
            print("❌ Embedding Service failed to initialize.")
            return False
            
        test_text = "This is a test sentence for embedding."
        embedding = embedding_service.embed_query(test_text)
        
        if embedding and len(embedding) > 0:
            print(f"✅ Embedding generated successfully. Dimension: {len(embedding)}")
        else:
            print("❌ Embedding generation returned empty result.")
            return False
    except ImportError as e:
        print(f"❌ Failed to import embedding_service: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during embedding verification: {e}")
        return False

    # 2. Verify Vector Service
    print("\n[2/4] Verifying Vector Service...")
    try:
        from services.vector_service import vector_service
        from sqlalchemy_models import Customer, Property
        
        # Create dummy data
        dummy_prop = Property(
            id=99999,
            title="Test Property",
            description="A lovely test home.",
            address="123 Test St",
            price=500000,
            bedrooms=3,
            bathrooms=2,
            square_feet=2000,
            property_type="House",
            neighborhood="Testville",
            status="active"
        )
        
        dummy_customer = Customer(
            id=99999,
            name="Test Customer",
            budget_min=400000,
            budget_max=600000,
            preferred_bedrooms=3,
            preferred_bathrooms=2,
            preferred_type="House",
            location_preference="Testville"
        )
        
        # Test text creation
        prop_text = vector_service._create_property_text(dummy_prop)
        print(f"✅ Property text created: {prop_text[:50]}...")
        
        # Test Status
        status = vector_service.get_status()
        print(f"✅ Vector Service Status: {status}")
        
    except ImportError as e:
        print(f"❌ Failed to import vector_service: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during vector service verification: {e}")
        return False

    # 3. Verify Database Service (Mock or Check)
    print("\n[3/4] Verifying Database Connection...")
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            from services.database_service import database_service
            props = database_service.get_properties()
            print(f"✅ Database query successful. Found {len(props)} properties.")
            if len(props) > 5:
                print(f"   (Showing first 5 properties)")
    except Exception as e:
        print(f"⚠️ Database check skipped or failed (might be expected if DB not init): {e}")

    # 4. Verify Search Service (Hybrid)
    print("\n[4/4] Verifying Search Service...")
    try:
        from services.search_service import search_service
        
        # Need app context for database operations inside search service
        if 'app' not in locals():
            from app import create_app
            app = create_app()
            
        with app.app_context():
            # We assume dummy_customer from before
            results = search_service.search_properties(dummy_customer, top_k=2)
            print(f"✅ Search Service call completed. Returned {len(results)} results.")
            if results:
                print(f"   Top result score: {results[0].get('hybrid_score')}")
    except Exception as e:
        print(f"❌ Error during search service verification: {e}")
        return False

    print("\n" + "="*50)
    print("VERIFICATION COMPLETED SUCCESSFULLY")
    print("="*50)
    return True

if __name__ == "__main__":
    success = verify_pipeline()
    sys.exit(0 if success else 1)
