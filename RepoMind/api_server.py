"""RepoMind HTTP API — connects the RepoMind web app to the existing Python engine.

Drop this file into the root of the RepoMind repository (next to app.py) and run:

    pip install fastapi uvicorn
    uvicorn api_server:app --host 0.0.0.0 --port 8000

It only *wraps* the existing RepoMind modules. Every step mirrors what the
Streamlit pages in repomind/frontend/*.py do, so behaviour is unchanged.
"""
from __future__ import annotations

import datetime
import math
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from repomind.ingestion.github_loader import get_connector_for_target
from repomind.ingestion.chunker import StructureAwareChunker
from repomind.graph.entity_extractor import EntityExtractor
from repomind.graph.relationship_extractor import RelationshipExtractor
from repomind.graph.graph_builder import RepoGraphBuilder
from repomind.retrieval.embeddings import get_embedding_engine
from repomind.retrieval.vector_store import FAISSVectorStore
from repomind.retrieval.hybrid_retriever import HybridRetriever
from repomind.llm.answer_generator import AnswerGenerator
from repomind.analysis.report_generator import WhatIfReportCoordinator
from repomind.evaluation.benchmark import BenchmarkRunner
from repomind.evaluation.dataset import BENCHMARK_DATASET, generate_ast_ground_truth_dataset

app = FastAPI(title="RepoMind API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single shared workspace, equivalent to Streamlit's st.session_state.
STATE: Dict[str, Any] = {"repo_loaded": False}
JOBS: Dict[str, Dict[str, Any]] = {}
LOCK = threading.Lock()


# ─────────────────────────────── helpers ────────────────────────────────

def _clean(v: Any) -> Any:
    """Make values JSON-safe (NaN -> None, numpy -> python, recurse)."""
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_clean(x) for x in v]
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        try:
            v = v.item()
        except Exception:
            pass
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if hasattr(v, "model_dump"):
        return _clean(v.model_dump())
    return str(v)


def _require_repo():
    if not STATE.get("repo_loaded"):
        raise HTTPException(status_code=409, detail="No repository loaded. Ingest a repository first.")


def _node_payload(graph, nid: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": nid,
        "name": data.get("name", nid),
        "type": data.get("type", "Unknown"),
        "file_path": data.get("file_path"),
        "line_number": data.get("line_number"),
        "docstring": data.get("docstring"),
        "source_snippet": data.get("source_snippet"),
        "in_degree": graph.in_degree(nid),
        "out_degree": graph.out_degree(nid),
    }


def _graph_payload(graph) -> Dict[str, Any]:
    if graph is None:
        return {"nodes": [], "edges": []}
    return {
        "nodes": [_clean(_node_payload(graph, n, d)) for n, d in graph.nodes(data=True)],
        "edges": [
            {"source": u, "target": v, "relation": d.get("relation", "CONNECTS")}
            for u, v, d in graph.edges(data=True)
        ],
    }


def _summary() -> Dict[str, Any]:
    if not STATE.get("repo_loaded"):
        return {"repo_loaded": False}
    meta = STATE["repo_meta"]
    files = STATE.get("repo_files", [])
    chunks = STATE.get("repo_chunks", [])
    graph = STATE.get("graph")
    builder = STATE.get("graph_builder")
    stats = builder.get_statistics() if builder else {}
    return _clean({
        "repo_loaded": True,
        "meta": meta.model_dump(),
        "files": len(files),
        "chunks": len(chunks),
        "nodes": graph.number_of_nodes() if graph else 0,
        "edges": graph.number_of_edges() if graph else 0,
        "lines_of_code": sum(f.line_count for f in files),
        "node_type_breakdown": stats.get("node_type_breakdown", {}),
        "edge_relation_breakdown": stats.get("edge_relation_breakdown", {}),
    })


# ─────────────────────────── ingestion (dashboard) ───────────────────────────

def _run_ingestion_pipeline(target: str, job: Dict[str, Any]):
    """Same steps as repomind/frontend/dashboard.py::_run_ingestion_pipeline."""
    def report(msg: str, pct: float):
        job["message"], job["progress"] = msg, pct

    try:
        report("Connecting to repository source...", 0.0)
        connector, owner, repo = get_connector_for_target(target)

        meta = connector.fetch_metadata(owner, repo)
        report(f"Fetched metadata for {meta.full_name}", 0.2)

        def progress_cb(msg: str, pct: float):
            report(msg, 0.2 + 0.4 * pct)

        files = connector.fetch_repository_files(owner, repo, progress_callback=progress_cb)
        report(f"Ingested {len(files)} files. Chunking...", 0.6)

        chunker = StructureAwareChunker()
        chunks = chunker.chunk_repository(files)
        report(f"Generated {len(chunks)} semantic chunks. Extracting Knowledge Graph...", 0.7)

        nodes = EntityExtractor.extract_entities(meta, files)
        edges = RelationshipExtractor.extract_relationships(meta, files, nodes)
        graph_builder = RepoGraphBuilder()
        graph = graph_builder.build(nodes, edges)
        report(f"Constructed Knowledge Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges.", 0.8)

        report("Generating vector embeddings and building FAISS index...", 0.8)
        embed_engine = get_embedding_engine()
        chunk_texts = [c.content for c in chunks]
        embeddings = (
            embed_engine.fit_and_embed(chunk_texts)
            if hasattr(embed_engine, "fit_and_embed")
            else embed_engine.embed_texts(chunk_texts)
        )
        vector_store = FAISSVectorStore(dimension=embed_engine.dimension)
        vector_store.add_chunks(chunks, embeddings)
        report("Building hybrid retriever...", 0.95)

        hybrid_retriever = HybridRetriever(vector_store, embed_engine, graph)

        with LOCK:
            for k in ("benchmark_results", "benchmark_last_run", "last_whatif_result"):
                STATE.pop(k, None)
            STATE.update({
                "repo_loaded": True,
                "repo_meta": meta,
                "repo_files": files,
                "repo_chunks": chunks,
                "graph_nodes": nodes,
                "graph_edges": edges,
                "graph": graph,
                "graph_builder": graph_builder,
                "vector_store": vector_store,
                "embed_engine": embed_engine,
                "hybrid_retriever": hybrid_retriever,
                "answer_generator": AnswerGenerator(),
            })

        report("Repository successfully analyzed and indexed!", 1.0)
        job["status"] = "done"
        job["result"] = _summary()
    except Exception as e:  # noqa: BLE001 — surface any ingestion error to the UI
        job["status"] = "error"
        job["error"] = f"Ingestion Error: {e}"


class IngestRequest(BaseModel):
    target: str


@app.on_event("startup")
def _auto_init():
    """Auto-initialize with the built-in sample repo, like app.py does."""
    job = {"status": "running", "progress": 0.0, "message": ""}
    try:
        _run_ingestion_pipeline("sample_repo", job)
    except Exception:
        STATE["repo_loaded"] = False


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/state")
def state():
    return _summary()


@app.post("/api/ingest")
def ingest(req: IngestRequest):
    target = req.target.strip()
    if not target:
        raise HTTPException(status_code=400, detail="Enter a repository URL or shorthand.")
    job_id = uuid.uuid4().hex
    job = {"id": job_id, "kind": "ingest", "status": "running", "progress": 0.0, "message": "Queued", "error": None}
    JOBS[job_id] = job
    threading.Thread(target=_run_ingestion_pipeline, args=(target, job), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _clean(job)


# ─────────────────────────── repository explorer ────────────────────────────

@app.get("/api/graph")
def graph_view():
    _require_repo()
    graph = STATE["graph"]
    builder = STATE["graph_builder"]
    stats = builder.get_statistics() if builder else {}
    libraries = [
        {
            "name": d.get("name", ""),
            "specifier": (d.get("metadata") or {}).get("specifier", "any"),
            "source": (d.get("metadata") or {}).get("source_file", "requirements.txt"),
        }
        for _, d in graph.nodes(data=True) if d.get("type") == "Library"
    ]
    return _clean({**_graph_payload(graph), "stats": stats, "libraries": libraries})


@app.get("/api/files")
def files_list():
    _require_repo()
    return [
        {
            "path": f.path, "name": f.name, "extension": f.extension, "file_type": f.file_type,
            "size_bytes": f.size_bytes, "line_count": f.line_count,
        }
        for f in STATE.get("repo_files", [])
    ]


@app.get("/api/files/content")
def file_content(path: str = Query(...)):
    _require_repo()
    f = next((x for x in STATE.get("repo_files", []) if x.path == path), None)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    return _clean(f.model_dump())


# ─────────────────────────────── chat ───────────────────────────────

def _get_suggested_questions(meta, graph):
    """Copied from repomind/frontend/chat.py::_get_suggested_questions."""
    if not graph or meta.name == "ragcraft":
        return [
            "How is the vector store configured?",
            "Where does caching get called?",
            "Which components connect to RAGPipeline?",
        ]
    classes = [d.get("name") for _, d in graph.nodes(data=True) if d.get("type") == "Class" and d.get("name")]
    libs = [d.get("name") for _, d in graph.nodes(data=True) if d.get("type") == "Library" and d.get("name")]
    q1 = f"What is the role of `{classes[0]}`?" if classes else "What is the primary architecture of this repository?"
    q2 = f"How does `{classes[1]}` interact with other components?" if len(classes) > 1 else "How are dependencies wired?"
    q3 = f"Which modules depend on `{libs[0]}`?" if libs else "What tests are available in this repository?"
    return [q1, q2, q3]


@app.get("/api/chat/suggestions")
def chat_suggestions():
    _require_repo()
    return _get_suggested_questions(STATE["repo_meta"], STATE["graph"])


class ChatRequest(BaseModel):
    query: str
    mode: str = "hybrid"  # "hybrid" | "graph"
    top_k: int = 4
    graph_depth: int = 2


@app.post("/api/chat")
def chat(req: ChatRequest):
    _require_repo()
    ret_res = STATE["hybrid_retriever"].retrieve(
        query=req.query, mode=req.mode, top_k=req.top_k, graph_depth=req.graph_depth
    )
    ans = STATE["answer_generator"].answer_question(req.query, ret_res)
    return _clean({
        "answer": ans.get("answer", ""),
        "citations": ans.get("citations", []),
        "graph_paths": ans.get("graph_paths", []),
        "latency": ans.get("latency", 0.0),
        "model_used": ans.get("model_used", "Local Grounded Engine"),
        "mode": req.mode.upper(),
    })


# ─────────────────────────────── what-if ───────────────────────────────

def _get_quick_scenarios(meta, graph):
    """Copied from repomind/frontend/whatif.py::_get_quick_scenarios."""
    if not graph or meta.name == "ragcraft":
        return [
            ("🔄 Replace FAISS with ChromaDB", "What if we replace FAISS with ChromaDB?"),
            ("🗑️ Remove Redis Caching", "What if we remove Redis caching?"),
            ("🛠️ Modify SemanticRetriever", "What components will be affected if I modify SemanticRetriever?"),
            ("🚀 Upgrade Pydantic to v2", "What happens if we upgrade Pydantic to v2?"),
        ]
    classes = [d.get("name") for _, d in graph.nodes(data=True) if d.get("type") == "Class" and d.get("name")]
    libs = [d.get("name") for _, d in graph.nodes(data=True) if d.get("type") == "Library" and d.get("name")]
    s1 = (f"🔄 Replace {classes[0]}", f"What if we replace {classes[0]} with a custom adapter?") if classes else ("🔄 Refactor Storage", "What if we refactor storage?")
    s2 = (f"🗑️ Remove {libs[0]}", f"What if we remove {libs[0]}?") if libs else ("🗑️ Remove Dep", "What if we remove external dependencies?")
    s3 = (f"🛠️ Modify {classes[1]}", f"What components will be affected if I modify {classes[1]}?") if len(classes) > 1 else ("🛠️ Modify Core", "What if we modify core modules?")
    s4 = (f"🚀 Upgrade {libs[1]}", f"What happens if we upgrade {libs[1]} to the latest version?") if len(libs) > 1 else ("🚀 Upgrade Dependencies", "What happens if we upgrade dependencies?")
    return [s1, s2, s3, s4]


@app.get("/api/whatif/scenarios")
def whatif_scenarios():
    _require_repo()
    return [{"label": l, "query": q} for l, q in _get_quick_scenarios(STATE["repo_meta"], STATE["graph"])]


class WhatIfRequest(BaseModel):
    hypothesis: str
    max_depth: int = 2


def _whatif_export_json(res: Dict[str, Any]) -> Dict[str, Any]:
    """Same structure as the JSON download in repomind/frontend/whatif.py."""
    return {
        "hypothesis": res.get("hypothesis"),
        "action": res.get("action"),
        "target_entity": res.get("target_entity"),
        "replacement_entity": res.get("replacement_entity"),
        "risk_level": res.get("risk_level"),
        "target_nodes": res.get("target_nodes"),
        "direct_affected": res.get("direct_affected"),
        "inferred_affected": res.get("inferred_affected"),
        "tests_to_update": res.get("tests_to_update"),
        "configs_to_update": res.get("configs_to_update"),
        "impact_paths": res.get("impact_paths"),
        "latency_seconds": res.get("latency"),
        "model_used": res.get("model_used"),
    }


@app.post("/api/whatif")
def whatif(req: WhatIfRequest):
    _require_repo()
    coordinator = WhatIfReportCoordinator(STATE["graph"], STATE["hybrid_retriever"], STATE["answer_generator"])
    res = coordinator.run_analysis(req.hypothesis.strip(), max_depth=req.max_depth)
    STATE["last_whatif_result"] = res
    out = {k: v for k, v in res.items() if k != "impact_subgraph"}
    out["impact_subgraph"] = _graph_payload(res.get("impact_subgraph"))
    out["export_markdown"] = WhatIfReportCoordinator.export_report_markdown(res)
    out["export_json"] = _whatif_export_json(res)
    return _clean(out)


# ─────────────────────────────── evaluation ───────────────────────────────

class BenchmarkRequest(BaseModel):
    modes: List[str] = ["graph", "hybrid"]
    num_questions: int = 3
    gt_source: str = "ast"      # "ast" (Live AST ground truth) | "curated" (golden set)
    speed_mode: str = "fast"    # "fast" (configured LLM) | "turbo" (local engine)


def _run_benchmark(req: BenchmarkRequest, job: Dict[str, Any]):
    """Same steps as repomind/frontend/evaluation.py::_run_and_store_benchmark."""
    try:
        graph = STATE.get("graph")
        if req.gt_source == "ast" and graph is not None:
            ast_dataset = generate_ast_ground_truth_dataset(graph, max_questions=req.num_questions)
            dataset = ast_dataset if ast_dataset else BENCHMARK_DATASET[: req.num_questions]
        else:
            dataset = BENCHMARK_DATASET[: req.num_questions]

        def prog_cb(msg: str, pct: float):
            job["message"], job["progress"] = msg, min(pct, 1.0)

        if req.speed_mode == "turbo":
            from repomind.llm.model_provider import LocalHeuristicSynthesizer
            eval_gen = AnswerGenerator(LocalHeuristicSynthesizer())
        else:
            eval_gen = STATE.get("answer_generator") or AnswerGenerator()

        runner = BenchmarkRunner(STATE["hybrid_retriever"], eval_gen, dataset)
        df = runner.run_benchmark(modes=req.modes, progress_callback=prog_cb, parallel=True, max_workers=4)
        rows = _clean(df.to_dict(orient="records"))
        STATE["benchmark_results"] = rows
        STATE["benchmark_last_run"] = datetime.datetime.now().isoformat()
        job["status"] = "done"
        job["progress"] = 1.0
        job["message"] = "Benchmark completed successfully!"
        job["result"] = {"rows": rows, "last_run": STATE["benchmark_last_run"]}
    except Exception as e:  # noqa: BLE001
        job["status"] = "error"
        job["error"] = f"Benchmark failed: {e}"


@app.post("/api/benchmark")
def benchmark(req: BenchmarkRequest):
    _require_repo()
    if not req.modes:
        raise HTTPException(status_code=400, detail="Please select at least one retrieval mode.")
    job_id = uuid.uuid4().hex
    job = {"id": job_id, "kind": "benchmark", "status": "running", "progress": 0.0, "message": "Starting…", "error": None}
    JOBS[job_id] = job
    threading.Thread(target=_run_benchmark, args=(req, job), daemon=True).start()
    return {"job_id": job_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
