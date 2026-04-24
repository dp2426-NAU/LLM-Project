from unittest.mock import MagicMock, patch
import pytest

from backend.config.constants import AgentRole, PipelineStage
from backend.memory.context_graph import AgentContext, AgentOutput, RetrievedChunk


class TestResearcherAgent:
    def test_runs_with_valid_chunks(self, settings, mock_prompt_engine, mock_llm_response, agent_context):
        from backend.agents.researcher import ResearcherAgent

        agent = ResearcherAgent(settings, mock_prompt_engine)
        with patch.object(agent, "_timed_llm_call", return_value=mock_llm_response):
            output = agent.run(agent_context)

        assert output.success is True
        assert output.agent == AgentRole.RESEARCHER
        assert output.stage == PipelineStage.RESEARCH
        assert len(output.content) > 0
        assert output.tokens_used == 150

    def test_handles_empty_chunks(self, settings, mock_prompt_engine):
        from backend.agents.researcher import ResearcherAgent
        from backend.memory.context_graph import AgentContext

        agent = ResearcherAgent(settings, mock_prompt_engine)
        ctx = AgentContext(session_id="no-chunks", query="empty query")
        ctx.retrieved_chunks = []

        output = agent.run(ctx)
        assert output.success is True
        assert "No relevant documents" in output.content

    def test_parses_section_output(self, settings, mock_prompt_engine, agent_context, mock_llm_response):
        from backend.agents.researcher import ResearcherAgent

        agent = ResearcherAgent(settings, mock_prompt_engine)
        with patch.object(agent, "_timed_llm_call", return_value=mock_llm_response):
            output = agent.run(agent_context)

        findings = output.structured.get("core_findings", [])
        gaps = output.structured.get("evidence_gaps", [])
        assert isinstance(findings, list)
        assert isinstance(gaps, list)


class TestCriticAgent:
    def test_skips_without_research_output(self, settings, mock_prompt_engine):
        from backend.agents.critic import CriticAgent
        from backend.memory.context_graph import AgentContext

        agent = CriticAgent(settings, mock_prompt_engine)
        ctx = AgentContext(session_id="no-research", query="test")
        ctx.research_output = None

        output = agent.run(ctx)
        assert output.success is True
        assert "Skipped" in output.content

    def test_returns_structured_critique(self, settings, mock_prompt_engine, agent_context):
        from backend.agents.critic import CriticAgent
        from backend.memory.context_graph import AgentOutput

        agent_context.research_output = AgentOutput(
            agent=AgentRole.RESEARCHER,
            stage=PipelineStage.RESEARCH,
            content="Transformers use attention. This is the key finding.",
            success=True,
        )

        mock_json = '{"issues": [], "coverage_gaps": ["scaling laws"], "bias_signals": [], "strength_score": 0.72, "strength_rationale": "Good but incomplete."}'
        agent = CriticAgent(settings, mock_prompt_engine)
        with patch.object(agent, "_timed_llm_call", return_value=(mock_json, 100, 200.0)):
            output = agent.run(agent_context)

        assert output.success is True
        assert "strength_score" in output.structured


class TestValidatorAgent:
    def test_composite_score_computation(self, settings, mock_prompt_engine):
        from backend.agents.validator import ValidatorAgent

        agent = ValidatorAgent(settings, mock_prompt_engine)
        structured = {
            "scores": {
                "coherence": {"score": 0.8},
                "relevance": {"score": 0.9},
                "factuality": {"score": 0.7},
                "completeness": {"score": 0.6},
            }
        }
        composite = agent._compute_composite_score(structured)
        assert 0.0 <= composite <= 1.0
        assert composite > 0.5

    def test_handles_missing_synthesis(self, settings, mock_prompt_engine):
        from backend.agents.validator import ValidatorAgent
        from backend.memory.context_graph import AgentContext

        agent = ValidatorAgent(settings, mock_prompt_engine)
        ctx = AgentContext(session_id="no-synth", query="test")
        ctx.synthesis_output = None

        output = agent.run(ctx)
        assert output.success is True
        assert output.structured["verdict"] == "FAIL"
