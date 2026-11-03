"""Evaluation metrics computation for RAG retrieval and What-If analysis."""
import re
from typing import List, Set, Dict, Any


class EvaluationMetrics:
    """Computes precision, recall, correctness, faithfulness, and efficiency metrics."""

    @staticmethod
    def retrieval_precision_at_k(retrieved_files: List[str], expected_files: List[str], k: int = 5) -> float:
        """Precision@K: Fraction of retrieved files in the top-k that are relevant."""
        if not retrieved_files or k <= 0:
            return 0.0
        top_k = retrieved_files[:k]
        expected_set = {f.lower().replace("\\", "/") for f in expected_files}
        hits = sum(1 for f in top_k if f.lower().replace("\\", "/") in expected_set)
        return round(hits / len(top_k), 4)

    @staticmethod
    def retrieval_recall_at_k(retrieved_files: List[str], expected_files: List[str], k: int = 5) -> float:
        """Recall@K: Fraction of expected relevant files that were retrieved in top-k."""
        if not expected_files:
            return 1.0
        if not retrieved_files or k <= 0:
            return 0.0
        top_k = retrieved_files[:k]
        top_k_set = {f.lower().replace("\\", "/") for f in top_k}
        expected_set = {f.lower().replace("\\", "/") for f in expected_files}
        hits = sum(1 for f in expected_set if f in top_k_set)
        return round(hits / len(expected_set), 4)

    @staticmethod
    def component_overlap(predicted_components: List[str], expected_components: List[str]) -> Dict[str, float]:
        """Compute precision, recall, and F1 for identified affected components."""
        if not expected_components:
            return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
        if not predicted_components:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

        pred_set = {c.lower() for c in predicted_components}
        exp_set = {c.lower() for c in expected_components}

        hits = sum(1 for c in exp_set if any(c in p or p in c for p in pred_set))
        prec = round(hits / max(len(pred_set), 1), 4)
        rec = round(hits / len(exp_set), 4)
        f1 = round((2 * prec * rec) / (prec + rec), 4) if (prec + rec) > 0 else 0.0

        return {"precision": prec, "recall": rec, "f1": f1}

    @staticmethod
    def answer_correctness(generated_answer: str, reference_answer: str) -> float:
        """Compute token-level F1 / overlap between generated answer and ground-truth reference."""
        gen_tokens = set(re.findall(r"\b[A-Za-z0-9_]{3,}\b", generated_answer.lower()))
        ref_tokens = set(re.findall(r"\b[A-Za-z0-9_]{3,}\b", reference_answer.lower()))

        if not ref_tokens:
            return 1.0
        if not gen_tokens:
            return 0.0

        common = gen_tokens.intersection(ref_tokens)
        prec = len(common) / len(gen_tokens)
        rec = len(common) / len(ref_tokens)

        if prec + rec == 0:
            return 0.0
        return round((2 * prec * rec) / (prec + rec), 4)

    @staticmethod
    def faithfulness_score(generated_answer: str, context: str) -> float:
        """Measure the proportion of key claims / technical tokens grounded in the retrieved context."""
        ans_tokens = set(re.findall(r"\b[A-Za-z0-9_]{4,}\b", generated_answer.lower()))
        ctx_tokens = set(re.findall(r"\b[A-Za-z0-9_]{4,}\b", context.lower()))

        if not ans_tokens:
            return 1.0
        grounded = ans_tokens.intersection(ctx_tokens)
        return round(len(grounded) / len(ans_tokens), 4)
