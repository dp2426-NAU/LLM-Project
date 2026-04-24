import logging
import uuid
from typing import Optional

from backend.agents.critic import CriticAgent
from backend.agents.researcher import ResearcherAgent
from backend.agents.synthesizer import SynthesizerAgent
from backend.agents.validator import ValidatorAgent
from backend.config.constants import PipelineStage
from backend.config.settings import Settings
from backend.logging.tracer import PipelineTracer
from backend.memory.context_graph import AgentContext, RetrievedChunk
from backend.memory.vector_store import CorpusStore
from backend.prompts.engine import PromptEngine

logger = logging.getLogger(__name__)


class SynapseOrchestrator:
    """Drives the full multi-agent pipeline from query to validated synthesis."""

    def __init__(
        self,
        settings: Settings,
        corpus_store: CorpusStore,
        prompt_engine: PromptEngine,
        tracer: Optional[PipelineTracer] = None,
    ) -> None:
        self._settings = settings
        self._store = corpus_store
        self._tracer = tracer

        self._researcher = ResearcherAgent(settings, prompt_engine)
        self._critic = CriticAgent(settings, prompt_engine)
        self._synthesizer = SynthesizerAgent(settings, prompt_engine)
        self._validator = ValidatorAgent(settings, prompt_engine)

    def run(
        self,
        query: str,
        output_format: str = "standard",
        citation_style: str = "inline",
        session_id: Optional[str] = None,
    ) -> AgentContext:
        session_id = session_id or str(uuid.uuid4())
        context = AgentContext(
            session_id=session_id,
            query=query,
            output_format=output_format,
            citation_style=citation_style,
        )

        if self._tracer:
            self._tracer.start_session(session_id, query)

        logger.info("Pipeline start: session=%s, query='%s...'", session_id, query[:60])

        # Stage 1: Retrieval
        context.current_stage = PipelineStage.INGESTION
        hits = self._store.search(
            query,
            top_k=self._settings.retrieval_top_k,
            min_score=self._settings.min_relevance_score,
        )
        context.retrieved_chunks = [
            RetrievedChunk(text=h["text"], source=h["source"], score=h["score"], metadata=h.get("metadata", {}))
            for h in hits
        ]
        logger.info("Retrieved %d chunks (query: %s)", len(context.retrieved_chunks), query[:40])

        # Stage 2: Research
        context.current_stage = PipelineStage.RESEARCH
        research_out = self._researcher._safe_run(context)
        context.record_agent_output(research_out)
        if self._tracer:
            self._tracer.record_agent(session_id, research_out)

        if not research_out.success:
            context.current_stage = PipelineStage.FAILED
            return context

        # Stage 3: Critique (optional)
        if self._settings.enable_critic_agent:
            context.current_stage = PipelineStage.CRITIQUE
            critique_out = self._critic._safe_run(context)
            context.record_agent_output(critique_out)
            if self._tracer:
                self._tracer.record_agent(session_id, critique_out)

        # Stage 4: Synthesis
        context.current_stage = PipelineStage.SYNTHESIS
        synthesis_out = self._synthesizer._safe_run(context)
        context.record_agent_output(synthesis_out)
        if self._tracer:
            self._tracer.record_agent(session_id, synthesis_out)

        if not synthesis_out.success:
            context.current_stage = PipelineStage.FAILED
            return context

        # Stage 5: Validation (optional)
        if self._settings.enable_validator_agent:
            context.current_stage = PipelineStage.VALIDATION
            validation_out = self._validator._safe_run(context)
            context.record_agent_output(validation_out)
            if self._tracer:
                self._tracer.record_agent(session_id, validation_out)

        context.current_stage = PipelineStage.COMPLETE
        if self._tracer:
            self._tracer.end_session(session_id, context)

        logger.info(
            "Pipeline complete: session=%s, tokens=%d, elapsed=%.0fms",
            session_id,
            context.total_tokens,
            context.elapsed_ms,
        )
        return context
