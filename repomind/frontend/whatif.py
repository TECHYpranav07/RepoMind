"""Page 4: What-If Analysis Engine (Core Differentiator)."""
import json
import streamlit as st
import streamlit.components.v1 as components
from repomind.analysis.report_generator import WhatIfReportCoordinator
from repomind.frontend.graph_visualizer import GraphVisualizer


def render_whatif():
    """Render the Explainable What-If Analysis page."""
    if not st.session_state.get("repo_loaded", False):
        st.warning("⚠️ No repository loaded. Please go to the **Home / Dashboard** page and ingest a repository first.")
        return

    meta = st.session_state.get("repo_meta")
    graph = st.session_state.get("graph")
    hybrid_retriever = st.session_state.get("hybrid_retriever")
    answer_generator = st.session_state.get("answer_generator")

    st.markdown(f"## 🔮 Explainable What-If Change-Impact Analysis")
    st.markdown(
        f"Simulate hypothetical architectural refactorings, component replacements, removals, or upgrades on **`{meta.full_name}`** "
        f"using evidence-grounded dependency graph traversal."
    )

    # Preset Quick Scenarios
    scenarios = _get_quick_scenarios(meta, graph)
    st.markdown("##### ⚡ Quick Scenarios:")
    pcols = st.columns(len(scenarios))
    clicked_preset = None

    for i, (label, query_text) in enumerate(scenarios):
        with pcols[i]:
            if st.button(label, key=f"whatif_preset_{i}", use_container_width=True):
                clicked_preset = query_text

    # Update input value in session state if preset was clicked
    if clicked_preset:
        st.session_state["whatif_hypothesis_input"] = clicked_preset

    # Ensure default value exists
    if "whatif_hypothesis_input" not in st.session_state:
        st.session_state["whatif_hypothesis_input"] = "What if we replace FAISS with ChromaDB?"

    # Input Box with synchronized key
    hypothesis_input = st.text_input(
        "Enter a hypothetical software modification:",
        key="whatif_hypothesis_input",
        placeholder="e.g. What if we replace FAISS with ChromaDB? or What if we remove Redis caching?"
    )

    col_btn, col_depth = st.columns([1, 2])
    with col_btn:
        run_analysis_btn = st.button("🔍 Analyze Impact", type="primary", use_container_width=True)
    with col_depth:
        max_depth = st.slider("Upstream / Downstream Traversal Depth:", min_value=1, max_value=4, value=2)

    if run_analysis_btn and hypothesis_input:
        with st.spinner("Analyzing dependency graph neighborhood and generating explainable impact report..."):
            coordinator = WhatIfReportCoordinator(graph, hybrid_retriever, answer_generator)
            analysis_result = coordinator.run_analysis(hypothesis_input.strip(), max_depth=max_depth)
            st.session_state["last_whatif_result"] = analysis_result

    # Display Results if available
    if "last_whatif_result" in st.session_state:
        res = st.session_state["last_whatif_result"]
        _render_whatif_results(res, graph)


def _render_whatif_results(res: dict, full_graph):
    """Render the structured What-If report, impacted subgraph, and export options."""
    st.markdown("---")

    # Risk and Overview Banner
    risk = res.get("risk_level", "Medium")
    risk_color = "#f43f5e" if risk == "High" else ("#f59e0b" if risk == "Medium" else "#10b981")
    action = res.get("action", "MODIFY").upper()
    target = res.get("target_entity", "N/A")
    replacement = res.get("replacement_entity")
    action_text = f"{action} `{target}`" + (f" with `{replacement}`" if replacement else "")

    st.markdown(
        f"""
        <div style="background:#0f172a; border-left: 5px solid {risk_color}; border-radius: 8px; padding: 18px 22px; margin-bottom: 20px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="margin:0; color:#f8fafc;">Proposed Modification: {action_text}</h3>
                <span style="background:{risk_color}22; color:{risk_color}; border:1px solid {risk_color}; padding:4px 14px; border-radius:9999px; font-weight:700; font-size:0.85rem;">
                    {risk.upper()} RISK
                </span>
            </div>
            <p style="color:#94a3b8; margin:8px 0 0 0; font-size:0.95rem;">
                Evaluated across <b>{len(res.get('direct_affected', []))}</b> direct callers, 
                <b>{len(res.get('inferred_affected', []))}</b> transitive components, and 
                <b>{len(res.get('tests_to_update', []))}</b> relevant test suites.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_report, tab_subgraph, tab_affected, tab_paths, tab_export = st.tabs([
        "📄 Structured Impact Report",
        "🕸️ Impacted Subgraph",
        "🧩 Affected Component Inventory",
        "🔗 Dependency Reasoning Paths",
        "💾 Export & Download"
    ])

    # Tab 1: Structured Report
    with tab_report:
        st.markdown(res.get("report_markdown", "No report text generated."))

    # Tab 2: Interactive Impact Subgraph
    with tab_subgraph:
        st.markdown("### 🕸️ Interactive Impacted Subgraph Topology")
        st.markdown(
            """
            Legend:
            - <span style="color:#dc2626; font-weight:700;">● Red (Target Component)</span>
            - <span style="color:#ea580c; font-weight:700;">● Orange (Direct Caller / Importer)</span>
            - <span style="color:#ca8a04; font-weight:700;">● Amber (Inferred / Transitive Caller)</span>
            """,
            unsafe_allow_html=True
        )

        subgraph = res.get("impact_subgraph")
        target_ids = {t["id"] for t in res.get("target_nodes", [])}
        direct_ids = {d["id"] for d in res.get("direct_affected", [])}
        inferred_ids = {i["id"] for i in res.get("inferred_affected", [])}

        if subgraph and subgraph.number_of_nodes() > 0:
            html_sub = GraphVisualizer.render_pyvis_html(
                subgraph,
                height="550px",
                target_ids=target_ids,
                direct_ids=direct_ids,
                inferred_ids=inferred_ids
            )
            components.html(html_sub, height=570, scrolling=False)
        else:
            st.info("No connected subgraph nodes found for this entity.")

    # Tab 3: Affected Component Inventory
    with tab_affected:
        st.markdown("### 📋 Affected Components by Category")

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("#### ⚡ Directly Impacted Components (1-Hop)")
            direct = res.get("direct_affected", [])
            if direct:
                for d in direct:
                    st.markdown(f"- **{d['name']}** (`{d['type']}`): `{d['file_path']}:{d.get('line_number') or 1}`")
            else:
                st.write("None detected.")

            st.markdown("#### 🧪 Tests Requiring Updates")
            tests = res.get("tests_to_update", [])
            if tests:
                for t in tests:
                    st.markdown(f"- 🧪 **{t['name']}**: `{t['file_path']}:{t.get('line_number') or 1}`")
            else:
                st.write("No direct tests found covering this component.")

        with col_c2:
            st.markdown("#### 🌊 Inferred / Transitive Impacts (>1-Hop)")
            inferred = res.get("inferred_affected", [])
            if inferred:
                for inf in inferred:
                    st.markdown(f"- **{inf['name']}** (`{inf['type']}`): `{inf['file_path']}:{inf.get('line_number') or 1}`")
            else:
                st.write("None detected.")

            st.markdown("#### ⚙️ Configuration Files")
            configs = res.get("configs_to_update", [])
            if configs:
                for c in configs:
                    st.markdown(f"- ⚙️ **{c['name']}**: `{c['file_path']}`")
            else:
                st.write("No configuration files explicitly linked.")

    # Tab 4: Dependency Reasoning Paths
    with tab_paths:
        st.markdown("### 🔗 Computed Dependency Reasoning Paths")
        st.write("These paths explain the causal chain connecting each affected component to the proposed change:")

        paths = res.get("impact_paths", [])
        if paths:
            for p in paths:
                badge = "🔴 Direct" if p.get("is_direct") else f"🟡 Depth {p.get('depth')}"
                st.markdown(f"- `[{badge}]` {p['path_text']}")
        else:
            st.info("No relationship paths discovered.")

        st.markdown("#### 📚 Supporting Source Citations")
        citations = res.get("citations", [])
        if citations:
            for c in citations:
                st.markdown(
                    f"**[Source {c['id']}]** `{c['file_path']}:{c['start_line']}-{c['end_line']}`\n"
                    f"> _{c['snippet']}..._"
                )
        else:
            st.info("No citations retrieved.")

    # Tab 5: Export & Download
    with tab_export:
        st.markdown("### 💾 Export What-If Impact Report")
        md_text = WhatIfReportCoordinator.export_report_markdown(res)

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="📥 Download as Markdown (.md)",
                data=md_text,
                file_name=f"repomind_whatif_{res.get('action')}_{res.get('target_entity')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        with col_dl2:
            # Prepare serializable JSON
            export_dict = {
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
                "model_used": res.get("model_used")
            }
            st.download_button(
                label="📥 Download as JSON (.json)",
                data=json.dumps(export_dict, indent=2),
                file_name=f"repomind_whatif_{res.get('action')}_{res.get('target_entity')}.json",
                mime="application/json",
                use_container_width=True
            )


def _get_quick_scenarios(meta, graph):
    """Return tailored quick What-If scenarios based on the loaded repository."""
    if not graph or meta.name == "ragcraft":
        return [
            ("🔄 Replace FAISS with ChromaDB", "What if we replace FAISS with ChromaDB?"),
            ("🗑️ Remove Redis Caching", "What if we remove Redis caching?"),
            ("🛠️ Modify SemanticRetriever", "What components will be affected if I modify SemanticRetriever?"),
            ("🚀 Upgrade Pydantic to v2", "What happens if we upgrade Pydantic to v2?")
        ]

    # For other repositories, build scenarios using actual components
    classes = [d.get("name") for _, d in graph.nodes(data=True) if d.get("type") == "Class" and d.get("name")]
    libs = [d.get("name") for _, d in graph.nodes(data=True) if d.get("type") == "Library" and d.get("name")]

    s1 = (f"🔄 Replace {classes[0]}", f"What if we replace {classes[0]} with a custom adapter?") if classes else ("🔄 Refactor Storage", "What if we refactor storage?")
    s2 = (f"🗑️ Remove {libs[0]}", f"What if we remove {libs[0]}?") if libs else ("🗑️ Remove Dep", "What if we remove external dependencies?")
    s3 = (f"🛠️ Modify {classes[1]}", f"What components will be affected if I modify {classes[1]}?") if len(classes) > 1 else ("🛠️ Modify Core", "What if we modify core modules?")
    s4 = (f"🚀 Upgrade {libs[1]}", f"What happens if we upgrade {libs[1]} to the latest version?") if len(libs) > 1 else ("🚀 Upgrade Dependencies", "What happens if we upgrade dependencies?")

    return [s1, s2, s3, s4]
