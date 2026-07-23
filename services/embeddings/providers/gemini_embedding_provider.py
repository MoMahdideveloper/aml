import hashlib
import logging
import os
from typing import List

try:
    from google import genai  # type: ignore
except Exception:  # pragma: no cover
    genai = None

from services.embeddings.providers.base import EmbeddingProvider

# Gemini Embedding 2 (GA). Keep EMBEDDING_DIM=768 for local vector store compatibility.
_DEFAULT_EMBED_MODEL = "gemini-embedding-2"


def _split_values(raw: str) -> List[str]:
    return [part.strip().strip('"').strip("'") for part in (raw or "").split(",") if part.strip()]


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider backed by Google Gemini (default host).

    Keys are intentionally separate from chat/LLM:
    - Prefer GEMINI_EMBED_API_KEY / GOOGLE_EMBED_API_KEY (Google AI Studio AQ.* key)
    - Fall back to GEMINI_API_KEY / GOOGLE_API_KEY only if embed-specific key is unset

    Base URL is also separate so chat can use A6API while embeddings hit Google:
    - GEMINI_EMBED_BASE_URL only (empty = official Google Generative Language API)
    - Does NOT inherit GEMINI_BASE_URL (chat gateway)
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger("services.embeddings.providers.gemini")
        self.api_keys = _split_values(os.environ.get("GEMINI_EMBED_API_KEYS", ""))
        if not self.api_keys:
            self.api_keys = _split_values(
                os.environ.get("GEMINI_EMBED_API_KEY", "")
                or os.environ.get("GOOGLE_EMBED_API_KEY", "")
            )
        if not self.api_keys:
            self.api_keys = _split_values(os.environ.get("GOOGLE_API_KEYS", ""))
        self.api_key = self.api_keys[0] if self.api_keys else ""
        self.models = _split_values(os.environ.get("GEMINI_EMBED_MODELS", ""))
        if not self.models:
            primary = os.environ.get("GEMINI_EMBED_MODEL", _DEFAULT_EMBED_MODEL).strip() or _DEFAULT_EMBED_MODEL
            self.models = [primary]
        self.model = self.models[0]
        self._dimension = int(os.environ.get("EMBEDDING_DIM", "768"))
        self.client = None

        if genai is None:
            return

        if not self.api_keys:
            return

        # Normalize key (strip quotes/whitespace that break auth)
        try:
            self.client = self._client_for(self.api_key)
        except Exception as exc:  # pragma: no cover
            self.logger.warning(f"Failed to initialize Gemini embedding client: {exc}")
            self.client = None

    def _client_for(self, api_key: str):
        """Build a Google-native client; embedding traffic never inherits chat base URLs."""
        kwargs = {"api_key": api_key}
        base_url = (os.environ.get("GEMINI_EMBED_BASE_URL") or "").strip().rstrip("/")
        if base_url:
            from google.genai import types as genai_types

            kwargs["http_options"] = genai_types.HttpOptions(base_url=base_url)
        return genai.Client(**kwargs)

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

    def _truncate_or_pad(self, values: List[float]) -> List[float]:
        """Align provider vectors to EMBEDDING_DIM for local vector store stability."""
        if len(values) == self._dimension:
            return values
        if len(values) > self._dimension:
            return values[: self._dimension]
        return values + [0.0] * (self._dimension - len(values))

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        if not self.client:
            return [self._fallback_vector(t) for t in texts]

        results: List[List[float]] = []
        for text in texts:
            embedded = False
            for key_index, api_key in enumerate(self.api_keys):
                if key_index:
                    try:
                        self.client = self._client_for(api_key)
                    except Exception:
                        continue
                for model in self.models:
                    try:
                        kwargs = {"model": model, "contents": text}
                        try:
                            from google.genai import types as genai_types

                            kwargs["config"] = genai_types.EmbedContentConfig(
                                output_dimensionality=self._dimension,
                            )
                        except Exception:
                            pass
                        try:
                            response = self.client.models.embed_content(**kwargs)
                        except TypeError:
                            kwargs.pop("config", None)
                            response = self.client.models.embed_content(**kwargs)
                        embeddings = getattr(response, "embeddings", None)
                        if embeddings:
                            values = getattr(embeddings[0], "values", None)
                            if values:
                                results.append(self._truncate_or_pad(list(values)))
                                embedded = True
                                break
                    except Exception as exc:
                        self.logger.warning(
                            "Embedding request failed key=%s model=%s: %s",
                            key_index + 1,
                            model,
                            type(exc).__name__,
                        )
                if embedded:
                    break
            if embedded:
                continue
            results.append(self._fallback_vector(text))

        return results
