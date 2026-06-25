import logging
import os

from services.embeddings.providers.gemini_embedding_provider import GeminiEmbeddingProvider


def _build_provider():
    provider_name = os.environ.get("EMBEDDING_PROVIDER", "gemini").lower().strip()

    if provider_name in ("gemini", "local"):
        # Local mode is handled by services.embedding_service.
        return GeminiEmbeddingProvider()

    # Keep startup resilient: unknown provider falls back to Gemini.
    logging.getLogger("services.embeddings").warning(
        "Unsupported EMBEDDING_PROVIDER=%s. Falling back to gemini.",
        provider_name,
    )
    return GeminiEmbeddingProvider()


embedding_provider = _build_provider()

__all__ = ["embedding_provider", "GeminiEmbeddingProvider"]
