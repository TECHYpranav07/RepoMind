"""RepoMind - Explainable GraphRAG for Software Repository What-If Analysis.

Main Streamlit Application Entrypoint.
"""
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import streamlit as st

# Configure Streamlit page settings
st.set_page_config(
    page_title="RepoMind — Explainable GraphRAG",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
css_path = root_dir / "repomind" / "frontend" / "styles.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Import Frontend Pages
from repomind.frontend.dashboard import render_dashboard, _run_ingestion_pipeline
from repomind.frontend.repository_explorer import render_repository_explorer
from repomind.frontend.chat import render_chat
from repomind.frontend.whatif import render_whatif
from repomind.frontend.evaluation import render_evaluation

# Auto-initialize with sample repo if nothing is loaded yet
if "repo_loaded" not in st.session_state:
    try:
        _run_ingestion_pipeline("sample_repo")
    except Exception as e:
        st.session_state["repo_loaded"] = False

# Sidebar Navigation
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding:12px 0 18px 0;">
            <h2 style="margin:0; font-size:1.6rem; font-weight:800; background:linear-gradient(90deg, #60a5fa, #a78bfa); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                🧠 RepoMind
            </h2>
            <p style="color:#94a3b8; font-size:0.8rem; margin:4px 0 0 0;">Explainable GraphRAG Platform</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    nav_selection = st.radio(
        "Navigation:",
        options=[
            "🏠 Home / Dashboard",
            "🔍 Repository Explorer",
            "💬 Repository Chat",
            "🔮 What-If Analysis",
            "📈 Evaluation & Benchmark"
        ],
        index=0
    )

    st.markdown("---")
    if st.session_state.get("repo_loaded", False):
        meta = st.session_state.get("repo_meta")
        graph = st.session_state.get("graph")
        chunks = st.session_state.get("repo_chunks", [])
        st.markdown(f"**Loaded Repo:** `{meta.name}`")
        st.caption(f"📊 Nodes: `{graph.number_of_nodes()}` | Chunks: `{len(chunks)}`")
    else:
        st.caption("No repository loaded.")

    st.markdown("---")
    st.markdown(
        """
        <div style="font-size:0.75rem; color:#64748b; line-height:1.4;">
            <b>RepoMind GraphRAG v1.0</b><br>
            Powered by NetworkX AST, FAISS, & Multi-Modal LLM reasoning.
        </div>
        """,
        unsafe_allow_html=True
    )

# Route to selected page
if nav_selection == "🏠 Home / Dashboard":
    render_dashboard()
elif nav_selection == "🔍 Repository Explorer":
    render_repository_explorer()
elif nav_selection == "💬 Repository Chat":
    render_chat()
elif nav_selection == "🔮 What-If Analysis":
    render_whatif()
elif nav_selection == "📈 Evaluation & Benchmark":
    render_evaluation()
