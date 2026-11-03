"""Impact Analysis Engine tracing upstream/downstream graph dependencies."""
from typing import Dict, Any, List, Set, Tuple, Optional
import networkx as nx

from repomind.analysis.change_parser import ParsedChange


class ImpactReportData:
    """Container for computed structural impact analysis results."""
    def __init__(self):
        self.target_nodes: List[Dict[str, Any]] = []
        self.direct_affected: List[Dict[str, Any]] = []
        self.inferred_affected: List[Dict[str, Any]] = []
        self.tests_to_update: List[Dict[str, Any]] = []
        self.configs_to_update: List[Dict[str, Any]] = []
        self.impact_paths: List[Dict[str, Any]] = []
        self.impact_subgraph: nx.DiGraph = nx.DiGraph()
        self.risk_level: str = "Low"


class ImpactAnalyzer:
    """Traces upstream and downstream dependency chains to evaluate hypothetical changes."""

    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    def analyze(self, change: ParsedChange, max_depth: int = 3) -> ImpactReportData:
        report = ImpactReportData()
        if not self.graph or not change.target_node_ids:
            return report

        reversed_graph = self.graph.reverse()
        seen_nodes: Set[str] = set(change.target_node_ids)

        for nid in change.target_node_ids:
            if nid in self.graph:
                report.target_nodes.append(self._format_node(nid))

        # 1. Direct Upstream (1-hop callers, importers, testers)
        direct_ids: Set[str] = set()
        for target_id in change.target_node_ids:
            if target_id not in reversed_graph:
                continue
            for upstream_neighbor in reversed_graph.neighbors(target_id):
                if upstream_neighbor not in change.target_node_ids:
                    direct_ids.add(upstream_neighbor)
                    edge_data = self.graph.get_edge_data(upstream_neighbor, target_id, default={})
                    rel = edge_data.get("relation", "DEPENDS_ON")
                    report.impact_paths.append({
                        "from": upstream_neighbor,
                        "to": target_id,
                        "relation": rel,
                        "path_text": f"{self._node_name(upstream_neighbor)} --[{rel}]--> {self._node_name(target_id)}",
                        "depth": 1,
                        "is_direct": True
                    })

        for nid in direct_ids:
            seen_nodes.add(nid)
            node_data = self._format_node(nid)
            node_type = node_data.get("type", "")

            if node_type == "Test":
                report.tests_to_update.append(node_data)
            elif node_type == "Configuration":
                report.configs_to_update.append(node_data)
            else:
                report.direct_affected.append(node_data)

        # 2. Inferred / Transitive Upstream (2-hop to max_depth)
        current_layer = set(direct_ids)
        for depth in range(2, max_depth + 1):
            next_layer: Set[str] = set()
            for current_nid in current_layer:
                if current_nid not in reversed_graph:
                    continue
                for parent_nid in reversed_graph.neighbors(current_nid):
                    if parent_nid not in seen_nodes:
                        seen_nodes.add(parent_nid)
                        next_layer.add(parent_nid)

                        edge_data = self.graph.get_edge_data(parent_nid, current_nid, default={})
                        rel = edge_data.get("relation", "DEPENDS_ON")
                        report.impact_paths.append({
                            "from": parent_nid,
                            "to": current_nid,
                            "relation": rel,
                            "path_text": f"{self._node_name(parent_nid)} --[{rel}]--> {self._node_name(current_nid)}",
                            "depth": depth,
                            "is_direct": False
                        })

                        p_data = self._format_node(parent_nid)
                        if p_data.get("type") == "Test":
                            report.tests_to_update.append(p_data)
                        elif p_data.get("type") == "Configuration":
                            report.configs_to_update.append(p_data)
                        else:
                            report.inferred_affected.append(p_data)

            current_layer = next_layer
            if not current_layer:
                break

        # 3. Create Impact Subgraph
        report.impact_subgraph = self.graph.subgraph(seen_nodes).copy()

        # 4. Assess Overall Risk Level
        total_affected = len(report.direct_affected) + len(report.inferred_affected)
        if total_affected > 6 or len(report.direct_affected) >= 3:
            report.risk_level = "High"
        elif total_affected >= 2:
            report.risk_level = "Medium"
        else:
            report.risk_level = "Low"

        return report

    def _node_name(self, nid: str) -> str:
        if nid in self.graph:
            return self.graph.nodes[nid].get("name", nid)
        return nid

    def _format_node(self, nid: str) -> Dict[str, Any]:
        nd = self.graph.nodes.get(nid, {})
        return {
            "id": nid,
            "name": nd.get("name", nid),
            "type": nd.get("type", "Unknown"),
            "file_path": nd.get("file_path", "N/A"),
            "line_number": nd.get("line_number"),
            "docstring": (nd.get("docstring") or "").strip()[:150]
        }
