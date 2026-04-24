import logging

from backend.agents.base import BaseAgent
from backend.config.constants import AgentRole, PipelineStage
from backend.config.settings import Settings
from backend.memory.context_graph import AgentContext, AgentOutput
from backend.prompts.engine import PromptEngine

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    def __init__(self, settings: Settings, prompt_engine: PromptEngine) -> None:
        super().__init__(AgentRole.RESEARCHER, settings, prompt_engine)

    def run(self, context: AgentContext) -> AgentOutput:
        if not context.retrieved_chunks:
            return AgentOutput(
                agent=self.role,
                stage=PipelineStage.RESEARCH,
                content="No relevant documents found in corpus for this query.",
                structured={"core_findings": [], "key_concepts": {}, "evidence_gaps": ["No source documents available"], "source_quality_notes": "N/A"},
                success=True,
            )

        chunk_dicts = [
            {"text": c.text, "source": c.source, "score": c.score}
            for c in context.retrieved_chunks
        ]

        system, user = self._prompt_engine.render(
            "researcher",
            query=context.query,
            output_format=context.output_format,
            retrieved_chunks=chunk_dicts,
        )

        content, tokens, latency = self._timed_llm_call(system, user)

        structured = self._parse_output(content)

        logger.info(
            "ResearcherAgent complete: findings=%d, gaps=%d",
            len(structured.get("core_findings", [])),
            len(structured.get("evidence_gaps", [])),
        )

        return AgentOutput(
            agent=self.role,
            stage=PipelineStage.RESEARCH,
            content=content,
            structured=structured,
            tokens_used=tokens,
            latency_ms=latency,
            success=True,
        )

    def _parse_output(self, content: str) -> dict:
        sections = {"core_findings": [], "key_concepts": {}, "evidence_gaps": [], "source_quality_notes": ""}
        current_section = None
        lines = content.splitlines()

        section_map = {
            "CORE FINDINGS": "core_findings",
            "KEY CONCEPTS": "key_concepts",
            "EVIDENCE GAPS": "evidence_gaps",
            "SOURCE QUALITY": "source_quality_notes",
        }

        for line in lines:
            stripped = line.strip()
            matched = False
            for header, key in section_map.items():
                if header in stripped.upper():
                    current_section = key
                    matched = True
                    break
            if matched or not stripped:
                continue

            if current_section == "core_findings" and stripped.startswith("-"):
                sections["core_findings"].append(stripped.lstrip("- ").strip())
            elif current_section == "evidence_gaps" and stripped.startswith("-"):
                sections["evidence_gaps"].append(stripped.lstrip("- ").strip())
            elif current_section == "source_quality_notes":
                sections["source_quality_notes"] += stripped + " "

        return sections
