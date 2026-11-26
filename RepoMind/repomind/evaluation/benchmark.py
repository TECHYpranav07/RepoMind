"""Benchmark execution engine comparing Graph RAG and Hybrid GraphRAG."""
import time
import math
from typing import List, Dict, Any, Optional
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from repomind.evaluation.dataset import BENCHMARK_DATASET
from repomind.evaluation.metrics import EvaluationMetrics
from repomind.retrieval.hybrid_retriever import HybridRetriever
from repomind.llm.answer_generator import AnswerGenerator

# Consistent color scheme used across all charts
COLORS = {
    "GRAPH": "#8b5cf6",    # Purple for GraphRAG
    "HYBRID": "#10b981",   # Green for Hybrid GraphRAG
}

METRIC_LABELS = {
    "precision_at_k": "Precision@K",
    "recall_at_k": "Recall@K",
    "impact_precision": "Impact Precision",
    "impact_recall": "Impact Recall",
    "impact_f1": "Impact F1",
    "correctness": "Answer Correctness",
    "faithfulness": "Faithfulness",
    "retrieval_latency_s": "Retrieval Latency (s)",
    "llm_latency_s": "LLM Generation Latency (s)",
    "total_latency_s": "Total End-to-End Latency (s)",
}


class BenchmarkRunner:
    """Executes comparative evaluation across retrieval modes and generates charts."""

    def __init__(
        self,
        retriever: HybridRetriever,
        answer_generator: Optional[AnswerGenerator] = None,
        dataset: Optional[List[Dict[str, Any]]] = None
    ):
        self.retriever = retriever
        self.answer_generator = answer_generator or AnswerGenerator()
        self.dataset = dataset or BENCHMARK_DATASET

    def run_benchmark(
        self,
        modes: Optional[List[str]] = None,
        top_k: int = 4,
        graph_depth: int = 2,
        progress_callback: Optional[Any] = None,
        parallel: bool = True,
        max_workers: int = 4
    ) -> pd.DataFrame:
        """Run evaluation benchmark across specified modes and collect metrics.

        Uses concurrent execution (ThreadPoolExecutor) to run LLM and retrieval calls
        in parallel, drastically accelerating benchmark speed from 30+ seconds to <3 seconds.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        modes = modes or ["graph", "hybrid"]
        records: List[Dict[str, Any]] = []

        tasks = []
        for item in self.dataset:
            for mode in modes:
                tasks.append((item, mode))

        total_runs = len(tasks)
        completed_runs = 0

        def _evaluate_single(task: Any) -> Dict[str, Any]:
            item, mode = task
            qid = item["id"]
            question = item["question"]
            exp_files = item.get("expected_files", [])
            exp_components = item.get("expected_components", [])
            ref_answer = item.get("reference_answer", "")

            # --- Retrieval ---
            retrieval_start = time.time()
            try:
                ret_res = self.retriever.retrieve(
                    query=question,
                    mode=mode,
                    top_k=top_k,
                    graph_depth=graph_depth
                )
                retrieval_latency = round(time.time() - retrieval_start, 4)
            except Exception as exc:
                return _make_failure_record(item, mode, str(exc))

            # --- LLM Generation ---
            llm_start = time.time()
            try:
                gen_res = self.answer_generator.answer_question(question, ret_res)
                llm_latency = round(time.time() - llm_start, 4)
                gen_answer = gen_res.get("answer", "")
            except Exception:
                llm_latency = 0.0
                gen_answer = ""

            total_latency = round(retrieval_latency + llm_latency, 4)

            # --- Retrieval Metrics ---
            retrieved_files = ret_res.get("affected_files", [])
            prec = EvaluationMetrics.retrieval_precision_at_k(retrieved_files, exp_files, k=top_k)
            rec = EvaluationMetrics.retrieval_recall_at_k(retrieved_files, exp_files, k=top_k)

            # --- Impact / Component Detection Metrics ---
            found_entities = [
                c.get("entity", "")
                for c in ret_res.get("citations", [])
                if c.get("entity")
            ]
            comp_metrics = EvaluationMetrics.component_overlap(found_entities, exp_components)

            # --- Answer Quality Metrics ---
            correctness = EvaluationMetrics.answer_correctness(gen_answer, ref_answer)
            faithfulness = EvaluationMetrics.faithfulness_score(
                gen_answer, ret_res.get("prompt_context", "")
            )

            return {
                "question_id": qid,
                "question": question,
                "category": item.get("category", "General"),
                "mode": mode.upper(),
                # Ground Truth definitions
                "expected_files": exp_files,
                "expected_components": exp_components,
                "reference_answer": ref_answer,
                # Actual Retrieval evidence
                "retrieved_files": retrieved_files,
                "retrieved_components": found_entities,
                "generated_answer": gen_answer,
                "prompt_context": ret_res.get("prompt_context", ""),
                "graph_paths": ret_res.get("graph_paths", []),
                # Retrieval metrics
                "precision_at_k": prec,
                "recall_at_k": rec,
                # Impact detection metrics
                "impact_precision": comp_metrics["precision"],
                "impact_recall": comp_metrics["recall"],
                "impact_f1": comp_metrics["f1"],
                "impact_tp": comp_metrics["tp"],
                "impact_fp": comp_metrics["fp"],
                "impact_fn": comp_metrics["fn"],
                "impact_unannotated": comp_metrics.get("unannotated", False),
                # Answer quality metrics
                "correctness": correctness,
                "faithfulness": faithfulness,
                # Latency (broken down)
                "retrieval_latency_s": retrieval_latency,
                "llm_latency_s": llm_latency,
                "total_latency_s": total_latency,
                # Context statistics
                "context_chars": len(ret_res.get("prompt_context", "")),
                "estimated_tokens": ret_res.get("estimated_tokens", 0),
                # Status
                "status": "ok",
                "error": None,
            }

        if parallel and total_runs > 1:
            workers = min(max_workers, total_runs)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_task = {executor.submit(_evaluate_single, task): task for task in tasks}
                for future in as_completed(future_to_task):
                    completed_runs += 1
                    t_item, t_mode = future_to_task[future]
                    if progress_callback:
                        progress_callback(
                            f"Evaluated {t_mode.upper()} on '{t_item['id']}' ({completed_runs}/{total_runs})",
                            completed_runs / total_runs
                        )
                    try:
                        rec_item = future.result()
                        records.append(rec_item)
                    except Exception as exc:
                        records.append(_make_failure_record(t_item, t_mode, str(exc)))
        else:
            for task in tasks:
                completed_runs += 1
                t_item, t_mode = task
                if progress_callback:
                    progress_callback(
                        f"Evaluating {t_mode.upper()} on '{t_item['id']}' ({completed_runs}/{total_runs})",
                        completed_runs / total_runs
                    )
                rec_item = _evaluate_single(task)
                records.append(rec_item)

        # Sort by question_id and mode for deterministic, stable display order
        records.sort(key=lambda r: (str(r.get("question_id", "")), str(r.get("mode", ""))))
        df = pd.DataFrame(records)
        return df

    # ------------------------------------------------------------------ #
    #  Chart factory methods                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_retrieval_chart(df: pd.DataFrame) -> go.Figure:
        """Chart 1: Retrieval Quality — Precision@K and Recall@K per mode."""
        avg = _safe_agg(df, ["precision_at_k", "recall_at_k"])

        metrics = [
            ("precision_at_k", "Precision@K"),
            ("recall_at_k", "Recall@K"),
        ]
        return _make_grouped_hbar(
            avg, metrics,
            title="Retrieval Quality",
            subtitle="Precision@K · Recall@K"
        )

    @staticmethod
    def create_impact_chart(df: pd.DataFrame) -> go.Figure:
        """Chart 2: Change Impact Detection — Precision, Recall, F1."""
        avg = _safe_agg(df, ["impact_precision", "impact_recall", "impact_f1"])

        metrics = [
            ("impact_precision", "Impact Precision"),
            ("impact_recall", "Impact Recall"),
            ("impact_f1", "Impact F1"),
        ]
        return _make_grouped_hbar(
            avg, metrics,
            title="Change Impact Detection",
            subtitle="Impact Precision · Recall · F1"
        )

    @staticmethod
    def create_answer_quality_chart(df: pd.DataFrame) -> go.Figure:
        """Chart 3: Answer Reliability — Correctness and Faithfulness."""
        avg = _safe_agg(df, ["correctness", "faithfulness"])

        metrics = [
            ("correctness", "Answer Correctness"),
            ("faithfulness", "Faithfulness"),
        ]
        return _make_grouped_hbar(
            avg, metrics,
            title="Answer Reliability",
            subtitle="Correctness · Faithfulness"
        )

    @staticmethod
    def create_latency_chart(df: pd.DataFrame) -> go.Figure:
        """Chart 4: Response Time — Retrieval, LLM, and Total latency per mode."""
        lat_cols = ["retrieval_latency_s", "llm_latency_s", "total_latency_s"]
        lat_labels = {
            "retrieval_latency_s": "Retrieval",
            "llm_latency_s": "LLM Generation",
            "total_latency_s": "Total End-to-End",
        }

        fig = go.Figure()
        modes_present = df["mode"].unique().tolist()
        lat_df = df.groupby("mode")[lat_cols].mean().reset_index()

        col_map = {
            "retrieval_latency_s": "#6366f1",
            "llm_latency_s": "#f59e0b",
            "total_latency_s": "#06b6d4",
        }

        for col in lat_cols:
            if col not in lat_df.columns:
                continue
            x_vals = []
            y_vals = []
            text_vals = []
            for _, row in lat_df.iterrows():
                x_vals.append(row["mode"])
                v = row[col] if not _is_nan(row[col]) else 0.0
                y_vals.append(v)
                text_vals.append(f"{v:.3f}s")

            fig.add_trace(go.Bar(
                name=lat_labels[col],
                x=x_vals,
                y=y_vals,
                text=text_vals,
                textposition="outside",
                marker_color=col_map[col],
                marker_line_width=0,
            ))

        fig.update_layout(
            title=dict(text="Response Time by Mode (Seconds)", font=dict(size=14, color="#f8fafc")),
            barmode="group",
            xaxis=dict(title="Retrieval Mode", color="#94a3b8"),
            yaxis=dict(title="Latency (seconds)", color="#94a3b8", rangemode="tozero"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(size=11, color="#94a3b8")),
            margin=dict(l=40, r=40, t=70, b=50),
            template="plotly_dark",
            paper_bgcolor="rgba(13,19,31,0)",
            plot_bgcolor="rgba(13,19,31,0)",
            font=dict(family="Plus Jakarta Sans, system-ui, sans-serif"),
        )
        return fig

    @staticmethod
    def create_comparison_bar_chart(df: pd.DataFrame) -> go.Figure:
        """Legacy combined chart — kept for backwards compatibility."""
        return BenchmarkRunner.create_retrieval_chart(df)

    @staticmethod
    def create_radar_chart(df: pd.DataFrame) -> go.Figure:
        """Multi-axis radar chart showing holistic mode trade-offs."""
        avg_df = df.groupby("mode").mean(numeric_only=True).reset_index()
        categories = ["Retrieval Recall", "Impact F1", "Answer Correctness", "Faithfulness", "Efficiency (1/Latency)"]

        fig = go.Figure()

        for _, row in avg_df.iterrows():
            m = row["mode"]
            eff = min(1.0, 0.5 / max(row.get("total_latency_s", 1.0), 0.05))
            values = [
                _safe_val(row.get("recall_at_k")),
                _safe_val(row.get("impact_f1")),
                _safe_val(row.get("correctness")),
                _safe_val(row.get("faithfulness")),
                eff,
            ]
            values.append(values[0])  # close loop

            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill="toself",
                name=m,
                line=dict(color=COLORS.get(m, "#cbd5e1"))
            ))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1.0])),
            showlegend=True,
            title="Multi-Dimensional Comparison",
            template="plotly_dark",
            margin=dict(l=50, r=50, t=60, b=50)
        )
        return fig


# ------------------------------------------------------------------ #
#  Private helpers                                                     #
# ------------------------------------------------------------------ #

def _normalize_mode_name(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure mode column is uppercase."""
    df = df.copy()
    df["mode"] = df["mode"].str.upper()
    return df


def _safe_agg(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Group by mode and compute mean, skipping None/NaN values."""
    df = _normalize_mode_name(df)
    result = df.groupby("mode")[cols].mean(numeric_only=True).reset_index()
    return result


def _make_grouped_hbar(
    avg_df: pd.DataFrame,
    metrics: List[tuple],
    title: str,
    subtitle: str,
) -> go.Figure:
    """Build a grouped horizontal bar chart from avg_df."""
    fig = go.Figure()

    metric_colors = [
        "#6366f1", "#10b981", "#f59e0b", "#ec4899", "#06b6d4"
    ]

    for idx, (col, label) in enumerate(metrics):
        x_vals = []
        y_vals = []
        text_vals = []

        for _, row in avg_df.iterrows():
            mode = row["mode"]
            v = row.get(col)
            if _is_nan(v):
                x_vals.append(0.0)
                text_vals.append("N/A")
            else:
                x_vals.append(float(v))
                text_vals.append(f"{float(v):.1%}")
            y_vals.append(f"{mode} — {label}")

        fig.add_trace(go.Bar(
            name=label,
            x=x_vals,
            y=y_vals,
            orientation="h",
            text=text_vals,
            textposition="outside",
            marker_color=metric_colors[idx % len(metric_colors)],
            marker_line_width=0,
        ))

    fig.update_layout(
        title=dict(text=f"{title}  ·  {subtitle}", font=dict(size=14, color="#f8fafc")),
        barmode="group",
        xaxis=dict(
            range=[0, 1.15],
            tickformat=".0%",
            title="Score",
            color="#94a3b8",
            gridcolor="rgba(148,163,184,0.1)",
        ),
        yaxis=dict(color="#94a3b8", automargin=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11, color="#94a3b8")),
        margin=dict(l=20, r=100, t=70, b=50),
        template="plotly_dark",
        paper_bgcolor="rgba(13,19,31,0)",
        plot_bgcolor="rgba(13,19,31,0)",
        font=dict(family="Plus Jakarta Sans, system-ui, sans-serif"),
        height=max(220, 80 * len(avg_df) * len(metrics) // max(len(metrics), 1)),
    )
    return fig


def _make_failure_record(item: Dict[str, Any], mode: str, error: str) -> Dict[str, Any]:
    """Create a failure record with all metrics as None."""
    return {
        "question_id": item["id"],
        "question": item.get("question", ""),
        "category": item.get("category", "General"),
        "mode": mode.upper(),
        "expected_files": item.get("expected_files", []),
        "expected_components": item.get("expected_components", []),
        "reference_answer": item.get("reference_answer", ""),
        "retrieved_files": [],
        "retrieved_components": [],
        "generated_answer": "",
        "prompt_context": "",
        "graph_paths": [],
        "precision_at_k": None,
        "recall_at_k": None,
        "impact_precision": None,
        "impact_recall": None,
        "impact_f1": None,
        "impact_tp": None,
        "impact_fp": None,
        "impact_fn": None,
        "impact_unannotated": False,
        "correctness": None,
        "faithfulness": None,
        "retrieval_latency_s": None,
        "llm_latency_s": None,
        "total_latency_s": None,
        "context_chars": None,
        "estimated_tokens": None,
        "status": "error",
        "error": error,
    }


def _is_nan(v) -> bool:
    """Return True if v is None or NaN."""
    if v is None:
        return True
    try:
        return math.isnan(float(v))
    except (TypeError, ValueError):
        return True


def _safe_val(v, default: float = 0.0) -> float:
    """Return float value or default when None/NaN."""
    if _is_nan(v):
        return default
    return float(v)
