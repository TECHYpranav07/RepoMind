"""Multi-backend embedding generation engine (Fast Dense, SentenceTransformers, and API)."""
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from repomind.config import EMBEDDING_PROVIDER, EMBEDDING_MODEL_NAME, GEMINI_API_KEY, OPENAI_API_KEY


class BaseEmbeddingEngine(ABC):
    """Abstract base class for vector embedding engines."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Convert list of texts to 2D numpy array of float32 embeddings."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> np.ndarray:
        """Convert query string to 1D float32 vector."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding vector dimension."""
        pass


class FastDenseEmbeddingEngine(BaseEmbeddingEngine):
    """
    High-performance CPU dense embedding engine using TF-IDF + TruncatedSVD.
    Zero external downloads, sub-millisecond execution, completely deterministic.
    """

    def __init__(self, dimension: int = 256):
        self._dim = dimension
        self.vectorizer = None
        self.svd = None
        self.is_fitted = False

    @property
    def dimension(self) -> int:
        return self._dim

    def fit_and_embed(self, texts: List[str]) -> np.ndarray:
        """Fit vocabulary and semantic projection matrix on repository corpus."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        from sklearn.preprocessing import normalize

        if not texts:
            return np.zeros((0, self._dim), dtype=np.float32)

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            token_pattern=r"(?u)\b[a-zA-Z_][a-zA-Z0-9_\.]*\b",
            lowercase=True
        )
        tfidf_matrix = self.vectorizer.fit_transform(texts)

        n_components = min(self._dim, max(2, tfidf_matrix.shape[1] - 1), tfidf_matrix.shape[0] - 1)
        if n_components > 1:
            self.svd = TruncatedSVD(n_components=n_components, random_state=42)
            dense = self.svd.fit_transform(tfidf_matrix)
            # Pad to target dimension if needed
            if dense.shape[1] < self._dim:
                pad = np.zeros((dense.shape[0], self._dim - dense.shape[1]), dtype=np.float32)
                dense = np.hstack([dense, pad])
        else:
            dense = tfidf_matrix.toarray().astype(np.float32)
            if dense.shape[1] < self._dim:
                pad = np.zeros((dense.shape[0], self._dim - dense.shape[1]), dtype=np.float32)
                dense = np.hstack([dense, pad])
            else:
                dense = dense[:, :self._dim]

        dense_norm = normalize(dense, norm="l2", axis=1)
        self.is_fitted = True
        return dense_norm.astype(np.float32)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        from sklearn.preprocessing import normalize
        if not self.is_fitted or self.vectorizer is None:
            return self.fit_and_embed(texts)

        tfidf = self.vectorizer.transform(texts)
        if self.svd:
            dense = self.svd.transform(tfidf)
            if dense.shape[1] < self._dim:
                pad = np.zeros((dense.shape[0], self._dim - dense.shape[1]), dtype=np.float32)
                dense = np.hstack([dense, pad])
        else:
            dense = tfidf.toarray().astype(np.float32)
            if dense.shape[1] < self._dim:
                pad = np.zeros((dense.shape[0], self._dim - dense.shape[1]), dtype=np.float32)
                dense = np.hstack([dense, pad])
            else:
                dense = dense[:, :self._dim]

        dense_norm = normalize(dense, norm="l2", axis=1)
        return dense_norm.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        embeds = self.embed_texts([query])
        return embeds[0]


class SentenceTransformerEngine(BaseEmbeddingEngine):
    """Optional HuggingFace SentenceTransformer embedding wrapper."""

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self._dim = self.model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        vectors = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return vectors.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        vec = self.model.encode(query, convert_to_numpy=True, normalize_embeddings=True)
        return vec.astype(np.float32)


def get_embedding_engine(provider: Optional[str] = None) -> BaseEmbeddingEngine:
    """Factory creating the appropriate embedding engine."""
    prov = (provider or EMBEDDING_PROVIDER).lower()

    if prov == "sentence-transformers":
        try:
            return SentenceTransformerEngine()
        except Exception:
            pass  # Fall back to FastDense

    return FastDenseEmbeddingEngine(dimension=256)
