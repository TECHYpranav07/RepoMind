"""Knowledge Graph Relationship Extractor using Python AST and Dependency Analysis."""
import ast
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from repomind.ingestion.mcp_connector import RepoFile, RepoMetadata
from repomind.graph.entity_extractor import GraphNode


class GraphEdge(BaseModel):
    """Represents a directed relationship between two entities in the knowledge graph."""
    source: str
    target: str
    relation: str  # CONTAINS, IMPORTS, CALLS, DEPENDS_ON, IMPLEMENTS, CONFIGURES, DOCUMENTS, TESTS, USES_API
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    extraction_method: str = "ast_deterministic"
    confidence: float = 1.0
    is_inferred: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RelationshipExtractor:
    """Extracts typed relationships between software entities."""

    @staticmethod
    def extract_relationships(
        metadata: RepoMetadata,
        files: List[RepoFile],
        nodes: Dict[str, GraphNode]
    ) -> List[GraphEdge]:
        edges: List[GraphEdge] = []
        repo_id = f"repo:{metadata.full_name}"

        # Fast lookup indices
        nodes_by_name: Dict[str, List[GraphNode]] = {}
        for node in nodes.values():
            nodes_by_name.setdefault(node.name.lower(), []).append(node)

        # 1. Repository CONTAINS Files and DEPENDS_ON Libraries
        for node in nodes.values():
            if node.type in ("File", "Test", "Configuration", "Documentation") and node.file_path:
                edges.append(GraphEdge(
                    source=repo_id,
                    target=node.id,
                    relation="CONTAINS",
                    file_path=node.file_path,
                    extraction_method="static_manifest",
                    confidence=1.0,
                    is_inferred=False
                ))
            elif node.type == "Library":
                edges.append(GraphEdge(
                    source=repo_id,
                    target=node.id,
                    relation="DEPENDS_ON",
                    file_path=node.metadata.get("source_file"),
                    extraction_method="dependency_manifest",
                    confidence=1.0,
                    is_inferred=False
                ))

        # 2. Extract internal Python AST relationships (CONTAINS, IMPORTS, CALLS, IMPLEMENTS, TESTS)
        for f in files:
            if f.extension != ".py":
                # For doc files, relate to files/classes they mention
                if f.file_type in ("markdown", "text"):
                    RelationshipExtractor._extract_doc_relationships(f, nodes, nodes_by_name, edges)
                continue

            file_id = f"file:{f.path}"
            try:
                tree = ast.parse(f.content)
            except SyntaxError:
                continue

            # File CONTAINS Classes & Functions
            for node in nodes.values():
                if node.file_path == f.path and node.id != file_id:
                    if node.type in ("Class", "Function", "Test"):
                        edges.append(GraphEdge(
                            source=file_id,
                            target=node.id,
                            relation="CONTAINS",
                            file_path=f.path,
                            line_number=node.line_number,
                            extraction_method="ast_deterministic",
                            confidence=1.0,
                            is_inferred=False
                        ))

            # AST Visitor for IMPORTS, CALLS, IMPLEMENTS
            visitor = ASTVisitor(f, nodes, nodes_by_name, edges)
            visitor.visit(tree)

        # Deduplicate edges
        seen_edges: Set[str] = set()
        unique_edges: List[GraphEdge] = []
        for e in edges:
            key = f"{e.source}|{e.relation}|{e.target}"
            if key not in seen_edges and e.source in nodes and e.target in nodes:
                seen_edges.add(key)
                unique_edges.append(e)

        return unique_edges

    @staticmethod
    def _extract_doc_relationships(
        doc_file: RepoFile,
        nodes: Dict[str, GraphNode],
        nodes_by_name: Dict[str, List[GraphNode]],
        edges: List[GraphEdge]
    ) -> None:
        """Link documentation to mentioned code entities and libraries."""
        doc_file_id = f"file:{doc_file.path}"
        content_lower = doc_file.content.lower()

        for name_lower, candidates in nodes_by_name.items():
            if len(name_lower) < 4:  # Avoid very short generic matches
                continue
            if name_lower in content_lower:
                for target_node in candidates:
                    if target_node.type in ("Class", "Function", "Library"):
                        edges.append(GraphEdge(
                            source=doc_file_id,
                            target=target_node.id,
                            relation="DOCUMENTS",
                            file_path=doc_file.path,
                            extraction_method="heuristic_reference",
                            confidence=0.85,
                            is_inferred=True
                        ))


class ASTVisitor(ast.NodeVisitor):
    """Walks Python AST to detect imports, function calls, class inheritances, and test linkages."""

    def __init__(
        self,
        file: RepoFile,
        nodes: Dict[str, GraphNode],
        nodes_by_name: Dict[str, List[GraphNode]],
        edges: List[GraphEdge]
    ):
        self.file = file
        self.file_id = f"file:{file.path}"
        self.nodes = nodes
        self.nodes_by_name = nodes_by_name
        self.edges = edges
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None
        self.imported_names: Dict[str, str] = {}  # local_alias -> full_or_module_name

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            mod_name = alias.name
            local_name = alias.asname or mod_name
            self.imported_names[local_name] = mod_name

            # Check if imported library exists in graph
            lib_id = f"lib:{mod_name.split('.')[0].lower()}"
            if lib_id in self.nodes:
                self.edges.append(GraphEdge(
                    source=self.file_id,
                    target=lib_id,
                    relation="IMPORTS",
                    file_path=self.file.path,
                    line_number=node.lineno,
                    extraction_method="ast_deterministic",
                    confidence=1.0,
                    is_inferred=False
                ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        for alias in node.names:
            imported_item = alias.name
            local_name = alias.asname or imported_item
            self.imported_names[local_name] = f"{mod}.{imported_item}"

            # Check library
            lib_key = mod.split(".")[0].lower()
            lib_id = f"lib:{lib_key}"
            if lib_id in self.nodes:
                self.edges.append(GraphEdge(
                    source=self.file_id,
                    target=lib_id,
                    relation="IMPORTS",
                    file_path=self.file.path,
                    line_number=node.lineno,
                    extraction_method="ast_deterministic",
                    confidence=1.0,
                    is_inferred=False
                ))

            # Check if target class/function in codebase is imported
            for candidate in self.nodes_by_name.get(imported_item.lower(), []):
                if candidate.file_path != self.file.path:
                    self.edges.append(GraphEdge(
                        source=self.file_id,
                        target=candidate.id,
                        relation="IMPORTS",
                        file_path=self.file.path,
                        line_number=node.lineno,
                        extraction_method="ast_deterministic",
                        confidence=1.0,
                        is_inferred=False
                    ))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        prev_class = self.current_class
        self.current_class = node.name
        class_id = f"class:{self.file.path}:{node.name}"

        # Class inheritance / implementation
        for base in node.bases:
            base_name = getattr(base, "id", None) or getattr(base, "attr", None)
            if base_name:
                for candidate in self.nodes_by_name.get(base_name.lower(), []):
                    self.edges.append(GraphEdge(
                        source=class_id,
                        target=candidate.id,
                        relation="IMPLEMENTS",
                        file_path=self.file.path,
                        line_number=node.lineno,
                        extraction_method="ast_deterministic",
                        confidence=1.0,
                        is_inferred=False
                    ))

        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function(node)

    def _handle_function(self, node) -> None:
        prev_func = self.current_function
        func_name = f"{self.current_class}.{node.name}" if self.current_class else node.name
        self.current_function = func_name
        caller_id = f"func:{self.file.path}:{func_name}"

        # If it's a test function, link to target functions/classes being tested
        if node.name.startswith("test_") or "test" in self.file.path.lower():
            target_guess = node.name.replace("test_", "")
            for candidate in self.nodes_by_name.get(target_guess.lower(), []):
                if candidate.id != caller_id:
                    self.edges.append(GraphEdge(
                        source=caller_id,
                        target=candidate.id,
                        relation="TESTS",
                        file_path=self.file.path,
                        line_number=node.lineno,
                        extraction_method="heuristic_reference",
                        confidence=0.9,
                        is_inferred=True
                    ))

        self.generic_visit(node)
        self.current_function = prev_func

    def visit_Call(self, node: ast.Call) -> None:
        caller_id = None
        if self.current_function:
            caller_id = f"func:{self.file.path}:{self.current_function}"
        elif self.current_class:
            caller_id = f"class:{self.file.path}:{self.current_class}"
        else:
            caller_id = self.file_id

        # Determine what is being called
        callee_name = None
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = node.func.attr

        if callee_name and caller_id:
            # Check if callee is in imported names or graph nodes
            candidates = self.nodes_by_name.get(callee_name.lower(), [])
            for target_node in candidates:
                if target_node.id != caller_id:
                    self.edges.append(GraphEdge(
                        source=caller_id,
                        target=target_node.id,
                        relation="CALLS",
                        file_path=self.file.path,
                        line_number=node.lineno,
                        extraction_method="ast_deterministic",
                        confidence=0.95,
                        is_inferred=False
                    ))

        self.generic_visit(node)
