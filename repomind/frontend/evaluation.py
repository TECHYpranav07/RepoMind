"""Page 5: Evaluation & Benchmarking."""
import streamlit as st
import pandas as pd
from repomind.evaluation.benchmark import BenchmarkRunner
from repomind.evaluation.dataset import BENCHMARK_DATASET


def render_evaluation():
    """Render the automated benchmarking and comparative evaluation page."""
    if not st.session_state.get("repo_loaded", False):
        st.warning("⚠️ No repository loaded. Please go to the **Home / Dashboard** page and ingest a repository first.")
        return

    meta = st.session_state.get("repo_meta")
    hybrid_retriever = st.session_state.get("hybrid_retriever")
    answer_generator = st.session_state.get("answer_generator")

    st.markdown(f"## 📈 Evaluation & Benchmark Framework: `{meta.full_name}`")
    st.write(
        "Evaluate retrieval precision, impact identification recall, answer correctness, faithfulness, and latency "
        "comparing **Vector RAG**, **Graph RAG**, and **Hybrid GraphRAG** on real repository questions."
    )

    col_btn, col_opts = st.columns([1, 2])
    with col_btn:
        run_btn = st.button("🚀 Run Full Benchmark Suite", type="primary", use_container_width=True)
    with col_opts:
        selected_modes = st.multiselect(
            "Select Baseline Modes to Benchmark:",
            options=["vector", "graph", "hybrid"],
            default=["vector", "graph", "hybrid"],
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
        st.info("Click **Run Full Benchmark Suite** above to execute the live empirical evaluation.")


def _render_benchmark_dashboard(df: pd.DataFrame):
    """Render metrics comparison charts, summary cards, and data table."""
    st.markdown("---")
    st.markdown("### 🏆 Comparative Benchmark Results")

    # Aggregate Metrics by Mode
    agg_df = df.groupby("mode").agg({
        "precision_at_k": "mean",
        "recall_at_k": "mean",
        "impact_f1": "mean",
        "correctness": "mean",
        "faithfulness": "mean",
        "total_latency_s": "mean"
    }).reset_index()

    # Metric Cards for Hybrid mode if present
    hybrid_row = agg_df[agg_df["mode"] == "HYBRID"]
    if not hybrid_row.empty:
        h = hybrid_row.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Hybrid Retrieval Recall@K", f"{h['recall_at_k']:.1%}")
        c2.metric("Hybrid Impact F1", f"{h['impact_f1']:.1%}")
        c3.metric("Hybrid Faithfulness", f"{h['faithfulness']:.1%}")
        c4.metric("Mean Latency", f"{h['total_latency_s']:.3f}s")

    st.markdown("#### 📊 Metric Visualizations")
    tab_chart1, tab_chart2, tab_chart3, tab_table = st.tabs([
        "📊 Accuracy & Quality Breakdown",
        "⏱️ Latency Comparison",
        "🕸️ Multi-Dimensional Radar",
        "📋 Full Execution Log & CSV"
    ])

    with tab_chart1:
        bar_fig = BenchmarkRunner.create_comparison_bar_chart(df)
        st.plotly_chart(bar_fig, use_container_width=True)

    with tab_chart2:
        lat_fig = BenchmarkRunner.create_latency_chart(df)
        st.plotly_chart(lat_fig, use_container_width=True)

    with tab_chart3:
        radar_fig = BenchmarkRunner.create_radar_chart(df)
        st.plotly_chart(radar_fig, use_container_width=True)

    with tab_table:
        st.markdown("#### Detailed Experiment Log")
        st.dataframe(df, use_container_width=True)

        csv_data = df.to_csv(index=False)
        st.download_button(
            label="📥 Export Benchmark Results to CSV",
            data=csv_data,
            file_name="repomind_evaluation_results.csv",
            mime="text/csv",
            use_container_width=True
        )
