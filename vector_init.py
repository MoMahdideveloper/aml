import logging
from typing import List
from vector_service import vector_service
from database_service import database_service
from sqlalchemy_models import Property


class VectorInitializer:
    """
    Initialize and manage the vector database with property data
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def initialize_vector_database(self) -> bool:
        """
        Initialize the vector database with all current properties
        """
        try:
            self.logger.info("Initializing vector database...")

            # Get all properties from data manager
            properties = database_service.get_properties()

            if not properties:
                self.logger.warning("No properties found to index")
                return True

            # Index properties in vector database
            success = vector_service.index_properties(properties)

            if success:
                self.logger.info(
                    f"Successfully initialized vector database with {len(properties)} properties"
                )
                return True
            else:
                self.logger.error("Failed to initialize vector database")
                return False

        except Exception as e:
            self.logger.error(f"Error initializing vector database: {e}")
            return False

    def refresh_property_index(self, properties: List[Property] = None) -> bool:
        """
        Refresh the property index with new or updated properties
        """
        try:
            if properties is None:
                properties = database_service.get_properties()

            self.logger.info(f"Refreshing property index with {len(properties)} properties")
            return vector_service.index_properties(properties)

        except Exception as e:
            self.logger.error(f"Error refreshing property index: {e}")
            return False

    def test_vector_search(self) -> bool:
        """
        Test the vector search functionality with sample data
        """
        try:
            self.logger.info("Testing vector search functionality...")

            # Get a sample customer
            customers = database_service.get_customers()
            if not customers:
                self.logger.warning("No customers found for testing")
                return False

            customer = customers[0]
            properties = database_service.get_properties()

            if not properties:
                self.logger.warning("No properties found for testing")
                return False

            # Perform test search
            recommendations = vector_service.search_properties(
                customer=customer, properties=properties, top_k=5
            )

            if recommendations:
                self.logger.info(
                    f"Vector search test successful: {len(recommendations)} recommendations returned"
                )

                # Log sample results for debugging
                for i, rec in enumerate(recommendations[:3]):
                    self.logger.info(
                        f"  {i+1}. Property {rec['property'].id}: {rec['hybrid_score']:.1f} score"
                    )

                return True
            else:
                self.logger.warning("Vector search test returned no results")
                return False

        except Exception as e:
            self.logger.error(f"Error testing vector search: {e}")
            return False

    def get_vector_database_stats(self) -> dict:
        """
        Get statistics about the vector database
        """
        try:
            stats = {"properties_indexed": 0, "customers_indexed": 0, "database_ready": False}

            # Check properties collection
            try:
                properties_count = vector_service.properties_collection.count()
                stats["properties_indexed"] = properties_count
            except Exception as e:
                self.logger.warning(f"Could not get properties count: {e}")

            # Check customers collection
            try:
                customers_count = vector_service.customers_collection.count()
                stats["customers_indexed"] = customers_count
            except Exception as e:
                self.logger.warning(f"Could not get customers count: {e}")

            # Check if database is ready
            stats["database_ready"] = stats["properties_indexed"] > 0

            return stats

        except Exception as e:
            self.logger.error(f"Error getting vector database stats: {e}")
            return {"error": str(e)}


# Global initializer instance
vector_initializer = VectorInitializer()


def ensure_vector_database_ready():
    """
    Ensure the vector database is ready for use
    """
    stats = vector_initializer.get_vector_database_stats()

    if not stats.get("database_ready", False):
        logging.info("Vector database not ready, initializing...")
        return vector_initializer.initialize_vector_database()

    return True
