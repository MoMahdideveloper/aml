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
        # Indices of the most recent embed() batch that came back as non-semantic
        # fallbacks. Callers must not cache these as if they were real vectors.
        self.last_fallback_indices: set[int] = set()
        # Texts sent per API request. The free tier bills per *request* (RPD 1000)
        # but caps tokens per minute (TPM 30000), so batching many short texts into
        # one call is strictly better: same tokens, a fraction of the request quota.
        self._batch_size = max(1, int(os.environ.get("GEMINI_EMBED_BATCH", "20")))
        # Round-robin cursor so consecutive batches spread across keys instead of
        # hammering key 1 until it 429s.
        self._key_cursor = 0

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

    def _fallback_vector(self, text: str, reason: str = "provider unavailable") -> List[float]:
        """Deterministic low-cost pseudo-vector used when the provider fails.

        This vector carries NO semantic meaning -- it is a hash, so similarity
        against real embeddings is noise. Always warn, otherwise a degraded
        provider looks identical to healthy semantic search from the outside.
        Never log the text itself: embedded content includes customer PII.
        """
        self.logger.warning(
            "Using non-semantic fallback embedding (%s); similarity results are unreliable. chars=%d",
            reason,
            len(text),
        )
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vec = []
        for i in range(self._dimension):
            byte_val = digest[i % len(digest)]
            vec.append((byte_val / 255.0) * 2 - 1)
        return vec

    @staticmethod
    def _l2_normalize(values: List[float]) -> List[float]:
        """Scale a vector to unit length so cosine similarity stays meaningful.

        Gemini only guarantees normalized output at its native 3072 dimensions.
        Any other output_dimensionality -- and any client-side slicing we do --
        breaks unit length, which silently distorts every cosine score compared
        against the matcher threshold. Normalizing an already-unit vector is a
        no-op, so this is safe to apply unconditionally.
        """
        magnitude = sum(component * component for component in values) ** 0.5
        if magnitude <= 0.0:
            return values
        return [component / magnitude for component in values]

    def _truncate_or_pad(self, values: List[float]) -> List[float]:
        """Align provider vectors to EMBEDDING_DIM for local vector store stability.

        Re-normalizes whenever the vector is resized: truncating drops part of
        the magnitude and zero-padding leaves it unchanged while the dimension
        grows, so in both cases the result is no longer unit length.
        """
        if len(values) == self._dimension:
            return self._l2_normalize(values)
        if len(values) > self._dimension:
            return self._l2_normalize(values[: self._dimension])
        return self._l2_normalize(values + [0.0] * (self._dimension - len(values)))

    def embed(self, texts: List[str]) -> List[List[float]]:
        self.last_fallback_indices = set()
        if not texts:
            return []

        if not self.client:
            self.last_fallback_indices = set(range(len(texts)))
            return [
                self._fallback_vector(t, reason="embedding client not initialized")
                for t in texts
            ]

        results: List[List[float]] = []
        for start in range(0, len(texts), self._batch_size):
            chunk = texts[start : start + self._batch_size]
            vectors = self._embed_batch(chunk)
            for offset, vector in enumerate(vectors):
                if vector is None:
                    self.last_fallback_indices.add(len(results))
                    results.append(
                        self._fallback_vector(
                            chunk[offset],
                            reason=(
                                f"all {len(self.api_keys)} key(s) x "
                                f"{len(self.models)} model(s) failed"
                            ),
                        )
                    )
                else:
                    results.append(vector)

        return results

    def _embed_batch(self, chunk: List[str]) -> List[object]:
        """Embed one chunk in a single request, retrying across keys then models.

        Returns a list the same length as ``chunk``; entries are vectors, or None
        where no key/model combination produced one. A batch request costs one
        unit of the per-day request quota regardless of how many texts it carries,
        which is what keeps a full re-index inside the free tier.

        If the batch call fails, falls back to individual per-text retries so that
        one bad input doesn't poison the whole batch.
        """
        key_count = len(self.api_keys)
        for attempt in range(key_count):
            key_index = (self._key_cursor + attempt) % key_count
            api_key = self.api_keys[key_index]
            try:
                client = self._client_for(api_key)
            except Exception:
                continue
            for model in self.models:
                try:
                    vectors = self._request_batch(client, model, chunk)
                except Exception as exc:
                    self.logger.warning(
                        "Embedding request failed key=%s model=%s size=%d: %s",
                        key_index + 1,
                        model,
                        len(chunk),
                        type(exc).__name__,
                    )
                    continue
                if vectors is None:
                    continue
                # Advance past the key that worked so load spreads over the pool.
                self._key_cursor = (key_index + 1) % key_count
                self.client = client
                return vectors
        # Batch failed on all keys/models. If chunk has >1 item, retry each one
        # individually so that only the truly-failing texts fall back.
        if len(chunk) > 1:
            result = []
            for text in chunk:
                solo = self._embed_batch([text])
                result.append(solo[0] if solo else None)
            return result
        return [None] * len(chunk)

    def _request_batch(self, client, model: str, chunk: List[str]):
        """Single embed_content call for a list of texts.

        A partial response (fewer vectors than inputs) is rejected outright: silently
        misaligning vectors with properties would attach one listing's embedding to
        another, which is worse than falling back.
        """
        kwargs = {"model": model, "contents": chunk}
        try:
            from google.genai import types as genai_types

            kwargs["config"] = genai_types.EmbedContentConfig(
                output_dimensionality=self._dimension,
            )
        except Exception:
            pass
        try:
            response = client.models.embed_content(**kwargs)
        except TypeError:
            kwargs.pop("config", None)
            response = client.models.embed_content(**kwargs)

        embeddings = getattr(response, "embeddings", None)
        if not embeddings or len(embeddings) != len(chunk):
            return None

        vectors = []
        for item in embeddings:
            values = getattr(item, "values", None)
            if not values:
                return None
            vectors.append(self._truncate_or_pad(list(values)))
        return vectors
