import logging

from backend.agents.base import BaseAgent
from backend.config.constants import AgentRole, EVAL_WEIGHTS, PipelineStage
from backend.config.settings import Settings
from backend.memory.context_graph import AgentContext, AgentOutput
from backend.prompts.engine import PromptEngine

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    def __init__(self, settings: Settings, prompt_engine: PromptEngine) -> None:
        super().__init__(AgentRole.VALIDATOR, settings, prompt_engine)

    def run(self, context: AgentContext) -> AgentOutput:
        if context.synthesis_output is None or not context.synthesis_output.success:
            return AgentOutput(
                agent=self.role,
                stage=PipelineStage.VALIDATION,
                content="Skipped — no synthesis output to validate.",
                structured=self._empty_result("FAIL"),
                success=True,
            )

        system, user = self._prompt_engine.render(
            "validator",
            query=context.query,
            synthesis_output=context.synthesis_output.content,
        )

        content, tokens, latency = self._timed_llm_call(system, user)
        structured = self._llm.extract_json(content)

        composite = self._compute_composite_score(structured)
        structured["composite_score"] = composite

        verdict = structured.get("verdict", "FAIL")
        logger.info(
            "ValidatorAgent complete: verdict=%s, composite=%.3f",
            verdict,
            composite,
        )

        return AgentOutput(
            agent=self.role,
            stage=PipelineStage.VALIDATION,
            content=content,
            structured=structured,
            tokens_used=tokens,
            latency_ms=latency,
            success=True,
        )

    def _compute_composite_score(self, structured: dict) -> float:
        scores = structured.get("scores", {})
        total = 0.0
        for dimension, weight in EVAL_WEIGHTS.items():
            dim_data = scores.get(dimension, {})
            score = dim_data.get("score", 0.0) if isinstance(dim_data, dict) else 0.0
            total += score * weight
        return round(total, 4)

    def _empty_result(self, verdict: str) -> dict:
        return {
            "scores": {
                d: {"score": 0.0, "rationale": "skipped"}
                for d in ["coherence", "relevance", "factuality", "completeness"]
            },
            "fabrication_flags": [],
            "omission_flags": [],
            "verdict": verdict,
            "verdict_note": "Validation skipped.",
            "composite_score": 0.0,
        }
