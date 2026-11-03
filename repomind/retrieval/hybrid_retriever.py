"""Hybrid GraphRAG retrieval coordinator combining vector and graph evidence."""
import time
from typing import Dict, Any, List, Optional, Tuple
import networkx as nx

from repomind.config import DEFAULT_TOP_K, DEFAULT_GRAPH_DEPTH
from repomind.retrieval.embeddings import BaseEmbeddingEngine
from repomind.retrieval.vector_store import FAISSVectorStore
from repomind.graph.graph_retriever import GraphRetriever
from repomind.retrieval.context_builder import ContextBuilder
from repomind.ingestion.chunker import CodeChunk


class HybridRetriever:
    """Retrieves relevant evidence from vector index, knowledge graph, or both."""

    def __init__(
        self,
        vector_store: FAISSVectorStore,
        embedding_engine: BaseEmbeddingEngine,
        graph: nx.DiGraph
    ):
        self.vector_store = vector_store
        self.embedding_engine = embedding_engine
        self.graph = graph
        self.graph_retriever = GraphRetriever(graph)

    def retrieve(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = DEFAULT_TOP_K,
        graph_depth: int = DEFAULT_GRAPH_DEPTH
    ) -> Dict[str, Any]:
        """
        Execute retrieval based on selected mode: 'vector', 'graph', or 'hybrid'.
        """
        start_time = time.time()
        mode_lower = mode.lower()

        vector_results: List[Tuple[CodeChunk, float]] = []
        graph_evidence: Dict[str, Any] = {"subgraph": nx.DiGraph(), "paths": [], "nodes": [], "text_context": ""}
        matched_entity_ids: List[str] = []

        # 1. Mode A: Vector RAG
        if mode_lower in ("vector", "hybrid"):
            q_vec = self.embedding_engine.embed_query(query)
            vector_results = self.vector_store.search(q_vec, top_k=top_k)

        # 2. Mode B: Graph RAG
        if mode_lower in ("graph", "hybrid"):
            # Resolve entities from query
            resolved = self.graph_retriever.resolve_entities(query, limit=5)
            matched_entity_ids = [nid for nid, _ in resolved]

            # In hybrid mode, also add entities discovered in top vector chunks
            if mode_lower == "hybrid" and vector_results:
                for chunk, _ in vector_results:
                    if chunk.entity_name:
                        for nid, data in self.graph.nodes(data=True):
                            if data.get("name", "").lower() == chunk.entity_name.lower():
                                if nid not in matched_entity_ids:
                                    matched_entity_ids.append(nid)

            graph_evidence = self.graph_retriever.get_connected_evidence(
                matched_entity_ids,
                depth=graph_depth,
                max_nodes=12
            )

        # In Graph-only mode, if vector results are empty, create synthetic chunks from node snippets
        if mode_lower == "graph" and not vector_results:
            synth_chunks = []
            for nd in graph_evidence.get("nodes", []):
                snippet = nd.get("source_snippet") or nd.get("docstring")
                if snippet:
                    synth_chunks.append((
                        CodeChunk(
                            chunk_id=f"graph_{nd.get('id')}",
                            file_path=nd.get("file_path") or "graph",
                            content=f"Entity: {nd.get('name')}\nType: {nd.get('type')}\n{snippet}",
                            start_line=nd.get("line_number") or 1,
                            end_line=nd.get("end_line") or 10,
                            chunk_type="graph_node",
                            entity_name=nd.get("name")
                        ),
                        1.0
                    ))
            vector_results = synth_chunks[:top_k]

        # 3. Assemble unified context
        assembled = ContextBuilder.build_context(vector_results, graph_evidence)
        elapsed_sec = time.time() - start_time

        return {
            "mode": mode_lower,
            "query": query,
            "vector_chunks": vector_results,
            "graph_evidence": graph_evidence,
            "matched_entities": matched_entity_ids,
            "prompt_context": assembled["prompt_context"],
            "citations": assembled["citations"],
            "graph_paths": assembled["graph_paths"],
            "affected_files": assembled["affected_files"],
            "retrieval_latency": round(elapsed_sec, 4),
            "estimated_tokens": assembled["estimated_tokens"]
        }
