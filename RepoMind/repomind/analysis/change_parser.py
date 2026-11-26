"""Hypothetical software change parser and entity grounder."""
import re
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
import networkx as nx


class ParsedChange(BaseModel):
    """Structured representation of a user's hypothetical change."""
    raw_query: str
    action: str  # replace, remove, modify, add, upgrade, compare
    target_entity: str
    replacement_entity: Optional[str] = None
    target_node_ids: List[str] = Field(default_factory=list)
    confidence: float = 0.9


class ChangeParser:
    """Parses natural-language What-If scenarios and grounds them to knowledge graph entities."""

    PATTERNS = [
        # Replace X with Y
        (r"(?:what if we|what happens if we|can we|should we)?\s*replace\s+([A-Za-z0-9_\-\.]+)\s+(?:with|by)\s+([A-Za-z0-9_\-\.]+)", "replace"),
        (r"(?:switch|swap|migrate)\s+(?:from\s+)?([A-Za-z0-9_\-\.]+)\s+to\s+([A-Za-z0-9_\-\.]+)", "replace"),
        # Upgrade X [to Y]
        (r"(?:what if we|what happens if we|can we)?\s*upgrade\s+([A-Za-z0-9_\-\.]+)\s+(?:to\s+([A-Za-z0-9_\-\.]+))?", "upgrade"),
        # Remove X
        (r"(?:what if we|what happens if we|can we)?\s*(?:remove|delete|drop|deprecate|eliminate)\s+([^?!\.;]+)", "remove"),
        # Add / Introduce X
        (r"(?:what if we|what happens if we|can we)?\s*(?:add|introduce|integrate|implement)\s+([^?!\.;]+)", "add"),
        # Modify / Change X
        (r"(?:what if we|what happens if we|what components.*?(?:affect|impact).*?if\s+(?:we|i)\s+)?(?:modify|change|refactor|update|rewrite)\s+([^?!\.;]+)", "modify"),
    ]

    @staticmethod
    def parse(query: str, graph: Optional[nx.DiGraph] = None) -> ParsedChange:
        cleaned = query.strip()
        action = "modify"
        target = ""
        replacement = None

        for pattern, act in ChangeParser.PATTERNS:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                action = act
                raw_target = match.group(1).strip()
                # Clean trailing punctuation from target
                target = re.sub(r"[^\w\s\-\.]+$", "", raw_target).strip()
                if match.lastindex and match.lastindex >= 2 and match.group(2):
                    raw_replacement = match.group(2).strip()
                    replacement = re.sub(r"[^\w\s\-\.]+$", "", raw_replacement).strip()
                break

        if not target:
            # Fallback extraction: pull prominent identifiers
            words = re.findall(r"\b[A-Za-z0-9_]{3,}\b", cleaned)
            target = words[0] if words else cleaned

        # Ground target against Knowledge Graph nodes
        target_node_ids = []
        if graph is not None and graph.number_of_nodes() > 0:
            target_node_ids = ChangeParser._ground_entity_to_nodes(target, graph)

        return ParsedChange(
            raw_query=cleaned,
            action=action,
            target_entity=target,
            replacement_entity=replacement,
            target_node_ids=target_node_ids
        )

    @staticmethod
    def _ground_entity_to_nodes(target: str, graph: nx.DiGraph) -> List[str]:
        """Ground a target name to graph nodes using exact, token, and semantic matching."""
        target_clean = re.sub(r"[^\w\s\-\.]", "", target).strip().lower()
        if not target_clean:
            return []

        tokens = [
            t for t in re.findall(r"\b[a-zA-Z0-9_\-\.]{3,}\b", target_clean)
            if t not in {"what", "with", "from", "into", "under", "over", "replace", "remove", "modify"}
        ]

        # Score candidate nodes
        scored_nodes: List[Tuple[str, float]] = []

        for nid, data in graph.nodes(data=True):
            name = (data.get("name") or "").lower()
            ntype = data.get("type", "")
            nid_lower = nid.lower()

            score = 0.0

            # 1. Exact match on name or ID
            if target_clean == name:
                score += 10.0
            elif target_clean in name or name == target_clean:
                score += 8.0
            elif target_clean in nid_lower:
                score += 6.0

            # 2. Token overlap and stems
            for t in tokens:
                if t == name:
                    score += 6.0
                elif t in name:
                    score += 4.0
                elif t in nid_lower:
                    score += 2.5
                # Stemming (e.g. caching -> cache)
                elif len(t) > 4 and t.endswith("ing") and t[:-3] in name:
                    score += 4.0
                elif len(name) > 4 and name.endswith("ing") and name[:-3] in t:
                    score += 4.0

            # 3. Boost meaningful software constructs (Classes, Libraries, Functions) over generic Files
            if score > 0:
                if ntype in ("Class", "Library"):
                    score += 1.5
                elif ntype == "Function":
                    score += 0.5
                scored_nodes.append((nid, score))

        scored_nodes.sort(key=lambda x: x[1], reverse=True)

        if not scored_nodes:
            return []

        # Take the top tier of matching nodes (highest score and those within 70% of top score)
        top_score = scored_nodes[0][1]
        threshold = max(3.0, top_score * 0.6)
        matched_ids = [nid for nid, sc in scored_nodes if sc >= threshold]

        return matched_ids[:6]
