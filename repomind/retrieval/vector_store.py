"""FAISS vector store index with metadata persistence and similarity search."""
import json
import pickle
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from repomind.config import INDEXES_DIR
from repomind.ingestion.chunker import CodeChunk


class FAISSVectorStore:
    """FAISS-backed vector database for repository code and documentation chunks."""

    def __init__(self, dimension: int = 256):
        self.dimension = dimension
        self.chunks: List[CodeChunk] = []
        self.index = None
        self._raw_vectors: Optional[np.ndarray] = None
        self._initialize_index()

    def _initialize_index(self) -> None:
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatIP(self.dimension)
        else:
            self.index = None

    def add_chunks(self, chunks: List[CodeChunk], embeddings: np.ndarray) -> None:
        """Add chunks and corresponding float32 normalized embeddings to index."""
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(f"Mismatch: {len(chunks)} chunks vs {embeddings.shape[0]} embeddings")

        embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)
        self.chunks.extend(chunks)

        if FAISS_AVAILABLE and self.index is not None:
            self.index.add(embeddings)
        else:
            if self._raw_vectors is None:
                self._raw_vectors = embeddings
            else:
                self._raw_vectors = np.vstack([self._raw_vectors, embeddings])

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[CodeChunk, float]]:
        """Find the top-k most similar chunks for a query vector."""
        if not self.chunks:
            return []

        top_k = min(top_k, len(self.chunks))
        query_vector = np.ascontiguousarray(query_vector.reshape(1, -1), dtype=np.float32)

        if FAISS_AVAILABLE and self.index is not None and self.index.ntotal > 0:
            scores, indices = self.index.search(query_vector, top_k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(self.chunks):
                    results.append((self.chunks[idx], float(score)))
            return results
        elif self._raw_vectors is not None:
            # Fallback numpy cosine similarity
            sims = np.dot(self._raw_vectors, query_vector.T).flatten()
            top_indices = np.argsort(sims)[::-1][:top_k]
            return [(self.chunks[i], float(sims[i])) for i in top_indices]

        return []

    def save(self, base_path: Path) -> None:
        """Save FAISS binary and chunk metadata to disk."""
        base_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path = base_path.with_suffix(".chunks.pkl")
        faiss_path = base_path.with_suffix(".faiss")

        # Save chunks metadata
        with open(meta_path, "wb") as f:
            pickle.dump(self.chunks, f)

        # Save index
        if FAISS_AVAILABLE and self.index is not None:
            faiss.write_index(self.index, str(faiss_path))
        elif self._raw_vectors is not None:
            np.save(str(base_path.with_suffix(".npy")), self._raw_vectors)

    def load(self, base_path: Path) -> bool:
        """Load FAISS index and chunk metadata from disk if available."""
        meta_path = base_path.with_suffix(".chunks.pkl")
        faiss_path = base_path.with_suffix(".faiss")
        npy_path = base_path.with_suffix(".npy")

        if not meta_path.exists():
            return False

        with open(meta_path, "rb") as f:
            self.chunks = pickle.load(f)

        if FAISS_AVAILABLE and faiss_path.exists():
            self.index = faiss.read_index(str(faiss_path))
            self.dimension = self.index.d
            return True
        elif npy_path.exists():
            self._raw_vectors = np.load(str(npy_path))
            self.dimension = self._raw_vectors.shape[1]
            return True

        return False
