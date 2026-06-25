import logging
import os
from typing import List, Union

from services.embeddings import embedding_provider
from utils.execution_tracer import log_execution


class EmbeddingService:
    """
    Lightweight embedding facade.
    - Default: API provider via services.embeddings
    - Optional local mode: set EMBEDDING_PROVIDER=local and install ai_local extras
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = None):
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        self.device = device
        self.provider_mode = os.environ.get("EMBEDDING_PROVIDER", "gemini")
        self.model = None

    @log_execution
    def _ensure_local_model(self) -> bool:
        if self.model is not None:
            return True

        if self.provider_mode != "local":
            return False

        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            import torch  # type: ignore

            runtime_device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
            self.logger.info(f"Loading local embedding model {self.model_name} on {runtime_device}")
            self.model = SentenceTransformer(self.model_name, device=runtime_device)
            return True
        except Exception as exc:
            self.logger.warning(f"Local embedding model unavailable: {exc}")
            return False

    @log_execution
    def embed(
        self,
        texts: Union[str, List[str]],
        normalize: bool = True,
        show_progress: bool = False,
    ) -> List[List[float]]:
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return []

        if self._ensure_local_model():
            try:
                embeddings = self.model.encode(  # type: ignore[union-attr]
                    texts,
                    normalize_embeddings=normalize,
                    show_progress_bar=show_progress,
                    convert_to_numpy=True,
                )
                return embeddings.tolist()
            except Exception as exc:
                self.logger.warning(f"Local embedding failed, provider fallback used: {exc}")

        return embedding_provider.embed(texts)

    @log_execution
    def embed_query(self, query: str) -> List[float]:
        vectors = self.embed([query])
        return vectors[0] if vectors else []

    @log_execution
    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        return self.embed(documents)

    @log_execution
    def get_embedding_dimension(self) -> int:
        if self.model is not None and hasattr(self.model, "get_sentence_embedding_dimension"):
            try:
                return int(self.model.get_sentence_embedding_dimension())
            except Exception:
                pass
        return embedding_provider.dimension


embedding_service = EmbeddingService()
