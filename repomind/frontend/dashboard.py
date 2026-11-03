"""Page 1: Home / Repository Dashboard."""
import os
import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional

from repomind.config import SAMPLE_REPO_DIR, REPOSITORIES_DIR
from repomind.ingestion.github_loader import get_connector_for_target, parse_repo_url
from repomind.ingestion.chunker import StructureAwareChunker
from repomind.graph.entity_extractor import EntityExtractor
from repomind.graph.relationship_extractor import RelationshipExtractor
from repomind.graph.graph_builder import RepoGraphBuilder
from repomind.retrieval.embeddings import get_embedding_engine
from repomind.retrieval.vector_store import FAISSVectorStore
from repomind.retrieval.hybrid_retriever import HybridRetriever
from repomind.llm.answer_generator import AnswerGenerator


def render_dashboard():
    """Render repository ingestion and statistics dashboard."""
    st.markdown(
        """
        <div class="repomind-header">
            <h1 class="repomind-title">🧠 RepoMind</h1>
            <p class="repomind-subtitle">Explainable GraphRAG for Software Repository What-If Change-Impact Analysis</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_main, col_sidebar = st.columns([2.2, 1])

    with col_main:
        st.markdown("### 📥 Ingest Repository")
        st.write("Enter a public GitHub repository URL or click to explore the built-in reference architecture.")

        repo_input = st.text_input(
            "GitHub Repository URL or Shorthand (e.g. `owner/repo`):",
            value="sample_repo",
            placeholder="https://github.com/owner/repo or owner/repo or sample_repo"
        )

        col_btn1, col_btn2 = st.columns([1, 1.2])
        with col_btn1:
            analyze_clicked = st.button("🚀 Analyze Repository", type="primary", use_container_width=True)
        with col_btn2:
            sample_clicked = st.button("⚡ Load Built-in RagCraft Repo", use_container_width=True)

        if sample_clicked:
            repo_input = "sample_repo"
            analyze_clicked = True

        if analyze_clicked and repo_input:
            _run_ingestion_pipeline(repo_input.strip())

    with col_sidebar:
        st.markdown("### ⚙️ Engine Status")
        is_loaded = st.session_state.get("repo_loaded", False)
        if is_loaded:
            meta = st.session_state.get("repo_meta")
            st.success(f"Active: **{meta.full_name}**")
            st.info(f"🌿 Branch: `{meta.default_branch}` | 🌟 Stars: `{meta.stars}`")
        else:
            st.warning("No repository currently loaded in memory.")

        st.markdown("---")
        st.markdown("### 🏷️ Supported Formats")
        st.markdown(
            """
            - <span class="badge-pill badge-indigo">Python AST (.py)</span>
            - <span class="badge-pill badge-cyan">Markdown Docs (.md)</span>
            - <span class="badge-pill badge-emerald">Dependencies (.txt, .toml)</span>
            - <span class="badge-pill badge-amber">Configurations (.yaml, .cfg)</span>
            """,
            unsafe_allow_html=True
        )

    # If repo loaded, show statistics
    if st.session_state.get("repo_loaded", False):
        st.markdown("---")
        _render_repository_stats()


def _run_ingestion_pipeline(target: str):
    """Execute complete ingestion, AST parsing, Graph construction, and Vector indexing."""
    progress_bar = st.progress(0.0)
    status_text = st.empty()

    try:
        status_text.text("Connecting to repository source...")
        connector, owner, repo = get_connector_for_target(target)

        # 1. Fetch metadata
        meta = connector.fetch_metadata(owner, repo)
        status_text.text(f"Fetched metadata for {meta.full_name}")
        progress_bar.progress(0.2)

        # 2. Fetch files
        def progress_cb(msg: str, pct: float):
            status_text.text(msg)
            progress_bar.progress(0.2 + 0.4 * pct)

        files = connector.fetch_repository_files(owner, repo, progress_callback=progress_cb)
        status_text.text(f"Ingested {len(files)} files. Chunking...")
        progress_bar.progress(0.6)

        # 3. Structure-aware chunking
        chunker = StructureAwareChunker()
        chunks = chunker.chunk_repository(files)
        status_text.text(f"Generated {len(chunks)} semantic chunks. Extracting Knowledge Graph...")
        progress_bar.progress(0.7)

        # 4. Extract Entities and Relationships
        nodes = EntityExtractor.extract_entities(meta, files)
        edges = RelationshipExtractor.extract_relationships(meta, files, nodes)

        graph_builder = RepoGraphBuilder()
        graph = graph_builder.build(nodes, edges)
        status_text.text(f"Constructed Knowledge Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges.")
        progress_bar.progress(0.8)

        # 5. Build Vector Store
        status_text.text("Generating vector embeddings and building FAISS index...")
        embed_engine = get_embedding_engine()
        chunk_texts = [c.content for c in chunks]
        embeddings = embed_engine.fit_and_embed(chunk_texts) if hasattr(embed_engine, "fit_and_embed") else embed_engine.embed_texts(chunk_texts)

        vector_store = FAISSVectorStore(dimension=embed_engine.dimension)
        vector_store.add_chunks(chunks, embeddings)
        progress_bar.progress(0.95)

        # 6. Initialize Hybrid Retriever
        hybrid_retriever = HybridRetriever(vector_store, embed_engine, graph)

        # Save into session state
        st.session_state["repo_loaded"] = True
        st.session_state["repo_meta"] = meta
        st.session_state["repo_files"] = files
        st.session_state["repo_chunks"] = chunks
        st.session_state["graph_nodes"] = nodes
        st.session_state["graph_edges"] = edges
        st.session_state["graph"] = graph
        st.session_state["graph_builder"] = graph_builder
        st.session_state["vector_store"] = vector_store
        st.session_state["embed_engine"] = embed_engine
        st.session_state["hybrid_retriever"] = hybrid_retriever
        st.session_state["answer_generator"] = AnswerGenerator()

        progress_bar.progress(1.0)
        status_text.text("Repository successfully analyzed and indexed!")
        st.success(f"Successfully processed **{meta.full_name}** with {len(files)} files, {len(chunks)} chunks, and {graph.number_of_nodes()} graph entities!")

    except Exception as e:
        st.error(f"Ingestion Error: {str(e)}")
        progress_bar.empty()
        status_text.empty()


def _render_repository_stats():
    """Render structural metrics cards for active repository."""
    meta = st.session_state.get("repo_meta")
    files = st.session_state.get("repo_files", [])
    chunks = st.session_state.get("repo_chunks", [])
    graph = st.session_state.get("graph")
    graph_builder = st.session_state.get("graph_builder")
    stats = graph_builder.get_statistics() if graph_builder else {}

    st.markdown("### 📊 Repository Architecture Metrics")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-val">{len(files)}</div>
                <div class="stat-label">Indexed Files</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-val">{len(chunks)}</div>
                <div class="stat-label">Vector Chunks</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-val">{graph.number_of_nodes() if graph else 0}</div>
                <div class="stat-label">Graph Nodes</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-val">{graph.number_of_edges() if graph else 0}</div>
                <div class="stat-label">Graph Edges</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c5:
        total_loc = sum(f.line_count for f in files)
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-val">{total_loc}</div>
                <div class="stat-label">Lines of Code</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    col_breakdown1, col_breakdown2 = st.columns(2)

    with col_breakdown1:
        st.markdown("#### 🧩 Entity Breakdown")
        node_counts = stats.get("node_type_breakdown", {})
        if node_counts:
            for ntype, count in node_counts.items():
                st.write(f"- **{ntype}**: {count}")
        else:
            st.write("No entity breakdown available.")

    with col_breakdown2:
        st.markdown("#### 🔗 Relationship Breakdown")
        edge_counts = stats.get("edge_relation_breakdown", {})
        if edge_counts:
            for rel, count in edge_counts.items():
                st.write(f"- **{rel}**: {count}")
        else:
            st.write("No relationship breakdown available.")
