"""Document cleaning, normalization, and dependency parser."""
import re
from typing import List, Dict, Any, Optional
from repomind.ingestion.mcp_connector import RepoFile


class DocumentProcessor:
    """Preprocesses files, extracts dependencies, cleans markdown, and identifies test suites."""

    @staticmethod
    def is_test_file(file_path: str) -> bool:
        """Detect whether a given file path is a test file."""
        lowered = file_path.lower()
        parts = lowered.replace("\\", "/").split("/")
        if any(part in ("test", "tests", "testing") for part in parts):
            return True
        filename = parts[-1]
        return filename.startswith("test_") or filename.endswith("_test.py")

    @staticmethod
    def is_config_file(file_path: str) -> bool:
        """Detect whether a file is an environment, setup, or config file."""
        lowered = file_path.lower()
        return (
            "config" in lowered or "settings" in lowered or
            lowered.endswith((".toml", ".yaml", ".yml", ".ini", ".cfg", ".json")) or
            "setup.py" in lowered or "dockerfile" in lowered
        )

    @staticmethod
    def parse_dependencies(files: List[RepoFile]) -> List[Dict[str, str]]:
        """Extract third-party libraries and versions from dependency files."""
        dependencies: List[Dict[str, str]] = []

        for f in files:
            path_lower = f.path.lower()
            if "requirements" in path_lower and path_lower.endswith(".txt"):
                for line in f.content.splitlines():
                    cleaned = line.strip()
                    if not cleaned or cleaned.startswith("#") or cleaned.startswith("-"):
                        continue
                    # Match package name and specifier
                    match = re.match(r"^([a-zA-Z0-9_\-\.]+)(?:([<>=~!]=?.*))?$", cleaned)
                    if match:
                        dependencies.append({
                            "name": match.group(1),
                            "specifier": match.group(2) or "any",
                            "source_file": f.path
                        })

            elif "pyproject.toml" in path_lower:
                in_deps = False
                for line in f.content.splitlines():
                    trimmed = line.strip()
                    if "dependencies = [" in trimmed or "[project.dependencies]" in trimmed:
                        in_deps = True
                        continue
                    if in_deps:
                        if trimmed.startswith("]") or trimmed.startswith("["):
                            in_deps = False
                            continue
                        dep_str = trimmed.strip('",\'')
                        match = re.match(r"^([a-zA-Z0-9_\-\.]+)(?:([<>=~!]=?.*))?", dep_str)
                        if match and match.group(1):
                            dependencies.append({
                                "name": match.group(1),
                                "specifier": match.group(2) or "any",
                                "source_file": f.path
                            })

        # Deduplicate
        seen = set()
        unique_deps = []
        for dep in dependencies:
            if dep["name"].lower() not in seen:
                seen.add(dep["name"].lower())
                unique_deps.append(dep)

        return unique_deps

    @staticmethod
    def clean_markdown(content: str) -> str:
        """Strip raw HTML comments and extraneous blank lines from markdown."""
        cleaned = re.sub(r"<!--[\s\S]*?-->", "", content)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()
