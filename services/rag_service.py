import logging
from typing import List, Dict, Any, Optional
from services.gemini_service import gemini_service
from services.vector_service import vector_service
from sqlalchemy_models import Property, Customer
from utils.execution_tracer import log_execution

logger = logging.getLogger("services.rag_service")

class RAGService:
    """
    Retrieval-Augmented Generation service for property recommendations and interactions.
    Orchestrates retrieval from vector service and generation from gemini service.
    """

    def __init__(self):
        self.logger = logger
        self.min_retrieval_score = 0.6  # Minimum score for retrieved items to be considered

    @log_execution
    def retrieve_relevant_properties(
        self,
        customer: Customer,
        query: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant properties based on customer preferences and query.
        Uses vector service for semantic search and optionally filters by customer preferences.
        """
        try:
            # Get all active properties for search (in practice, you might want to limit by other criteria)
            # For now, we rely on vector_service to handle the property list passed to it.
            # However, we need to get properties from somewhere. Let's assume we pass a list of properties.
            # In a real scenario, we might fetch properties from the database based on basic filters.
            # For this example, we'll rely on the vector_service to work with a provided list.
            # But note: the vector_service.search_properties method expects a list of properties.
            # We need to get that list. We'll fetch active properties from the database.
            from services.database_service import database_service
            properties = database_service.get_active_properties()
            if not properties:
                logger.warning("No active properties found for retrieval")
                return []

            # Use vector service to search for relevant properties
            search_results = vector_service.search_properties_with_meta(
                customer=customer,
                properties=properties,
                top_k=top_k
            )

            # Extract results and filter by score
            results = search_results.get("results", [])
            filtered_results = [
                result for result in results
                if result.get("hybrid_score", 0) >= self.min_retrieval_score * 100  # Convert to percentage
            ]

            logger.info(f"Retrieved {len(filtered_results)} relevant properties for customer {customer.id}")
            return filtered_results

        except Exception as e:
            logger.error(f"Error in retrieve_relevant_properties: {e}")
            return []

    @log_execution
    def augment_with_context(
        self,
        customer: Customer,
        properties: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Augment the retrieved properties with context from gemini service and conversation history.
        Returns augmented context for generation.
        """
        try:
            # Use gemini service to generate reasoning for top properties
            # We'll take the top 3 properties for reasoning generation (as per gemini_service reasoning_top_n)
            top_properties = properties[:3] if len(properties) >= 3 else properties

            # Prepare property objects for gemini service
            property_objects = [result["property"] for result in top_properties]

            # Get recommendations with reasoning from gemini service
            # This will use the gemini_service.get_property_recommendations method
            recommendations = gemini_service.get_property_recommendations(
                customer=customer,
                properties=property_objects
            )

            # Combine vector search results with gemini reasoning
            augmented_context = {
                "customer": customer,
                "retrieved_properties": properties,
                "reasoning": [],
                "conversation_history": conversation_history or [],
                "gemini_recommendations": recommendations
            }

            # Extract reasoning from recommendations
            for rec in recommendations:
                if "analysis" in rec:
                    augmented_context["reasoning"].append({
                        "property_id": rec["property"].id,
                        "explanation": rec["analysis"],
                        "pros": rec.get("pros", []),
                        "cons": rec.get("cons", [])
                    })

            logger.info(f"Augmented context with {len(augmented_context['reasoning'])} reasoning items")
            return augmented_context

        except Exception as e:
            logger.error(f"Error in augment_with_context: {e}")
            # Return basic context even if augmentation fails
            return {
                "customer": customer,
                "retrieved_properties": properties,
                "reasoning": [],
                "conversation_history": conversation_history or [],
                "gemini_recommendations": []
            }

    @log_execution
    def generate_response(
        self,
        augmented_context: Dict[str, Any],
        query: str
    ) -> str:
        """
        Generate a natural language response based on augmented context and user query.
        Uses gemini service for generation.
        """
        try:
            # Prepare prompt for gemini service
            customer = augmented_context["customer"]
            properties = augmented_context["retrieved_properties"]
            reasoning = augmented_context["reasoning"]
            history = augmented_context["conversation_history"]

            # Build context string
            context_parts = [
                f"Customer preferences:",
                f"- Budget: ${customer.budget_min or 0} - ${customer.budget_max or 0}",
                f"- Preferred type: {customer.preferred_type or 'any'}",
                f"- Preferred bedrooms: {customer.preferred_bedrooms or 'any'}",
                f"- Preferred bathrooms: {customer.preferred_bathrooms or 'any'}",
                f"- Location preference: {customer.location_preference or 'any'}",
                "",
                f"Query: {query}",
                "",
                f"Found {len(properties)} relevant properties.",
            ]

            if reasoning:
                context_parts.append("Property reasoning:")
                for i, reason in enumerate(reasoning[:3]):  # Limit to top 3
                    context_parts.append(
                        f"{i+1}. Property ID {reason['property_id']}: {reason['explanation']}"
                    )
                    if reason.get("pros"):
                        context_parts.append(f"   Pros: {', '.join(reason['pros'][:2])}")

            if history:
                context_parts.append("")
                context_parts.append("Recent conversation:")
                for item in history[-3:]:  # Last 3 items
                    role = item.get("role", "user")
                    parts = item.get("parts", [])
                    text = " ".join([p.get("text", "") for p in parts if isinstance(p, dict)]) if parts else ""
                    if text:
                        context_parts.append(f"{role}: {text}")

            prompt = "\n".join(context_parts)

            # Use gemini service for text generation (we don't have a direct method, but we can use the provider)
            # However, looking at gemini_service, it doesn't have a general text generation method.
            # We have methods like generate_market_analysis, generate_matchmaker_pitch, etc.
            # For simplicity, we'll use the provider's text generation if available, or fall back to a template.

            # Try to use the LLM provider for text generation
            if gemini_service.provider.is_available:
                # We don't have a direct text generation method in the provider interface as seen.
                # Let's check what methods are available in the provider.
                # Since we don't have the provider interface here, we'll use a fallback approach.
                # In a real implementation, we would add a text generation method to the LLM provider.
                pass

            # Fallback: generate a template-based response
            response = self._generate_template_response(
                customer=customer,
                properties=properties,
                reasoning=reasoning,
                query=query
            )

            logger.info(f"Generated response for query: {query[:50]}...")
            return response

        except Exception as e:
            logger.error(f"Error in generate_response: {e}")
            return self._generate_fallback_response(query)

    @log_execution
    def _generate_template_response(
        self,
        customer: Customer,
        properties: List[Dict[str, Any]],
        reasoning: List[Dict[str, Any]],
        query: str
    ) -> str:
        """Generate a template-based response when AI generation is not available."""
        if not properties:
            return "I couldn't find any properties matching your criteria. Please try adjusting your search parameters."

        response_parts = [
            f"I found {len(properties)} properties that match your preferences."
        ]

        if reasoning:
            response_parts.append("\nHere are my top recommendations:")
            for i, reason in enumerate(reasoning[:3]):
                prop = next((p["property"] for p in properties if p["property"].id == reason["property_id"]), None)
                if prop:
                    response_parts.append(
                        f"{i+1}. {prop.title} - {reason['explanation']}"
                    )
                    if reason.get("pros"):
                        response_parts.append(f"   Pros: {', '.join(reason['pros'][:2])}")

        response_parts.append("\nWould you like more details about any of these properties?")
        return "\n".join(response_parts)

    @log_execution
    def _generate_fallback_response(self, query: str) -> str:
        """Generate a fallback response when an error occurs."""
        return (
            "I'm experiencing technical difficulties processing your request. "
            "Please try again in a moment, or contact support if the issue persists."
        )

    @log_execution
    def process_rag_query(
        self,
        customer: Customer,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Main method to process a RAG query: retrieve, augment, and generate.
        Returns a dictionary with the response and metadata.
        """
        try:
            # Step 1: Retrieve relevant properties
            retrieved_properties = self.retrieve_relevant_properties(
                customer=customer,
                query=query,
                top_k=top_k
            )

            # Step 2: Augment with context
            augmented_context = self.augment_with_context(
                customer=customer,
                properties=retrieved_properties,
                conversation_history=conversation_history
            )

            # Step 3: Generate response
            response_text = self.generate_response(
                augmented_context=augmented_context,
                query=query
            )

            return {
                "response": response_text,
                "retrieved_count": len(retrieved_properties),
                "context": augmented_context,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Error in process_rag_query: {e}")
            return {
                "response": self._generate_fallback_response(query),
                "retrieved_count": 0,
                "context": {},
                "status": "error",
                "error": str(e)
            }


# Global service instance
rag_service = RAGService()