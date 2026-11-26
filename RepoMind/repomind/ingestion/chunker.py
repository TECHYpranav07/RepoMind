"""Structure-aware and semantic chunking for Python and documentation."""
import ast
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from repomind.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
from repomind.ingestion.mcp_connector import RepoFile


class CodeChunk(BaseModel):
    """A semantic or structural chunk of code/documentation with provenance metadata."""
    chunk_id: str
    file_path: str
    content: str
    start_line: int
    end_line: int
    chunk_type: str  # class, function, module_doc, doc_section, config, block
    entity_name: Optional[str] = None
    parent_scope: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StructureAwareChunker:
    """Splits repository files into semantic units using AST and structural cues."""

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_repository(self, files: List[RepoFile]) -> List[CodeChunk]:
        """Process all files in the repository into structured chunks."""
        all_chunks: List[CodeChunk] = []
        for file in files:
            if file.extension == ".py":
                all_chunks.extend(self._chunk_python_file(file))
            elif file.file_type in ("markdown", "text") or file.extension in (".md", ".rst", ".txt"):
                all_chunks.extend(self._chunk_markdown_file(file))
            else:
                all_chunks.extend(self._chunk_text_file(file))
        return all_chunks

    def _chunk_python_file(self, file: RepoFile) -> List[CodeChunk]:
        """Parse Python source into class, method, function, and module chunks."""
        chunks: List[CodeChunk] = []
        lines = file.content.splitlines()

        try:
            tree = ast.parse(file.content)
        except SyntaxError:
            # Fallback to sliding window if AST fails
            return self._chunk_text_file(file)

        # 1. Module docstring chunk if present
        mod_doc = ast.get_docstring(tree)
        if mod_doc:
            chunks.append(CodeChunk(
                chunk_id=f"{file.path}#module_doc",
                file_path=file.path,
                content=f"File: {file.path}\nModule Overview:\n{mod_doc}",
                start_line=1,
                end_line=len(mod_doc.splitlines()) + 2,
                chunk_type="module_doc",
                entity_name=file.name,
                metadata={"type": "module_doc"}
            ))

        # 2. Iterate top-level classes and functions
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                c_start = node.lineno
                c_end = getattr(node, "end_lineno", len(lines))
                class_content = "\n".join(lines[c_start - 1 : c_end])

                class_doc = ast.get_docstring(node) or ""
                chunks.append(CodeChunk(
                    chunk_id=f"{file.path}#class_{node.name}",
                    file_path=file.path,
                    content=(
                        f"File: {file.path}\nClass: {node.name}\n"
                        f"Docstring: {class_doc}\n"
                        f"Code:\n{class_content}"
                    ),
                    start_line=c_start,
                    end_line=c_end,
                    chunk_type="class",
                    entity_name=node.name,
                    metadata={"docstring": class_doc, "bases": [b.id for b in node.bases if isinstance(b, ast.Name)]}
                ))

                # Also chunk individual methods inside the class for fine-grained retrieval
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        m_start = item.lineno
                        m_end = getattr(item, "end_lineno", len(lines))
                        method_content = "\n".join(lines[m_start - 1 : m_end])
                        method_doc = ast.get_docstring(item) or ""
                        chunks.append(CodeChunk(
                            chunk_id=f"{file.path}#{node.name}.{item.name}",
                            file_path=file.path,
                            content=(
                                f"File: {file.path}\nClass: {node.name}\nMethod: {item.name}\n"
                                f"Docstring: {method_doc}\n"
                                f"Code:\n{method_content}"
                            ),
                            start_line=m_start,
                            end_line=m_end,
                            chunk_type="function",
                            entity_name=f"{node.name}.{item.name}",
                            parent_scope=node.name,
                            metadata={"docstring": method_doc, "is_method": True}
                        ))

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                f_start = node.lineno
                f_end = getattr(node, "end_lineno", len(lines))
                func_content = "\n".join(lines[f_start - 1 : f_end])
                func_doc = ast.get_docstring(node) or ""

                chunks.append(CodeChunk(
                    chunk_id=f"{file.path}#func_{node.name}",
                    file_path=file.path,
                    content=(
                        f"File: {file.path}\nFunction: {node.name}\n"
                        f"Docstring: {func_doc}\n"
                        f"Code:\n{func_content}"
                    ),
                    start_line=f_start,
                    end_line=f_end,
                    chunk_type="function",
                    entity_name=node.name,
                    metadata={"docstring": func_doc, "is_method": False}
                ))

        if not chunks:
            # If no classes or functions were found (e.g. script or config), chunk file directly
            return self._chunk_text_file(file)

        return chunks

    def _chunk_markdown_file(self, file: RepoFile) -> List[CodeChunk]:
        """Split markdown files by headings (# and ## and ###)."""
        chunks: List[CodeChunk] = []
        lines = file.content.splitlines()

        header_pattern = re.compile(r"^(#{1,4})\s+(.+)$")
        current_header = file.name
        current_lines: List[str] = []
        start_line = 1

        for idx, line in enumerate(lines, start=1):
            match = header_pattern.match(line)
            if match:
                if current_lines:
                    text_block = "\n".join(current_lines).strip()
                    if text_block:
                        chunks.append(CodeChunk(
                            chunk_id=f"{file.path}#section_{start_line}",
                            file_path=file.path,
                            content=f"File: {file.path}\nSection: {current_header}\n\n{text_block}",
                            start_line=start_line,
                            end_line=idx - 1,
                            chunk_type="doc_section",
                            entity_name=current_header,
                            metadata={"section": current_header}
                        ))
                current_header = match.group(2).strip()
                current_lines = [line]
                start_line = idx
            else:
                current_lines.append(line)

        if current_lines:
            text_block = "\n".join(current_lines).strip()
            if text_block:
                chunks.append(CodeChunk(
                    chunk_id=f"{file.path}#section_{start_line}",
                    file_path=file.path,
                    content=f"File: {file.path}\nSection: {current_header}\n\n{text_block}",
                    start_line=start_line,
                    end_line=len(lines),
                    chunk_type="doc_section",
                    entity_name=current_header,
                    metadata={"section": current_header}
                ))

        return chunks or self._chunk_text_file(file)

    def _chunk_text_file(self, file: RepoFile) -> List[CodeChunk]:
        """Sliding window fallback chunker with line number tracking."""
        chunks: List[CodeChunk] = []
        lines = file.content.splitlines()
        if not lines:
            return chunks

        step = max(self.chunk_size // 30, 20)  # lines per step
        overlap_lines = max(self.chunk_overlap // 30, 5)

        i = 0
        while i < len(lines):
            end_idx = min(i + step, len(lines))
            chunk_content = "\n".join(lines[i:end_idx]).strip()

            if chunk_content:
                chunks.append(CodeChunk(
                    chunk_id=f"{file.path}#lines_{i+1}_{end_idx}",
                    file_path=file.path,
                    content=f"File: {file.path} (Lines {i+1}-{end_idx}):\n{chunk_content}",
                    start_line=i + 1,
                    end_line=end_idx,
                    chunk_type="config" if file.file_type == "config" else "block",
                    entity_name=file.name,
                    metadata={"start_line": i + 1, "end_line": end_idx}
                ))

            if end_idx >= len(lines):
                break
            i += max(1, step - overlap_lines)

        return chunks
