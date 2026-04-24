import logging

from backend.config.constants import EVAL_WEIGHTS
from backend.config.settings import Settings
from backend.evaluation.metrics import (
    EvaluationResult,
    compute_length_completeness,
    compute_lexical_relevance,
    compute_structural_coherence,
    extract_validation_scores,
)
from backend.memory.context_graph import AgentContext

logger = logging.getLogger(__name__)


class PipelineEvaluator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def evaluate(self, context: AgentContext) -> EvaluationResult:
        synthesis_text = (
            context.synthesis_output.content
            if context.synthesis_output and context.synthesis_output.success
            else ""
        )

        validation_structured = (
            context.validation_output.structured
            if context.validation_output and context.validation_output.success
            else None
        )

        # Prefer LLM scores from validator; fallback to heuristics
        if validation_structured and "scores" in validation_structured:
            scores = extract_validation_scores(validation_structured)
        else:
            scores = {
                "coherence": compute_structural_coherence(synthesis_text),
                "relevance": compute_lexical_relevance(context.query, synthesis_text),
                "factuality": 0.5,  # can't compute without LLM
                "completeness": compute_length_completeness(synthesis_text, context.output_format),
            }

        composite = sum(
            scores.get(dim, 0.0) * weight
            for dim, weight in EVAL_WEIGHTS.items()
        )
        composite = round(composite, 4)

        verdict = "FAIL"
        if validation_structured:
            verdict = validation_structured.get("verdict", "FAIL")
        elif composite >= 0.65:
            verdict = "PASS"
        elif composite >= 0.45:
            verdict = "CONDITIONAL_PASS"

        fabrication_flags = []
        if validation_structured:
            fabrication_flags = validation_structured.get("fabrication_flags", [])

        passed = verdict in {"PASS", "CONDITIONAL_PASS"}

        result = EvaluationResult(
            session_id=context.session_id,
            query=context.query,
            coherence_score=scores["coherence"],
            relevance_score=scores["relevance"],
            factuality_score=scores["factuality"],
            completeness_score=scores["completeness"],
            composite_score=composite,
            verdict=verdict,
            total_tokens=context.total_tokens,
            elapsed_ms=context.elapsed_ms,
            fabrication_flags=fabrication_flags,
            passed=passed,
        )

        logger.info(
            "Evaluation: session=%s, composite=%.3f, verdict=%s",
            context.session_id,
            composite,
            verdict,
        )
        return result
