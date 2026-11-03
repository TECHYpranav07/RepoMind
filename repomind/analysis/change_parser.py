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
        (r"(?:what if we|what happens if we|can we)?\s*replace\s+([A-Za-z0-9_\-\.]+)\s+(?:with|by)\s+([A-Za-z0-9_\-\.]+)", "replace"),
        (r"(?:switch|swap|migrate)\s+(?:from\s+)?([A-Za-z0-9_\-\.]+)\s+to\s+([A-Za-z0-9_\-\.]+)", "replace"),
        # Remove X
        (r"(?:what if we|what happens if we)?\s*(?:remove|delete|drop|deprecate)\s+([A-Za-z0-9_\-\.\s]+)", "remove"),
        # Add / Introduce X
        (r"(?:what if we|what happens if we)?\s*(?:add|introduce|integrate|implement)\s+([A-Za-z0-9_\-\.\s]+)", "add"),
        # Modify X
        (r"(?:what if we|what happens if we)?\s*(?:modify|change|refactor|update|rewrite)\s+([A-Za-z0-9_\-\.\s]+)", "modify"),
        # Upgrade X
        (r"(?:what if we|what happens if we)?\s*upgrade\s+([A-Za-z0-9_\-\.]+)\s+(?:to\s+([A-Za-z0-9_\-\.]+))?", "upgrade"),
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
                target = match.group(1).strip()
                if match.lastindex and match.lastindex >= 2 and match.group(2):
                    replacement = match.group(2).strip()
                break

        if not target:
            # Fallback extraction: pull prominent identifiers
            words = re.findall(r"\b[A-Za-z0-9_]{3,}\b", cleaned)
            target = words[0] if words else cleaned

        # Ground target against Knowledge Graph nodes
        target_node_ids = []
        if graph is not None:
            target_lower = target.lower()
            for nid, data in graph.nodes(data=True):
                name = (data.get("name") or "").lower()
                nid_lower = nid.lower()
                if target_lower == name or target_lower in nid_lower or name in target_lower:
                    target_node_ids.append(nid)

        return ParsedChange(
            raw_query=cleaned,
            action=action,
            target_entity=target,
            replacement_entity=replacement,
            target_node_ids=target_node_ids
        )
