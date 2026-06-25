import logging
import os

from services.llm.providers.gemini_provider import GeminiProvider
from services.llm.providers.kie_provider import KieProvider


def _build_provider():
    provider_name = os.environ.get("LLM_PROVIDER", "gemini").lower().strip()

    if provider_name == "kie":
        return KieProvider()

    if provider_name == "gemini":
        return GeminiProvider()

    # Keep startup resilient: unknown provider falls back to Gemini.
    logging.getLogger("services.llm").warning(
        "Unsupported LLM_PROVIDER=%s. Supported values: gemini, kie. Falling back to gemini.",
        provider_name,
    )
    return GeminiProvider()


llm_provider = _build_provider()

__all__ = ["llm_provider", "GeminiProvider", "KieProvider"]
