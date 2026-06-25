import hashlib
import logging
import os
from typing import List

try:
    from google import genai  # type: ignore
except Exception:  # pragma: no cover
    genai = None

from services.embeddings.providers.base import EmbeddingProvider


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by Gemini API with deterministic fallback vectors."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("services.embeddings.providers.gemini")
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model = os.environ.get("GEMINI_EMBED_MODEL", "text-embedding-004")
        self._dimension = int(os.environ.get("EMBEDDING_DIM", "768"))
        self.client = None

        if genai is None:
            return

        if not self.api_key:
            return

        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as exc:  # pragma: no cover
            self.logger.warning(f"Failed to initialize Gemini embedding client: {exc}")
            self.client = None

    @property
    def is_available(self) -> bool:
        return self.client is not None

    @property
    def dimension(self) -> int:
        return self._dimension

    def _fallback_vector(self, text: str) -> List[float]:
        # Deterministic low-cost fallback vector when provider unavailable.
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vec = []
        for i in range(self._dimension):
            byte_val = digest[i % len(digest)]
            vec.append((byte_val / 255.0) * 2 - 1)
        return vec

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        if not self.client:
            return [self._fallback_vector(t) for t in texts]

        results: List[List[float]] = []
        for text in texts:
            try:
                response = self.client.models.embed_content(
                    model=self.model,
                    contents=text,
                )
                embeddings = getattr(response, "embeddings", None)
                if embeddings:
                    values = getattr(embeddings[0], "values", None)
                    if values:
                        results.append(list(values))
                        continue
            except Exception as exc:
                self.logger.warning(f"Embedding request failed, fallback used: {exc}")
            results.append(self._fallback_vector(text))

        return results
