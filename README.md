# RepoMind — Explainable GraphRAG for Software Repository What-If Analysis

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/frontend-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![NetworkX](https://img.shields.io/badge/graph-NetworkX-orange.svg)](https://networkx.org/)
[![FAISS](https://img.shields.io/badge/vector-FAISS--CPU-green.svg)](https://github.com/facebookresearch/faiss)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **RepoMind** is an AI-powered software repository intelligence platform. While traditional code assistants focus merely on explaining or writing code snippets, RepoMind focuses on **understanding how software components are connected** and **explaining the potential architectural consequences of changing them**.

---

## 🌟 Core Problem & Primary Differentiator

### The Core Problem
Codebases are complex directed dependency networks. Developers frequently need to know:
- *"What breaks if we replace our vector database with ChromaDB?"*
- *"What happens if we remove this function?"*
- *"Which tests must be updated if this class changes?"*
- *"Why does this repository use this particular architecture?"*

Standard Vector RAG looks only at semantic keyword similarity and misses causal call-chains, transitive caller paths, and configuration dependencies.

### The Primary Differentiator: Explainable What-If Analysis
RepoMind models the codebase as an explicit **typed Knowledge Graph** coupled with a **FAISS vector index**. When a hypothetical modification is proposed:
1. It parses the intent (e.g. `REPLACE FAISS WITH ChromaDB`).
2. It grounds the target entity to AST entities and third-party libraries.
3. It performs bidirectional graph traversal:
   - **Upstream (Callers & Importers)**: Who directly calls or imports this?
   - **Transitive (Indirect Callers)**: Who depends on those callers?
   - **Tests**: Which unit/integration tests cover this component?
   - **Configuration**: Which settings classes/files configure it?
4. It synthesizes an evidence-backed report with **human-readable graph paths**, **source citations**, and **risk severity scoring**.

---

## 🏗️ Architecture & System Design

```
                                  [ User Input ]
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
      [ Public GitHub URL / Repo ]                  [ Natural Language Query ]
                   │                                (e.g. "What if we replace FAISS?")
                   ▼                                           │
    ┌─────────────────────────────┐                            │
    │      Ingestion Engine       │                            │
    │  • GitHub REST API          │                            │
    │  • Rate-limit guard         │                            │
    │  • Local disk cache         │                            │
    └──────────────┬──────────────┘                            │
                   │                                           │
         ┌─────────┴─────────┐                                 │
         ▼                   ▼                                 ▼
┌──────────────────┐ ┌───────────────────┐        ┌─────────────────────────┐
│  Chunker (AST)   │ │  Knowledge Graph  │        │   What-If Change Parser │
│ • Python AST     │ │ • NetworkX DiGraph│        │ • Action extraction     │
│ • Markdown Head  │ │ • Entities & Edges│        │ • Entity grounding      │
└────────┬─────────┘ └─────────┬─────────┘        └────────────┬────────────┘
         │                     │                               │
         ▼                     ▼                               ▼
┌──────────────────┐ ┌───────────────────┐        ┌─────────────────────────┐
│   FAISS Index    │ │  Graph Retriever  │───────►│  Impact Analysis Engine │
│ • Dense Vectors  │ │ • BFS Traversal   │        │ • Upstream / Downstream │
│ • Cosine Sim     │ │ • Upstream paths  │        │ • Test coverage impact  │
└────────┬─────────┘ └─────────┬─────────┘        └────────────┬────────────┘
         │                     │                               │
         └──────────┬──────────┘                               │
                    ▼                                          │
       ┌─────────────────────────┐                             │
       │    Hybrid Retriever     │◄────────────────────────────┘
       │  • Vector RAG           │
       │  • Graph RAG            │
       │  • Hybrid GraphRAG      │
       └────────────┬────────────┘
                    │
                    ▼
       ┌─────────────────────────┐
       │   LLM Synthesis Engine  │
       │ • Gemini / OpenAI /     │
       │   Local Grounded Engine │
       └────────────┬────────────┘
                    │
                    ▼
       ┌─────────────────────────┐
       │     Streamlit UI        │
       │ • Interactive PyVis     │
       │ • What-If Impact Report │
       │ • Comparative Benchmark │
       └─────────────────────────┘
```

---

## 🧩 Knowledge Graph Schema

### Node Types
- `Repository`: Top-level repository metadata root
- `Module`: Python module / package namespace
- `File`: Individual source code or configuration file
- `Class`: Python class definition
- `Function`: Python function or class method
- `Library`: Third-party library dependency
- `Configuration`: Environment/settings specification
- `Documentation`: Markdown section or document
- `Test`: Unit/integration test function or test file

### Edge Types
- `CONTAINS`: File contains Class / Class contains Method
- `IMPORTS`: File / Function imports Module or Library
- `CALLS`: Function calls another Function / Class constructor
- `DEPENDS_ON`: Repository depends on third-party Library
- `IMPLEMENTS`: Class inherits from base Class or Interface
- `CONFIGURES`: Config model parameterizes Module / Class
- `DOCUMENTS`: Documentation references code entity
- `TESTS`: Test function validates target Function / Class

Every node and edge preserves: `file_path`, `line_number`, `source_snippet`, `confidence`, and `is_inferred`.

---

## 🚀 Quick Start & Installation

### Prerequisites
- Python 3.10 to 3.13
- Windows 11, macOS, or Linux (CPU-only friendly, no GPU required)
- Git installed on your system

### 1. Clone or Open Workspace
```bash
cd c:\Users\ASUS\Desktop\ANNA_PRO
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your API keys (optional):
```ini
# Optional: Higher rate limit for GitHub API
GITHUB_TOKEN=ghp_...

# LLM Provider: "auto", "gemini", "openai", or "local"
LLM_PROVIDER=auto

# Google Gemini API Key
GEMINI_API_KEY=AIzaSy...

# OpenAI API Key (optional)
OPENAI_API_KEY=sk-...
```
> **Note**: If no API keys are provided, RepoMind's **Local Grounded Engine** automatically takes over. All graph construction, vector retrieval, impact path computation, and what-if synthesis operate **100% locally with zero external API dependencies**!

### 4. Launch the Streamlit Web Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🖥️ Application Pages Overview

### Page 1: 🏠 Home / Repository Dashboard
- Enter any public GitHub repository (e.g. `facebookresearch/faiss`, `tiangolo/fastapi`) or click **Load Built-in RagCraft Repo**.
- Ingests README, dependency manifests, configuration files, and Python source code.
- Displays live ingestion progress and structural repository metrics (LOC, nodes, edges, entity breakdown).

### Page 2: 🔍 Repository Explorer
- **Interactive Knowledge Graph**: Rendered via PyVis physics engine with color-coded nodes. Zoom, pan, drag, and filter by entity types.
- **Source Code Browser**: Inspect any file with line numbers and syntax highlighting.
- **Detected Dependencies**: Table of all required third-party libraries and specifiers.
- **Architectural Hubs**: High-centrality classes and modules with high in/out degree.

### Page 3: 💬 Repository Chat
- Natural-language Q&A grounded strictly in repository context.
- **Retrieval Mode Selector**:
  - `Vector Only (FAISS)`: Standard semantic similarity.
  - `Graph Only (AST Traversal)`: Traverses explicit caller/import paths.
  - `Hybrid (Graph + Vector)`: Combined multi-hop retrieval with deduplication.
- Expandable **Source Citations** (file & line numbers) and **Traversed Graph Paths**.

### Page 4: 🔮 What-If Analysis (The Main Feature)
- Dedicated hypothetical change interface.
- Preset scenarios:
  - *"What if we replace FAISS with ChromaDB?"*
  - *"What if we remove Redis caching?"*
  - *"What components will be affected if I modify SemanticRetriever?"*
  - *"What happens if we upgrade Pydantic to v2?"*
- Outputs a comprehensive report:
  - **Risk Level Badge**: High, Medium, Low
  - **Directly Affected Components** (1-Hop callers)
  - **Inferred / Transitive Impacts** (>1-Hop callers)
  - **Tests Requiring Updates**
  - **Interactive Impacted Subgraph** (Target in Red, Direct Callers in Orange, Inferred in Amber)
  - **Dependency Reasoning Paths**
  - **Export to Markdown (`.md`) and JSON (`.json`)**

### Page 5: 📈 Evaluation & Benchmarking
- Automated benchmark suite executing on `BENCHMARK_DATASET`.
- Computes empirical metrics:
  - **Retrieval Precision@K** and **Recall@K**
  - **Impact Identification Precision & Recall (F1)**
  - **Answer Correctness**
  - **Faithfulness / Groundedness**
  - **Latency (Seconds)** and **Token Usage**
- Interactive Plotly visualizations:
  - Grouped Bar Chart comparing Vector vs Graph vs Hybrid
  - Latency comparison bar chart
  - Multi-dimensional Radar Chart
  - One-click CSV export of raw benchmark runs

---

## 🧪 Running Automated Tests

Run the full unit and integration test suite:
```bash
pytest repomind/tests/test_all_components.py -v
```

All 8 core test suites validate:
1. `test_url_parser`: URL and shorthand parsing.
2. `test_ingestion_and_chunker`: Local connector, AST class/function chunker, line preservation.
3. `test_knowledge_graph_construction`: Entity extraction, typed relationship mapping, NetworkX graph assembly.
4. `test_vector_store_and_embeddings`: Dense vector indexing, cosine similarity search, FAISS persistence.
5. `test_hybrid_retriever_modes`: Vector RAG, Graph RAG, and Hybrid GraphRAG modes.
6. `test_whatif_change_parser_and_impact`: Natural language change parsing, upstream/downstream neighborhood traversal.
7. `test_whatif_end_to_end_report`: End-to-end report generation and markdown export.
8. `test_evaluation_metrics_and_benchmark`: Precision@K, Recall@K, faithfulness, and component overlap metrics.

---

## 📁 Repository Directory Structure

```
ANNA_PRO/
├── app.py                         # Streamlit central application entrypoint
├── config.py                      # Root configuration alias
├── requirements.txt               # Dependencies
├── .env.example                   # Environment variable template
├── README.md                      # Documentation
├── repomind/
│   ├── config.py                  # Core configuration & settings
│   ├── app.py                     # Package app alias
│   ├── frontend/
│   │   ├── dashboard.py           # Page 1: Home / Dashboard
│   │   ├── repository_explorer.py # Page 2: Repository Explorer
│   │   ├── chat.py                # Page 3: Repository Chat
│   │   ├── whatif.py              # Page 4: What-If Analysis
│   │   ├── evaluation.py          # Page 5: Evaluation & Benchmarking
│   │   ├── graph_visualizer.py    # PyVis & Plotly interactive graph renderers
│   │   └── styles.css             # Polished dark developer tool UI styling
│   ├── ingestion/
│   │   ├── github_loader.py       # GitHub REST API & local repo connectors
│   │   ├── mcp_connector.py       # MCP & connector interface abstraction
│   │   ├── document_processor.py  # Markdown cleaning & dependency parser
│   │   └── chunker.py             # AST structure-aware code & doc chunker
│   ├── graph/
│   │   ├── entity_extractor.py    # AST node extractor (Classes, Funcs, Libs)
│   │   ├── relationship_extractor.py # Typed relationship extractor (AST Visitor)
│   │   ├── graph_builder.py       # NetworkX DiGraph builder & metrics
│   │   └── graph_retriever.py     # Entity resolution & neighborhood traversal
│   ├── retrieval/
│   │   ├── embeddings.py          # Fast Dense, SentenceTransformers, API embeddings
│   │   ├── vector_store.py        # FAISS vector store with disk persistence
│   │   ├── hybrid_retriever.py    # Hybrid GraphRAG coordinator
│   │   └── context_builder.py     # Grounded context & citation formatter
│   ├── llm/
│   │   ├── model_provider.py      # Gemini, OpenAI, & Local Heuristic Engine
│   │   ├── prompts.py             # Grounded Q&A & What-If analysis prompts
│   │   └── answer_generator.py    # Answer & report generation orchestrator
│   ├── analysis/
│   │   ├── change_parser.py       # Natural-language hypothetical change parser
│   │   ├── impact_analyzer.py     # Upstream/downstream causal dependency tracer
│   │   └── report_generator.py    # What-If impact report compiler & exporter
│   ├── evaluation/
│   │   ├── dataset.py             # Prepared repository benchmark dataset
│   │   ├── metrics.py             # Precision@K, Recall@K, Faithfulness, F1
│   │   └── benchmark.py           # Multi-mode benchmark runner & Plotly charts
│   ├── data/
│   │   ├── sample_repo/           # Reference "RagCraft" architecture microservice
│   │   ├── repositories/          # Local cache for ingested repo files
│   │   ├── indexes/               # Local cache for FAISS indexes
│   │   └── graphs/                # Local cache for NetworkX graphs
│   └── tests/
│       └── test_all_components.py # Comprehensive test suite
```

---

## ⚠️ Assumptions & Limitations

1. **Python Focus**: AST parsing and relationship extraction currently target Python codebases (`.py`). Other file types (`.md`, `.toml`, `.yaml`, `.txt`) are indexed as semantic and configuration units.
2. **Static Predictions vs Dynamic Execution**: What-If analysis is a predictive static impact evaluation based on code topology and AST relations. It does not compile or run test suites in an isolated sandbox.
3. **Dynamic Reflection**: Python dynamic invocations (e.g. `getattr(module, dynamic_string)()`) are classified as inferred relationships with lower confidence rather than deterministic AST edges.
