"""Evaluation metrics computation for RAG retrieval and What-If analysis.

Metric formulas:
  Precision@K  = |retrieved_top_k ∩ expected| / |retrieved_top_k|
  Recall@K     = |retrieved_top_k ∩ expected| / |expected|
  Impact Precision = TP / (TP + FP)   where TP = correctly predicted components
  Impact Recall    = TP / (TP + FN)   where FN = missed expected components
  Impact F1        = 2 * P * R / (P + R)

Special cases:
  - If expected set is empty, recall and impact metrics are returned as None (unannotated).
  - If predicted set is empty, precision=0, recall=0, f1=0.
  - Zero denominator is handled safely; never silently converts None to 0.
"""
import re
from typing import List, Optional, Dict, Any


class EvaluationMetrics:
    """Computes precision, recall, correctness, faithfulness, and efficiency metrics."""

    @staticmethod
    def retrieval_precision_at_k(
        retrieved_files: List[str],
        expected_files: List[str],
        k: int = 5,
    ) -> float:
        """Precision@K: fraction of retrieved top-k files that are relevant.

        Returns 0.0 when retrieved_files is empty or k <= 0.
        Returns 0.0 when expected_files is empty (no relevant items can be retrieved).
        """
        if not retrieved_files or k <= 0:
            return 0.0
        if not expected_files:
            # No ground-truth: every retrieved item is irrelevant by definition.
            return 0.0
        top_k = retrieved_files[:k]
        expected_set = {_normalize_path(f) for f in expected_files}
        hits = sum(1 for f in top_k if _normalize_path(f) in expected_set)
        return round(hits / len(top_k), 4)

    @staticmethod
    def retrieval_recall_at_k(
        retrieved_files: List[str],
        expected_files: List[str],
        k: int = 5,
    ) -> Optional[float]:
        """Recall@K: fraction of expected relevant files retrieved in top-k.

        Returns None when expected_files is empty (unannotated - cannot calculate recall).
        Returns 0.0 when retrieved_files is empty.
        """
        if not expected_files:
            return None  # Unannotated - do not silently return 1.0
        if not retrieved_files or k <= 0:
            return 0.0
        top_k = retrieved_files[:k]
        top_k_set = {_normalize_path(f) for f in top_k}
        expected_set = {_normalize_path(f) for f in expected_files}
        hits = sum(1 for f in expected_set if f in top_k_set)
        return round(hits / len(expected_set), 4)

    @staticmethod
    def component_overlap(
        predicted_components: List[str],
        expected_components: List[str],
    ) -> Dict[str, Any]:
        """Compute precision, recall, and F1 for identified affected components.

        Uses correct TP/FP/FN formulation:
          TP = number of expected components matched by at least one prediction
          FP = predicted components that do NOT match any expected component
          FN = expected components not matched by any prediction

          Precision = TP / (TP + FP) = TP / |pred_set|
          Recall    = TP / (TP + FN) = TP / |exp_set|
          F1        = 2 * P * R / (P + R)

        Returns:
          precision, recall, f1 as floats (0.0-1.0), or None where unannotated.
          Also includes tp, fp, fn counts for transparency.
        """
        if not expected_components:
            # Unannotated - cannot compute meaningful metrics
            return {
                "precision": None,
                "recall": None,
                "f1": None,
                "tp": None,
                "fp": None,
                "fn": None,
                "unannotated": True,
            }

        pred_set = {c.lower() for c in predicted_components}
        exp_set = {c.lower() for c in expected_components}

        # TP: expected components matched by at least one prediction (via substring)
        tp = sum(
            1 for e in exp_set
            if any(e in p or p in e for p in pred_set)
        )
        fn = len(exp_set) - tp

        # FP: predicted components that do NOT match any expected component
        fp = sum(
            1 for p in pred_set
            if not any(e in p or p in e for e in exp_set)
        )

        prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        rec  = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1   = round((2 * prec * rec) / (prec + rec), 4) if (prec + rec) > 0 else 0.0

        return {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "unannotated": False,
        }

    @staticmethod
    def answer_correctness(generated_answer: str, reference_answer: str) -> Optional[float]:
        """Token-level F1 overlap between generated answer and ground-truth reference.

        Returns None when reference_answer is empty (no ground truth available).
        Returns 0.0 when generated_answer is empty.
        """
        ref_tokens = set(re.findall(r"\b[A-Za-z0-9_]{3,}\b", reference_answer.lower()))
        if not ref_tokens:
            return None  # No reference - unannotated

        gen_tokens = set(re.findall(r"\b[A-Za-z0-9_]{3,}\b", generated_answer.lower()))
        if not gen_tokens:
            return 0.0

        common = gen_tokens.intersection(ref_tokens)
        prec = len(common) / len(gen_tokens)
        rec  = len(common) / len(ref_tokens)

        if prec + rec == 0:
            return 0.0
        return round((2 * prec * rec) / (prec + rec), 4)

    @staticmethod
    def faithfulness_score(generated_answer: str, context: str) -> Optional[float]:
        """Proportion of key technical tokens in the answer that appear in the retrieved context.

        Returns None when generated_answer is empty.
        Returns 0.0 when answer tokens are entirely absent from context.

        Note: This is a lexical approximation - not a semantic/NLI-based faithfulness metric.
        """
        ans_tokens = set(re.findall(r"\b[A-Za-z0-9_]{4,}\b", generated_answer.lower()))
        if not ans_tokens:
            return None  # No answer content - cannot evaluate faithfulness

        ctx_tokens = set(re.findall(r"\b[A-Za-z0-9_]{4,}\b", context.lower()))
        if not ctx_tokens:
            return 0.0  # Non-empty answer, empty context - nothing grounded

        grounded = ans_tokens.intersection(ctx_tokens)
        return round(len(grounded) / len(ans_tokens), 4)


def _normalize_path(path: str) -> str:
    """Normalize file paths for comparison (lowercase, forward slashes)."""
    return path.lower().replace("\\", "/")
