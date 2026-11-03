"""Benchmark execution engine comparing Vector RAG, Graph RAG, and Hybrid GraphRAG."""
import time
from typing import List, Dict, Any, Optional
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from repomind.evaluation.dataset import BENCHMARK_DATASET
from repomind.evaluation.metrics import EvaluationMetrics
from repomind.retrieval.hybrid_retriever import HybridRetriever
from repomind.llm.answer_generator import AnswerGenerator


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
        progress_callback: Optional[Any] = None
    ) -> pd.DataFrame:
        """Run evaluation benchmark across specified modes and collect metrics."""
        modes = modes or ["vector", "graph", "hybrid"]
        records: List[Dict[str, Any]] = []

        total_runs = len(self.dataset) * len(modes)
        current_run = 0

        for item in self.dataset:
            qid = item["id"]
            question = item["question"]
            exp_files = item.get("expected_files", [])
            exp_components = item.get("expected_components", [])
            ref_answer = item.get("reference_answer", "")

            for mode in modes:
                current_run += 1
                if progress_callback:
                    progress_callback(f"Evaluating {mode.upper()} on '{qid}' ({current_run}/{total_runs})", current_run / total_runs)

                start_time = time.time()
                ret_res = self.retriever.retrieve(
                    query=question,
                    mode=mode,
                    top_k=top_k,
                    graph_depth=graph_depth
                )

                gen_res = self.answer_generator.answer_question(question, ret_res)
                total_latency = round(time.time() - start_time, 4)

                retrieved_files = ret_res.get("affected_files", [])
                prec = EvaluationMetrics.retrieval_precision_at_k(retrieved_files, exp_files, k=top_k)
                rec = EvaluationMetrics.retrieval_recall_at_k(retrieved_files, exp_files, k=top_k)

                # Identified component overlap
                found_entities = [c.get("entity", "") for c in ret_res.get("citations", []) if c.get("entity")]
                comp_metrics = EvaluationMetrics.component_overlap(found_entities, exp_components)

                # Answer quality
                gen_answer = gen_res.get("answer", "")
                correctness = EvaluationMetrics.answer_correctness(gen_answer, ref_answer)
                faithfulness = EvaluationMetrics.faithfulness_score(gen_answer, ret_res.get("prompt_context", ""))

                records.append({
                    "question_id": qid,
                    "category": item.get("category", "General"),
                    "mode": mode.upper(),
                    "precision_at_k": prec,
                    "recall_at_k": rec,
                    "impact_precision": comp_metrics["precision"],
                    "impact_recall": comp_metrics["recall"],
                    "impact_f1": comp_metrics["f1"],
                    "correctness": correctness,
                    "faithfulness": faithfulness,
                    "retrieval_latency_s": ret_res.get("retrieval_latency", 0.0),
                    "total_latency_s": total_latency,
                    "context_chars": len(ret_res.get("prompt_context", "")),
                    "estimated_tokens": ret_res.get("estimated_tokens", 0)
                })

        df = pd.DataFrame(records)
        return df

    @staticmethod
    def create_comparison_bar_chart(df: pd.DataFrame) -> go.Figure:
        """Create grouped bar chart comparing mean metrics across modes."""
        avg_df = df.groupby("mode")[["precision_at_k", "recall_at_k", "impact_f1", "correctness", "faithfulness"]].mean().reset_index()

        fig = go.Figure()
        metrics = [
            ("precision_at_k", "Retrieval Precision@K", "#6366f1"),
            ("recall_at_k", "Retrieval Recall@K", "#10b981"),
            ("impact_f1", "Impact F1", "#f59e0b"),
            ("correctness", "Answer Correctness", "#ec4899"),
            ("faithfulness", "Faithfulness", "#06b6d4")
        ]

        for col, label, color in metrics:
            fig.add_trace(go.Bar(
                x=avg_df["mode"],
                y=avg_df[col],
                name=label,
                marker_color=color,
                text=[f"{v:.2f}" for v in avg_df[col]],
                textposition="auto"
            ))

        fig.update_layout(
            title="RAG Retrieval & Generation Performance by Mode",
            barmode="group",
            yaxis=dict(range=[0, 1.05], title="Score (0.0 to 1.0)"),
            xaxis=dict(title="Retrieval Mode"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=60, b=40),
            template="plotly_dark"
        )
        return fig

    @staticmethod
    def create_latency_chart(df: pd.DataFrame) -> go.Figure:
        """Create bar chart comparing average response latency."""
        lat_df = df.groupby("mode")["total_latency_s"].mean().reset_index()

        fig = px.bar(
            lat_df,
            x="mode",
            y="total_latency_s",
            color="mode",
            color_discrete_map={"VECTOR": "#3b82f6", "GRAPH": "#8b5cf6", "HYBRID": "#10b981"},
            title="Average End-to-End Latency by Mode (Seconds)",
            labels={"total_latency_s": "Latency (s)", "mode": "Retrieval Mode"},
            text_auto=".3f"
        )
        fig.update_layout(
            template="plotly_dark",
            showlegend=False,
            margin=dict(l=40, r=40, t=60, b=40)
        )
        return fig

    @staticmethod
    def create_radar_chart(df: pd.DataFrame) -> go.Figure:
        """Create multi-axis radar chart showing holistic mode trade-offs."""
        avg_df = df.groupby("mode").mean().reset_index()
        categories = ["Retrieval Recall", "Impact F1", "Answer Correctness", "Faithfulness", "Efficiency (1/Latency)"]

        fig = go.Figure()
        colors = {"VECTOR": "#3b82f6", "GRAPH": "#8b5cf6", "HYBRID": "#10b981"}

        for _, row in avg_df.iterrows():
            m = row["mode"]
            eff = min(1.0, 0.5 / max(row["total_latency_s"], 0.05))
            values = [
                row["recall_at_k"],
                row["impact_f1"],
                row["correctness"],
                row["faithfulness"],
                eff
            ]
            values.append(values[0])  # close loop

            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill="toself",
                name=m,
                line=dict(color=colors.get(m, "#cbd5e1"))
            ))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1.0])),
            showlegend=True,
            title="Multi-Dimensional Mode Comparison",
            template="plotly_dark",
            margin=dict(l=50, r=50, t=60, b=50)
        )
        return fig
