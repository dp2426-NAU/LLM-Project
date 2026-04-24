from enum import Enum


class AgentRole(str, Enum):
    COORDINATOR = "coordinator"
    RESEARCHER = "researcher"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"
    VALIDATOR = "validator"


class PipelineStage(str, Enum):
    INGESTION = "ingestion"
    RESEARCH = "research"
    CRITIQUE = "critique"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    COMPLETE = "complete"
    FAILED = "failed"


class OutputFormat(str, Enum):
    BRIEF = "brief"           # ~300 words, executive summary
    STANDARD = "standard"     # ~800 words, structured report
    DETAILED = "detailed"     # ~2000 words, full analysis


class CitationStyle(str, Enum):
    INLINE = "inline"
    FOOTNOTE = "footnote"
    NONE = "none"


# Token budget per agent (prevents runaway costs)
AGENT_TOKEN_BUDGETS: dict[str, int] = {
    AgentRole.RESEARCHER: 1200,
    AgentRole.CRITIC: 800,
    AgentRole.SYNTHESIZER: 1800,
    AgentRole.VALIDATOR: 600,
}

# Pipeline execution order
PIPELINE_ORDER = [
    PipelineStage.INGESTION,
    PipelineStage.RESEARCH,
    PipelineStage.CRITIQUE,
    PipelineStage.SYNTHESIS,
    PipelineStage.VALIDATION,
    PipelineStage.COMPLETE,
]

# Evaluation weight matrix (must sum to 1.0)
EVAL_WEIGHTS = {
    "coherence": 0.30,
    "relevance": 0.35,
    "factuality": 0.25,
    "completeness": 0.10,
}
