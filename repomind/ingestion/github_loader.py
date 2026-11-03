"""GitHub REST API and local repository ingestion loader."""
import os
import re
import json
import base64
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
import requests

from repomind.config import (
    GITHUB_TOKEN, GITHUB_API_BASE, MAX_FILE_SIZE_BYTES,
    SUPPORTED_EXTENSIONS, EXCLUDED_DIRS, REPOSITORIES_DIR, SAMPLE_REPO_DIR
)
from repomind.ingestion.mcp_connector import RepositoryConnector, RepoMetadata, RepoFile


def parse_repo_url(url_or_path: str) -> Tuple[str, str, bool]:
    """
    Parse a GitHub URL, shorthand 'owner/repo', or local path.
    Returns: (owner, repo, is_local)
    """
    cleaned = url_or_path.strip().rstrip("/")

    # Check if it points to a local directory
    if os.path.exists(cleaned) or cleaned in ("sample", "sample_repo", "ragcraft"):
        if cleaned in ("sample", "sample_repo", "ragcraft"):
            return "local", "ragcraft", True
        path_obj = Path(cleaned).resolve()
        return "local", path_obj.name, True

    # Match standard GitHub URLs
    gh_match = re.search(r"github\.com[/:]([\w\-\.]+)/([\w\-\.]+?)(?:\.git)?$", cleaned, re.IGNORECASE)
    if gh_match:
        return gh_match.group(1), gh_match.group(2), False

    # Match owner/repo pattern
    shorthand_match = re.match(r"^([\w\-\.]+)/([\w\-\.]+)$", cleaned)
    if shorthand_match:
        return shorthand_match.group(1), shorthand_match.group(2), False

    raise ValueError(f"Invalid GitHub repository URL or directory path: '{url_or_path}'")


class GitHubRESTConnector(RepositoryConnector):
    """Ingests repositories using GitHub REST API with raw content streaming & rate-limit handling."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or GITHUB_TOKEN
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RepoMind-GraphRAG/1.0"
        })
        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"

    def _check_rate_limit(self, response: requests.Response) -> None:
        """Inspect headers for rate limit exhaustion."""
        remaining = response.headers.get("x-ratelimit-remaining")
        if response.status_code in (403, 429) and remaining == "0":
            reset_time = response.headers.get("x-ratelimit-reset", "unknown")
            raise PermissionError(
                f"GitHub API rate limit exceeded. Resets at timestamp {reset_time}. "
                "Provide a GITHUB_TOKEN in settings or .env to get 5,000 requests/hour."
            )

    def fetch_metadata(self, owner: str, repo: str) -> RepoMetadata:
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        resp = self.session.get(url, timeout=12)
        self._check_rate_limit(resp)

        if resp.status_code != 200:
            raise FileNotFoundError(f"Failed to fetch repository metadata: HTTP {resp.status_code} ({resp.text})")

        data = resp.json()
        return RepoMetadata(
            owner=data.get("owner", {}).get("login", owner),
            name=data.get("name", repo),
            full_name=data.get("full_name", f"{owner}/{repo}"),
            description=data.get("description") or "No description provided.",
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            open_issues=data.get("open_issues_count", 0),
            default_branch=data.get("default_branch", "main"),
            language=data.get("language") or "Python",
            license=data.get("license", {}).get("spdx_id") if data.get("license") else "None",
            html_url=data.get("html_url", f"https://github.com/{owner}/{repo}"),
            clone_url=data.get("clone_url", f"https://github.com/{owner}/{repo}.git"),
            is_local=False
        )

    def fetch_repository_files(
        self,
        owner: str,
        repo: str,
        branch: Optional[str] = None,
        max_files: int = 150,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> List[RepoFile]:
        # First check local cache
        cache_dir = REPOSITORIES_DIR / f"{owner}_{repo}"
        cache_manifest = cache_dir / "manifest.json"
        if cache_manifest.exists():
            try:
                with open(cache_manifest, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                files = []
                for item in manifest_data:
                    file_path = cache_dir / item["path"]
                    if file_path.exists():
                        with open(file_path, "r", encoding="utf-8", errors="replace") as rf:
                            content = rf.read()
                        files.append(RepoFile(
                            path=item["path"],
                            name=item["name"],
                            extension=item["extension"],
                            file_type=item["file_type"],
                            content=content,
                            size_bytes=len(content.encode("utf-8")),
                            line_count=len(content.splitlines())
                        ))
                if files:
                    if progress_callback:
                        progress_callback(f"Loaded {len(files)} files from local cache", 1.0)
                    return files
            except Exception:
                pass  # Cache corrupt, refetch

        if not branch:
            meta = self.fetch_metadata(owner, repo)
            branch = meta.default_branch

        if progress_callback:
            progress_callback(f"Querying Git tree for {owner}/{repo}@{branch}...", 0.1)

        tree_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        tree_resp = self.session.get(tree_url, timeout=15)
        self._check_rate_limit(tree_resp)

        if tree_resp.status_code != 200:
            raise RuntimeError(f"Could not retrieve tree for {owner}/{repo}: HTTP {tree_resp.status_code}")

        tree_data = tree_resp.json()
        entries = tree_data.get("tree", [])

        # Filter candidate files
        candidate_entries = []
        for entry in entries:
            if entry.get("type") != "blob":
                continue
            path_str = entry.get("path", "")
            parts = path_str.split("/")
            if any(part in EXCLUDED_DIRS for part in parts):
                continue
            ext = Path(path_str).suffix.lower()
            name_lower = Path(path_str).name.lower()
            if ext in SUPPORTED_EXTENSIONS or name_lower in SUPPORTED_EXTENSIONS:
                candidate_entries.append(entry)

        candidate_entries = candidate_entries[:max_files]
        total_candidates = len(candidate_entries)
        fetched_files: List[RepoFile] = []

        cache_dir.mkdir(parents=True, exist_ok=True)
        manifest_records = []

        for idx, entry in enumerate(candidate_entries):
            file_path_str = entry["path"]
            ext = Path(file_path_str).suffix.lower()
            file_name = Path(file_path_str).name
            file_type = SUPPORTED_EXTENSIONS.get(ext) or SUPPORTED_EXTENSIONS.get(file_name.lower(), "text")

            pct = 0.1 + 0.8 * ((idx + 1) / max(total_candidates, 1))
            if progress_callback:
                progress_callback(f"Fetching ({idx+1}/{total_candidates}): {file_name}", pct)

            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path_str}"
            try:
                raw_resp = self.session.get(raw_url, timeout=10)
                if raw_resp.status_code == 200:
                    content = raw_resp.text
                else:
                    blob_url = entry["url"]
                    blob_resp = self.session.get(blob_url, timeout=10)
                    self._check_rate_limit(blob_resp)
                    if blob_resp.status_code == 200:
                        content_b64 = blob_resp.json().get("content", "")
                        content = base64.b64decode(content_b64).decode("utf-8", errors="replace")
                    else:
                        continue
            except Exception:
                continue

            if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
                continue

            repo_file = RepoFile(
                path=file_path_str,
                name=file_name,
                extension=ext,
                file_type=file_type,
                content=content,
                size_bytes=len(content.encode("utf-8")),
                line_count=len(content.splitlines())
            )
            fetched_files.append(repo_file)

            # Persist to cache
            local_save_path = cache_dir / file_path_str
            local_save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_save_path, "w", encoding="utf-8", errors="replace") as wf:
                wf.write(content)

            manifest_records.append({
                "path": file_path_str,
                "name": file_name,
                "extension": ext,
                "file_type": file_type
            })

        with open(cache_manifest, "w", encoding="utf-8") as mf:
            json.dump(manifest_records, mf, indent=2)

        if progress_callback:
            progress_callback(f"Completed ingestion of {len(fetched_files)} files", 1.0)

        return fetched_files


class LocalDirConnector(RepositoryConnector):
    """Ingests a local directory or the built-in sample repository."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = Path(root_dir) if root_dir else SAMPLE_REPO_DIR

    def fetch_metadata(self, owner: str, repo: str) -> RepoMetadata:
        readme_path = self.root_dir / "README.md"
        desc = "Local software repository."
        if readme_path.exists():
            with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
                first_lines = [line.strip() for line in f.readlines()[:4] if line.strip() and not line.startswith("#")]
                if first_lines:
                    desc = first_lines[0]

        return RepoMetadata(
            owner="local",
            name=repo or self.root_dir.name,
            full_name=f"local/{repo or self.root_dir.name}",
            description=desc,
            stars=128,
            forks=24,
            open_issues=2,
            default_branch="main",
            language="Python",
            license="MIT",
            html_url=str(self.root_dir),
            clone_url=str(self.root_dir),
            is_local=True
        )

    def fetch_repository_files(
        self,
        owner: str,
        repo: str,
        branch: Optional[str] = None,
        max_files: int = 150,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> List[RepoFile]:
        files: List[RepoFile] = []
        all_paths = []

        for root, dirs, filenames in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            for fn in filenames:
                ext = Path(fn).suffix.lower()
                name_lower = fn.lower()
                if ext in SUPPORTED_EXTENSIONS or name_lower in SUPPORTED_EXTENSIONS:
                    all_paths.append(Path(root) / fn)

        total = len(all_paths)
        for idx, p in enumerate(all_paths[:max_files]):
            rel_path = p.relative_to(self.root_dir).as_posix()
            ext = p.suffix.lower()
            name = p.name
            file_type = SUPPORTED_EXTENSIONS.get(ext) or SUPPORTED_EXTENSIONS.get(name.lower(), "text")

            pct = (idx + 1) / max(total, 1)
            if progress_callback:
                progress_callback(f"Reading local file: {rel_path}", pct)

            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                continue

            if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
                continue

            files.append(RepoFile(
                path=rel_path,
                name=name,
                extension=ext,
                file_type=file_type,
                content=content,
                size_bytes=len(content.encode("utf-8")),
                line_count=len(content.splitlines())
            ))

        return files


def get_connector_for_target(target: str) -> Tuple[RepositoryConnector, str, str]:
    """Factory helper resolving an input target to connector, owner, repo."""
    owner, repo, is_local = parse_repo_url(target)
    if is_local:
        if target in ("sample", "sample_repo", "ragcraft"):
            return LocalDirConnector(SAMPLE_REPO_DIR), "local", "ragcraft"
        return LocalDirConnector(Path(target)), owner, repo
    return GitHubRESTConnector(), owner, repo
