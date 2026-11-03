"""Global configuration and settings for RepoMind."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Data and cache storage paths
DATA_DIR = BASE_DIR / "data"
REPOSITORIES_DIR = DATA_DIR / "repositories"
INDEXES_DIR = DATA_DIR / "indexes"
GRAPHS_DIR = DATA_DIR / "graphs"
SAMPLE_REPO_DIR = DATA_DIR / "sample_repo"

# Ensure runtime directories exist
for path in [REPOSITORIES_DIR, INDEXES_DIR, GRAPHS_DIR, SAMPLE_REPO_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# GitHub settings
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_BASE = "https://api.github.com"
MAX_FILE_SIZE_BYTES = int(os.getenv("MAX_FILE_SIZE_BYTES", 1024 * 1024))  # 1 MB

# Supported source and documentation file extensions
SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".md": "markdown",
    ".txt": "text",
    ".toml": "config",
    ".yaml": "config",
    ".yml": "config",
    ".json": "data",
    ".rst": "markdown",
    ".cfg": "config",
    ".ini": "config",
    ".env.example": "config",
    "dockerfile": "docker",
    "requirements.txt": "dependencies"
}

EXCLUDED_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache",
    "node_modules", ".venv", "venv", "env", ".idea", ".vscode",
    "build", "dist", ".egg-info", "site-packages", ".tox"
}

# Embedding and Vector Index Configuration
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "fast-embed")  # fast-embed, sentence-transformers, openai, gemini
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
DEFAULT_CHUNK_SIZE = int(os.getenv("DEFAULT_CHUNK_SIZE", 800))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("DEFAULT_CHUNK_OVERLAP", 150))
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", 4))

# Knowledge Graph settings
DEFAULT_GRAPH_DEPTH = int(os.getenv("DEFAULT_GRAPH_DEPTH", 2))
MAX_GRAPH_NODES_VISUALIZE = int(os.getenv("MAX_GRAPH_NODES_VISUALIZE", 150))

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")  # auto, gemini, openai, local
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.1))
