"""Answer and Report generation orchestrator."""
import time
from typing import Dict, Any, Optional

from repomind.llm.model_provider import BaseLLMClient, get_llm_client
from repomind.llm.prompts import (
    REPO_QA_SYSTEM_PROMPT, REPO_QA_USER_TEMPLATE,
    WHAT_IF_SYSTEM_PROMPT, WHAT_IF_USER_TEMPLATE
)


class AnswerGenerator:
    """Generates grounded responses for repository Q&A and What-If analysis."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client or get_llm_client()

    def answer_question(self, query: str, retrieval_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate answer for natural language repository question."""
        context_str = retrieval_result.get("prompt_context", "")
        prompt = REPO_QA_USER_TEMPLATE.format(context=context_str, question=query)

        start = time.time()
        answer_text = self.llm.generate(prompt, system_instruction=REPO_QA_SYSTEM_PROMPT)
        latency = round(time.time() - start, 3)

        return {
            "query": query,
            "answer": answer_text,
            "citations": retrieval_result.get("citations", []),
            "graph_paths": retrieval_result.get("graph_paths", []),
            "affected_files": retrieval_result.get("affected_files", []),
            "latency": latency,
            "model_used": self.llm.model_name
        }

    def generate_whatif_report(self, hypothesis: str, retrieval_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured explainable impact analysis for hypothetical change."""
        context_str = retrieval_result.get("prompt_context", "")
        prompt = WHAT_IF_USER_TEMPLATE.format(context=context_str, hypothesis=hypothesis)

        start = time.time()
        report_text = self.llm.generate(prompt, system_instruction=WHAT_IF_SYSTEM_PROMPT)
        latency = round(time.time() - start, 3)

        return {
            "hypothesis": hypothesis,
            "report_markdown": report_text,
            "citations": retrieval_result.get("citations", []),
            "graph_paths": retrieval_result.get("graph_paths", []),
            "affected_files": retrieval_result.get("affected_files", []),
            "latency": latency,
            "model_used": self.llm.model_name
        }
