"""Page 3: Repository Chat with Mode Selection & Explainable Citations."""
import streamlit as st


def render_chat():
    """Render repository chat interface with Vector, Graph, and Hybrid GraphRAG modes."""
    if not st.session_state.get("repo_loaded", False):
        st.warning("⚠️ No repository loaded. Please go to the **Home / Dashboard** page and ingest a repository first.")
        return

    meta = st.session_state.get("repo_meta")
    hybrid_retriever = st.session_state.get("hybrid_retriever")
    answer_generator = st.session_state.get("answer_generator")

    st.markdown(f"## 💬 Repository Architecture Chat: `{meta.full_name}`")
    st.write("Ask natural-language questions about the codebase architecture, design patterns, and internal wiring.")

    # Sidebar controls for retrieval mode
    with st.sidebar:
        st.markdown("### 🎛️ Retrieval Settings")
        mode = st.radio(
            "Retrieval Strategy:",
            options=["Hybrid (Graph + Vector)", "Vector Only (FAISS)", "Graph Only (AST Traversal)"],
            index=0,
            help="Choose between standard semantic vector retrieval, pure graph relationship traversal, or combined hybrid GraphRAG."
        )

        mode_key = "hybrid"
        if "Vector Only" in mode:
            mode_key = "vector"
        elif "Graph Only" in mode:
            mode_key = "graph"

        top_k = st.slider("Top-K Vector Chunks:", min_value=1, max_value=10, value=4)
        graph_depth = st.slider("Graph Traversal Depth:", min_value=1, max_value=4, value=2)

        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state["chat_messages"] = []
            st.rerun()

    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": f"Hello! I am **RepoMind**. I have parsed `{meta.full_name}` into a knowledge graph and vector index. Ask me anything about how this codebase is structured, or switch to the **What-If Analysis** page to test hypothetical refactorings!",
                "citations": [],
                "paths": []
            }
        ]

    # Sample query prompts
    st.markdown("##### 💡 Suggested Questions:")
    sample_col1, sample_col2, sample_col3 = st.columns(3)
    with sample_col1:
        if st.button("How is the vector store configured?", use_container_width=True):
            st.session_state["query_input_val"] = "How is the vector store configured?"
    with sample_col2:
        if st.button("Where does caching get called?", use_container_width=True):
            st.session_state["query_input_val"] = "Where does caching get called?"
    with sample_col3:
        if st.button("Which components connect to RAGPipeline?", use_container_width=True):
            st.session_state["query_input_val"] = "Which components connect to RAGPipeline?"

    # Display chat history
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Render citations if present
            citations = msg.get("citations", [])
            paths = msg.get("paths", [])

            if citations:
                with st.expander(f"📚 Verified Source Citations ({len(citations)})", expanded=False):
                    for cite in citations:
                        st.markdown(
                            f"**[Source {cite['id']}]** `{cite['file_path']}:{cite['start_line']}-{cite['end_line']}` "
                            f"(Relevance: `{cite['score']}`)\n"
                            f"> _{cite['snippet']}..._"
                        )

            if paths:
                with st.expander(f"🔗 Traversed Knowledge Graph Paths ({len(paths)})", expanded=False):
                    for p in paths:
                        st.markdown(f"- `{p}`")

    # User Input
    user_prompt = st.chat_input("Ask a question about this repository...")
    if "query_input_val" in st.session_state and st.session_state["query_input_val"]:
        user_prompt = st.session_state.pop("query_input_val")

    if user_prompt:
        st.session_state["chat_messages"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner(f"Retrieving evidence via {mode_key.upper()} GraphRAG..."):
                ret_res = hybrid_retriever.retrieve(
                    query=user_prompt,
                    mode=mode_key,
                    top_k=top_k,
                    graph_depth=graph_depth
                )
                answer_res = answer_generator.answer_question(user_prompt, ret_res)

                ans_text = answer_res.get("answer", "")
                citations = answer_res.get("citations", [])
                paths = answer_res.get("graph_paths", [])
                latency = answer_res.get("latency", 0.0)
                model = answer_res.get("model_used", "Local")

                st.markdown(ans_text)
                st.caption(f"⚡ Mode: **{mode_key.upper()}** | Model: **{model}** | Latency: **{latency}s**")

                if citations:
                    with st.expander(f"📚 Verified Source Citations ({len(citations)})", expanded=False):
                        for cite in citations:
                            st.markdown(
                                f"**[Source {cite['id']}]** `{cite['file_path']}:{cite['start_line']}-{cite['end_line']}` "
                                f"(Relevance: `{cite['score']}`)\n"
                                f"> _{cite['snippet']}..._"
                            )

                if paths:
                    with st.expander(f"🔗 Traversed Knowledge Graph Paths ({len(paths)})", expanded=False):
                        for p in paths:
                            st.markdown(f"- `{p}`")

                st.session_state["chat_messages"].append({
                    "role": "assistant",
                    "content": ans_text,
                    "citations": citations,
                    "paths": paths
                })
