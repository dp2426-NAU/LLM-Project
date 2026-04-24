import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class EvaluationResult:
    session_id: str
    query: str
    coherence_score: float
    relevance_score: float
    factuality_score: float
    completeness_score: float
    composite_score: float
    verdict: str
    total_tokens: int
    elapsed_ms: float
    fabrication_flags: list[str]
    passed: bool


def compute_lexical_relevance(query: str, synthesis_text: str) -> float:
    """Lightweight relevance proxy using keyword overlap. Used when LLM scoring not available."""
    query_terms = set(re.findall(r"\b\w{4,}\b", query.lower()))
    synth_terms = set(re.findall(r"\b\w{4,}\b", synthesis_text.lower()))
    if not query_terms:
        return 0.0
    overlap = len(query_terms & synth_terms) / len(query_terms)
    return round(min(overlap * 1.5, 1.0), 3)


def compute_length_completeness(text: str, output_format: str) -> float:
    """Scores completeness based on word count relative to expected output format length."""
    word_count = len(re.findall(r"\w+", text))
    targets = {"brief": 250, "standard": 700, "detailed": 1800}
    target = targets.get(output_format, 700)
    ratio = word_count / target
    if ratio >= 0.90:
        return 1.0
    elif ratio >= 0.65:
        return 0.75
    elif ratio >= 0.40:
        return 0.50
    return 0.25


def compute_structural_coherence(text: str) -> float:
    """Heuristic: checks for section headers, paragraph breaks, and sentence endings."""
    has_sections = bool(re.search(r"^[A-Z\s]{5,}$", text, re.MULTILINE))
    para_count = len([p for p in text.split("\n\n") if len(p.strip()) > 30])
    sentence_count = len(re.findall(r"[.!?]\s", text))
    avg_sentence_len = len(text.split()) / max(sentence_count, 1)

    score = 0.0
    if has_sections:
        score += 0.25
    if para_count >= 3:
        score += 0.35
    if 10 <= avg_sentence_len <= 35:
        score += 0.40
    return round(min(score, 1.0), 3)


def extract_validation_scores(validation_structured: Optional[dict]) -> dict[str, float]:
    """Pull the LLM-generated scores from validator output."""
    if not validation_structured:
        return {"coherence": 0.0, "relevance": 0.0, "factuality": 0.0, "completeness": 0.0}

    scores_raw = validation_structured.get("scores", {})
    result = {}
    for dim in ["coherence", "relevance", "factuality", "completeness"]:
        dim_data = scores_raw.get(dim, {})
        if isinstance(dim_data, dict):
            result[dim] = float(dim_data.get("score", 0.0))
        else:
            result[dim] = float(dim_data)
    return result
