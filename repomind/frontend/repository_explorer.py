"""Page 2: Repository Explorer with Simplified Architecture and Unified Insights."""
import streamlit as st
import streamlit.components.v1 as components
from repomind.frontend.graph_visualizer import GraphVisualizer


def render_repository_explorer():
    """Render interactive knowledge graph and unified codebase insights."""
    if not st.session_state.get("repo_loaded", False):
        st.warning("⚠️ No repository loaded. Please go to the **Home / Dashboard** page and ingest a repository first.")
        return

    meta = st.session_state.get("repo_meta")
    files = st.session_state.get("repo_files", [])
    graph = st.session_state.get("graph")
    graph_builder = st.session_state.get("graph_builder")
    stats = graph_builder.get_statistics() if graph_builder else {}

    st.markdown(f"## 🔍 Repository Explorer: `{meta.full_name}`")
    st.caption("Explore interactive component call-graphs, architectural hubs, dependencies, and source files.")

    tab_graph, tab_codebase = st.tabs([
        "🕸️ Interactive Architecture Graph",
        "📁 Codebase & Architectural Overview"
    ])

    # 1. Interactive Knowledge Graph Tab (PyVis only)
    with tab_graph:
        st.markdown("### 🌐 Software Architecture Knowledge Graph")
        st.write("Drag, zoom, and explore component dependencies, class hierarchies, function calls, and import bindings.")

        # Entity type filter
        available_types = list(stats.get("node_type_breakdown", {}).keys())
        selected_types = st.multiselect(
            "Filter Visible Entity Types:",
            options=available_types,
            default=available_types[:6] if len(available_types) >= 6 else available_types,
            help="Filter which nodes appear in the physics graph."
        )

        html_graph = GraphVisualizer.render_pyvis_html(
            graph,
            height="580px",
            selected_node_types=selected_types
        )
        components.html(html_graph, height=600, scrolling=False)

        # Node Details Inspector
        st.markdown("---")
        st.markdown("#### 🔬 Inspect Entity Details")
        all_node_ids = sorted(list(graph.nodes()))
        selected_node_id = st.selectbox("Select Graph Entity to Inspect:", options=all_node_ids)

        if selected_node_id and selected_node_id in graph:
            node_data = graph.nodes[selected_node_id]
            col_d1, col_d2 = st.columns([1, 1.8])
            with col_d1:
                st.markdown(f"**Entity Name:** `{node_data.get('name')}`")
                st.markdown(f"**Type:** `{node_data.get('type')}`")
                st.markdown(f"**File Location:** `{node_data.get('file_path')}` (Line {node_data.get('line_number') or 1})")
                in_deg = graph.in_degree(selected_node_id)
                out_deg = graph.out_degree(selected_node_id)
                st.markdown(f"**In-Degree (Incoming Callers):** `{in_deg}`")
                st.markdown(f"**Out-Degree (Outgoing Dependencies):** `{out_deg}`")

            with col_d2:
                doc = node_data.get("docstring")
                if doc:
                    st.markdown("**Docstring:**")
                    st.info(doc)

                snippet = node_data.get("source_snippet")
                if snippet:
                    st.markdown("**Source Code Snippet:**")
                    st.code(snippet, language="python")

    # 2. Unified Codebase & Architectural Overview Tab (Merges Hubs, Dependencies & Files)
    with tab_codebase:
        st.markdown("### 🏛️ Architecture & Codebase Inventory")
        st.write("A unified summary of central architectural hubs, external package dependencies, and repository source code.")

        # Top row: Hubs & Dependencies side-by-side
        col_hubs, col_deps = st.columns(2)

        with col_hubs:
            st.markdown("#### 🏛️ Top Architectural Hubs")
            st.caption("Most connected classes and functions across the repository.")
            hubs = stats.get("top_hubs", [])
            if hubs:
                hub_rows = [
                    {
                        "Component": h.get("name", ""),
                        "Type": h.get("type", ""),
                        "Callers (In)": h.get("in_degree", 0),
                        "Calls (Out)": h.get("out_degree", 0)
                    }
                    for h in hubs
                ]
                st.dataframe(hub_rows, use_container_width=True, hide_index=True)
            else:
                st.info("No architectural hubs detected.")

        with col_deps:
            st.markdown("#### 📦 Detected Third-Party Packages")
            st.caption("Libraries extracted from requirements and project manifests.")
            lib_nodes = [data for _, data in graph.nodes(data=True) if data.get("type") == "Library"]
            if lib_nodes:
                dep_rows = [
                    {
                        "Package": lib.get("name", ""),
                        "Specifier": lib.get("metadata", {}).get("specifier", "any"),
                        "Source": lib.get("metadata", {}).get("source_file", "requirements.txt")
                    }
                    for lib in lib_nodes
                ]
                st.dataframe(dep_rows, use_container_width=True, hide_index=True)
            else:
                st.info("No external dependencies detected.")

        st.markdown("---")

        # Bottom row: File Browser & Source Code
        st.markdown("#### 📄 Source Code & Documentation Browser")
        if files:
            file_paths = [f.path for f in files]
            chosen_path = st.selectbox("Select File to View:", options=file_paths)
            matched_file = next((f for f in files if f.path == chosen_path), None)

            if matched_file:
                c_f1, c_f2, c_f3 = st.columns(3)
                c_f1.metric("File Type", matched_file.file_type.upper())
                c_f2.metric("Size", f"{matched_file.size_bytes:,} bytes")
                c_f3.metric("Line Count", matched_file.line_count)

                lang = "python" if matched_file.extension == ".py" else ("markdown" if matched_file.extension == ".md" else "text")
                st.code(matched_file.content, language=lang, line_numbers=True)
        else:
            st.info("No files available.")
