"""Standard benchmark dataset for software repository Q&A and What-If analysis."""
from typing import List, Dict, Any

BENCHMARK_DATASET: List[Dict[str, Any]] = [
    {
        "id": "q1_vector_store_role",
        "category": "Architecture",
        "question": "What vector store does this repository use and how is it initialized?",
        "expected_files": [
            "ragcraft/storage/vector_store.py",
            "ragcraft/config.py",
            "README.md"
        ],
        "expected_components": [
            "FAISSVectorStore",
            "VectorStoreConfig",
            "VectorStore"
        ],
        "reference_answer": "The repository uses FAISSVectorStore, which wraps FAISS index types (IndexFlatIP/IndexFlatL2) and is configured using VectorStoreConfig with default dimension 384."
    },
    {
        "id": "q2_cache_integration",
        "category": "Architecture",
        "question": "How is caching implemented and where is it checked during retrieval?",
        "expected_files": [
            "ragcraft/storage/cache.py",
            "ragcraft/retrieval/retriever.py",
            "ragcraft/config.py"
        ],
        "expected_components": [
            "RedisCache",
            "SemanticRetriever",
            "CacheConfig"
        ],
        "reference_answer": "RedisCache manages key-value lookups with TTL. SemanticRetriever checks the cache first in retrieve() before generating embeddings and querying the vector store."
    },
    {
        "id": "q3_whatif_replace_faiss",
        "category": "What-If",
        "question": "What if we replace FAISS with ChromaDB?",
        "expected_files": [
            "ragcraft/storage/vector_store.py",
            "ragcraft/retrieval/retriever.py",
            "ragcraft/config.py",
            "ragcraft/pipeline/rag_pipeline.py",
            "tests/test_retriever.py",
            "requirements.txt"
        ],
        "expected_components": [
            "FAISSVectorStore",
            "VectorStore",
            "SemanticRetriever",
            "VectorStoreConfig",
            "test_faiss_store_initialization"
        ],
        "reference_answer": "Replacing FAISS with ChromaDB requires implementing a ChromaDBVectorStore adhering to VectorStore, updating VectorStoreConfig, adjusting SemanticRetriever initialization, updating requirements.txt, and rewriting unit tests in test_retriever.py."
    },
    {
        "id": "q4_whatif_remove_redis",
        "category": "What-If",
        "question": "What if we remove Redis caching?",
        "expected_files": [
            "ragcraft/storage/cache.py",
            "ragcraft/retrieval/retriever.py",
            "ragcraft/config.py",
            "tests/test_retriever.py"
        ],
        "expected_components": [
            "RedisCache",
            "SemanticRetriever",
            "CacheConfig",
            "test_retriever_query_caching"
        ],
        "reference_answer": "Removing Redis caching impacts SemanticRetriever by eliminating cache checks, rendering CacheConfig redundant, increasing latency on repeated queries, and breaking test_retriever_query_caching."
    },
    {
        "id": "q5_test_coverage_pipeline",
        "category": "Testing",
        "question": "Which tests should be updated if RAGPipeline.run() signature is modified?",
        "expected_files": [
            "ragcraft/pipeline/rag_pipeline.py",
            "tests/test_pipeline.py",
            "ragcraft/api/server.py"
        ],
        "expected_components": [
            "RAGPipeline",
            "test_pipeline_run",
            "handle_query"
        ],
        "reference_answer": "Modifying RAGPipeline.run() directly affects tests/test_pipeline.py (specifically test_pipeline_run) and the API handler handle_query in ragcraft/api/server.py."
    }
]
