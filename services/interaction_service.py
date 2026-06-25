import logging
from typing import Dict, Any, Optional, List
from services.gemini_service import gemini_service, chat_with_agentic_rag
from sqlalchemy_models import Customer, Property, Agent, Deal, Task
from services.database_service import database_service
from utils.execution_tracer import log_execution

logger = logging.getLogger("services.interaction_service")

class InteractionService:
    """
    Service for handling AI-powered user interactions, extending the base agentic RAG chat
    with estate-specific context and CRM integration.
    """

    def __init__(self):
        self.logger = logger

    @log_execution
    def process_customer_chat(
        self,
        customer_id: int,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message from a customer, generating a response and optionally
        logging the interaction and updating lead scores.

        Args:
            customer_id: ID of the customer
            user_message: The customer's message
            conversation_history: List of previous conversation turns

        Returns:
            Dictionary containing the response and any actions taken
        """
        try:
            # Fetch customer from database
            customer = database_service.get_customer_by_id(customer_id)
            if not customer:
                return {
                    "response": "I'm sorry, I couldn't find your customer profile. Please ensure you are logged in.",
                    "status": "error",
                    "error": "Customer not found"
                }

            # Use the base agentic RAG chat function to get a response
            response_text = chat_with_agentic_rag(
                user_prompt=user_message,
                conversation_history=conversation_history or []
            )

            # Log the interaction (if we have a logging mechanism)
            self._log_interaction(
                customer_id=customer_id,
                user_message=user_message,
                agent_response=response_text,
                interaction_type="customer_chat"
            )

            # Optionally update lead score based on interaction
            # This is a placeholder for more sophisticated lead scoring
            self._update_lead_score_from_interaction(
                customer_id=customer_id,
                interaction_type="chat",
                message_content=user_message
            )

            return {
                "response": response_text,
                "status": "success",
                "customer_id": customer_id
            }

        except Exception as e:
            self.logger.error(f"Error in process_customer_chat: {e}")
            return {
                "response": "I'm experiencing technical difficulties. Please try again later.",
                "status": "error",
                "error": str(e)
            }

    @log_execution
    def process_agent_chat(
        self,
        agent_id: int,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message from an agent, providing CRM-related assistance.

        Args:
            agent_id: ID of the agent
            user_message: The agent's message
            conversation_history: List of previous conversation turns

        Returns:
            Dictionary containing the response and any actions taken
        """
        try:
            # Fetch agent from database
            agent = database_service.get_agent_by_id(agent_id)
            if not agent:
                return {
                    "response": "I'm sorry, I couldn't find your agent profile.",
                    "status": "error",
                    "error": "Agent not found"
                }

            # For agent chats, we might want to focus on different aspects:
            # - Property searches for clients
            # - Deal information
            # - Task management
            # - Customer follow-ups

            # We can still use the base agentic RAG chat, but we might want to
            # bias the search towards agent-relevant data or add agent-specific context.
            # For now, we'll use the same function but note that the conversation
            # history and user message might be interpreted differently.

            response_text = chat_with_agentic_rag(
                user_prompt=user_message,
                conversation_history=conversation_history or []
            )

            # Log the interaction
            self._log_interaction(
                agent_id=agent_id,
                user_message=user_message,
                agent_response=response_text,
                interaction_type="agent_chat"
            )

            return {
                "response": response_text,
                "status": "success",
                "agent_id": agent_id
            }

        except Exception as e:
            self.logger.error(f"Error in process_agent_chat: {e}")
            return {
                "response": "I'm experiencing technical difficulties. Please try again later.",
                "status": "error",
                "error": str(e)
            }

    @log_execution
    def _log_interaction(
        self,
        customer_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        user_message: str = "",
        agent_response: str = "",
        interaction_type: str = "general"
    ) -> None:
        """
        Log an interaction to the database for analytics and follow-up.
        This is a placeholder implementation - in a real system, you would
        have an interaction log table and service.
        """
        try:
            # In a real implementation, you would insert into an interaction_log table
            # For now, we'll just log it
            self.logger.info(
                f"Interaction logged - Type: {interaction_type}, "
                f"CustomerID: {customer_id}, AgentID: {agent_id}, "
                f"UserMessage length: {len(user_message)}, "
                f"Response length: {len(agent_response)}"
            )
            # TODO: Implement actual database logging
        except Exception as e:
            self.logger.error(f"Failed to log interaction: {e}")

    @log_execution
    def _update_lead_score_from_interaction(
        self,
        customer_id: int,
        interaction_type: str,
        message_content: str
    ) -> None:
        """
        Update a customer's lead score based on their interaction.
        This is a simplified example - real lead scoring would be more complex.
        """
        try:
            # Fetch current customer
            customer = database_service.get_customer_by_id(customer_id)
            if not customer:
                return

            # Simple scoring:
            # - Any interaction: +5 points
            # - Asking about specific properties: +10 points
            # - Asking about scheduling a viewing: +15 points
            # - Providing contact information: +10 points

            score_increase = 5  # Base for any interaction
            lower_content = message_content.lower()

            if any(keyword in lower_content for keyword in ["property", "house", "apartment", "villa", "listing"]):
                score_increase += 10
            if any(keyword in lower_content for keyword in ["viewing", "visit", "tour", "see"]):
                score_increase += 15
            if any(keyword in lower_content for keyword in ["phone", "email", "contact", "call"]):
                score_increase += 10

            # In a real system, you would update the customer's lead score in the database
            # For now, we'll just log it
            self.logger.info(
                f"Lead score update for customer {customer_id}: +{score_increase} "
                f"for interaction type '{interaction_type}'"
            )
            # TODO: Implement actual lead score update in database
        except Exception as e:
            self.logger.error(f"Failed to update lead score: {e}")

    @log_execution
    def get_suggested_responses(
        self,
        customer_id: int,
        context: Optional[str] = None
    ) -> List[str]:
        """
        Get suggested responses or next steps for a customer based on their profile and context.
        This could be used to show quick-reply buttons in a chat interface.

        Args:
            customer_id: ID of the customer
            context: Optional context (e.g., current page, recent activity)

        Returns:
            List of suggested response strings
        """
        try:
            customer = database_service.get_customer_by_id(customer_id)
            if not customer:
                return ["Tell me about your property preferences"]

            suggestions = []

            # Context-aware suggestions
            if context == "property_viewing":
                suggestions.extend([
                    "Schedule a viewing for this property",
                    "Ask about similar properties",
                    "Request more photos or details"
                ])
            elif context == "price_discussion":
                suggestions.extend([
                    "Negotiate the price",
                    "Ask about payment terms",
                    "Request a mortgage consultation"
                ])
            else:
                # General suggestions based on customer profile
                if customer.budget_min and customer.budget_max:
                    suggestions.append(
                        f"Show me properties in my budget (${customer.budget_min:,.0f} - ${customer.budget_max:,.0f})"
                    )
                if customer.preferred_bedrooms:
                    suggestions.append(
                        f"Find {customer.preferred_bedrooms}-bedroom properties"
                    )
                if customer.location_preference:
                    suggestions.append(
                        f"Show me properties in {customer.location_preference}"
                    )

                # Always include some general options
                suggestions.extend([
                    "Tell me about the market trends",
                    "Help me schedule a viewing",
                    "What are the next steps in the buying process?"
                ])

            # Limit to 4 suggestions to avoid overwhelming the interface
            return suggestions[:4]

        except Exception as e:
            self.logger.error(f"Error generating suggested responses: {e}")
            return [
                "Tell me about your property preferences",
                "Help me find a property",
                "Schedule a viewing",
                "Market trends"
            ]


# Global service instance
interaction_service = InteractionService()