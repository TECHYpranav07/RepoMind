"""Comprehensive test suite for RepoMind end-to-end functionality."""
import sys
from pathlib import Path
import networkx as nx

# Add root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from repomind.ingestion.github_loader import LocalDirConnector, parse_repo_url
from repomind.ingestion.chunker import StructureAwareChunker, CodeChunk
from repomind.graph.entity_extractor import EntityExtractor
from repomind.graph.relationship_extractor import RelationshipExtractor
from repomind.graph.graph_builder import RepoGraphBuilder
from repomind.graph.graph_retriever import GraphRetriever
from repomind.retrieval.embeddings import FastDenseEmbeddingEngine
from repomind.retrieval.vector_store import FAISSVectorStore
from repomind.retrieval.hybrid_retriever import HybridRetriever
from repomind.retrieval.context_builder import ContextBuilder
from repomind.analysis.change_parser import ChangeParser
from repomind.analysis.impact_analyzer import ImpactAnalyzer
from repomind.analysis.report_generator import WhatIfReportCoordinator
from repomind.evaluation.metrics import EvaluationMetrics
from repomind.evaluation.benchmark import BenchmarkRunner
from repomind.frontend.graph_visualizer import GraphVisualizer
from repomind.config import SAMPLE_REPO_DIR


def test_url_parser():
    owner, repo, is_local = parse_repo_url("https://github.com/facebookresearch/faiss")
    assert owner == "facebookresearch"
    assert repo == "faiss"
    assert not is_local

    owner2, repo2, is_local2 = parse_repo_url("sample_repo")
    assert is_local2
    assert repo2 == "ragcraft"


def test_ingestion_and_chunker():
    connector = LocalDirConnector(SAMPLE_REPO_DIR)
    meta = connector.fetch_metadata("local", "ragcraft")
    files = connector.fetch_repository_files("local", "ragcraft")

    assert len(files) >= 5
    file_names = [f.name for f in files]
    assert "README.md" in file_names
    assert "vector_store.py" in file_names

    chunker = StructureAwareChunker()
    chunks = chunker.chunk_repository(files)
    assert len(chunks) > 0
    # Verify entity names and lines
    has_class_chunk = any(c.chunk_type == "class" and "FAISSVectorStore" in (c.entity_name or "") for c in chunks)
    assert has_class_chunk


def test_knowledge_graph_construction():
    connector = LocalDirConnector(SAMPLE_REPO_DIR)
    meta = connector.fetch_metadata("local", "ragcraft")
    files = connector.fetch_repository_files("local", "ragcraft")

    nodes = EntityExtractor.extract_entities(meta, files)
    edges = RelationshipExtractor.extract_relationships(meta, files, nodes)

    assert len(nodes) > 10
    assert len(edges) > 10

    builder = RepoGraphBuilder()
    graph = builder.build(nodes, edges)

    assert graph.number_of_nodes() == len(nodes)
    assert graph.number_of_edges() > 0
    assert graph.number_of_edges() <= len(edges)

    stats = builder.get_statistics()
    assert stats["total_nodes"] > 0
    assert "Class" in stats["node_type_breakdown"]
    assert "CALLS" in stats["edge_relation_breakdown"] or "IMPORTS" in stats["edge_relation_breakdown"]


def test_vector_store_and_embeddings():
    connector = LocalDirConnector(SAMPLE_REPO_DIR)
    meta = connector.fetch_metadata("local", "ragcraft")
    files = connector.fetch_repository_files("local", "ragcraft")

    chunker = StructureAwareChunker()
    chunks = chunker.chunk_repository(files)

    embed_engine = FastDenseEmbeddingEngine(dimension=128)
    embeddings = embed_engine.fit_and_embed([c.content for c in chunks])

    assert embeddings.shape[0] == len(chunks)
    assert embeddings.shape[1] == 128

    store = FAISSVectorStore(dimension=128)
    store.add_chunks(chunks, embeddings)

    q_vec = embed_engine.embed_query("FAISS vector storage")
    results = store.search(q_vec, top_k=3)
    assert len(results) == 3
    assert results[0][1] >= 0.0  # Cosine score


def test_hybrid_retriever_modes():
    connector = LocalDirConnector(SAMPLE_REPO_DIR)
    meta = connector.fetch_metadata("local", "ragcraft")
    files = connector.fetch_repository_files("local", "ragcraft")

    chunker = StructureAwareChunker()
    chunks = chunker.chunk_repository(files)

    embed_engine = FastDenseEmbeddingEngine(dimension=128)
    embeddings = embed_engine.fit_and_embed([c.content for c in chunks])

    store = FAISSVectorStore(dimension=128)
    store.add_chunks(chunks, embeddings)

    nodes = EntityExtractor.extract_entities(meta, files)
    edges = RelationshipExtractor.extract_relationships(meta, files, nodes)
    graph = RepoGraphBuilder().build(nodes, edges)

    retriever = HybridRetriever(store, embed_engine, graph)

    # Test Vector Mode
    v_res = retriever.retrieve("FAISS vector store", mode="vector", top_k=3)
    assert v_res["mode"] == "vector"
    assert len(v_res["vector_chunks"]) == 3

    # Test Graph Mode
    g_res = retriever.retrieve("SemanticRetriever", mode="graph", top_k=3)
    assert g_res["mode"] == "graph"
    assert len(g_res["graph_paths"]) >= 0

    # Test Hybrid Mode
    h_res = retriever.retrieve("What does SemanticRetriever call?", mode="hybrid", top_k=3)
    assert h_res["mode"] == "hybrid"
    assert "prompt_context" in h_res


def test_whatif_change_parser_and_impact():
    connector = LocalDirConnector(SAMPLE_REPO_DIR)
    meta = connector.fetch_metadata("local", "ragcraft")
    files = connector.fetch_repository_files("local", "ragcraft")

    nodes = EntityExtractor.extract_entities(meta, files)
    edges = RelationshipExtractor.extract_relationships(meta, files, nodes)
    graph = RepoGraphBuilder().build(nodes, edges)

    # Parse change
    parsed = ChangeParser.parse("What if we replace FAISS with ChromaDB?", graph)
    assert parsed.action == "replace"
    assert parsed.target_entity.lower() == "faiss"
    assert parsed.replacement_entity.lower() == "chromadb"
    assert len(parsed.target_node_ids) > 0

    # Impact Analyzer
    analyzer = ImpactAnalyzer(graph)
    impact = analyzer.analyze(parsed, max_depth=2)

    assert len(impact.target_nodes) > 0
    assert len(impact.direct_affected) > 0 or len(impact.tests_to_update) > 0
    assert impact.risk_level in ("Low", "Medium", "High")


def test_whatif_redis_caching_impact():
    """Verify that 'What if we remove Redis caching?' correctly resolves RedisCache and its callers."""
    connector = LocalDirConnector(SAMPLE_REPO_DIR)
    meta = connector.fetch_metadata("local", "ragcraft")
    files = connector.fetch_repository_files("local", "ragcraft")

    nodes = EntityExtractor.extract_entities(meta, files)
    edges = RelationshipExtractor.extract_relationships(meta, files, nodes)
    graph = RepoGraphBuilder().build(nodes, edges)

    parsed = ChangeParser.parse("What if we remove Redis caching?", graph)
    assert parsed.action == "remove"
    assert "redis" in parsed.target_entity.lower()
    # Must match RedisCache class or functions
    matched_names = [graph.nodes[nid].get("name", "") for nid in parsed.target_node_ids]
    assert any("RedisCache" in name or "redis" in name for name in matched_names)

    analyzer = ImpactAnalyzer(graph)
    impact = analyzer.analyze(parsed, max_depth=3)

    # Directly affected or inferred must include SemanticRetriever
    all_affected = [n["name"] for n in impact.direct_affected + impact.inferred_affected]
    assert any("SemanticRetriever" in a for a in all_affected)
    # Tests to update should detect test_retriever
    test_names = [n["name"] for n in impact.tests_to_update]
    assert any("test_retriever" in t for t in test_names)


def test_whatif_end_to_end_report():
    connector = LocalDirConnector(SAMPLE_REPO_DIR)
    meta = connector.fetch_metadata("local", "ragcraft")
    files = connector.fetch_repository_files("local", "ragcraft")

    chunker = StructureAwareChunker()
    chunks = chunker.chunk_repository(files)
    embed_engine = FastDenseEmbeddingEngine(dimension=128)
    embeddings = embed_engine.fit_and_embed([c.content for c in chunks])
    store = FAISSVectorStore(dimension=128)
    store.add_chunks(chunks, embeddings)

    nodes = EntityExtractor.extract_entities(meta, files)
    edges = RelationshipExtractor.extract_relationships(meta, files, nodes)
    graph = RepoGraphBuilder().build(nodes, edges)

    retriever = HybridRetriever(store, embed_engine, graph)
    coordinator = WhatIfReportCoordinator(graph, retriever)

    report_res = coordinator.run_analysis("What if we replace FAISS with ChromaDB?")
    assert "hypothesis" in report_res
    assert "report_markdown" in report_res
    assert "Potentially Affected Components" in report_res["report_markdown"]
    assert "Testing Recommendations" in report_res["report_markdown"]

    md_export = coordinator.export_report_markdown(report_res)
    assert "# RepoMind What-If Impact Report" in md_export


def test_context_builder_unique_citations():
    """Verify that citations generated by ContextBuilder have distinct, monotonically increasing IDs."""
    chunk = CodeChunk(
        chunk_id="chunk_1",
        file_path="ragcraft/storage/vector_store.py",
        content="def search(): pass",
        start_line=1,
        end_line=5,
        chunk_type="function",
        entity_name="search"
    )
    graph_evidence = {
        "nodes": [
            {
                "id": "node_1",
                "file_path": "ragcraft/config.py",
                "name": "Config",
                "line_number": 1,
                "end_line": 10,
                "source_snippet": "class Config: pass"
            }
        ],
        "paths": ["NodeA --[CALLS]--> NodeB"]
    }
    ctx = ContextBuilder.build_context([(chunk, 0.9)], graph_evidence)
    citations = ctx["citations"]
    ids = [c["id"] for c in citations]
    assert len(ids) == len(set(ids)), f"Duplicate citation IDs found: {ids}"
    assert len(ids) == 2
    assert ids == [1, 2]


def test_evaluation_metrics_and_benchmark():
    p = EvaluationMetrics.retrieval_precision_at_k(
        ["ragcraft/storage/vector_store.py", "other.py"],
        ["ragcraft/storage/vector_store.py"],
        k=2
    )
    assert p == 0.5

    r = EvaluationMetrics.retrieval_recall_at_k(
        ["ragcraft/storage/vector_store.py"],
        ["ragcraft/storage/vector_store.py", "ragcraft/config.py"],
        k=2
    )
    assert r == 0.5

    # Empty expected -> None (unannotated)
    r_empty = EvaluationMetrics.retrieval_recall_at_k(["a.py"], [], k=2)
    assert r_empty is None

    # Empty predicted -> 0.0
    r_zero = EvaluationMetrics.retrieval_recall_at_k([], ["a.py"], k=2)
    assert r_zero == 0.0

    f1_comp = EvaluationMetrics.component_overlap(["FAISSVectorStore"], ["FAISSVectorStore"])
    assert f1_comp["f1"] == 1.0
    assert not f1_comp["unannotated"]


def test_pyvis_in_memory_html():
    """Verify that PyVis HTML generation works in-memory without error."""
    g = nx.DiGraph()
    g.add_node("A", name="NodeA", type="Class", file_path="a.py", line_number=1)
    g.add_node("B", name="NodeB", type="Function", file_path="b.py", line_number=10)
    g.add_edge("A", "B", relation="CALLS")

    html = GraphVisualizer.render_pyvis_html(g)
    assert "<html" in html.lower() or "<div" in html.lower()
    assert len(html) > 50


def test_ast_ground_truth_dataset_synthesis():
    """Verify that deterministic ground truth is automatically generated from AST."""
    from repomind.evaluation.dataset import generate_ast_ground_truth_dataset
    
    g = nx.DiGraph()
    # Add a target class
    g.add_node("auth_service", name="AuthService", type="Class", file_path="auth.py", line_number=10)
    # Add caller function
    g.add_node("login_handler", name="login_handler", type="Function", file_path="api.py", line_number=25)
    g.add_edge("login_handler", "auth_service", relation="CALLS")
    # Add test case
    g.add_node("test_login", name="test_login_success", type="Test", file_path="test_auth.py", line_number=5)
    g.add_edge("test_login", "auth_service", relation="TESTS")

    gt_items = generate_ast_ground_truth_dataset(g, max_questions=3)
    assert len(gt_items) > 0
    item = gt_items[0]
    assert "AuthService" in item["question"]
    assert "auth.py" in item["expected_files"]
    assert "api.py" in item["expected_files"]
    assert "test_auth.py" in item["expected_files"]
    assert "AuthService" in item["expected_components"]
    assert "login_handler" in item["expected_components"]
    assert item["is_ast_ground_truth"] is True
    assert len(item["reference_answer"]) > 20


if __name__ == "__main__":
    tests = [
        test_url_parser,
        test_ingestion_and_chunker,
        test_knowledge_graph_construction,
        test_vector_store_and_embeddings,
        test_hybrid_retriever_modes,
        test_whatif_change_parser_and_impact,
        test_whatif_redis_caching_impact,
        test_whatif_end_to_end_report,
        test_context_builder_unique_citations,
        test_evaluation_metrics_and_benchmark,
        test_pyvis_in_memory_html,
        test_ast_ground_truth_dataset_synthesis
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except Exception as e:
            print(f"FAIL: {t.__name__} -> {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\nTest Summary: {len(tests) - failed}/{len(tests)} passed.")
    if failed:
        sys.exit(1)
