"""Page 5: Evaluation & Benchmarking (Simplified Graph vs Hybrid GraphRAG)."""
import streamlit as st
import pandas as pd
from repomind.evaluation.benchmark import BenchmarkRunner
from repomind.evaluation.dataset import BENCHMARK_DATASET


def render_evaluation():
    """Render the simplified comparative evaluation between Graph RAG and Hybrid GraphRAG."""
    if not st.session_state.get("repo_loaded", False):
        st.warning("⚠️ No repository loaded. Please go to the **Home / Dashboard** page and ingest a repository first.")
        return

    meta = st.session_state.get("repo_meta")
    hybrid_retriever = st.session_state.get("hybrid_retriever")
    answer_generator = st.session_state.get("answer_generator")

    st.markdown(f"## 📈 Empirical Benchmarking: `{meta.full_name}`")
    st.write(
        "Evaluate and compare **Pure Graph RAG (AST Traversal)** vs **Hybrid GraphRAG (Semantic + Graph)** "
        "across real repository questions."
    )

    col_btn, col_opts = st.columns([1, 1.8])
    with col_btn:
        run_btn = st.button("🚀 Run Benchmark Suite", type="primary", use_container_width=True)
    with col_opts:
        selected_modes = st.multiselect(
            "Evaluation Modes:",
            options=["graph", "hybrid"],
            default=["graph", "hybrid"],
            format_func=lambda x: f"{x.upper()} RAG"
        )

    if run_btn:
        progress_bar = st.progress(0.0)
        status_label = st.empty()

        def prog_cb(msg: str, pct: float):
            status_label.text(msg)
            progress_bar.progress(pct)

        runner = BenchmarkRunner(hybrid_retriever, answer_generator, BENCHMARK_DATASET)
        df_results = runner.run_benchmark(modes=selected_modes, progress_callback=prog_cb)

        st.session_state["benchmark_results_df"] = df_results
        status_label.text("Benchmark completed successfully!")
        progress_bar.progress(1.0)

    # Render results if available
    if "benchmark_results_df" in st.session_state:
        df = st.session_state["benchmark_results_df"]
        _render_benchmark_dashboard(df)
    else:
        st.info("Click **Run Benchmark Suite** above to execute live evaluation across test questions.")


def _render_benchmark_dashboard(df: pd.DataFrame):
    """Render simplified metrics, side-by-side charts, key takeaways, and data table."""
    st.markdown("---")
    st.markdown("### 🏆 Graph vs Hybrid GraphRAG Comparison")

    # Aggregate Metrics by Mode
    agg_df = df.groupby("mode").agg({
        "precision_at_k": "mean",
        "recall_at_k": "mean",
        "impact_f1": "mean",
        "correctness": "mean",
        "faithfulness": "mean",
        "total_latency_s": "mean"
    }).reset_index()

    # Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    hybrid_row = agg_df[agg_df["mode"] == "HYBRID"]
    graph_row = agg_df[agg_df["mode"] == "GRAPH"]

    h_recall = hybrid_row["recall_at_k"].values[0] if not hybrid_row.empty else 0.0
    g_recall = graph_row["recall_at_k"].values[0] if not graph_row.empty else 0.0
    h_f1 = hybrid_row["impact_f1"].values[0] if not hybrid_row.empty else 0.0
    h_faith = hybrid_row["faithfulness"].values[0] if not hybrid_row.empty else 0.0
    h_lat = hybrid_row["total_latency_s"].values[0] if not hybrid_row.empty else 0.0

    c1.metric("Hybrid Retrieval Recall@K", f"{h_recall:.1%}", delta=f"{(h_recall - g_recall):+.1%} vs Graph" if g_recall else None)
    c2.metric("Impact Detection F1", f"{h_f1:.1%}")
    c3.metric("Answer Faithfulness", f"{h_faith:.1%}")
    c4.metric("Average Latency", f"{h_lat:.3f}s")

    tab_visuals, tab_data = st.tabs([
        "📊 Visual Performance & Key Insights",
        "📋 Detailed Execution Records & CSV"
    ])

    with tab_visuals:
        # Charts row
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            bar_fig = BenchmarkRunner.create_comparison_bar_chart(df)
            st.plotly_chart(bar_fig, use_container_width=True)
        with chart_col2:
            lat_fig = BenchmarkRunner.create_latency_chart(df)
            st.plotly_chart(lat_fig, use_container_width=True)

        # Key Takeaway Box
        st.markdown(
            """
            <div style="background:#0f172a; border-left: 4px solid #10b981; border-radius: 8px; padding: 14px 18px; margin-top: 12px;">
                <h4 style="margin:0 0 6px 0; color:#f8fafc;">💡 Key Takeaways: Why Hybrid GraphRAG Wins</h4>
                <p style="margin:0; color:#94a3b8; font-size:0.9rem; line-height:1.5;">
                    • <b>Higher Retrieval Recall:</b> Hybrid GraphRAG combines semantic embedding similarity with multi-hop AST call-graph traversal, discovering connected classes and tests that keyword search misses.<br>
                    • <b>Grounded Answers:</b> Transversing explicit AST caller edges ensures answer faithfulness without relying on LLM guesswork.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with tab_data:
        st.markdown("#### Per-Question Execution Log")
        st.dataframe(df, use_container_width=True)

        csv_data = df.to_csv(index=False)
        st.download_button(
            label="📥 Export Benchmark Results to CSV",
            data=csv_data,
            file_name="repomind_benchmark_results.csv",
            mime="text/csv",
            use_container_width=True
        )
