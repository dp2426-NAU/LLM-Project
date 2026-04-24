import logging

from backend.agents.base import BaseAgent
from backend.config.constants import AgentRole, PipelineStage
from backend.config.settings import Settings
from backend.memory.context_graph import AgentContext, AgentOutput
from backend.prompts.engine import PromptEngine

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    def __init__(self, settings: Settings, prompt_engine: PromptEngine) -> None:
        super().__init__(AgentRole.CRITIC, settings, prompt_engine)

    def run(self, context: AgentContext) -> AgentOutput:
        if context.research_output is None or not context.research_output.success:
            return AgentOutput(
                agent=self.role,
                stage=PipelineStage.CRITIQUE,
                content="Skipped — no valid research output to critique.",
                structured={"issues": [], "coverage_gaps": [], "bias_signals": [], "strength_score": 0.5, "strength_rationale": "Skipped"},
                success=True,
            )

        system, user = self._prompt_engine.render(
            "critic",
            query=context.query,
            research_output=context.research_output.content,
        )

        content, tokens, latency = self._timed_llm_call(system, user)
        structured = self._llm.extract_json(content)

        critical_count = sum(
            1 for issue in structured.get("issues", [])
            if issue.get("severity", "").upper() in {"HIGH", "CRITICAL"}
        )

        logger.info(
            "CriticAgent complete: issues=%d, critical=%d, strength=%.2f",
            len(structured.get("issues", [])),
            critical_count,
            structured.get("strength_score", 0.0),
        )

        return AgentOutput(
            agent=self.role,
            stage=PipelineStage.CRITIQUE,
            content=content,
            structured=structured,
            tokens_used=tokens,
            latency_ms=latency,
            success=True,
        )
