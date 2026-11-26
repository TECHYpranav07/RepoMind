"""Configuration settings for RagCraft microservice."""
import os
from pydantic import BaseModel, Field


class VectorStoreConfig(BaseModel):
    """Configuration parameters for vector indexing and FAISS storage."""
    dimension: int = Field(default=384, description="Embedding vector dimension")
    index_type: str = Field(default="IndexFlatIP", description="FAISS index metric type")
    index_path: str = Field(default="data/vector_store.faiss", description="Local index serialization file")
    similarity_threshold: float = Field(default=0.72, description="Minimum cosine similarity cutoff")


class CacheConfig(BaseModel):
    """Redis cache configuration settings."""
    redis_host: str = Field(default="localhost", description="Redis host address")
    redis_port: int = Field(default=6379, description="Redis port number")
    ttl_seconds: int = Field(default=3600, description="Cache entry time-to-live in seconds")
    enabled: bool = Field(default=True, description="Flag to enable Redis caching")


class PipelineConfig(BaseModel):
    """Pipeline orchestration settings."""
    max_retrieved_docs: int = Field(default=5, description="Top K documents retrieved per query")
    llm_model: str = Field(default="gemini-1.5-pro", description="LLM model identifier")
    temperature: float = Field(default=0.2, description="Generation temperature")


class AppConfig(BaseModel):
    """Global microservice configuration aggregate."""
    app_name: str = "RagCraft Service"
    vector: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)


def load_config() -> AppConfig:
    """Load and validate system configuration from environment variables."""
    return AppConfig()
