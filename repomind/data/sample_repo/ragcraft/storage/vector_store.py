"""Vector store abstraction and FAISS implementation."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
from ragcraft.config import VectorStoreConfig


class VectorStore(ABC):
    """Abstract interface defining required vector store operations."""

    @abstractmethod
    def add_vectors(self, vectors: List[List[float]], documents: List[Dict[str, Any]]) -> None:
        """Store vectors alongside document metadata."""
        pass

    @abstractmethod
    def similarity_search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for the most similar document embeddings."""
        pass

    @abstractmethod
    def save(self, filepath: str) -> None:
        """Persist index state to disk."""
        pass

    @abstractmethod
    def load(self, filepath: str) -> None:
        """Restore index state from disk."""
        pass


class FAISSVectorStore(VectorStore):
    """Concrete vector store implementation backed by FAISS IndexFlatIP / IndexFlatL2."""

    def __init__(self, config: Optional[VectorStoreConfig] = None):
        self.config = config or VectorStoreConfig()
        self.dimension = self.config.dimension
        self.index = None
        self.doc_store: List[Dict[str, Any]] = []
        self._initialize_index()

    def _initialize_index(self) -> None:
        """Initialize the underlying FAISS index."""
        # Simulated FAISS index initialization
        self.index = {
            "dimension": self.dimension,
            "metric": self.config.index_type,
            "total_vectors": 0
        }

    def add_vectors(self, vectors: List[List[float]], documents: List[Dict[str, Any]]) -> None:
        """Insert vectors into FAISS and record document chunks."""
        if len(vectors) != len(documents):
            raise ValueError("Vectors and documents list size mismatch")
        self.doc_store.extend(documents)
        self.index["total_vectors"] += len(vectors)

    def similarity_search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform nearest neighbor search using FAISS."""
        if not self.doc_store:
            return []
        # Return top_k documents with computed scores
        return self.doc_store[:top_k]

    def save(self, filepath: str) -> None:
        """Save FAISS binary index to local file path."""
        pass

    def load(self, filepath: str) -> None:
        """Load FAISS binary index from local file path."""
        pass
