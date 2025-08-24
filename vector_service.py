import os
import logging
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import chromadb
from chromadb.config import Settings
from models import Property, Customer

class VectorService:
    """
    Vector-based recommendation service using Chroma DB and scikit-learn embeddings
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.logger = logging.getLogger(__name__)
        self.persist_directory = persist_directory
        
        # Initialize Chroma client
        self.chroma_client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collections
        self.properties_collection = self.chroma_client.get_or_create_collection(
            name="properties",
            metadata={"description": "Property embeddings for semantic search"}
        )
        
        self.customers_collection = self.chroma_client.get_or_create_collection(
            name="customers", 
            metadata={"description": "Customer preference embeddings"}
        )
        
        # Initialize TF-IDF vectorizer for text embeddings
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        
        self.vectorizer_fitted = False
        self.logger.info("Vector service initialized successfully")
    
    def _create_property_text(self, property: Property) -> str:
        """
        Create a comprehensive text representation of a property for embedding
        """
        # Normalize price to price range description
        price_range = self._get_price_range_description(property.price)
        
        # Create rich text description
        text_parts = [
            property.title,
            property.description,
            property.address,
            property.property_type,
            f"{property.bedrooms} bedroom",
            f"{property.bathrooms} bathroom",
            f"{property.square_feet} square feet",
            price_range,
            property.status
        ]
        
        return " ".join(str(part) for part in text_parts if part)
    
    def _create_customer_text(self, customer: Customer) -> str:
        """
        Create a text representation of customer preferences for embedding
        """
        budget_range = self._get_price_range_description((customer.budget_min + customer.budget_max) / 2)
        
        text_parts = [
            f"{customer.preferred_bedrooms} bedroom",
            f"{customer.preferred_bathrooms} bathroom",
            customer.preferred_type,
            customer.location_preference,
            budget_range,
            "property search preferences"
        ]
        
        return " ".join(str(part) for part in text_parts if part)
    
    def _get_price_range_description(self, price: float) -> str:
        """
        Convert price to descriptive text for better semantic matching
        """
        if price < 200000:
            return "affordable budget-friendly economical"
        elif price < 400000:
            return "moderate mid-range"
        elif price < 600000:
            return "upper-middle premium"
        elif price < 1000000:
            return "luxury high-end"
        else:
            return "ultra-luxury exclusive"
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate TF-IDF embedding for text
        """
        try:
            if not self.vectorizer_fitted:
                # For the first embedding, we need to fit the vectorizer
                # This is a limitation - in production, you'd fit once on all data
                embedding = self.vectorizer.fit_transform([text])
                self.vectorizer_fitted = True
            else:
                embedding = self.vectorizer.transform([text])
            
            return embedding.toarray()[0].tolist()
        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 100
    
    def _generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently
        """
        try:
            if not texts:
                return []
            
            # Fit and transform all texts at once
            embeddings = self.vectorizer.fit_transform(texts)
            self.vectorizer_fitted = True
            
            return embeddings.toarray().tolist()
        except Exception as e:
            self.logger.error(f"Error generating batch embeddings: {e}")
            # Return zero vectors as fallback
            return [[0.0] * 100 for _ in texts]
    
    def index_properties(self, properties: List[Property]) -> bool:
        """
        Index all properties in the vector database
        """
        try:
            if not properties:
                self.logger.warning("No properties to index")
                return True
            
            # Clear existing data
            try:
                self.properties_collection.delete(where={})
            except Exception:
                pass  # Collection might be empty
            
            # Prepare data for batch processing
            property_texts = [self._create_property_text(prop) for prop in properties]
            embeddings = self._generate_embeddings_batch(property_texts)
            
            # Prepare data for Chroma
            ids = [f"property_{prop.id}" for prop in properties]
            metadatas = []
            documents = []
            
            for prop, text in zip(properties, property_texts):
                metadatas.append({
                    'property_id': prop.id,
                    'price': prop.price,
                    'bedrooms': prop.bedrooms,
                    'bathrooms': prop.bathrooms,
                    'property_type': prop.property_type,
                    'address': prop.address,
                    'square_feet': prop.square_feet,
                    'status': prop.status
                })
                documents.append(text)
            
            # Add to Chroma collection
            self.properties_collection.add(
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
                ids=ids
            )
            
            self.logger.info(f"Successfully indexed {len(properties)} properties")
            return True
            
        except Exception as e:
            self.logger.error(f"Error indexing properties: {e}")
            return False
    
    def search_properties(self, customer: Customer, properties: List[Property], 
                         top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform semantic search for properties matching customer preferences
        """
        try:
            # Ensure properties are indexed
            if not self._is_collection_populated(self.properties_collection):
                self.logger.info("Properties not indexed, indexing now...")
                if not self.index_properties(properties):
                    return self._fallback_search(customer, properties, top_k)
            
            # Create customer preference embedding
            customer_text = self._create_customer_text(customer)
            customer_embedding = self._generate_embedding(customer_text)
            
            # Perform vector search
            results = self.properties_collection.query(
                query_embeddings=[customer_embedding],
                n_results=min(top_k, len(properties)),
                include=['metadatas', 'documents', 'distances']
            )
            
            # Process results
            recommendations = []
            if results and results['metadatas'] and results['metadatas'][0]:
                for i, metadata in enumerate(results['metadatas'][0]):
                    property_id = metadata['property_id']
                    
                    # Find the property object
                    property_obj = next((p for p in properties if p.id == property_id), None)
                    if not property_obj:
                        continue
                    
                    # Calculate distance/similarity score
                    distance = results['distances'][0][i] if results['distances'] else 0.5
                    similarity_score = max(0, (1 - distance) * 100)  # Convert to 0-100 scale
                    
                    # Calculate hybrid score combining semantic similarity with rules
                    hybrid_score = self._calculate_hybrid_score(
                        customer, property_obj, similarity_score
                    )
                    
                    recommendations.append({
                        'property': property_obj,
                        'similarity_score': similarity_score,
                        'hybrid_score': hybrid_score,
                        'match_reasons': self._generate_match_reasons(customer, property_obj, similarity_score)
                    })
            
            # Sort by hybrid score
            recommendations.sort(key=lambda x: x['hybrid_score'], reverse=True)
            
            self.logger.info(f"Vector search returned {len(recommendations)} recommendations")
            return recommendations[:top_k]
            
        except Exception as e:
            self.logger.error(f"Error in vector search: {e}")
            return self._fallback_search(customer, properties, top_k)
    
    def _is_collection_populated(self, collection) -> bool:
        """
        Check if a collection has any documents
        """
        try:
            count = collection.count()
            return count > 0
        except Exception:
            return False
    
    def _calculate_hybrid_score(self, customer: Customer, property: Property, 
                               similarity_score: float) -> float:
        """
        Calculate hybrid score combining semantic similarity with rule-based factors
        Weights: Semantic similarity (60%), Budget match (25%), Hard requirements (15%)
        """
        # Semantic similarity (60% weight)
        semantic_component = similarity_score * 0.6
        
        # Budget compatibility (25% weight)
        budget_score = 0
        if customer.budget_min <= property.price <= customer.budget_max:
            budget_score = 100
        elif property.price <= customer.budget_max * 1.1:  # 10% tolerance
            budget_score = 80
        elif property.price <= customer.budget_max * 1.2:  # 20% tolerance
            budget_score = 60
        else:
            budget_score = 20
        
        budget_component = budget_score * 0.25
        
        # Hard requirements (15% weight)
        requirements_score = 0
        
        # Bedroom match
        if property.bedrooms == customer.preferred_bedrooms:
            requirements_score += 40
        elif abs(property.bedrooms - customer.preferred_bedrooms) <= 1:
            requirements_score += 20
        
        # Bathroom match
        if property.bathrooms >= customer.preferred_bathrooms:
            requirements_score += 30
        elif property.bathrooms >= customer.preferred_bathrooms - 0.5:
            requirements_score += 15
        
        # Property type match
        if property.property_type.lower() == customer.preferred_type.lower():
            requirements_score += 30
        
        requirements_component = requirements_score * 0.15
        
        # Final hybrid score
        hybrid_score = semantic_component + budget_component + requirements_component
        return min(100, max(0, hybrid_score))
    
    def _generate_match_reasons(self, customer: Customer, property: Property, 
                               similarity_score: float) -> List[str]:
        """
        Generate human-readable reasons for the match
        """
        reasons = []
        
        # Semantic similarity
        if similarity_score > 70:
            reasons.append(f"High semantic match ({similarity_score:.1f}% similarity)")
        elif similarity_score > 50:
            reasons.append(f"Good semantic match ({similarity_score:.1f}% similarity)")
        
        # Budget analysis
        if customer.budget_min <= property.price <= customer.budget_max:
            reasons.append("Perfect budget match")
        elif property.price <= customer.budget_max * 1.1:
            reasons.append("Within budget range")
        
        # Feature matches
        if property.bedrooms == customer.preferred_bedrooms:
            reasons.append("Matches bedroom preference")
        if property.bathrooms >= customer.preferred_bathrooms:
            reasons.append("Meets bathroom requirements")
        if property.property_type.lower() == customer.preferred_type.lower():
            reasons.append("Matches property type preference")
        
        return reasons[:4]  # Limit to top 4 reasons
    
    def _fallback_search(self, customer: Customer, properties: List[Property], 
                        top_k: int) -> List[Dict[str, Any]]:
        """
        Fallback to rule-based search when vector search fails
        """
        self.logger.info("Using fallback rule-based search")
        
        recommendations = []
        for property in properties:
            score = self._calculate_hybrid_score(customer, property, 50)  # Default similarity
            reasons = self._generate_match_reasons(customer, property, 50)
            
            recommendations.append({
                'property': property,
                'similarity_score': 50.0,
                'hybrid_score': score,
                'match_reasons': reasons
            })
        
        recommendations.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return recommendations[:top_k]
    
    def reset_database(self):
        """
        Reset the vector database (useful for testing)
        """
        try:
            self.chroma_client.reset()
            self.logger.info("Vector database reset successfully")
        except Exception as e:
            self.logger.error(f"Error resetting database: {e}")

# Global vector service instance
vector_service = VectorService()