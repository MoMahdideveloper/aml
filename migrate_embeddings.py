import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_embeddings():
    print("="*50)
    print("STARTING EMBEDDING MIGRATION")
    print("="*50)

    try:
        # Initialize Flask App Context
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from services.database_service import database_service
            from services.vector_service import vector_service
            
            # Fetch all active properties
            print("Fetching properties from database...")
            # We fetch all properties, not just active ones, to ensure complete index
            # But search service filters by status usually. Let's index everything.
            properties_data = database_service.search_properties_advanced(per_page=10000)
            properties = properties_data.get('properties', [])
            
            if not properties:
                print("⚠️ No properties found in database to migrate.")
                return True
                
            print(f"Found {len(properties)} properties. Starting indexing...")
            
            # Index properties
            success = vector_service.index_properties(properties)
            
            if success:
                print(f"✅ Successfully indexed {len(properties)} properties into ChromaDB.")
            else:
                print("❌ Failed to index properties.")
                return False
                
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

    print("\n" + "="*50)
    print("MIGRATION COMPLETED")
    print("="*50)
    return True

if __name__ == "__main__":
    success = migrate_embeddings()
    sys.exit(0 if success else 1)
