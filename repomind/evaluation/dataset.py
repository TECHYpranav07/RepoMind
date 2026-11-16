"""Standard benchmark dataset for software repository Q&A and What-If analysis."""
from typing import List, Dict, Any

BENCHMARK_DATASET: List[Dict[str, Any]] = [
    {
        "id": "q1_vector_store_role",
        "category": "Architecture",
        "question": "What vector store does this repository use and how is it initialized?",
        "expected_files": [
            "ragcraft/storage/vector_store.py",
            "ragcraft/config.py",
            "README.md"
        ],
        "expected_components": [
            "FAISSVectorStore",
            "VectorStoreConfig",
            "VectorStore"
        ],
        "reference_answer": "The repository uses FAISSVectorStore, which wraps FAISS index types (IndexFlatIP/IndexFlatL2) and is configured using VectorStoreConfig with default dimension 384."
    },
    {
        "id": "q2_cache_integration",
        "category": "Architecture",
        "question": "How is caching implemented and where is it checked during retrieval?",
        "expected_files": [
            "ragcraft/storage/cache.py",
            "ragcraft/retrieval/retriever.py",
            "ragcraft/config.py"
        ],
        "expected_components": [
            "RedisCache",
            "SemanticRetriever",
            "CacheConfig"
        ],
        "reference_answer": "RedisCache manages key-value lookups with TTL. SemanticRetriever checks the cache first in retrieve() before generating embeddings and querying the vector store."
    },
    {
        "id": "q3_whatif_replace_faiss",
        "category": "What-If",
        "question": "What if we replace FAISS with ChromaDB?",
        "expected_files": [
            "ragcraft/storage/vector_store.py",
            "ragcraft/retrieval/retriever.py",
            "ragcraft/config.py",
            "ragcraft/pipeline/rag_pipeline.py",
            "tests/test_retriever.py",
            "requirements.txt"
        ],
        "expected_components": [
            "FAISSVectorStore",
            "VectorStore",
            "SemanticRetriever",
            "VectorStoreConfig",
            "test_faiss_store_initialization"
        ],
        "reference_answer": "Replacing FAISS with ChromaDB requires implementing a ChromaDBVectorStore adhering to VectorStore, updating VectorStoreConfig, adjusting SemanticRetriever initialization, updating requirements.txt, and rewriting unit tests in test_retriever.py."
    },
    {
        "id": "q4_whatif_remove_redis",
        "category": "What-If",
        "question": "What if we remove Redis caching?",
        "expected_files": [
            "ragcraft/storage/cache.py",
            "ragcraft/retrieval/retriever.py",
            "ragcraft/config.py",
            "tests/test_retriever.py"
        ],
        "expected_components": [
            "RedisCache",
            "SemanticRetriever",
            "CacheConfig",
            "test_retriever_query_caching"
        ],
        "reference_answer": "Removing Redis caching impacts SemanticRetriever by eliminating cache checks, rendering CacheConfig redundant, increasing latency on repeated queries, and breaking test_retriever_query_caching."
    },
    {
        "id": "q5_test_coverage_pipeline",
        "category": "Testing",
        "question": "Which tests should be updated if RAGPipeline.run() signature is modified?",
        "expected_files": [
            "ragcraft/pipeline/rag_pipeline.py",
            "tests/test_pipeline.py",
            "ragcraft/api/server.py"
        ],
        "expected_components": [
            "RAGPipeline",
            "test_pipeline_run",
            "handle_query"
        ],
        "reference_answer": "Modifying RAGPipeline.run() directly affects tests/test_pipeline.py (specifically test_pipeline_run) and the API handler handle_query in ragcraft/api/server.py."
    }
]


def generate_ast_ground_truth_dataset(
    graph: Any,
    max_questions: int = 5
) -> List[Dict[str, Any]]:
    """Synthesize 100% deterministic Ground Truth benchmark items directly from code AST.

    Instead of relying on an LLM to predict/hallucinate questions or answers (circular evaluation),
    this function directly inspects the compiler-extracted AST graph:
      - Targets real architectural entities (Classes, Functions, Methods).
      - Extracts mathematically verified callers (CALLS, IMPORTS, DEPENDS_ON) as Ground Truth.
      - Extracts verified test cases (TESTS edges) as Ground Truth.
      - Assembles precise reference answers and expected file sets.

    Works dynamically on ANY repository without manual annotation.
    """
    if graph is None or getattr(graph, "number_of_nodes", lambda: 0)() == 0:
        return BENCHMARK_DATASET[:max_questions]

    candidates = []
    for nid, data in graph.nodes(data=True):
        ntype = data.get("type", "")
        name = data.get("name", nid)
        fpath = data.get("file_path", "")
        if ntype in ("Class", "Function", "Method", "AsyncFunction") and fpath:
            callers = []
            tests = []
            for pred in graph.predecessors(nid):
                edge_data = graph.get_edge_data(pred, nid, {}) or {}
                rel = edge_data.get("relation", "")
                pred_data = graph.nodes.get(pred, {})
                p_name = pred_data.get("name", pred)
                p_type = pred_data.get("type", "")
                p_file = pred_data.get("file_path", "")
                if rel == "TESTS" or p_type == "Test" or "test" in (p_file or "").lower():
                    tests.append((p_name, p_file))
                elif rel in ("CALLS", "IMPORTS", "DEPENDS_ON", "IMPLEMENTS", "INHERITS"):
                    callers.append((p_name, p_file))

            # Score by architectural centrality and test linkage
            score = len(callers) * 2 + len(tests) * 3
            if callers or tests or graph.out_degree(nid) > 1:
                candidates.append({
                    "id": nid,
                    "name": name,
                    "type": ntype,
                    "file_path": fpath,
                    "callers": callers,
                    "tests": tests,
                    "score": score
                })

    candidates.sort(key=lambda x: x["score"], reverse=True)

    if not candidates:
        return BENCHMARK_DATASET[:max_questions]

    generated_items: List[Dict[str, Any]] = []
    for i, c in enumerate(candidates[:max_questions]):
        c_name = c["name"]
        c_file = c["file_path"]
        c_type = c["type"]
        c_callers = c["callers"]
        c_tests = c["tests"]

        caller_names = list(dict.fromkeys(name for name, _ in c_callers if name))
        test_names = list(dict.fromkeys(name for name, _ in c_tests if name))

        # Files containing the subject, its callers, and its tests
        relevant_files = [c_file]
        for _, fp in c_callers + c_tests:
            if fp and fp not in relevant_files:
                relevant_files.append(fp)

        # Expected components
        expected_components = [c_name] + caller_names[:4] + test_names[:3]

        # Ground truth reference text
        callers_str = ", ".join(caller_names[:3]) if caller_names else "no direct callers"
        tests_str = ", ".join(test_names[:3]) if test_names else "no dedicated test suites"

        ref_answer = (
            f"Modifying {c_type.lower()} '{c_name}' in '{c_file}' directly impacts "
            f"{len(caller_names)} caller(s) ({callers_str}) and {len(test_names)} test case(s) ({tests_str}). "
            f"Any breaking signature changes will require updating call sites across {len(relevant_files)} related file(s)."
        )

        generated_items.append({
            "id": f"ast_gt_{i+1}_{c_name.lower()}",
            "category": "What-If (AST Ground Truth)",
            "question": f"If we modify {c_type.lower()} '{c_name}' in '{c_file}', which downstream callers and test suites are affected?",
            "expected_files": relevant_files,
            "expected_components": expected_components,
            "reference_answer": ref_answer,
            "is_ast_ground_truth": True,
            "target_entity": c_name,
            "target_file": c_file,
            "total_callers": len(caller_names),
            "total_tests": len(test_names)
        })

    return generated_items
