"""Integration tests for RAGPipeline."""
from ragcraft.pipeline.rag_pipeline import RAGPipeline


def test_pipeline_run():
    pipeline = RAGPipeline()
    result = pipeline.run("Explain knowledge graph retrieval")
    assert "query" in result
    assert "answer" in result
    assert "retrieved_documents" in result


def test_prompt_formatting():
    pipeline = RAGPipeline()
    docs = [{"text": "FAISS is a library for dense vector search."}]
    prompt = pipeline.format_prompt("Tell me about FAISS", docs)
    assert "FAISS is a library" in prompt
