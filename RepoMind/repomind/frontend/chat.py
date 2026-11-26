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
    graph = st.session_state.get("graph")

    st.markdown(f"## 💬 Repository Architecture Chat: `{meta.full_name}`")
    st.write("Ask natural-language questions about the codebase architecture, design patterns, and internal wiring.")

    # Sidebar controls for retrieval mode
    with st.sidebar:
        st.markdown("### 🎛️ Retrieval Settings")
        mode_option = st.radio(
            "Retrieval Strategy:",
            options=[
                "Hybrid (Graph + Vector) [Recommended]",
                "Graph Only (AST Traversal)"
            ],
            index=0,
            help="Choose between combined hybrid GraphRAG (semantic search + graph traversal) or pure graph relationship traversal."
        )

        if "Hybrid" in mode_option:
            mode_key = "hybrid"
        else:
            mode_key = "graph"

        top_k = st.slider("Top-K Evidence Chunks:", min_value=1, max_value=10, value=4)
        graph_depth = st.slider("Graph Traversal Depth:", min_value=1, max_value=4, value=2)

        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state["chat_messages"] = [
                {
                    "role": "assistant",
                    "content": f"Hello! I am **RepoMind**. I have parsed `{meta.full_name}` into a knowledge graph and vector index. Ask me anything about how this codebase is structured, or switch to the **What-If Analysis** page to test hypothetical refactorings!",
                    "citations": [],
                    "paths": [],
                    "mode": mode_key.upper(),
                    "model": "RepoMind Engine",
                    "latency": None
                }
            ]
            st.rerun()

    # Initialize chat history if absent or empty
    if not st.session_state.get("chat_messages"):
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": f"Hello! I am **RepoMind**. I have parsed `{meta.full_name}` into a knowledge graph and vector index. Ask me anything about how this codebase is structured, or switch to the **What-If Analysis** page to test hypothetical refactorings!",
                "citations": [],
                "paths": [],
                "mode": mode_key.upper(),
                "model": "RepoMind Engine",
                "latency": None
            }
        ]

    # Generate suggested questions tailored to the active repo
    suggested_questions = _get_suggested_questions(meta, graph)
    st.markdown("##### 💡 Suggested Questions:")
    scols = st.columns(len(suggested_questions))
    selected_prompt = None

    for i, sq in enumerate(suggested_questions):
        with scols[i]:
            if st.button(sq, key=f"sq_btn_{i}", use_container_width=True):
                selected_prompt = sq

    # Text input for chat
    chat_input_val = st.chat_input("Ask a question about this repository...")
    user_prompt = selected_prompt or chat_input_val

    # If user provided a prompt, process it immediately before rendering
    if user_prompt:
        st.session_state["chat_messages"].append({
            "role": "user",
            "content": user_prompt,
            "citations": [],
            "paths": []
        })

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
            model = answer_res.get("model_used", "Local Grounded Engine")

            st.session_state["chat_messages"].append({
                "role": "assistant",
                "content": ans_text,
                "citations": citations,
                "paths": paths,
                "mode": mode_key.upper(),
                "model": model,
                "latency": latency
            })

    # Render all chat messages in chronological order
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Render provenance and metadata for assistant responses
            if msg["role"] == "assistant":
                meta_parts = []
                if msg.get("mode"):
                    meta_parts.append(f"⚡ Mode: **{msg['mode']}**")
                if msg.get("model"):
                    meta_parts.append(f"Model: **{msg['model']}**")
                if msg.get("latency") is not None:
                    meta_parts.append(f"Latency: **{msg['latency']:.3f}s**")

                if meta_parts:
                    st.caption(" | ".join(meta_parts))

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


def _get_suggested_questions(meta, graph):
    """Return tailored sample questions based on the loaded repository."""
    if not graph or meta.name == "ragcraft":
        return [
            "How is the vector store configured?",
            "Where does caching get called?",
            "Which components connect to RAGPipeline?"
        ]

    # Dynamically extract classes and libraries from graph
    classes = [data.get("name") for _, data in graph.nodes(data=True) if data.get("type") == "Class" and data.get("name")]
    libs = [data.get("name") for _, data in graph.nodes(data=True) if data.get("type") == "Library" and data.get("name")]

    q1 = f"What is the role of `{classes[0]}`?" if classes else "What is the primary architecture of this repository?"
    q2 = f"How does `{classes[1]}` interact with other components?" if len(classes) > 1 else "How are dependencies wired?"
    q3 = f"Which modules depend on `{libs[0]}`?" if libs else "What tests are available in this repository?"

    return [q1, q2, q3]
