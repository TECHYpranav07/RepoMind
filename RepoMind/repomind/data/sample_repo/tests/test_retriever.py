"""Unit tests for SemanticRetriever and FAISSVectorStore."""
from ragcraft.storage.vector_store import FAISSVectorStore
from ragcraft.retrieval.retriever import SemanticRetriever


def test_faiss_store_initialization():
    store = FAISSVectorStore()
    assert store.dimension == 384
    assert store.doc_store == []


def test_retriever_query_caching():
    retriever = SemanticRetriever()
    results1 = retriever.retrieve("What is RAG?", top_k=2)
    results2 = retriever.retrieve("What is RAG?", top_k=2)
    assert results1 == results2
