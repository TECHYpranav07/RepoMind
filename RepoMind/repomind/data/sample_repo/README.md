# RagCraft: High-Throughput Enterprise RAG Microservice

RagCraft is a modular Retrieval-Augmented Generation (RAG) microservice designed for knowledge-intensive enterprise applications.

## Architecture Overview

RagCraft connects vector search with large language models through an asynchronous pipeline:

1. **API Layer (`ragcraft/api/server.py`)**: Exposes REST endpoints (`/query`, `/index`, `/health`) built on FastAPI.
2. **Pipeline Layer (`ragcraft/pipeline/rag_pipeline.py`)**: Coordinates semantic retrieval, prompt formatting, and answer synthesis.
3. **Retrieval Layer (`ragcraft/retrieval/retriever.py`)**: Provides hybrid caching and vector search querying.
4. **Storage Layer (`ragcraft/storage/vector_store.py`)**: Wraps FAISS index persistence, vector quantization, and document chunk lookups.
5. **Cache Layer (`ragcraft/storage/cache.py`)**: Redis-backed cache for hot query answers and intermediate embeddings.
6. **Configuration (`ragcraft/config.py`)**: Pydantic-based settings for index paths, embedding dimensions, and thresholds.

## Key Dependencies
- `faiss-cpu`: Core in-memory and disk-persisted vector similarity search index.
- `fastapi` & `uvicorn`: High-performance asynchronous REST API server.
- `redis`: High-speed key-value cache to minimize redundant embeddings and LLM calls.
- `sentence-transformers`: Local embedding generation for query and document vectors.
- `pydantic`: Environment validation and schema enforcement.

## What-If Scenarios Supported
- What happens if we replace FAISS with ChromaDB or Milvus?
- What happens if Redis caching is disabled or removed?
- What if the embedding model is upgraded to 1536-dimensional vectors?
- Which components are impacted if `SemanticRetriever.retrieve()` signature changes?
