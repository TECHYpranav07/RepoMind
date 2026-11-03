"""Comprehensive test suite for RepoMind end-to-end functionality."""
import sys
from pathlib import Path
import pytest
import networkx as nx

# Add root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from repomind.ingestion.github_loader import LocalDirConnector, parse_repo_url
from repomind.ingestion.chunker import StructureAwareChunker
from repomind.graph.entity_extractor import EntityExtractor
from repomind.graph.relationship_extractor import RelationshipExtractor
from repomind.graph.graph_builder import RepoGraphBuilder
from repomind.graph.graph_retriever import GraphRetriever
from repomind.retrieval.embeddings import FastDenseEmbeddingEngine
from repomind.retrieval.vector_store import FAISSVectorStore
from repomind.retrieval.hybrid_retriever import HybridRetriever
from repomind.analysis.change_parser import ChangeParser
from repomind.analysis.impact_analyzer import ImpactAnalyzer
from repomind.analysis.report_generator import WhatIfReportCoordinator
from repomind.evaluation.metrics import EvaluationMetrics
from repomind.evaluation.benchmark import BenchmarkRunner
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
    # FAISSVectorStore or faiss lib is connected to SemanticRetriever or test_retriever
    assert len(impact.direct_affected) > 0 or len(impact.tests_to_update) > 0
    assert impact.risk_level in ("Low", "Medium", "High")


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

    f1_comp = EvaluationMetrics.component_overlap(["FAISSVectorStore"], ["FAISSVectorStore"])
    assert f1_comp["f1"] == 1.0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
