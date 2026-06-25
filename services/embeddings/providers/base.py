from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Provider interface for dense vector embeddings."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError
