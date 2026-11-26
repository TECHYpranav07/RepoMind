"""Page 5: Evaluation & Benchmark Dashboard — Simplified & Streamlined.

Features:
  - Page Header: Clean stats (Repository, Graph Nodes, Last Run)
  - Benchmark Controls: 2-row layout with Live AST vs Curated source and execution speed
  - Executive Summary: 4 core KPI cards with clear winner indicators
  - Performance Charts: 2x2 grid of comparative Plotly charts
  - Smart Interpretation: Executive verdict banner + concise comparison matrix
  - Detailed Results: Filterable table + CSV export in a dedicated expander
  - Query Deep Dive: Side-by-side Ground Truth vs RAG retrieval in a dedicated expander
  - Metric Glossary: Plain-English metric explanations
"""
from __future__ import annotations

import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from repomind.evaluation.benchmark import BenchmarkRunner, _is_nan
from repomind.evaluation.dataset import BENCHMARK_DATASET, generate_ast_ground_truth_dataset


# ─────────────────────────────────────────────────────────────────────────────
# Public Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def render_evaluation():
    """Render the simplified Evaluation & Benchmark dashboard."""
    _inject_eval_css()

    if not st.session_state.get("repo_loaded", False):
        st.warning(
            "⚠️ No repository loaded. "
            "Please go to **Home / Dashboard** and ingest a repository first."
        )
        return

    meta = st.session_state.get("repo_meta")
    hybrid_retriever = st.session_state.get("hybrid_retriever")
    answer_generator = st.session_state.get("answer_generator")
    graph = st.session_state.get("graph")

    # Header
    _render_header(meta, graph)

    # Controls
    run_clicked, selected_modes, num_questions, gt_source, speed_mode = _render_controls()

    if run_clicked:
        if not selected_modes:
            st.error("Please select at least one retrieval mode.")
        elif hybrid_retriever is None:
            st.error("Retriever not initialized. Please reload the repository.")
        else:
            _run_and_store_benchmark(
                hybrid_retriever, answer_generator, selected_modes,
                num_questions, gt_source, speed_mode, graph
            )

    df: Optional[pd.DataFrame] = st.session_state.get("benchmark_results_df")

    if df is None or df.empty:
        _render_empty_state()
        _render_glossary()
        return

    st.markdown('<div class="eval-divider"></div>', unsafe_allow_html=True)

    # Executive Summary (KPIs)
    _render_kpi_cards(df)

    st.markdown('<div class="eval-divider"></div>', unsafe_allow_html=True)

    # Performance Charts (2x2 grid)
    _render_charts(df)

    st.markdown('<div class="eval-divider"></div>', unsafe_allow_html=True)

    # Smart Interpretation (Verdict + Matrix)
    _render_interpretation(df)

    st.markdown('<div class="eval-divider"></div>', unsafe_allow_html=True)

    # Detailed Results (Expander)
    _render_detailed_results(df)

    # Query Deep Dive vs Ground Truth (Expander)
    _render_query_deep_dive(df)

    # Glossary (Expander)
    _render_glossary()


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

def _render_header(meta, graph):
    last_run = st.session_state.get("benchmark_last_run")
    last_run_str = last_run.strftime("%H:%M:%S") if last_run else "Not run yet"
    repo_name = meta.full_name if meta else "Loaded Repo"
    node_count = graph.number_of_nodes() if graph else 0

    st.markdown(
        """
        <div class="eval-header">
            <h1 class="eval-title">Evaluation &amp; Benchmark</h1>
            <p class="eval-subtitle">
                Compare <span class="mode-badge mode-graph">GraphRAG</span> vs 
                <span class="mode-badge mode-hybrid">Hybrid GraphRAG</span> against 
                <span class="mode-badge mode-ast">⚡ Deterministic AST Ground Truth</span>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1.5, 1.2, 1.3])
    with c1:
        _stat_pill("📦 Active Repository", repo_name, "#6366f1")
    with c2:
        _stat_pill("🕸️ Code Graph Nodes", f"{node_count:,} AST nodes", "#10b981")
    with c3:
        _stat_pill("⏱️ Last Run Time", last_run_str, "#f59e0b")


def _stat_pill(label: str, value: str, border_color: str):
    st.markdown(
        f"""
        <div class="stat-pill" style="border-left-color:{border_color};">
            <div class="stat-pill-label">{label}</div>
            <div class="stat-pill-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Controls (Clean 2-Row Layout)
# ─────────────────────────────────────────────────────────────────────────────

def _render_controls():
    with st.container():
        st.markdown('<div class="controls-panel">', unsafe_allow_html=True)

        # Row 1: Source & Engine
        r1_c1, r1_c2 = st.columns([1.5, 1.5])
        with r1_c1:
            gt_source = st.selectbox(
                "Ground Truth Source:",
                options=[
                    "⚡ Live AST Ground Truth (Auto-extracted from Repo)",
                    "📚 Curated Architecture Golden Set",
                ],
                index=0,
                key="eval_gt_source",
                help="Live AST directly inspects Python syntax trees to compute ground-truth dependencies with 0% hallucination.",
            )
        with r1_c2:
            speed_mode = st.selectbox(
                "Execution Engine:",
                options=[
                    "⚡ Fast Parallel (Gemini Flash · 2-3s)",
                    "🚀 Instant Turbo (Local Engine · <1s)",
                ],
                index=0,
                key="eval_speed_mode",
                help="Fast Parallel runs queries concurrently. Instant Turbo uses local deterministic AST synthesis with 0 API delay.",
            )

        # Row 2: Mode, Count, Run Button
        r2_c1, r2_c2, r2_c3 = st.columns([1.6, 0.8, 1.0])
        with r2_c1:
            mode_choice = st.radio(
                "Retrieval Modes to Test:",
                options=["Both (GraphRAG + Hybrid)", "GraphRAG only", "Hybrid only"],
                index=0,
                horizontal=True,
                key="eval_mode_choice",
            )
        with r2_c2:
            num_questions = st.number_input(
                "Questions:",
                min_value=1,
                max_value=10,
                value=3,
                step=1,
                key="eval_num_questions",
                help="Number of benchmark queries to evaluate.",
            )
        with r2_c3:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            is_running = st.session_state.get("benchmark_running", False)
            run_clicked = st.button(
                "🚀 Run Benchmark" if not is_running else "⏳ Running…",
                type="primary",
                use_container_width=True,
                disabled=is_running,
                key="eval_run_btn",
            )

        st.markdown('</div>', unsafe_allow_html=True)

    mode_map = {
        "Both (GraphRAG + Hybrid)": ["graph", "hybrid"],
        "GraphRAG only": ["graph"],
        "Hybrid only": ["hybrid"],
    }
    selected_modes = mode_map[mode_choice]

    return run_clicked, selected_modes, int(num_questions), gt_source, speed_mode


def _run_and_store_benchmark(hybrid_retriever, answer_generator, modes, num_questions, gt_source, speed_mode, graph=None):
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
        status_label.markdown(f'<div class="progress-msg">⏳ {msg}</div>', unsafe_allow_html=True)
        progress_bar.progress(min(pct, 1.0))

    try:
        if "Turbo" in speed_mode:
            from repomind.llm.model_provider import LocalHeuristicSynthesizer
            from repomind.llm.answer_generator import AnswerGenerator
            eval_gen = AnswerGenerator(LocalHeuristicSynthesizer())
        else:
            eval_gen = answer_generator or AnswerGenerator()

        runner = BenchmarkRunner(hybrid_retriever, eval_gen, dataset)
        df_results = runner.run_benchmark(modes=modes, progress_callback=prog_cb, parallel=True, max_workers=4)

        st.session_state["benchmark_results_df"] = df_results
        st.session_state["benchmark_last_run"] = datetime.datetime.now()
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
# Executive Summary KPI Cards
# ─────────────────────────────────────────────────────────────────────────────

def _render_kpi_cards(df: pd.DataFrame):
    st.markdown("### 📊 Executive Summary")

    agg = df.groupby("mode").mean(numeric_only=True).reset_index()
    graph_row = agg[agg["mode"] == "GRAPH"].iloc[0] if "GRAPH" in agg["mode"].values else None
    hybrid_row = agg[agg["mode"] == "HYBRID"].iloc[0] if "HYBRID" in agg["mode"].values else None

    kpis = [
        {
            "title": "Retrieval Recall",
            "metric": "recall_at_k",
            "icon": "🎯",
            "unit": "%",
            "desc": "% of relevant files successfully retrieved",
            "higher_is_better": True,
        },
        {
            "title": "Impact Detection",
            "metric": "impact_f1",
            "icon": "🔍",
            "unit": "%",
            "desc": "F1 score for detecting blast-radius affected components",
            "higher_is_better": True,
        },
        {
            "title": "Answer Faithfulness",
            "metric": "faithfulness",
            "icon": "✅",
            "unit": "%",
            "desc": "% of generated answer grounded in retrieved code",
            "higher_is_better": True,
        },
        {
            "title": "Response Speed",
            "metric": "total_latency_s",
            "icon": "⚡",
            "unit": "s",
            "desc": "Total end-to-end execution time",
            "higher_is_better": False,
        },
    ]

    cols = st.columns(4)
    for col, kpi in zip(cols, kpis):
        with col:
            _render_single_kpi(kpi, graph_row, hybrid_row)


def _render_single_kpi(kpi: dict, graph_row, hybrid_row):
    metric = kpi["metric"]
    is_latency = kpi["unit"] == "s"
    higher_is_better = kpi["higher_is_better"]

    g_val = _get_num(graph_row, metric)
    h_val = _get_num(hybrid_row, metric)

    def _fmt(v):
        if v is None:
            return "N/A"
        return f"{v:.3f}s" if is_latency else f"{v:.1%}"

    # Determine winner badge
    winner_pill = ""
    if g_val is not None and h_val is not None:
        diff = h_val - g_val
        threshold = 0.001 if not is_latency else 0.05
        if abs(diff) < threshold:
            winner_pill = '<span class="kpi-tag tie">Tied</span>'
        elif (diff > 0 and higher_is_better) or (diff < 0 and not higher_is_better):
            winner_pill = '<span class="kpi-tag hybrid">Hybrid leads</span>'
        else:
            winner_pill = '<span class="kpi-tag graph">Graph leads</span>'

    g_str = _fmt(g_val)
    h_str = _fmt(h_val)

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-top">
                <span class="kpi-icon">{kpi['icon']}</span>
                <span class="kpi-title">{kpi['title']}</span>
                {winner_pill}
            </div>
            <div class="kpi-body">
                <div class="kpi-row">
                    <span class="mode-badge mode-graph">Graph</span>
                    <span class="kpi-val">{g_str}</span>
                </div>
                <div class="kpi-row">
                    <span class="mode-badge mode-hybrid">Hybrid</span>
                    <span class="kpi-val">{h_str}</span>
                </div>
            </div>
            <div class="kpi-footer">{kpi['desc']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _get_num(row, col: str) -> Optional[float]:
    if row is None:
        return None
    val = row.get(col)
    if _is_nan(val):
        return None
    return float(val)


# ─────────────────────────────────────────────────────────────────────────────
# Performance Charts (Clean 2x2 Grid)
# ─────────────────────────────────────────────────────────────────────────────

def _render_charts(df: pd.DataFrame):
    st.markdown("### 📈 Performance Visualizations")

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(BenchmarkRunner.create_retrieval_chart(df), use_container_width=True)
    with c2:
        st.plotly_chart(BenchmarkRunner.create_impact_chart(df), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(BenchmarkRunner.create_answer_quality_chart(df), use_container_width=True)
    with c4:
        st.plotly_chart(BenchmarkRunner.create_latency_chart(df), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Smart Interpretation (Executive Verdict + Comparison Matrix)
# ─────────────────────────────────────────────────────────────────────────────

def _render_interpretation(df: pd.DataFrame):
    st.markdown("### 💡 Key Takeaways & Comparison Matrix")

    agg = df.groupby("mode").mean(numeric_only=True).reset_index()
    graph_row = agg[agg["mode"] == "GRAPH"].iloc[0] if "GRAPH" in agg["mode"].values else None
    hybrid_row = agg[agg["mode"] == "HYBRID"].iloc[0] if "HYBRID" in agg["mode"].values else None

    if graph_row is None and hybrid_row is None:
        st.info("Run benchmark to view comparison insights.")
        return

    # Metrics definition
    metrics_meta = [
        ("recall_at_k", "Retrieval Recall", True, "%", "Broader semantic file discovery"),
        ("precision_at_k", "Retrieval Precision", True, "%", "Noise filtration in context"),
        ("impact_f1", "Impact Detection F1", True, "%", "Deterministic AST dependency traversal"),
        ("correctness", "Answer Correctness", True, "%", "Overlap with golden reference answer"),
        ("faithfulness", "Answer Faithfulness", True, "%", "Evidence grounding in code chunks"),
        ("total_latency_s", "Total Latency", False, "s", "Zero embedding overhead"),
    ]

    h_wins, g_wins, total = 0, 0, 0
    table_rows = []

    for key, label, higher_is_better, unit, advantage_note in metrics_meta:
        g = _get_num(graph_row, key)
        h = _get_num(hybrid_row, key)

        if g is None or h is None:
            continue

        total += 1
        diff = h - g
        is_lat = unit == "s"
        threshold = 0.005 if not is_lat else 0.05

        def _format_val(v):
            return f"{v:.3f}s" if is_lat else f"{v:.1%}"

        if abs(diff) < threshold:
            winner = "🤝 Tied"
            winner_class = "color:#94a3b8;"
            takeaway = "Comparable performance"
        elif (diff > 0 and higher_is_better) or (diff < 0 and not higher_is_better):
            h_wins += 1
            winner = "🟢 Hybrid"
            winner_class = "color:#34d399; font-weight:700;"
            takeaway = f"Hybrid +{abs(diff):.1%}" if not is_lat else f"Hybrid {abs(diff):.3f}s faster"
        else:
            g_wins += 1
            winner = "🟣 GraphRAG"
            winner_class = "color:#a78bfa; font-weight:700;"
            takeaway = f"GraphRAG +{abs(diff):.1%}" if not is_lat else f"Graph {abs(diff):.3f}s faster"

        table_rows.append(
            f"""
            <tr>
                <td style="font-weight:600; color:#f8fafc;">{label}</td>
                <td style="color:#cbd5e1;">{_format_val(g)}</td>
                <td style="color:#cbd5e1;">{_format_val(h)}</td>
                <td style="{winner_class}">{winner}</td>
                <td style="color:#94a3b8; font-size:0.85rem;">{takeaway}</td>
            </tr>
            """
        )

    # Verdict
    if h_wins > g_wins:
        verdict = f"🏆 Hybrid GraphRAG leads across {h_wins} of {total} key metrics with superior recall and context grounding."
        v_border = "#10b981"
        v_color = "#34d399"
    elif g_wins > h_wins:
        verdict = f"🏆 GraphRAG leads across {g_wins} of {total} key metrics with tighter deterministic AST precision."
        v_border = "#8b5cf6"
        v_color = "#a78bfa"
    else:
        verdict = "🤝 Balanced trade-off: GraphRAG offers faster AST precision, while Hybrid offers broader semantic discovery."
        v_border = "#f59e0b"
        v_color = "#fbbf24"

    rows_html = "".join(table_rows)

    st.markdown(
        f"""
        <div class="verdict-banner" style="border-left-color:{v_border}; color:{v_color};">
            {verdict}
        </div>
        <div class="matrix-card">
            <table class="matrix-table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>GraphRAG</th>
                        <th>Hybrid GraphRAG</th>
                        <th>Leading Approach</th>
                        <th>Summary</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Detailed Results (Expander)
# ─────────────────────────────────────────────────────────────────────────────

def _render_detailed_results(df: pd.DataFrame):
    with st.expander("📋 Detailed Results Table & CSV Export", expanded=False):
        f1, f2 = st.columns(2)
        with f1:
            categories = ["All"] + sorted(df["category"].dropna().unique().tolist())
            cat_filter = st.selectbox("Filter Category:", categories, key="det_cat_filter")
        with f2:
            modes = ["All"] + sorted(df["mode"].dropna().unique().tolist())
            mode_filter = st.selectbox("Filter Mode:", modes, key="det_mode_filter")

        filtered = df.copy()
        if cat_filter != "All":
            filtered = filtered[filtered["category"] == cat_filter]
        if mode_filter != "All":
            filtered = filtered[filtered["mode"] == mode_filter]

        cols_wanted = [
            "question_id", "category", "mode",
            "recall_at_k", "precision_at_k", "impact_f1",
            "correctness", "faithfulness", "total_latency_s", "status"
        ]
        cols_present = [c for c in cols_wanted if c in filtered.columns]
        display_df = filtered[cols_present].copy()

        # Format percentages
        for p_col in ["recall_at_k", "precision_at_k", "impact_f1", "correctness", "faithfulness"]:
            if p_col in display_df.columns:
                display_df[p_col] = display_df[p_col].apply(
                    lambda v: "N/A" if _is_nan(v) else f"{float(v):.1%}"
                )

        if "total_latency_s" in display_df.columns:
            display_df["total_latency_s"] = display_df["total_latency_s"].apply(
                lambda v: "N/A" if _is_nan(v) else f"{float(v):.3f}s"
            )

        display_df = display_df.rename(columns={
            "question_id": "QID",
            "category": "Category",
            "mode": "Mode",
            "recall_at_k": "Recall@K",
            "precision_at_k": "Precision@K",
            "impact_f1": "Impact F1",
            "correctness": "Correctness",
            "faithfulness": "Faithfulness",
            "total_latency_s": "Total Latency",
            "status": "Status"
        })

        st.dataframe(display_df, use_container_width=True, height=280)

        st.download_button(
            label="📥 Download Full Benchmark CSV",
            data=df.to_csv(index=False),
            file_name="repomind_benchmark_results.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Query Deep Dive vs Ground Truth (Expander)
# ─────────────────────────────────────────────────────────────────────────────

def _render_query_deep_dive(df: pd.DataFrame):
    if df.empty or "question_id" not in df.columns:
        return

    with st.expander("🔬 Query & Retrieval Deep Dive vs. Ground Truth", expanded=False):
        qids = df["question_id"].unique().tolist()

        def _fmt_qid(q_val):
            rows = df[df["question_id"] == q_val]
            if not rows.empty:
                q_text = rows.iloc[0].get("question") or q_val
                return f"[{q_val}] {q_text[:70]}..."
            return q_val

        selected_qid = st.selectbox(
            "Select Question to Inspect:",
            options=qids,
            format_func=_fmt_qid,
            key="deep_dive_qid_simple",
        )

        q_data = df[df["question_id"] == selected_qid]
        if q_data.empty:
            return

        first_row = q_data.iloc[0]
        q_text = first_row.get("question") or selected_qid
        category = first_row.get("category", "General")
        exp_files = first_row.get("expected_files") or []
        if isinstance(exp_files, str):
            exp_files = [f.strip() for f in exp_files.split(",") if f.strip()]
        exp_comps = first_row.get("expected_components") or []
        if isinstance(exp_comps, str):
            exp_comps = [c.strip() for c in exp_comps.split(",") if c.strip()]
        ref_ans = first_row.get("reference_answer", "—")

        # Ground Truth Box
        files_html = "".join(f'<span class="badge-code">📄 {f}</span>' for f in exp_files) if exp_files else "None"
        comps_html = "".join(f'<span class="badge-comp">🧩 {c}</span>' for c in exp_comps) if exp_comps else "None"

        st.markdown(
            f"""
            <div class="gt-card">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <span style="font-size:0.8rem; font-weight:700; color:#60a5fa; text-transform:uppercase;">
                        🎯 Verified Ground Truth · {category}
                    </span>
                    <span class="mode-badge mode-ast">Compiler AST Truth</span>
                </div>
                <h4 style="margin:4px 0 10px 0; color:#f8fafc;">Query: "{q_text}"</h4>
                <div style="margin-bottom:6px;"><strong>Target Files:</strong> {files_html}</div>
                <div style="margin-bottom:8px;"><strong>Blast Radius Components:</strong> {comps_html}</div>
                <div class="gt-ref-answer">
                    <strong>Reference Answer:</strong> {ref_ans}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Mode cards side by side
        modes_in_q = q_data["mode"].unique().tolist()
        cols = st.columns(len(modes_in_q))

        for idx, m_name in enumerate(modes_in_q):
            m_row = q_data[q_data["mode"] == m_name].iloc[0]
            is_hybrid = "HYBRID" in m_name
            accent = "#10b981" if is_hybrid else "#8b5cf6"
            badge_class = "mode-hybrid" if is_hybrid else "mode-graph"

            ret_files = m_row.get("retrieved_files") or []
            if isinstance(ret_files, str):
                ret_files = [f.strip() for f in ret_files.split(",") if f.strip()]
            ret_comps = m_row.get("retrieved_components") or []
            if isinstance(ret_comps, str):
                ret_comps = [c.strip() for c in ret_comps.split(",") if c.strip()]
            gen_ans = m_row.get("generated_answer") or "—"

            rec = m_row.get("recall_at_k")
            f1 = m_row.get("impact_f1")
            lat = m_row.get("total_latency_s")

            rec_str = f"{rec:.0%}" if not _is_nan(rec) else "N/A"
            f1_str = f"{f1:.0%}" if not _is_nan(f1) else "N/A"
            lat_str = f"{lat:.2f}s" if lat is not None else "—"

            files_chips = "".join(
                f'<span class="badge-code" style="color:{"#34d399" if f in exp_files else "#94a3b8"};">{"✓ " if f in exp_files else ""}{f}</span>'
                for f in ret_files[:4]
            ) or '<span style="color:#64748b;">No files retrieved</span>'

            comps_chips = "".join(
                f'<span class="badge-comp" style="color:{"#34d399" if c in exp_comps else "#60a5fa"};">{"✓ " if c in exp_comps else ""}{c}</span>'
                for c in ret_comps[:4]
            ) or '<span style="color:#64748b;">None detected</span>'

            with cols[idx]:
                st.markdown(
                    f"""
                    <div class="deep-card" style="border-top:3px solid {accent};">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <span class="mode-badge {badge_class}">{m_name} RAG</span>
                            <span style="color:#94a3b8; font-size:0.8rem;">⏱️ {lat_str}</span>
                        </div>
                        <div style="display:flex; gap:6px; margin-bottom:10px;">
                            <span class="kpi-mini">Recall: <b>{rec_str}</b></span>
                            <span class="kpi-mini">Impact F1: <b>{f1_str}</b></span>
                        </div>
                        <div style="margin-bottom:6px; font-size:0.8rem; color:#94a3b8;"><b>Retrieved Files:</b></div>
                        <div style="margin-bottom:8px;">{files_chips}</div>
                        <div style="margin-bottom:6px; font-size:0.8rem; color:#94a3b8;"><b>Detected Components:</b></div>
                        <div style="margin-bottom:8px;">{comps_chips}</div>
                        <div class="answer-box">
                            <strong style="color:{accent}; font-size:0.8rem;">Generated Answer:</strong>
                            <p style="margin:4px 0 0 0; font-size:0.85rem; color:#cbd5e1; line-height:1.4;">{gen_ans}</p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Context viewer inside tab
        with st.expander("🔍 Inspect Exact Prompt Context Sent to LLM", expanded=False):
            ctx_tabs = st.tabs([f"{m} Context" for m in modes_in_q])
            for i, m_name in enumerate(modes_in_q):
                with ctx_tabs[i]:
                    ctx = q_data[q_data["mode"] == m_name].iloc[0].get("prompt_context", "")
                    if ctx:
                        st.code(ctx, language="markdown")
                    else:
                        st.caption("No prompt context recorded.")


# ─────────────────────────────────────────────────────────────────────────────
# Metric Glossary (Expander)
# ─────────────────────────────────────────────────────────────────────────────

def _render_glossary():
    with st.expander("📖 Metric Glossary & Evaluation Methodology", expanded=False):
        st.markdown(
            """
            | Metric | Plain English | Formula |
            |---|---|---|
            | **Recall@K** | Did the system find all relevant files? | True Positives / Expected Files |
            | **Precision@K** | Were the retrieved files actually relevant? | True Positives / K Retrieved |
            | **Impact F1** | Accuracy in predicting affected blast radius | 2 · Precision · Recall / (P + R) |
            | **Answer Correctness** | Semantic token overlap with golden answer | Token-level F1 vs reference |
            | **Answer Faithfulness** | Was the answer grounded in retrieved code? | Grounded tokens / Answer tokens |
            | **Total Latency** | End-to-end execution time (Retrieval + LLM) | Seconds |

            **Why Live AST Ground Truth Matters:**
            Conventional RAG benchmarks rely on LLM-generated questions and answers, introducing circular evaluation bias.
            RepoMind extracts actual callers, test suites, and imports from the **Python Abstract Syntax Tree (AST)**, 
            guaranteeing 100% objective, mathematically verifiable benchmark facts with zero hallucination.
            """,
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Empty State
# ─────────────────────────────────────────────────────────────────────────────

def _render_empty_state():
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-state-icon">📊</div>
            <h3 style="color:#f8fafc; margin-bottom:8px;">Ready for Ground-Truth Evaluation</h3>
            <p style="color:#94a3b8; font-size:0.95rem; max-width:540px; margin:0 auto 20px auto; line-height:1.5;">
                Select your parameters above and click <strong>🚀 Run Benchmark</strong> to evaluate 
                GraphRAG vs Hybrid GraphRAG against mathematically verified repository facts.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div class="info-card">
                <h4 style="color:#60a5fa; margin-top:0;">⚡ Live AST Ground Truth</h4>
                <p style="color:#94a3b8; font-size:0.88rem; line-height:1.5; margin-bottom:0;">
                    Synthesizes benchmark test suites directly from the repository's syntax tree. 
                    Target files, callers, and test suites are 100% deterministic with zero LLM hallucination.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="info-card">
                <h4 style="color:#34d399; margin-top:0;">🎯 Works on Any Repository</h4>
                <p style="color:#94a3b8; font-size:0.88rem; line-height:1.5; margin-bottom:0;">
                    No manual test annotations required. RepoMind scans topological hubs in any ingested GitHub repo
                    and automatically generates an explainable What-If benchmark suite on the fly.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# CSS Styling (Clean, Compact, Modern Dark Mode)
# ─────────────────────────────────────────────────────────────────────────────

def _inject_eval_css():
    st.markdown(
        """
        <style>
        /* Header */
        .eval-header { padding: 12px 0 8px 0; }
        .eval-title {
            font-size: 1.85rem;
            font-weight: 800;
            background: linear-gradient(90deg, #60a5fa, #a78bfa, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
        }
        .eval-subtitle { color: #94a3b8; font-size: 0.95rem; margin-top: 4px; }
        .eval-divider { border-top: 1px solid #1e293b; margin: 18px 0; }

        /* Badges */
        .mode-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
        }
        .mode-graph  { background: rgba(139,92,246,0.15); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }
        .mode-hybrid { background: rgba(16,185,129,0.15);  color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
        .mode-ast    { background: rgba(59,130,246,0.15);  color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }

        /* Stat Pills */
        .stat-pill {
            background: #111827;
            border: 1px solid #1e293b;
            border-left: 3px solid #6366f1;
            border-radius: 8px;
            padding: 8px 12px;
        }
        .stat-pill-label { font-size: 0.7rem; color: #64748b; text-transform: uppercase; font-weight: 600; }
        .stat-pill-value { font-size: 0.95rem; font-weight: 700; color: #f1f5f9; margin-top: 2px; }

        /* Controls Panel */
        .controls-panel {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 16px 18px 12px 18px;
            margin: 12px 0;
        }

        /* KPI Cards */
        .kpi-card {
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 14px 16px;
            height: 100%;
        }
        .kpi-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
        .kpi-icon { font-size: 1.15rem; margin-right: 6px; }
        .kpi-title { font-size: 0.88rem; font-weight: 700; color: #f8fafc; flex: 1; }
        .kpi-tag { font-size: 0.65rem; font-weight: 700; padding: 2px 6px; border-radius: 999px; }
        .kpi-tag.hybrid { background: rgba(16,185,129,0.2); color: #34d399; }
        .kpi-tag.graph  { background: rgba(139,92,246,0.2); color: #a78bfa; }
        .kpi-tag.tie    { background: rgba(100,116,139,0.2); color: #94a3b8; }
        .kpi-row { display: flex; justify-content: space-between; align-items: center; margin: 4px 0; }
        .kpi-val { font-size: 1.05rem; font-weight: 700; color: #f8fafc; }
        .kpi-footer { font-size: 0.72rem; color: #64748b; margin-top: 8px; border-top: 1px solid #1e293b; padding-top: 6px; }
        .kpi-mini { background: #1e293b; color: #cbd5e1; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; }

        /* Verdict Banner */
        .verdict-banner {
            font-size: 0.95rem;
            font-weight: 700;
            border-left: 4px solid;
            padding: 10px 14px;
            border-radius: 0 8px 8px 0;
            background: rgba(255,255,255,0.03);
            margin-bottom: 12px;
        }

        /* Matrix Table */
        .matrix-card {
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 10px;
            overflow-x: auto;
        }
        .matrix-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
        .matrix-table th { background: #0f172a; color: #94a3b8; text-align: left; padding: 10px 14px; border-bottom: 1px solid #1e293b; font-size: 0.78rem; text-transform: uppercase; }
        .matrix-table td { padding: 9px 14px; border-bottom: 1px solid #1e293b22; }

        /* Deep Dive & Ground Truth Cards */
        .gt-card {
            background: #0f172a;
            border: 1px solid #3b82f6;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 14px;
        }
        .gt-ref-answer {
            background: #131c31;
            border-left: 3px solid #3b82f6;
            padding: 8px 12px;
            border-radius: 0 6px 6px 0;
            font-size: 0.85rem;
            color: #cbd5e1;
            margin-top: 8px;
        }
        .deep-card {
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 14px;
            height: 100%;
        }
        .badge-code {
            display: inline-block;
            background: #1e293b;
            font-family: monospace;
            font-size: 0.78rem;
            padding: 2px 6px;
            border-radius: 4px;
            margin: 2px 4px 2px 0;
            border: 1px solid #334155;
        }
        .badge-comp {
            display: inline-block;
            background: #1e293b;
            font-family: monospace;
            font-size: 0.78rem;
            padding: 2px 6px;
            border-radius: 4px;
            margin: 2px 4px 2px 0;
            border: 1px solid #0369a1;
        }
        .answer-box {
            background: #090d16;
            padding: 8px 10px;
            border-radius: 6px;
            margin-top: 8px;
            border-left: 2px solid #334155;
        }

        /* Empty State */
        .empty-state { text-align: center; padding: 40px 16px 24px 16px; }
        .empty-state-icon { font-size: 2.5rem; margin-bottom: 8px; }
        .info-card {
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 16px;
            height: 100%;
        }
        .progress-msg { font-size: 0.85rem; color: #94a3b8; padding: 4px 0; }
        .progress-msg.success { color: #34d399; }
        </style>
        """,
        unsafe_allow_html=True,
    )
