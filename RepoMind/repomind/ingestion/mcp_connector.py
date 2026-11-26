"""Connector interface and MCP abstraction for repository sources."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RepoMetadata(BaseModel):
    """Metadata describing a software repository."""
    owner: str
    name: str
    full_name: str
    description: Optional[str] = "No description provided."
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    default_branch: str = "main"
    language: str = "Python"
    license: Optional[str] = "None"
    html_url: str = ""
    clone_url: str = ""
    is_local: bool = False


class RepoFile(BaseModel):
    """Represents a single source or documentation file from the repository."""
    path: str
    name: str
    extension: str
    file_type: str  # python, markdown, config, dependencies, text
    content: str
    size_bytes: int
    line_count: int


class RepositoryConnector(ABC):
    """Abstract interface for repository data sources (REST API, Git, or MCP Server)."""

    @abstractmethod
    def fetch_metadata(self, owner: str, repo: str) -> RepoMetadata:
        """Fetch general repository information and statistics."""
        pass

    @abstractmethod
    def fetch_repository_files(
        self,
        owner: str,
        repo: str,
        branch: Optional[str] = None,
        max_files: int = 200,
        progress_callback: Optional[Any] = None
    ) -> List[RepoFile]:
        """Fetch all eligible repository files including source, docs, and configs."""
        pass


class MCPConnector(RepositoryConnector):
    """Optional MCP (Model Context Protocol) Server Connector placeholder."""

    def __init__(self, mcp_server_url: Optional[str] = None):
        self.mcp_server_url = mcp_server_url

    def fetch_metadata(self, owner: str, repo: str) -> RepoMetadata:
        raise NotImplementedError("MCP direct tool connector is reserved for active MCP server bridges.")

    def fetch_repository_files(
        self,
        owner: str,
        repo: str,
        branch: Optional[str] = None,
        max_files: int = 200,
        progress_callback: Optional[Any] = None
    ) -> List[RepoFile]:
        raise NotImplementedError("MCP direct tool connector is reserved for active MCP server bridges.")
