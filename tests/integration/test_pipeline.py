from unittest.mock import MagicMock, patch
import pytest

from backend.config.constants import AgentRole, PipelineStage
from backend.memory.context_graph import AgentContext, AgentOutput, RetrievedChunk


def _make_agent_output(agent, stage, content="Test output", tokens=100):
    return AgentOutput(
        agent=agent,
        stage=stage,
        content=content,
        structured={},
        tokens_used=tokens,
        latency_ms=250.0,
        success=True,
    )


class TestOrchestratorPipeline:
    def test_full_pipeline_completes(self, settings, mock_prompt_engine, mock_corpus_store):
        from backend.pipeline.orchestrator import SynapseOrchestrator
        from backend.logging.tracer import PipelineTracer
        import tempfile, os

        db_path = os.path.join(tempfile.mkdtemp(), "test.db")
        tracer = PipelineTracer(db_path)

        orchestrator = SynapseOrchestrator(settings, mock_corpus_store, mock_prompt_engine, tracer)

        researcher_out = _make_agent_output(AgentRole.RESEARCHER, PipelineStage.RESEARCH, "Core findings here.")
        critic_out = _make_agent_output(AgentRole.CRITIC, PipelineStage.CRITIQUE, '{"issues": [], "strength_score": 0.8, "strength_rationale": "Good", "coverage_gaps": [], "bias_signals": []}')
        synth_out = _make_agent_output(AgentRole.SYNTHESIZER, PipelineStage.SYNTHESIS, "ABSTRACT\nThis is the synthesis.\n\nMAIN FINDINGS\nKey findings.")
        valid_out = _make_agent_output(AgentRole.VALIDATOR, PipelineStage.VALIDATION, '{"scores": {"coherence": {"score": 0.8}, "relevance": {"score": 0.85}, "factuality": {"score": 0.75}, "completeness": {"score": 0.7}}, "verdict": "PASS", "verdict_note": "Solid.", "fabrication_flags": [], "omission_flags": []}')

        with patch.object(orchestrator._researcher, "_safe_run", return_value=researcher_out), \
             patch.object(orchestrator._critic, "_safe_run", return_value=critic_out), \
             patch.object(orchestrator._synthesizer, "_safe_run", return_value=synth_out), \
             patch.object(orchestrator._validator, "_safe_run", return_value=valid_out):

            context = orchestrator.run("What are the principles of transformer models?")

        assert context.current_stage == PipelineStage.COMPLETE
        assert context.synthesis_output is not None
        assert context.total_tokens == 400
        assert not context.has_errors

    def test_pipeline_handles_researcher_failure(self, settings, mock_prompt_engine, mock_corpus_store):
        from backend.pipeline.orchestrator import SynapseOrchestrator

        orchestrator = SynapseOrchestrator(settings, mock_corpus_store, mock_prompt_engine)
        failed_out = AgentOutput(
            agent=AgentRole.RESEARCHER,
            stage=PipelineStage.FAILED,
            content="",
            success=False,
            error="LLM timeout",
        )

        with patch.object(orchestrator._researcher, "_safe_run", return_value=failed_out):
            context = orchestrator.run("Test query")

        assert context.current_stage == PipelineStage.FAILED

    def test_context_token_accumulation(self, agent_context):
        out1 = _make_agent_output(AgentRole.RESEARCHER, PipelineStage.RESEARCH, tokens=200)
        out2 = _make_agent_output(AgentRole.CRITIC, PipelineStage.CRITIQUE, tokens=150)
        agent_context.record_agent_output(out1)
        agent_context.record_agent_output(out2)
        assert agent_context.total_tokens == 350


class TestEvaluator:
    def test_evaluates_complete_context(self, settings, agent_context):
        from backend.evaluation.evaluator import PipelineEvaluator
        from backend.memory.context_graph import AgentOutput

        agent_context.synthesis_output = AgentOutput(
            agent=AgentRole.SYNTHESIZER,
            stage=PipelineStage.SYNTHESIS,
            content="ABSTRACT\nThis paper examines transformers.\n\nMAIN FINDINGS\nAttention is the key mechanism. It allows tokens to interact. This is important for performance. Multiple heads capture different patterns. Feed-forward layers add capacity. Positional encodings handle order.",
            structured={"sections": {"ABSTRACT": "This paper examines transformers."}, "word_count": 40},
            success=True,
        )

        evaluator = PipelineEvaluator(settings)
        result = evaluator.evaluate(agent_context)

        assert 0.0 <= result.composite_score <= 1.0
        assert result.verdict in {"PASS", "CONDITIONAL_PASS", "FAIL"}
        assert isinstance(result.fabrication_flags, list)
