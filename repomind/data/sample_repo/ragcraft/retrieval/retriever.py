"""Semantic retrieval engine combining vector storage and Redis caching."""
from typing import List, Dict, Any, Optional
from ragcraft.storage.vector_store import VectorStore, FAISSVectorStore
from ragcraft.storage.cache import RedisCache
from ragcraft.config import VectorStoreConfig, CacheConfig


class SemanticRetriever:
    """Orchestrates embedding lookup, cache verification, and vector search."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        cache: Optional[RedisCache] = None,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.vector_store = vector_store or FAISSVectorStore()
        self.cache = cache or RedisCache()
        self.embedding_model = embedding_model

    def encode_query(self, query: str) -> List[float]:
        """Convert query string into dense vector embedding."""
        # Simulated 384-dimensional dense vector
        return [0.05] * 384

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant document chunks with cache-aside lookup."""
        cache_key = f"query:{query}:top_k:{top_k}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        query_vector = self.encode_query(query)
        results = self.vector_store.similarity_search(query_vector, top_k=top_k)

        self.cache.set(cache_key, results)
        return results

    def add_documents(self, documents: List[Dict[str, Any]]) -> int:
        """Embed and insert new documents into vector store."""
        vectors = [self.encode_query(doc.get("text", "")) for doc in documents]
        self.vector_store.add_vectors(vectors, documents)
        self.cache.invalidate("query:*")
        return len(documents)
