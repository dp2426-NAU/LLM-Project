import logging
import re

from backend.agents.base import BaseAgent
from backend.config.constants import AgentRole, PipelineStage
from backend.config.settings import Settings
from backend.memory.context_graph import AgentContext, AgentOutput
from backend.prompts.engine import PromptEngine

logger = logging.getLogger(__name__)


class SynthesizerAgent(BaseAgent):
    def __init__(self, settings: Settings, prompt_engine: PromptEngine) -> None:
        super().__init__(AgentRole.SYNTHESIZER, settings, prompt_engine)

    def run(self, context: AgentContext) -> AgentOutput:
        research_text = (
            context.research_output.content
            if context.research_output and context.research_output.success
            else "No research output available."
        )
        critique_text = (
            context.critique_output.content
            if context.critique_output and context.critique_output.success
            else "No critique available."
        )

        system, user = self._prompt_engine.render(
            "synthesizer",
            query=context.query,
            output_format=context.output_format,
            citation_style=context.citation_style,
            research_output=research_text,
            critique_output=critique_text,
        )

        # Synthesizer gets more tokens since it produces the full artifact
        content, tokens, latency = self._timed_llm_call(system, user, max_tokens=2000)

        word_count = len(re.findall(r"\w+", content))
        structured = {
            "sections": self._extract_sections(content),
            "word_count": word_count,
            "sources_used": self._extract_citations(content),
            "unresolved_uncertainties": [],
        }

        logger.info(
            "SynthesizerAgent complete: words=%d, sections=%d",
            word_count,
            len(structured["sections"]),
        )

        return AgentOutput(
            agent=self.role,
            stage=PipelineStage.SYNTHESIS,
            content=content,
            structured=structured,
            tokens_used=tokens,
            latency_ms=latency,
            success=True,
        )

    def _extract_sections(self, content: str) -> dict[str, str]:
        sections: dict[str, str] = {}
        current_title: str | None = None
        current_lines: list[str] = []

        for line in content.splitlines():
            stripped = line.strip()
            if stripped.isupper() and len(stripped) > 4 and len(stripped) < 80:
                if current_title:
                    sections[current_title] = "\n".join(current_lines).strip()
                current_title = stripped
                current_lines = []
            else:
                current_lines.append(line)

        if current_title and current_lines:
            sections[current_title] = "\n".join(current_lines).strip()

        return sections

    def _extract_citations(self, content: str) -> list[str]:
        return list(set(re.findall(r"\[S\d+\]", content)))
