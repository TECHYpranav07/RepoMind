"""FastAPI web server exposing HTTP endpoints for RagCraft."""
from typing import Dict, Any, List
from pydantic import BaseModel
from ragcraft.pipeline.rag_pipeline import RAGPipeline
from ragcraft.config import load_config

config = load_config()
pipeline = RAGPipeline()


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


class IndexRequest(BaseModel):
    documents: List[Dict[str, Any]]


def create_app():
    """Create and configure FastAPI application."""
    # Simulated FastAPI application
    app_routes = {
        "/query": "Handles user queries via RAGPipeline",
        "/index": "Ingests new documents into vector store",
        "/health": "Service health check endpoint"
    }
    return app_routes


def handle_query(request: QueryRequest) -> Dict[str, Any]:
    """Process query endpoint execution."""
    return pipeline.run(request.query)


def handle_index(request: IndexRequest) -> Dict[str, Any]:
    """Process document ingestion endpoint."""
    count = pipeline.retriever.add_documents(request.documents)
    return {"status": "success", "indexed_count": count}


def health_check() -> Dict[str, str]:
    """Health status check."""
    return {"status": "healthy", "service": config.app_name}
