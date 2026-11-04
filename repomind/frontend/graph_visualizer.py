"""Interactive Knowledge Graph visualizer using PyVis and Plotly."""
import os
import tempfile
from typing import Dict, Any, List, Optional, Set
import networkx as nx

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False


# Node color palette by software entity type
NODE_COLORS = {
    "Repository": "#6366f1",    # Indigo
    "Module": "#8b5cf6",        # Purple
    "File": "#3b82f6",          # Blue
    "Class": "#06b6d4",         # Cyan
    "Function": "#10b981",      # Emerald
    "Library": "#f59e0b",       # Amber
    "API": "#ec4899",           # Pink
    "Configuration": "#f97316", # Orange
    "Documentation": "#64748b", # Slate
    "Test": "#ef4444",          # Rose / Red
    "Target": "#dc2626",        # Crimson for What-If target
    "DirectImpact": "#ea580c",  # Dark Orange
    "InferredImpact": "#ca8a04",# Yellow-Gold
    "Unknown": "#94a3b8"
}

EDGE_COLORS = {
    "CONTAINS": "#64748b",
    "IMPORTS": "#3b82f6",
    "CALLS": "#10b981",
    "DEPENDS_ON": "#f59e0b",
    "IMPLEMENTS": "#8b5cf6",
    "CONFIGURES": "#f97316",
    "DOCUMENTS": "#94a3b8",
    "TESTS": "#ef4444",
    "USES_API": "#ec4899"
}


class GraphVisualizer:
    """Renders interactive NetworkX subgraphs to PyVis HTML or Plotly figures."""

    @staticmethod
    def render_pyvis_html(
        graph: nx.DiGraph,
        height: str = "550px",
        target_ids: Optional[Set[str]] = None,
        direct_ids: Optional[Set[str]] = None,
        inferred_ids: Optional[Set[str]] = None,
        selected_node_types: Optional[List[str]] = None
    ) -> str:
        """Generate interactive self-contained PyVis HTML string."""
        if not PYVIS_AVAILABLE or graph.number_of_nodes() == 0:
            return "<div>No graph nodes available to display.</div>"

        target_ids = target_ids or set()
        direct_ids = direct_ids or set()
        inferred_ids = inferred_ids or set()

        net = Network(height=height, width="100%", directed=True, bgcolor="#0f172a", font_color="#e2e8f0")
        net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=95, spring_strength=0.05, damping=0.9)

        # Filter nodes if filter requested
        nodes_to_render = []
        for nid, data in graph.nodes(data=True):
            ntype = data.get("type", "Unknown")
            if selected_node_types and ntype not in selected_node_types and nid not in target_ids and nid not in direct_ids:
                continue
            nodes_to_render.append(nid)

        sub = graph.subgraph(nodes_to_render)

        for nid, data in sub.nodes(data=True):
            ntype = data.get("type", "Unknown")
            label = data.get("name", nid)
            fpath = data.get("file_path", "")
            line = data.get("line_number", "")
            doc = (data.get("docstring") or "").strip()[:100]

            # Determine color and size
            if nid in target_ids:
                color = NODE_COLORS["Target"]
                size = 28
                title = f"🎯 TARGET MODIFICATION\nID: {nid}\nName: {label}\nFile: {fpath}:{line}\n{doc}"
            elif nid in direct_ids:
                color = NODE_COLORS["DirectImpact"]
                size = 22
                title = f"⚠️ DIRECT IMPACT\nID: {nid}\nName: {label}\nFile: {fpath}:{line}\n{doc}"
            elif nid in inferred_ids:
                color = NODE_COLORS["InferredImpact"]
                size = 18
                title = f"⚡ INFERRED IMPACT\nID: {nid}\nName: {label}\nFile: {fpath}:{line}\n{doc}"
            else:
                color = NODE_COLORS.get(ntype, NODE_COLORS["Unknown"])
                size = 14 if ntype in ("Function", "Documentation") else 20
                title = f"Entity: {label}\nType: {ntype}\nLocation: {fpath}:{line}\n{doc}"

            net.add_node(
                nid,
                label=label,
                title=title,
                color=color,
                size=size,
                borderWidth=2,
                font={"size": 12, "color": "#f8fafc", "face": "system-ui"}
            )

        for u, v, data in sub.edges(data=True):
            rel = data.get("relation", "CONNECTS")
            color = EDGE_COLORS.get(rel, "#475569")
            net.add_edge(
                u, v,
                title=f"Relation: {rel}",
                label=rel if len(sub.edges) < 40 else "",
                color=color,
                arrows="to",
                width=1.5
            )

        # Generate HTML
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as tf:
            temp_path = tf.name
            net.write_html(temp_path)

        with open(temp_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        try:
            os.remove(temp_path)
        except Exception:
            pass

        return html_content
