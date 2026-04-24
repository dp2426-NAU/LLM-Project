import pytest

from backend.evaluation.metrics import (
    compute_length_completeness,
    compute_lexical_relevance,
    compute_structural_coherence,
    extract_validation_scores,
)


class TestLexicalRelevance:
    def test_perfect_overlap(self):
        query = "transformer attention mechanism"
        synthesis = "The transformer attention mechanism works by computing attention weights."
        score = compute_lexical_relevance(query, synthesis)
        assert score >= 0.75

    def test_no_overlap(self):
        query = "quantum computing entanglement"
        synthesis = "Dogs and cats are common household pets."
        score = compute_lexical_relevance(query, synthesis)
        assert score < 0.30

    def test_empty_query(self):
        score = compute_lexical_relevance("", "some text here")
        assert score == 0.0


class TestLengthCompleteness:
    def test_brief_adequate_length(self):
        text = "word " * 260
        score = compute_length_completeness(text, "brief")
        assert score >= 0.75

    def test_standard_too_short(self):
        text = "word " * 100
        score = compute_length_completeness(text, "standard")
        assert score < 0.75

    def test_detailed_full_length(self):
        text = "word " * 1900
        score = compute_length_completeness(text, "detailed")
        assert score == 1.0


class TestStructuralCoherence:
    def test_well_structured_document(self):
        text = """ABSTRACT
This paper examines the impact of attention mechanisms.

MAIN FINDINGS
Transformers outperform RNNs on long-range dependencies. The attention mechanism
allows all tokens to interact directly. This is a key advantage.

CONCLUSIONS
Attention is central to modern NLP. Future work should explore efficiency.
"""
        score = compute_structural_coherence(text)
        assert score >= 0.50

    def test_unstructured_text(self):
        text = "this is a run on sentence with no structure whatsoever and it continues endlessly"
        score = compute_structural_coherence(text)
        assert score < 0.75


class TestValidationScoreExtraction:
    def test_extracts_all_dimensions(self):
        structured = {
            "scores": {
                "coherence": {"score": 0.85, "rationale": "Flows well"},
                "relevance": {"score": 0.90, "rationale": "On target"},
                "factuality": {"score": 0.70, "rationale": "Mostly supported"},
                "completeness": {"score": 0.80, "rationale": "Covers key areas"},
            }
        }
        scores = extract_validation_scores(structured)
        assert scores["coherence"] == 0.85
        assert scores["relevance"] == 0.90
        assert all(0.0 <= v <= 1.0 for v in scores.values())

    def test_handles_missing_scores(self):
        scores = extract_validation_scores(None)
        assert all(v == 0.0 for v in scores.values())

    def test_handles_partial_scores(self):
        structured = {"scores": {"coherence": {"score": 0.7}}}
        scores = extract_validation_scores(structured)
        assert scores["coherence"] == 0.7
        assert scores["relevance"] == 0.0


class TestCostTracker:
    def test_cost_estimation(self):
        from backend.utils.cost_tracker import SessionCostTracker
        tracker = SessionCostTracker(model="gpt-4o-mini")
        tracker.record("researcher", input_tokens=500, output_tokens=300)
        tracker.record("synthesizer", input_tokens=800, output_tokens=600)
        report = tracker.report()
        assert report.total_tokens == 2200
        assert report.estimated_cost_usd > 0
        assert "researcher" in report.by_agent

    def test_local_model_zero_cost(self):
        from backend.utils.cost_tracker import SessionCostTracker
        tracker = SessionCostTracker(model="llama3")
        tracker.record("researcher", input_tokens=1000, output_tokens=500)
        report = tracker.report()
        assert report.estimated_cost_usd == 0.0
