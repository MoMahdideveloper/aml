"""Compatibility shim — use services.gemini_service in new code."""
from services.gemini_service import GeminiService, chat_with_agentic_rag, gemini_service

__all__ = ["GeminiService", "chat_with_agentic_rag", "gemini_service"]
