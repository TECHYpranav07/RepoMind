"""NetworkX Graph construction, serialization, metrics, and subgraph utilities."""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
import networkx as nx

from repomind.config import GRAPHS_DIR
from repomind.graph.entity_extractor import GraphNode
from repomind.graph.relationship_extractor import GraphEdge


class RepoGraphBuilder:
    """Builds and serializes NetworkX DiGraph for software repository knowledge representation."""

    def __init__(self):
        self.graph = nx.DiGraph()

    def build(self, nodes: Dict[str, GraphNode], edges: List[GraphEdge]) -> nx.DiGraph:
        """Populate NetworkX graph with typed nodes and edges."""
        self.graph.clear()

        # Add Nodes
        for node_id, node in nodes.items():
            self.graph.add_node(
                node_id,
                id=node.id,
                type=node.type,
                name=node.name,
                file_path=node.file_path,
                line_number=node.line_number,
                end_line=node.end_line,
                docstring=node.docstring,
                source_snippet=node.source_snippet,
                metadata=node.metadata
            )

        # Add Edges
        for edge in edges:
            if edge.source in self.graph and edge.target in self.graph:
                self.graph.add_edge(
                    edge.source,
                    edge.target,
                    relation=edge.relation,
                    file_path=edge.file_path,
                    line_number=edge.line_number,
                    extraction_method=edge.extraction_method,
                    confidence=edge.confidence,
                    is_inferred=edge.is_inferred,
                    metadata=edge.metadata
                )

        return self.graph

    def get_statistics(self) -> Dict[str, Any]:
        """Compute structural metrics and breakdown counts."""
        node_type_counts: Dict[str, int] = {}
        for _, data in self.graph.nodes(data=True):
            ntype = data.get("type", "Unknown")
            node_type_counts[ntype] = node_type_counts.get(ntype, 0) + 1

        edge_relation_counts: Dict[str, int] = {}
        for _, _, data in self.graph.edges(data=True):
            rel = data.get("relation", "Unknown")
            edge_relation_counts[rel] = edge_relation_counts.get(rel, 0) + 1

        # Centrality hubs
        in_degrees = sorted(self.graph.in_degree(), key=lambda x: x[1], reverse=True)[:5]
        out_degrees = sorted(self.graph.out_degree(), key=lambda x: x[1], reverse=True)[:5]

        top_hubs = [
            {
                "id": nid,
                "name": self.graph.nodes[nid].get("name", nid),
                "type": self.graph.nodes[nid].get("type", "Unknown"),
                "in_degree": in_d,
                "out_degree": self.graph.out_degree(nid)
            }
            for nid, in_d in in_degrees if nid in self.graph
        ]

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_type_breakdown": node_type_counts,
            "edge_relation_breakdown": edge_relation_counts,
            "density": round(nx.density(self.graph), 4) if self.graph.number_of_nodes() > 0 else 0.0,
            "top_hubs": top_hubs
        }

    def save(self, filepath: Path) -> None:
        """Persist graph structure to JSON."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self.graph)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, filepath: Path) -> nx.DiGraph:
        """Load graph structure from JSON file."""
        if not filepath.exists():
            raise FileNotFoundError(f"Graph file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.graph = nx.node_link_graph(data, directed=True)
        return self.graph

    def get_subgraph(
        self,
        node_ids: List[str],
        depth: int = 1,
        include_upstream: bool = True,
        include_downstream: bool = True
    ) -> nx.DiGraph:
        """Extract neighborhood subgraph surrounding specified node(s)."""
        selected_nodes: Set[str] = set()

        for start_node in node_ids:
            if start_node not in self.graph:
                continue
            selected_nodes.add(start_node)

            if include_downstream:
                downstream = nx.single_source_shortest_path_length(self.graph, start_node, cutoff=depth)
                selected_nodes.update(downstream.keys())

            if include_upstream:
                reversed_graph = self.graph.reverse()
                upstream = nx.single_source_shortest_path_length(reversed_graph, start_node, cutoff=depth)
                selected_nodes.update(upstream.keys())

        return self.graph.subgraph(selected_nodes).copy()
