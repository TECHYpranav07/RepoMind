"""Graph traversal and entity retrieval engine."""
import re
from typing import List, Dict, Any, Optional, Set, Tuple
import networkx as nx


class GraphRetriever:
    """Traverses knowledge graph to link query terms, extract subgraphs, and build relationship trails."""

    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    def resolve_entities(self, query: str, limit: int = 5) -> List[Tuple[str, float]]:
        """
        Map words in query to knowledge graph node IDs using exact, token, and fuzzy matches.
        Returns list of (node_id, match_score).
        """
        if not self.graph:
            return []

        query_tokens = set(re.findall(r"\b[A-Za-z0-9_]{3,}\b", query.lower()))
        scores: List[Tuple[str, float]] = []

        for node_id, data in self.graph.nodes(data=True):
            node_name = (data.get("name") or "").lower()
            node_type = (data.get("type") or "").lower()
            file_path = (data.get("file_path") or "").lower()

            score = 0.0

            # Exact name match in query
            if node_name and re.search(rf"\b{re.escape(node_name)}\b", query.lower()):
                score += 3.0

            # Substring match
            if node_name in query.lower() and len(node_name) >= 3:
                score += 1.5

            # Token overlap
            node_tokens = set(re.findall(r"\b[A-Za-z0-9_]{3,}\b", node_name))
            overlap = query_tokens.intersection(node_tokens)
            if overlap:
                score += len(overlap) * 1.0

            # File path match
            for token in query_tokens:
                if token in file_path:
                    score += 0.5

            if score > 0:
                scores.append((node_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:limit]

    def get_connected_evidence(
        self,
        node_ids: List[str],
        depth: int = 2,
        max_nodes: int = 15
    ) -> Dict[str, Any]:
        """
        Extract subgraph paths and formatted context from matched nodes.
        """
        if not node_ids or not self.graph:
            return {"subgraph": nx.DiGraph(), "paths": [], "nodes": [], "text_context": ""}

        subgraph_nodes: Set[str] = set(node_ids)
        reversed_graph = self.graph.reverse()

        for nid in node_ids:
            if nid not in self.graph:
                continue
            # Downstream
            down = nx.single_source_shortest_path_length(self.graph, nid, cutoff=depth)
            subgraph_nodes.update(list(down.keys())[:max_nodes])

            # Upstream (who depends on or calls this node)
            up = nx.single_source_shortest_path_length(reversed_graph, nid, cutoff=depth)
            subgraph_nodes.update(list(up.keys())[:max_nodes])

        subgraph = self.graph.subgraph(list(subgraph_nodes)[:max_nodes]).copy()

        # Build paths
        paths: List[str] = []
        for u, v, data in subgraph.edges(data=True):
            u_name = self.graph.nodes[u].get("name", u)
            v_name = self.graph.nodes[v].get("name", v)
            rel = data.get("relation", "CONNECTS")
            fpath = data.get("file_path", "")
            line = data.get("line_number")
            loc = f" ({fpath}:{line})" if fpath and line else (f" ({fpath})" if fpath else "")
            paths.append(f"{u_name} --[{rel}]--> {v_name}{loc}")

        # Assemble textual node context
        text_lines: List[str] = []
        for nid in subgraph.nodes():
            nd = self.graph.nodes[nid]
            ntype = nd.get("type", "Node")
            name = nd.get("name", nid)
            fpath = nd.get("file_path", "global")
            line = nd.get("line_number", "")
            loc = f" [{fpath}:{line}]" if line else f" [{fpath}]"
            doc = nd.get("docstring") or ""
            snip = nd.get("source_snippet") or ""

            entry = f"• Entity: {name} (Type: {ntype}){loc}"
            if doc:
                entry += f"\n  Description: {doc.strip()}"
            if snip:
                entry += f"\n  Snippet:\n{snip.strip()}"
            text_lines.append(entry)

        return {
            "subgraph": subgraph,
            "paths": paths,
            "nodes": [self.graph.nodes[n] for n in subgraph.nodes()],
            "text_context": "\n\n".join(text_lines)
        }
