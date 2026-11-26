"""Knowledge Graph Entity Extractor for Software Repositories."""
import ast
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from repomind.ingestion.mcp_connector import RepoFile, RepoMetadata
from repomind.ingestion.document_processor import DocumentProcessor


class GraphNode(BaseModel):
    """Represents a node in the RepoMind software knowledge graph."""
    id: str
    type: str  # Repository, Module, File, Class, Function, Library, API, Configuration, Documentation, Test
    name: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    end_line: Optional[int] = None
    docstring: Optional[str] = None
    source_snippet: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EntityExtractor:
    """Extracts typed software entities from files, AST, and repository metadata."""

    @staticmethod
    def extract_entities(metadata: RepoMetadata, files: List[RepoFile]) -> Dict[str, GraphNode]:
        """Extract all nodes from repo metadata, source files, and dependencies."""
        nodes: Dict[str, GraphNode] = {}

        # 1. Repository Root Node
        repo_node_id = f"repo:{metadata.full_name}"
        nodes[repo_node_id] = GraphNode(
            id=repo_node_id,
            type="Repository",
            name=metadata.name,
            docstring=metadata.description,
            metadata={
                "owner": metadata.owner,
                "stars": metadata.stars,
                "language": metadata.language,
                "default_branch": metadata.default_branch
            }
        )

        # 2. Extract Dependencies / Libraries
        dependencies = DocumentProcessor.parse_dependencies(files)
        for dep in dependencies:
            dep_id = f"lib:{dep['name'].lower()}"
            if dep_id not in nodes:
                nodes[dep_id] = GraphNode(
                    id=dep_id,
                    type="Library",
                    name=dep["name"],
                    metadata={"specifier": dep.get("specifier", "any"), "source_file": dep.get("source_file")}
                )

        # 3. Extract Files, Modules, Classes, Functions, Tests, Configs
        for f in files:
            file_id = f"file:{f.path}"
            is_test = DocumentProcessor.is_test_file(f.path)
            is_config = DocumentProcessor.is_config_file(f.path)

            file_type = "Test" if is_test else ("Configuration" if is_config else "File")
            nodes[file_id] = GraphNode(
                id=file_id,
                type=file_type,
                name=f.name,
                file_path=f.path,
                line_number=1,
                end_line=f.line_count,
                metadata={"extension": f.extension, "size_bytes": f.size_bytes}
            )

            if f.extension == ".py":
                EntityExtractor._extract_python_nodes(f, nodes, is_test)
            elif f.file_type in ("markdown", "text") or f.extension in (".md", ".rst"):
                EntityExtractor._extract_doc_nodes(f, nodes)

        return nodes

    @staticmethod
    def _extract_python_nodes(file: RepoFile, nodes: Dict[str, GraphNode], is_test: bool) -> None:
        """Extract classes, methods, and functions from a Python AST."""
        lines = file.content.splitlines()
        try:
            tree = ast.parse(file.content)
        except SyntaxError:
            return

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_id = f"class:{file.path}:{node.name}"
                doc = ast.get_docstring(node) or ""
                snippet = "\n".join(lines[node.lineno - 1 : min(getattr(node, "end_lineno", node.lineno + 15), len(lines))])
                node_type = "Test" if is_test or node.name.startswith("Test") else "Class"

                nodes[class_id] = GraphNode(
                    id=class_id,
                    type=node_type,
                    name=node.name,
                    file_path=file.path,
                    line_number=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    docstring=doc,
                    source_snippet=snippet,
                    metadata={"bases": [b.id for b in node.bases if isinstance(b, ast.Name)]}
                )

                # Extract member methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_id = f"func:{file.path}:{node.name}.{item.name}"
                        m_doc = ast.get_docstring(item) or ""
                        m_snippet = "\n".join(lines[item.lineno - 1 : min(getattr(item, "end_lineno", item.lineno + 10), len(lines))])
                        m_type = "Test" if is_test or item.name.startswith("test_") else "Function"

                        nodes[method_id] = GraphNode(
                            id=method_id,
                            type=m_type,
                            name=f"{node.name}.{item.name}",
                            file_path=file.path,
                            line_number=item.lineno,
                            end_line=getattr(item, "end_lineno", item.lineno),
                            docstring=m_doc,
                            source_snippet=m_snippet,
                            metadata={"parent_class": node.name, "is_async": isinstance(item, ast.AsyncFunctionDef)}
                        )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_id = f"func:{file.path}:{node.name}"
                f_doc = ast.get_docstring(node) or ""
                f_snippet = "\n".join(lines[node.lineno - 1 : min(getattr(node, "end_lineno", node.lineno + 10), len(lines))])
                f_type = "Test" if is_test or node.name.startswith("test_") else "Function"

                nodes[func_id] = GraphNode(
                    id=func_id,
                    type=f_type,
                    name=node.name,
                    file_path=file.path,
                    line_number=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    docstring=f_doc,
                    source_snippet=f_snippet,
                    metadata={"is_async": isinstance(node, ast.AsyncFunctionDef)}
                )

    @staticmethod
    def _extract_doc_nodes(file: RepoFile, nodes: Dict[str, GraphNode]) -> None:
        """Extract documentation section nodes."""
        lines = file.content.splitlines()
        for idx, line in enumerate(lines, start=1):
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
                sec_id = f"doc:{file.path}#{heading.lower().replace(' ', '_')}"
                nodes[sec_id] = GraphNode(
                    id=sec_id,
                    type="Documentation",
                    name=heading,
                    file_path=file.path,
                    line_number=idx,
                    metadata={"heading_level": len(line) - len(line.lstrip("#"))}
                )
