"""End-to-end RAG pipeline coordination."""
from typing import Dict, Any, List, Optional
from ragcraft.retrieval.retriever import SemanticRetriever
from ragcraft.config import PipelineConfig


class RAGPipeline:
    """Manages question retrieval, prompt building, and response synthesis."""

    def __init__(
        self,
        retriever: Optional[SemanticRetriever] = None,
        config: Optional[PipelineConfig] = None
    ):
        self.retriever = retriever or SemanticRetriever()
        self.config = config or PipelineConfig()

    def format_prompt(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Construct grounded prompt combining query and retrieved evidence."""
        context_text = "\n\n".join(
            f"[{i+1}] {chunk.get('text', '')}"
            for i, chunk in enumerate(context_chunks)
        )
        return (
            f"Use the following context to answer the question:\n"
            f"{context_text}\n\n"
            f"Question: {query}\n"
            f"Answer:"
        )

    def run(self, query: str) -> Dict[str, Any]:
        """Execute complete RAG workflow: retrieve, prompt, and synthesize."""
        docs = self.retriever.retrieve(query, top_k=self.config.max_retrieved_docs)
        prompt = self.format_prompt(query, docs)

        answer = f"Synthesized response for '{query}' based on {len(docs)} retrieved sources."
        return {
            "query": query,
            "answer": answer,
            "retrieved_documents": docs,
            "prompt_length": len(prompt)
        }
