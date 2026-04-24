"""
Basic evaluation harness for RegDelta.

Measures:
  - Retrieval Recall@K: given a known (query, relevant_policy_id) pair,
    does the retriever surface it in top-K results?
  - Report quality: simple rubric-based LLM self-evaluation.
"""

import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RetrievalExample:
    query: str
    relevant_policy_ids: list[str]


RETRIEVAL_EVAL_SET: list[RetrievalExample] = [
    RetrievalExample(
        query="record retention requirements for electronic communications",
        relevant_policy_ids=["POL-REC-001", "POL-IT-003"],
    ),
    RetrievalExample(
        query="customer due diligence and beneficial ownership verification",
        relevant_policy_ids=["POL-AML-001", "POL-KYC-002"],
    ),
    RetrievalExample(
        query="stress testing and capital adequacy reporting",
        relevant_policy_ids=["POL-RISK-002"],
    ),
    RetrievalExample(
        query="whistleblower protection and internal reporting procedures",
        relevant_policy_ids=["POL-COMP-001"],
    ),
]


def recall_at_k(hits: list[dict], relevant_ids: list[str], k: int) -> float:
    top_k_ids = {h["metadata"].get("policy_id") for h in hits[:k]}
    found = sum(1 for rid in relevant_ids if rid in top_k_ids)
    return found / len(relevant_ids) if relevant_ids else 0.0


def run_retrieval_eval(retriever, k: int = 5) -> dict:
    results = []
    for example in RETRIEVAL_EVAL_SET:
        hits = retriever.retrieve_policies(example.query, top_k=k)
        r_at_k = recall_at_k(hits, example.relevant_policy_ids, k)
        results.append(
            {
                "query": example.query,
                "recall_at_k": r_at_k,
                "expected": example.relevant_policy_ids,
                "retrieved": [h["metadata"].get("policy_id") for h in hits[:k]],
            }
        )

    mean_recall = sum(r["recall_at_k"] for r in results) / len(results)
    return {"k": k, "mean_recall": round(mean_recall, 3), "examples": results}


def evaluate_report_quality(report: dict, generator) -> dict:
    """Ask the LLM to rate a generated report on a 1-5 rubric."""
    rubric_prompt = f"""
Rate this regulatory impact report on three dimensions (score 1-5 each):
1. Completeness: Does the executive summary cover the key changes?
2. Actionability: Are the recommended actions specific and implementable?
3. Accuracy: Does the risk level seem appropriate given the described changes?

Report:
{json.dumps(report, indent=2)[:2000]}

Respond ONLY in JSON:
{{"completeness": <1-5>, "actionability": <1-5>, "accuracy": <1-5>, "notes": "<brief note>"}}
"""
    try:
        result = generator.generate_json(
            system_prompt="You are an expert compliance auditor evaluating AI-generated reports.",
            user_prompt=rubric_prompt,
        )
        result["mean_score"] = round(
            (result.get("completeness", 0) + result.get("actionability", 0) + result.get("accuracy", 0)) / 3,
            2,
        )
        return result
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Lazy imports so the module is importable without full app setup
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from app.config import get_settings
    from store.vector_store import VectorStore
    from rag.retriever import Retriever

    settings = get_settings()
    vs = VectorStore(settings)
    retriever = Retriever(settings, vs)

    print("\n=== Retrieval Evaluation ===")
    results = run_retrieval_eval(retriever, k=5)
    print(f"Mean Recall@5: {results['mean_recall']}")
    for ex in results["examples"]:
        status = "✓" if ex["recall_at_k"] > 0 else "✗"
        print(f"  {status} [{ex['recall_at_k']:.2f}] {ex['query'][:60]}")

    report_path = Path("sample_report.json")
    if report_path.exists():
        from rag.generator import LLMGenerator
        generator = LLMGenerator(settings)
        report = json.loads(report_path.read_text())
        print("\n=== Report Quality Evaluation ===")
        quality = evaluate_report_quality(report, generator)
        print(json.dumps(quality, indent=2))


if __name__ == "__main__":
    main()
