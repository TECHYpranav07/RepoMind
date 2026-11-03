"""Context assembly and deduplication for RAG generation."""
from typing import List, Dict, Any, Tuple
from repomind.ingestion.chunker import CodeChunk


class ContextBuilder:
    """Combines vector chunks and graph relationship paths into a structured prompt context."""

    @staticmethod
    def build_context(
        vector_chunks: List[Tuple[CodeChunk, float]],
        graph_evidence: Dict[str, Any],
        max_total_chars: int = 12000
    ) -> Dict[str, Any]:
        citations: List[Dict[str, Any]] = []
        formatted_sections: List[str] = []
        seen_files = set()
        seen_chunks = set()
        total_chars = 0

        # 1. Format Knowledge Graph Path Evidence & Traverse Graph Nodes
        graph_paths = graph_evidence.get("paths", [])
        graph_nodes = graph_evidence.get("nodes", [])

        if graph_nodes:
            for g_node in graph_nodes:
                fpath = g_node.get("file_path")
                if fpath:
                    seen_files.add(fpath)
                    citations.append({
                        "id": len(citations) + 1,
                        "file_path": fpath,
                        "start_line": g_node.get("line_number") or 1,
                        "end_line": g_node.get("end_line") or 10,
                        "entity": g_node.get("name"),
                        "score": 0.95,
                        "snippet": (g_node.get("source_snippet") or g_node.get("docstring") or f"Entity {g_node.get('name')}")[:200]
                    })

        if graph_paths:
            path_header = "### Knowledge Graph Structural Relationships:"
            path_body = "\n".join(f"- {p}" for p in graph_paths[:12])
            graph_block = f"{path_header}\n{path_body}"
            formatted_sections.append(graph_block)
            total_chars += len(graph_block)

        # 2. Format Vector Source Chunks with Provenance Citations
        if vector_chunks:
            source_header = "### Retrieved Code & Documentation Sources:"
            formatted_sections.append(source_header)

            for idx, (chunk, score) in enumerate(vector_chunks, start=1):
                if chunk.chunk_id in seen_chunks:
                    continue
                seen_chunks.add(chunk.chunk_id)

                loc = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
                entry = (
                    f"--- [Source {idx}: {loc} (Relevance: {score:.2f})] ---\n"
                    f"Entity: {chunk.entity_name or 'General'}\n"
                    f"{chunk.content.strip()}"
                )

                if total_chars + len(entry) > max_total_chars:
                    break

                formatted_sections.append(entry)
                total_chars += len(entry)
                seen_files.add(chunk.file_path)

                citations.append({
                    "id": idx,
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "entity": chunk.entity_name,
                    "score": round(score, 3),
                    "snippet": chunk.content[:200]
                })

        assembled_text = "\n\n".join(formatted_sections)

        return {
            "prompt_context": assembled_text,
            "citations": citations,
            "graph_paths": graph_paths,
            "affected_files": sorted(list(seen_files)),
            "char_count": len(assembled_text),
            "estimated_tokens": len(assembled_text) // 4
        }
