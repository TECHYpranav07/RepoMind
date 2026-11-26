# 🧠 RepoMind — Explainable GraphRAG Platform

RepoMind combines **AST-based Knowledge Graph construction**, **FAISS Vector Embeddings**, and **Multi-Modal / LLM Reasoning** to deliver deep codebase understanding, semantic chat with citation tracing, and What-If refactoring impact analysis.

This repository integrates:
1. **Python GraphRAG Backend** (`RepoMind/` or `backend/`): FastAPI REST API wrapping the AST parser, Knowledge Graph builder, FAISS vector store, hybrid retriever, and What-If analysis engine.
2. **Modern Web Frontend** (`repomind-explorer/` or `frontend/`): React, Vite, Tailwind CSS, TanStack Router, and dynamic interactive force-directed graph visualization.

---

## 📁 Project Structure

```
repomind/
├── RepoMind/                  # Python Engine & Backend
│   ├── api_server.py          # FastAPI REST API (serves port 8000)
│   ├── app.py                 # (Optional) Legacy Streamlit UI
│   ├── requirements.txt       # Python dependencies (FastAPI, FAISS, NetworkX, etc.)
│   ├── .env                   # API keys (Groq, OpenAI, Gemini)
│   └── repomind/              # Core GraphRAG package
│       ├── analysis/          # What-If impact & change analyzers
│       ├── graph/             # Entity & relationship extractors, graph builder
│       ├── ingestion/         # GitHub loader, chunker, document processor
│       ├── llm/               # Answer generator, model provider, prompts
│       ├── retrieval/         # FAISS vector store, hybrid retriever
│       └── evaluation/        # Ground-truth benchmarks & metrics
│
├── repomind-explorer/         # Frontend Web Application (built with Lovable)
│   ├── src/                   # React + TypeScript + TanStack Router
│   │   ├── components/graph/  # 2D Interactive Force-Directed Knowledge Graph
│   │   ├── lib/repomind/      # API client & live workspace context
│   │   └── routes/            # Dashboard, Explorer, Chat, What-If, Benchmark
│   ├── package.json           # Frontend dependencies & scripts
│   └── vite.config.ts         # Vite configuration
│
├── backend -> RepoMind        # Convenient directory junction
├── frontend -> repomind-explorer # Convenient directory junction
├── start_project.bat          # 1-Click launcher for Windows (starts both)
├── start_project.ps1          # 1-Click launcher for PowerShell
├── run_backend.bat            # Launches backend standalone
└── run_frontend.bat           # Launches frontend standalone
```

---

## 🚀 Quick Start (Recommended)

### Method 1: One-Click Launcher

Simply double-click:
```bash
start_project.bat
```
*(or run `.\start_project.ps1` in PowerShell)*

This automatically starts both the FastAPI backend on port 8000 and the Vite frontend on port 5173 in separate terminal windows.

---

### Method 2: Manual Start (Two Terminals)

#### Terminal 1 — Start Backend:
```powershell
cd RepoMind
# Activate Python Virtual Environment
venv\Scripts\activate
# Start FastAPI Server
python -m uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
```
*Backend runs at: [http://127.0.0.1:8000](http://127.0.0.1:8000)*  
*API docs at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)*

#### Terminal 2 — Start Frontend:
```powershell
cd repomind-explorer
npm run dev
```
*Frontend runs at: [http://localhost:5173](http://localhost:5173)*

---

## ⚙️ Configuration & Environment Variables

Create or inspect `RepoMind/.env`:
```ini
# Optional: LLM Provider API Keys (falls back to local heuristic/grounded engine if omitted)
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
GITHUB_TOKEN=your_github_token   # Needed for cloning private or high-rate GitHub repos
```

In `repomind-explorer/.env`:
```ini
VITE_REPOMIND_API_URL=http://localhost:8000
```

---

## 🌐 Features & Endpoints

- **Dashboard (`/`)**: Ingest any GitHub repository or local sample repository; tracks live progress via background jobs.
- **Repository Explorer (`/explorer`)**: Dynamic interactive Force-Directed Knowledge Graph with interactive node inspections, source code preview, and library dependency viewers.
- **Repository Chat (`/chat`)**: Multi-hop Hybrid Retrieval (FAISS + AST Graph) with citation tracking and execution path visualization.
- **What-If Analysis (`/whatif`)**: Proactive impact prediction (ripple effects, impacted files, tests to update) when replacing or modifying components.
- **Evaluation Benchmark (`/evaluation`)**: AST-grounded retrieval evaluation comparing Graph, Hybrid, and Vector-only modes.
