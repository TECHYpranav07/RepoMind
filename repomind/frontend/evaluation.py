"""Page 5: Evaluation & Benchmark Dashboard — Redesigned.

Sections:
  A — Page Header (repo info, graph nodes, chunks, question count, last run status)
  B — Benchmark Controls (run button, mode selector, progress)
  C — Executive Summary KPI cards
  D — Performance Comparison charts (4 separate charts)
  E — Automated Interpretation
  F — Detailed Results (collapsible, filterable table + CSV export)
  G — Metric Glossary
"""
from __future__ import annotations

import math
import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from repomind.evaluation.benchmark import BenchmarkRunner, COLORS, _is_nan, _safe_val
from repomind.evaluation.dataset import BENCHMARK_DATASET, generate_ast_ground_truth_dataset


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def render_evaluation():
    """Render the redesigned Evaluation & Benchmark dashboard."""
    _inject_eval_css()

    # Guard — repo must be loaded
    if not st.session_state.get("repo_loaded", False):
        st.warning(
            "⚠️ No repository loaded. "
            "Please go to **Home / Dashboard** and ingest a repository first."
        )
        return

    meta           = st.session_state.get("repo_meta")
    hybrid_retriever = st.session_state.get("hybrid_retriever")
    answer_generator = st.session_state.get("answer_generator")
    graph          = st.session_state.get("graph")
    chunks         = st.session_state.get("repo_chunks", [])

    # ── SECTION A: Header ───────────────────────────────────────────────────
    _render_header(meta, graph, chunks)

    st.markdown('<div class="eval-divider"></div>', unsafe_allow_html=True)

    # ── SECTION B: Controls ─────────────────────────────────────────────────
    run_clicked, selected_modes, num_questions, gt_source = _render_controls(graph)

    # Execute benchmark
    if run_clicked:
        if not selected_modes:
            st.error("Please select at least one retrieval mode.")
        elif hybrid_retriever is None:
            st.error("Retriever not initialised. Please reload the repository.")
        else:
            _run_and_store_benchmark(hybrid_retriever, answer_generator, selected_modes, num_questions, gt_source, graph)

    # ── Render results (or placeholder) ────────────────────────────────────
    df: Optional[pd.DataFrame] = st.session_state.get("benchmark_results_df")

    if df is None or df.empty:
        _render_empty_state()
        _render_glossary()
        return

    st.markdown('<div class="eval-divider"></div>', unsafe_allow_html=True)

    # ── SECTION C: Executive Summary ────────────────────────────────────────
    _render_kpi_cards(df)

    st.markdown('<div class="eval-divider"></div>', unsafe_allow_html=True)

    # ── SECTION D: Performance Charts ───────────────────────────────────────
    _render_charts(df)

    st.markdown('<div class="eval-divider"></div>', unsafe_allow_html=True)

    # ── SECTION E: Interpretation ────────────────────────────────────────────
    _render_interpretation(df)

    st.markdown('<div class="eval-divider"></div>', unsafe_allow_html=True)

    # ── SECTION F: Detailed Results ─────────────────────────────────────────
    _render_detailed_results(df)

    st.markdown('<div class="eval-divider"></div>', unsafe_allow_html=True)

    # ── SECTION G: Glossary ─────────────────────────────────────────────────
    _render_glossary()


# ─────────────────────────────────────────────────────────────────────────────
# Section A — Header
# ─────────────────────────────────────────────────────────────────────────────

def _render_header(meta, graph, chunks):
    last_run = st.session_state.get("benchmark_last_run")
    last_run_status = st.session_state.get("benchmark_last_status", "—")

    st.markdown(
        """
        <div class="eval-header">
            <div class="eval-header-left">
                <h1 class="eval-title">Evaluation &amp; Benchmark</h1>
                <p class="eval-subtitle">
                    Measure how effectively <span class="mode-badge mode-graph">GraphRAG</span>
                    and <span class="mode-badge mode-hybrid">Hybrid GraphRAG</span>
                    understand software repositories against <span class="mode-badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3);">⚡ Deterministic AST Ground Truth</span>.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    n_nodes  = graph.number_of_nodes() if graph else 0
    n_chunks = len(chunks)
    n_q      = len(BENCHMARK_DATASET)
    repo_name = meta.full_name if meta else "—"
    last_run_str = last_run.strftime("%Y-%m-%d %H:%M") if last_run else "Never"

    c1, c2, c3, c4, c5 = st.columns(5)
    _stat_pill(c1, "📦 Repository",   repo_name,      "#6366f1")
    _stat_pill(c2, "🕸️ Graph Nodes",  str(n_nodes),   "#10b981")
    _stat_pill(c3, "📄 Doc Chunks",   str(n_chunks),  "#06b6d4")
    _stat_pill(c4, "❓ Test Questions", str(n_q),      "#f59e0b")
    _stat_pill(c5, "🕐 Last Run",      last_run_str,  "#ec4899")


def _stat_pill(col, label: str, value: str, color: str):
    col.markdown(
        f"""
        <div class="stat-pill" style="border-left-color:{color};">
            <div class="stat-pill-label">{label}</div>
            <div class="stat-pill-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Section B — Benchmark Controls
# ─────────────────────────────────────────────────────────────────────────────

def _render_controls(graph=None):
    st.markdown("### ⚙️ Benchmark Controls")

    col_source, col_mode, col_num, col_btn = st.columns([1.8, 1.6, 0.8, 1.0])

    with col_source:
        gt_source = st.selectbox(
            "Ground Truth Source:",
            options=[
                "⚡ Live AST Ground Truth (Auto-extracted from Repo)",
                "📚 Curated Architecture Golden Set"
            ],
            index=0,
            key="eval_gt_source",
            help="Live AST dynamically extracts 100% deterministic compiler facts from this repository's Abstract Syntax Tree, guaranteeing verifiable callers and tests with zero hallucinations."
        )

    with col_mode:
        mode_choice = st.radio(
            "Retrieval Mode:",
            options=["Both (GraphRAG + Hybrid)", "GraphRAG only", "Hybrid GraphRAG only"],
            index=0,
            horizontal=True,
            key="eval_mode_choice",
        )

    with col_num:
        default_q = 5
        num_questions = st.number_input(
            "Questions:",
            min_value=1,
            max_value=15,
            value=default_q,
            step=1,
            key="eval_num_questions",
            help="Number of questions to evaluate.",
        )

    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        is_running = st.session_state.get("benchmark_running", False)
        run_clicked = st.button(
            "🚀 Run Benchmark" if not is_running else "⏳ Running…",
            type="primary",
            use_container_width=True,
            disabled=is_running,
            key="eval_run_btn",
        )

    # Map radio to mode list
    mode_map = {
        "Both (GraphRAG + Hybrid)": ["graph", "hybrid"],
        "GraphRAG only":            ["graph"],
        "Hybrid GraphRAG only":     ["hybrid"],
    }
    selected_modes = mode_map[mode_choice]

    return run_clicked, selected_modes, int(num_questions), gt_source


def _run_and_store_benchmark(hybrid_retriever, answer_generator, modes, num_questions, gt_source, graph=None):
    st.session_state["benchmark_running"] = True
    st.session_state["benchmark_dataset_source"] = gt_source

    progress_bar = st.progress(0.0)
    status_label = st.empty()

    if "Live AST" in gt_source and graph is not None:
        ast_dataset = generate_ast_ground_truth_dataset(graph, max_questions=num_questions)
        dataset = ast_dataset if ast_dataset else BENCHMARK_DATASET[:num_questions]
    else:
        dataset = BENCHMARK_DATASET[:num_questions]

    def prog_cb(msg: str, pct: float):
        status_label.markdown(
            f'<div class="progress-msg">⏳ {msg}</div>', unsafe_allow_html=True
        )
        progress_bar.progress(min(pct, 1.0))

    try:
        runner = BenchmarkRunner(hybrid_retriever, answer_generator, dataset)
        df_results = runner.run_benchmark(modes=modes, progress_callback=prog_cb)

        st.session_state["benchmark_results_df"]  = df_results
        st.session_state["benchmark_last_run"]    = datetime.datetime.now()
        st.session_state["benchmark_last_status"] = "✅ Success"

        progress_bar.progress(1.0)
        status_label.markdown(
            '<div class="progress-msg success">✅ Benchmark completed successfully!</div>',
            unsafe_allow_html=True,
        )
    except Exception as e:
        st.session_state["benchmark_last_status"] = f"❌ Error: {e}"
        st.error(f"Benchmark failed: {e}")
    finally:
        st.session_state["benchmark_running"] = False


# ─────────────────────────────────────────────────────────────────────────────
# Section C — Executive Summary KPI Cards
# ─────────────────────────────────────────────────────────────────────────────

def _render_kpi_cards(df: pd.DataFrame):
    st.markdown("### 📊 Executive Summary")
    st.caption(
        "Four key performance indicators — each answers one important question about the system."
    )

    agg = df.groupby("mode").mean(numeric_only=True).reset_index()

    graph_row  = agg[agg["mode"] == "GRAPH"].iloc[0]  if "GRAPH"  in agg["mode"].values else None
    hybrid_row = agg[agg["mode"] == "HYBRID"].iloc[0] if "HYBRID" in agg["mode"].values else None

    kpis = [
        {
            "title": "Retrieval Quality",
            "metric": "recall_at_k",
            "icon": "🎯",
            "unit": "%",
            "description": "How often the system retrieves the information needed to answer a question.",
            "metric_name": "Recall@K",
            "higher_is_better": True,
        },
        {
            "title": "Impact Detection",
            "metric": "impact_f1",
            "icon": "🔍",
            "unit": "%",
            "description": "How accurately the system identifies components affected by a proposed change.",
            "metric_name": "Impact F1",
            "higher_is_better": True,
        },
        {
            "title": "Answer Reliability",
            "metric": "faithfulness",
            "icon": "✅",
            "unit": "%",
            "description": "How well the generated answer is supported by retrieved evidence.",
            "metric_name": "Faithfulness",
            "higher_is_better": True,
        },
        {
            "title": "Response Speed",
            "metric": "total_latency_s",
            "icon": "⚡",
            "unit": "s",
            "description": "How long the system takes to produce an answer (retrieval + LLM generation).",
            "metric_name": "Avg Latency",
            "higher_is_better": False,
        },
    ]

    cols = st.columns(4)
    for col, kpi in zip(cols, kpis):
        with col:
            _render_kpi_card(kpi, graph_row, hybrid_row)


def _render_kpi_card(kpi: dict, graph_row, hybrid_row):
    metric = kpi["metric"]
    is_latency = kpi["unit"] == "s"
    higher_is_better = kpi["higher_is_better"]

    g_val = _get_val(graph_row,  metric)
    h_val = _get_val(hybrid_row, metric)

    def fmt(v):
        if v is None:
            return "N/A"
        return f"{v:.3f}s" if is_latency else f"{v:.1%}"

    def winner_badge(g, h):
        if g is None and h is None:
            return ""
        if g is None:
            return '<span class="winner-badge hybrid">Hybrid</span>'
        if h is None:
            return '<span class="winner-badge graph">Graph</span>'
        if higher_is_better:
            if h > g + 0.001:
                return '<span class="winner-badge hybrid">↑ Hybrid</span>'
            elif g > h + 0.001:
                return '<span class="winner-badge graph">↑ Graph</span>'
        else:
            if h < g - 0.001:
                return '<span class="winner-badge hybrid">↓ Hybrid faster</span>'
            elif g < h - 0.001:
                return '<span class="winner-badge graph">↓ Graph faster</span>'
        return '<span class="winner-badge tie">≈ Tied</span>'

    def diff_text(g, h):
        if g is None or h is None:
            return ""
        diff = h - g
        if is_latency:
            sign = "+" if diff > 0 else ""
            return f"{sign}{diff:.3f}s vs Graph"
        else:
            sign = "+" if diff > 0 else ""
            return f"{sign}{diff:.1%} vs Graph"

    rows_html = ""
    if graph_row is not None:
        rows_html += f'<div class="kpi-row"><span class="kpi-mode graph-label">Graph</span><span class="kpi-val">{fmt(g_val)}</span></div>'
    if hybrid_row is not None:
        rows_html += f'<div class="kpi-row"><span class="kpi-mode hybrid-label">Hybrid</span><span class="kpi-val">{fmt(h_val)}</span></div>'
    if graph_row is not None and hybrid_row is not None:
        d = diff_text(g_val, h_val)
        if d:
            rows_html += f'<div class="kpi-diff">{d}</div>'

    badge = winner_badge(g_val, h_val)

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-icon">{kpi["icon"]}</span>
                <span class="kpi-title">{kpi["title"]}</span>
                {badge}
            </div>
            <div class="kpi-metric-name">{kpi["metric_name"]}</div>
            {rows_html}
            <div class="kpi-desc">{kpi["description"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _get_val(row, col: str):
    if row is None:
        return None
    v = row.get(col)
    if _is_nan(v):
        return None
    return float(v)


# ─────────────────────────────────────────────────────────────────────────────
# Section D — Performance Charts
# ─────────────────────────────────────────────────────────────────────────────

def _render_charts(df: pd.DataFrame):
    st.markdown("### 📈 Performance Comparison")
    st.caption(
        "Each chart focuses on one aspect of the experiment. "
        "Purple = **GraphRAG** · Green = **Hybrid GraphRAG**."
    )

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.plotly_chart(
            BenchmarkRunner.create_retrieval_chart(df),
            use_container_width=True,
        )
        st.caption(
            "**Retrieval Quality** — What fraction of relevant files were retrieved "
            "(Recall) and what fraction of retrieved files were relevant (Precision)?"
        )

    with chart_col2:
        st.plotly_chart(
            BenchmarkRunner.create_impact_chart(df),
            use_container_width=True,
        )
        st.caption(
            "**Change Impact Detection** — How accurately did the system identify "
            "components affected by a proposed change?"
        )

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.plotly_chart(
            BenchmarkRunner.create_answer_quality_chart(df),
            use_container_width=True,
        )
        st.caption(
            "**Answer Reliability** — How correct (vs. reference) and how grounded "
            "(vs. retrieved context) was the generated answer?"
        )

    with chart_col4:
        st.plotly_chart(
            BenchmarkRunner.create_latency_chart(df),
            use_container_width=True,
        )
        st.caption(
            "**Response Time** — Broken down into retrieval latency, "
            "LLM generation latency, and total end-to-end latency."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Section E — Interpretation
# ─────────────────────────────────────────────────────────────────────────────

def _render_interpretation(df: pd.DataFrame):
    st.markdown("### 💡 What Do These Results Mean?")

    agg = df.groupby("mode").mean(numeric_only=True).reset_index()
    graph_row  = agg[agg["mode"] == "GRAPH"].iloc[0]  if "GRAPH"  in agg["mode"].values else None
    hybrid_row = agg[agg["mode"] == "HYBRID"].iloc[0] if "HYBRID" in agg["mode"].values else None

    if graph_row is None and hybrid_row is None:
        st.info("No results to interpret.")
        return

    # Build interpretation narratives
    bullets = []
    hybrid_wins = 0
    graph_wins  = 0
    total_comparable = 0

    comparisons = [
        ("recall_at_k",   "retrieval recall",         "higher is better", True),
        ("precision_at_k","retrieval precision",       "higher is better", True),
        ("impact_f1",     "impact detection F1",       "higher is better", True),
        ("correctness",   "answer correctness",        "higher is better", True),
        ("faithfulness",  "answer faithfulness",       "higher is better", True),
        ("total_latency_s","end-to-end latency",       "lower is better",  False),
    ]

    for metric, label, direction, higher_is_better in comparisons:
        g = _get_val(graph_row,  metric)
        h = _get_val(hybrid_row, metric)

        if g is None and h is None:
            bullets.append(f"• **{label.title()}**: Not enough data to compare.")
            continue

        if g is None:
            bullets.append(f"• **{label.title()}**: Only Hybrid evaluated ({_fmt_metric(h, metric)}).")
            continue

        if h is None:
            bullets.append(f"• **{label.title()}**: Only Graph evaluated ({_fmt_metric(g, metric)}).")
            continue

        total_comparable += 1
        diff = h - g
        threshold = 0.01 if metric != "total_latency_s" else 0.05

        if abs(diff) < threshold:
            bullets.append(
                f"• **{label.title()}**: Both methods performed similarly "
                f"(Graph: {_fmt_metric(g, metric)}, Hybrid: {_fmt_metric(h, metric)})."
            )
        elif (diff > 0 and higher_is_better) or (diff < 0 and not higher_is_better):
            hybrid_wins += 1
            verb = "achieved higher" if higher_is_better else "was faster"
            reason = _get_reason(metric, "hybrid")
            bullets.append(
                f"• **{label.title()}**: Hybrid GraphRAG {verb} "
                f"({_fmt_metric(h, metric)} vs {_fmt_metric(g, metric)}). {reason}"
            )
        else:
            graph_wins += 1
            verb = "achieved higher" if higher_is_better else "was faster"
            reason = _get_reason(metric, "graph")
            bullets.append(
                f"• **{label.title()}**: GraphRAG {verb} "
                f"({_fmt_metric(g, metric)} vs {_fmt_metric(h, metric)}). {reason}"
            )

    # Overall verdict
    if total_comparable == 0:
        verdict = "Not enough evidence to declare an overall winner."
        verdict_color = "#64748b"
    elif hybrid_wins > graph_wins + 1:
        verdict = (
            f"Hybrid GraphRAG outperforms GraphRAG on {hybrid_wins} of "
            f"{total_comparable} measured dimensions."
        )
        verdict_color = "#10b981"
    elif graph_wins > hybrid_wins + 1:
        verdict = (
            f"GraphRAG outperforms Hybrid GraphRAG on {graph_wins} of "
            f"{total_comparable} measured dimensions."
        )
        verdict_color = "#8b5cf6"
    else:
        verdict = (
            "Results are mixed — neither method dominates across all dimensions. "
            "Consider the trade-offs based on your use case."
        )
        verdict_color = "#f59e0b"

    bullets_html = "".join(f"<p class='interp-bullet'>{b}</p>" for b in bullets)

    st.markdown(
        f"""
        <div class="interpretation-box">
            <div class="verdict-banner" style="border-color:{verdict_color}; color:{verdict_color};">
                📌 {verdict}
            </div>
            <div class="interp-bullets">
                {bullets_html}
            </div>
            <div class="interp-note">
                ⓘ Metric-by-metric interpretation. No single method is automatically 
                declared the winner — results depend on actual benchmark outcomes.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _fmt_metric(v, metric: str) -> str:
    if v is None:
        return "N/A"
    if "latency" in metric:
        return f"{v:.3f}s"
    return f"{v:.1%}"


def _get_reason(metric: str, winner: str) -> str:
    """Return a brief domain-specific explanation for why a method won on a metric."""
    reasons = {
        ("recall_at_k", "hybrid"): (
            "Semantic vector retrieval likely identified relevant files that "
            "keyword/graph traversal alone missed."
        ),
        ("recall_at_k", "graph"): (
            "AST-based graph traversal likely followed explicit call-graph edges "
            "to reach files that semantic similarity missed."
        ),
        ("precision_at_k", "hybrid"): (
            "The combined approach may filter noise better by requiring both "
            "semantic relevance and graph connectivity."
        ),
        ("precision_at_k", "graph"): (
            "Graph traversal follows deterministic code structure edges, "
            "potentially reducing irrelevant semantic matches."
        ),
        ("impact_f1", "hybrid"): (
            "Combining vector and graph evidence may surface more components "
            "than graph traversal alone."
        ),
        ("impact_f1", "graph"): (
            "AST-based graph traversal may follow explicit dependency edges "
            "more precisely for impact detection."
        ),
        ("correctness", "hybrid"): (
            "Richer combined context from both retrieval sources likely "
            "provided better material for the LLM."
        ),
        ("correctness", "graph"): (
            "Graph-structured context may have provided more precise, "
            "less noisy material for answer generation."
        ),
        ("faithfulness", "hybrid"): (
            "Larger combined context may contain more tokens that appear "
            "in the generated answer."
        ),
        ("faithfulness", "graph"): (
            "Graph-focused context may be more concise and directly "
            "referenced by the generated answer."
        ),
        ("total_latency_s", "hybrid"): (
            "Hybrid retrieval avoids a full vector search when graph "
            "traversal resolves queries quickly."
        ),
        ("total_latency_s", "graph"): (
            "Pure graph traversal skips the embedding step, reducing "
            "total computation time."
        ),
    }
    return reasons.get((metric, winner), "")


# ─────────────────────────────────────────────────────────────────────────────
# Section F — Detailed Results
# ─────────────────────────────────────────────────────────────────────────────

def _render_detailed_results(df: pd.DataFrame):
    with st.expander("📋 Detailed Results — Inspect Every Question", expanded=False):
        st.markdown(
            "Filter and explore per-question results. "
            "**N/A** indicates the metric could not be calculated (unannotated or empty)."
        )

        # Filters
        fil_col1, fil_col2 = st.columns(2)
        with fil_col1:
            categories = ["All"] + sorted(df["category"].dropna().unique().tolist())
            cat_filter = st.selectbox("Filter by Category:", categories, key="detail_cat_filter")
        with fil_col2:
            modes = ["All"] + sorted(df["mode"].dropna().unique().tolist())
            mode_filter = st.selectbox("Filter by Mode:", modes, key="detail_mode_filter")

        filtered = df.copy()
        if cat_filter != "All":
            filtered = filtered[filtered["category"] == cat_filter]
        if mode_filter != "All":
            filtered = filtered[filtered["mode"] == mode_filter]

        # Select and format display columns
        display_cols = [
            "question_id", "category", "mode",
            "precision_at_k", "recall_at_k",
            "impact_precision", "impact_recall", "impact_f1",
            "correctness", "faithfulness",
            "retrieval_latency_s", "llm_latency_s", "total_latency_s",
            "status",
        ]
        display_cols = [c for c in display_cols if c in filtered.columns]
        display_df = filtered[display_cols].copy()

        # Format percentage columns
        pct_cols = [
            "precision_at_k", "recall_at_k",
            "impact_precision", "impact_recall", "impact_f1",
            "correctness", "faithfulness",
        ]
        for col in pct_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda v: "N/A" if _is_nan(v) else f"{float(v):.1%}"
                )

        # Format latency columns
        lat_cols = ["retrieval_latency_s", "llm_latency_s", "total_latency_s"]
        for col in lat_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda v: "N/A" if _is_nan(v) else f"{float(v):.3f}s"
                )

        # Rename columns for readability
        col_rename = {
            "question_id": "Question ID",
            "category": "Category",
            "mode": "Mode",
            "precision_at_k": "Precision@K",
            "recall_at_k": "Recall@K",
            "impact_precision": "Impact Prec.",
            "impact_recall": "Impact Rec.",
            "impact_f1": "Impact F1",
            "correctness": "Correctness",
            "faithfulness": "Faithfulness",
            "retrieval_latency_s": "Retr. Latency",
            "llm_latency_s": "LLM Latency",
            "total_latency_s": "Total Latency",
            "status": "Status",
        }
        display_df = display_df.rename(columns=col_rename)

        st.dataframe(display_df, use_container_width=True, height=380)

        # CSV export (raw numeric values, not formatted strings)
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="📥 Export Full Results to CSV",
            data=csv_data,
            file_name="repomind_benchmark_results.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Section G — Metric Glossary
# ─────────────────────────────────────────────────────────────────────────────

def _render_glossary():
    with st.expander("📖 What Do These Metrics Mean? (Glossary)", expanded=False):
        st.markdown(
            """
            | Metric | Plain English | Formula |
            |---|---|---|
            | **Precision@K** | Of the files the system retrieved, how many were actually relevant? | TP / K |
            | **Recall@K** | Of all relevant files, how many did the system find? | TP / \|Expected\| |
            | **Impact Precision** | Of the components predicted to be affected, how many were actually affected? | TP / (TP + FP) |
            | **Impact Recall** | Of all components that are truly affected, how many did the system identify? | TP / (TP + FN) |
            | **Impact F1** | Balance between impact precision and recall (harmonic mean). | 2·P·R / (P+R) |
            | **Answer Correctness** | How much does the generated answer overlap with the reference answer? (token F1) | Token-level F1 vs reference |
            | **Faithfulness** | How much of the generated answer is supported by the retrieved evidence? (lexical approximation) | Grounded tokens / Answer tokens |
            | **Retrieval Latency** | Time spent retrieving relevant context (vector search + graph traversal). | Seconds |
            | **LLM Latency** | Time spent generating the answer using the language model. | Seconds |
            | **Total Latency** | End-to-end time from question to answer. | Retrieval + LLM Latency |

            **Notes on N/A values:**
            - **N/A** means the metric *cannot* be calculated — not that the system scored zero.
            - Recall cannot be computed when no ground-truth files are annotated.
            - Faithfulness cannot be computed when the answer is empty.
            - A genuine zero score is displayed as **0.0%**, not N/A.

            **About Faithfulness:**
            The faithfulness score here is a *lexical* approximation — it checks whether
            technical terms in the answer appear in the retrieved context. It does *not* use
            NLI-based semantic entailment. Treat it as a signal, not a definitive measure.
            """,
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Empty-state placeholder
# ─────────────────────────────────────────────────────────────────────────────

def _render_empty_state():
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-state-icon">📊</div>
            <div class="empty-state-title">Ready for Ground-Truth Evaluation</div>
            <div class="empty-state-desc">
                Select your benchmark source above and click <strong>🚀 Run Benchmark</strong> to evaluate
                GraphRAG vs Hybrid GraphRAG with mathematically proven AST ground truth.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            <div style="background:#131b2e; border:1px solid #1e293b; border-radius:10px; padding:18px; height:100%;">
                <h4 style="color:#60a5fa; margin-top:0;">⚡ Deterministic AST Ground Truth</h4>
                <p style="color:#94a3b8; font-size:0.9rem; line-height:1.5;">
                    Instead of relying on an LLM to guess or invent the test questions and answers (circular evaluation bias),
                    RepoMind directly extracts ground-truth caller chains, test suites, and imports from the 
                    <strong>Python compiler's Abstract Syntax Tree (AST)</strong>. Every dependency is an unshakeable mathematical fact with <strong>0% hallucination</strong>.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            """
            <div style="background:#131b2e; border:1px solid #1e293b; border-radius:10px; padding:18px; height:100%;">
                <h4 style="color:#34d399; margin-top:0;">🎯 Works on Any Arbitrary Repository</h4>
                <p style="color:#94a3b8; font-size:0.9rem; line-height:1.5;">
                    Whenever you ingest a new GitHub URL, RepoMind's AST scanner identifies the top architectural hubs,
                    computes their exact upstream and downstream blast radius, and synthesizes a dedicated 
                    <strong>custom What-If benchmark suite on the fly</strong> without requiring manual human annotations.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────────────────────────────────────
# CSS injection
# ─────────────────────────────────────────────────────────────────────────────

def _inject_eval_css():
    st.markdown(
        """
        <style>
        /* ── Eval Page Layout ───────────────────────────────────── */
        .eval-header {
            display: flex;
            align-items: flex-start;
            gap: 24px;
            padding: 20px 0 12px 0;
        }
        .eval-title {
            font-size: 1.9rem;
            font-weight: 800;
            background: linear-gradient(90deg, #60a5fa, #a78bfa, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
        }
        .eval-subtitle {
            color: #94a3b8;
            font-size: 1rem;
            margin-top: 6px;
        }
        .eval-divider {
            border-top: 1px solid #1e293b;
            margin: 20px 0;
        }
        .mode-badge {
            display: inline-block;
            padding: 1px 8px;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .mode-graph  { background: rgba(139,92,246,0.15); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }
        .mode-hybrid { background: rgba(16,185,129,0.15);  color: #34d399; border: 1px solid rgba(16,185,129,0.3); }

        /* ── Stat Pills ─────────────────────────────────────────── */
        .stat-pill {
            background: #131b2e;
            border: 1px solid #1e293b;
            border-left: 3px solid #6366f1;
            border-radius: 10px;
            padding: 10px 14px;
            margin-bottom: 8px;
        }
        .stat-pill-label {
            font-size: 0.72rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .stat-pill-value {
            font-size: 1rem;
            font-weight: 700;
            color: #f1f5f9;
            margin-top: 2px;
            word-break: break-all;
        }

        /* ── Progress ───────────────────────────────────────────── */
        .progress-msg {
            font-size: 0.85rem;
            color: #94a3b8;
            padding: 4px 0;
        }
        .progress-msg.success { color: #34d399; }

        /* ── KPI Cards ──────────────────────────────────────────── */
        .kpi-card {
            background: #131b2e;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 16px 18px;
            margin-bottom: 8px;
            height: 100%;
            transition: border-color 0.15s;
        }
        .kpi-card:hover { border-color: #334155; }
        .kpi-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
            flex-wrap: wrap;
        }
        .kpi-icon { font-size: 1.3rem; }
        .kpi-title {
            font-size: 0.9rem;
            font-weight: 700;
            color: #f1f5f9;
            flex: 1;
        }
        .kpi-metric-name {
            font-size: 0.72rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }
        .kpi-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }
        .kpi-mode {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 1px 7px;
            border-radius: 999px;
        }
        .graph-label  { background: rgba(139,92,246,0.15); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }
        .hybrid-label { background: rgba(16,185,129,0.15);  color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
        .kpi-val {
            font-size: 1.15rem;
            font-weight: 700;
            color: #f1f5f9;
            font-variant-numeric: tabular-nums;
        }
        .kpi-diff {
            font-size: 0.75rem;
            color: #94a3b8;
            margin: 4px 0 6px 0;
            font-variant-numeric: tabular-nums;
        }
        .kpi-desc {
            font-size: 0.75rem;
            color: #64748b;
            line-height: 1.4;
            margin-top: 8px;
            border-top: 1px solid #1e293b;
            padding-top: 8px;
        }

        /* Winner badges */
        .winner-badge {
            font-size: 0.65rem;
            font-weight: 700;
            padding: 1px 7px;
            border-radius: 999px;
            white-space: nowrap;
        }
        .winner-badge.hybrid { background: rgba(16,185,129,0.2);  color: #34d399; }
        .winner-badge.graph  { background: rgba(139,92,246,0.2); color: #a78bfa; }
        .winner-badge.tie    { background: rgba(100,116,139,0.2); color: #94a3b8; }

        /* ── Interpretation box ─────────────────────────────────── */
        .interpretation-box {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 14px;
            padding: 20px 24px;
        }
        .verdict-banner {
            font-size: 1rem;
            font-weight: 700;
            border-left: 4px solid;
            padding: 8px 14px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 16px;
            background: rgba(255,255,255,0.03);
        }
        .interp-bullets { }
        .interp-bullet {
            font-size: 0.88rem;
            color: #cbd5e1;
            line-height: 1.6;
            margin: 6px 0;
            padding-left: 4px;
        }
        .interp-note {
            font-size: 0.75rem;
            color: #64748b;
            margin-top: 14px;
            padding-top: 10px;
            border-top: 1px solid #1e293b;
        }

        /* ── Empty state ────────────────────────────────────────── */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #64748b;
        }
        .empty-state-icon   { font-size: 3rem; margin-bottom: 12px; }
        .empty-state-title  { font-size: 1.1rem; font-weight: 600; color: #94a3b8; margin-bottom: 8px; }
        .empty-state-desc   { font-size: 0.88rem; line-height: 1.6; max-width: 480px; margin: 0 auto; }
        </style>
        """,
        unsafe_allow_html=True,
    )
