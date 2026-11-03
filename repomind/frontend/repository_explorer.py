"""Page 2: Repository Explorer."""
import streamlit as st
import streamlit.components.v1 as components
from repomind.frontend.graph_visualizer import GraphVisualizer, NODE_COLORS


def render_repository_explorer():
    """Render repository code tree, dependency inspector, and interactive knowledge graph."""
    if not st.session_state.get("repo_loaded", False):
        st.warning("⚠️ No repository loaded. Please go to the **Home / Dashboard** page and ingest a repository first.")
        return

    meta = st.session_state.get("repo_meta")
    files = st.session_state.get("repo_files", [])
    graph = st.session_state.get("graph")
    graph_builder = st.session_state.get("graph_builder")
    stats = graph_builder.get_statistics() if graph_builder else {}

    st.markdown(f"## 🔍 Repository Explorer: `{meta.full_name}`")

    tab_graph, tab_files, tab_deps, tab_hubs = st.tabs([
        "🕸️ Interactive Knowledge Graph",
        "📁 File Browser & Source Code",
        "📦 Detected Dependencies",
        "🏛️ Central Architectural Hubs"
    ])

    # 1. Interactive Knowledge Graph Tab
    with tab_graph:
        st.markdown("### 🌐 Software Architecture Knowledge Graph")
        st.write("Explore component dependencies, class hierarchies, function calls, and import bindings.")

        # Filters
        available_types = list(stats.get("node_type_breakdown", {}).keys())
        c_filt1, c_filt2 = st.columns([3, 1])

        with c_filt1:
            selected_types = st.multiselect(
                "Filter by Entity Type:",
                options=available_types,
                default=available_types[:6] if len(available_types) >= 6 else available_types
            )

        with c_filt2:
            view_mode = st.radio("Viewer Engine:", ["Interactive PyVis (Physics)", "Plotly 2D Network"], horizontal=True)

        if view_mode == "Interactive PyVis (Physics)":
            html_graph = GraphVisualizer.render_pyvis_html(
                graph,
                height="600px",
                selected_node_types=selected_types
            )
            components.html(html_graph, height=620, scrolling=False)
        else:
            fig = GraphVisualizer.render_plotly_figure(
                graph.subgraph([n for n, d in graph.nodes(data=True) if d.get("type") in selected_types]),
                title=f"Architecture Topology ({len(selected_types)} Types Filtered)"
            )
            st.plotly_chart(fig, use_container_width=True)

        # Node Details Inspector
        st.markdown("#### 🔬 Inspect Entity Details")
        all_node_ids = sorted(list(graph.nodes()))
        selected_node_id = st.selectbox("Select Graph Entity to Inspect:", options=all_node_ids)

        if selected_node_id and selected_node_id in graph:
            node_data = graph.nodes[selected_node_id]
            col_d1, col_d2 = st.columns([1, 2])
            with col_d1:
                st.markdown(f"**Entity Name:** `{node_data.get('name')}`")
                st.markdown(f"**Type:** `{node_data.get('type')}`")
                st.markdown(f"**File Location:** `{node_data.get('file_path')}` (Line {node_data.get('line_number')})")
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

    # 2. File Browser Tab
    with tab_files:
        st.markdown("### 📂 Source Files & Documentation")
        if files:
            file_paths = [f.path for f in files]
            chosen_path = st.selectbox("Select File to View:", options=file_paths)
            matched_file = next((f for f in files if f.path == chosen_path), None)

            if matched_file:
                c_f1, c_f2, c_f3 = st.columns(3)
                c_f1.metric("File Type", matched_file.file_type.upper())
                c_f2.metric("Size (Bytes)", f"{matched_file.size_bytes:,}")
                c_f3.metric("Line Count", matched_file.line_count)

                lang = "python" if matched_file.extension == ".py" else ("markdown" if matched_file.extension == ".md" else "text")
                st.code(matched_file.content, language=lang, line_numbers=True)
        else:
            st.info("No files found.")

    # 3. Dependencies Tab
    with tab_deps:
        st.markdown("### 📦 Third-Party Libraries & Dependencies")
        lib_nodes = [data for _, data in graph.nodes(data=True) if data.get("type") == "Library"]
        if lib_nodes:
            dep_rows = []
            for lib in lib_nodes:
                name = lib.get("name", "")
                src = lib.get("metadata", {}).get("source_file", "requirements.txt")
                spec = lib.get("metadata", {}).get("specifier", "any")
                dep_rows.append({"Library Name": name, "Specifier": spec, "Discovered In": src})
            st.dataframe(dep_rows, use_container_width=True)
        else:
            st.info("No explicit third-party libraries detected in dependency manifests.")

    # 4. Central Hubs Tab
    with tab_hubs:
        st.markdown("### 🏛️ Most Connected Architectural Components")
        hubs = stats.get("top_hubs", [])
        if hubs:
            st.dataframe(hubs, use_container_width=True)
        else:
            st.info("No centrality statistics available.")
