from pathlib import Path
import pytest


class TestPromptEngine:
    def test_loads_all_templates(self, settings):
        from backend.prompts.engine import PromptEngine
        engine = PromptEngine(settings.prompts_dir)
        expected = {"researcher", "critic", "synthesizer", "validator"}
        assert expected.issubset(set(engine.loaded_agents))

    def test_render_researcher_template(self, settings):
        from backend.prompts.engine import PromptEngine
        engine = PromptEngine(settings.prompts_dir)
        system, user = engine.render(
            "researcher",
            query="What is transformer attention?",
            output_format="standard",
            retrieved_chunks=[
                {"text": "Attention allows tokens to interact.", "source": "paper.pdf", "score": 0.9}
            ],
        )
        assert len(system) > 20
        assert "transformer" in user.lower() or "attention" in user.lower()

    def test_render_critic_template(self, settings):
        from backend.prompts.engine import PromptEngine
        engine = PromptEngine(settings.prompts_dir)
        system, user = engine.render(
            "critic",
            query="What is RLHF?",
            research_output="RLHF involves human feedback to train reward models.",
        )
        assert "peer reviewer" in system.lower() or "critic" in system.lower() or "rigorous" in system.lower()
        assert "RLHF" in user

    def test_render_synthesizer_template_formats(self, settings):
        from backend.prompts.engine import PromptEngine
        engine = PromptEngine(settings.prompts_dir)
        for fmt in ["brief", "standard", "detailed"]:
            system, user = engine.render(
                "synthesizer",
                query="Explain LLM fine-tuning",
                output_format=fmt,
                citation_style="inline",
                research_output="Fine-tuning adjusts pretrained model weights.",
                critique_output="Coverage of PEFT methods is missing.",
            )
            assert len(user) > 50

    def test_unknown_agent_raises(self, settings):
        from backend.prompts.engine import PromptEngine
        engine = PromptEngine(settings.prompts_dir)
        with pytest.raises(KeyError):
            engine.render("nonexistent_agent", query="test")


class TestTokenCounter:
    def test_basic_estimate(self):
        from backend.utils.token_counter import count_tokens
        short = "Hello world"
        long_text = " ".join(["word"] * 100)
        assert count_tokens(short) < count_tokens(long_text)
        assert count_tokens("") == 0

    def test_budget_check(self):
        from backend.utils.token_counter import budget_check
        within, count = budget_check("short text", max_tokens=1000)
        assert within is True

        within2, _ = budget_check("word " * 500, max_tokens=10)
        assert within2 is False

    def test_truncate(self):
        from backend.utils.token_counter import truncate_to_budget
        text = "word " * 1000
        result = truncate_to_budget(text, max_tokens=50)
        from backend.utils.token_counter import count_tokens
        assert count_tokens(result) <= 60  # some tolerance
