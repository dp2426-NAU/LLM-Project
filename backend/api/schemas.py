from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class SynthesisRequest(BaseModel):
    query: str = Field(..., min_length=10, max_length=1000, description="The research question or topic")
    output_format: str = Field("standard", description="'brief' | 'standard' | 'detailed'")
    citation_style: str = Field("inline", description="'inline' | 'footnote' | 'none'")
    session_id: Optional[str] = None

    @field_validator("output_format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        allowed = {"brief", "standard", "detailed"}
        if v not in allowed:
            raise ValueError(f"output_format must be one of {allowed}")
        return v

    @field_validator("citation_style")
    @classmethod
    def validate_citation(cls, v: str) -> str:
        allowed = {"inline", "footnote", "none"}
        if v not in allowed:
            raise ValueError(f"citation_style must be one of {allowed}")
        return v


class AgentOutputSchema(BaseModel):
    agent: str
    stage: str
    content: str
    tokens_used: int
    latency_ms: float
    success: bool
    error: Optional[str] = None


class EvaluationSchema(BaseModel):
    coherence_score: float
    relevance_score: float
    factuality_score: float
    completeness_score: float
    composite_score: float
    verdict: str
    fabrication_flags: list[str]
    passed: bool


class SynthesisResponse(BaseModel):
    session_id: str
    query: str
    output_format: str
    synthesis: str
    sections: dict[str, str]
    sources_cited: list[str]
    evaluation: EvaluationSchema
    pipeline_summary: dict[str, Any]
    agent_traces: list[AgentOutputSchema]


class IngestRequest(BaseModel):
    text: Optional[str] = None
    file_path: Optional[str] = None
    source_label: str = Field(..., description="Human-readable source name")
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    status: str
    source: str
    chunks_indexed: int
    total_corpus_size: int


class AnalyticsResponse(BaseModel):
    recent_sessions: list[dict]
    agent_stats: list[dict]
    cost_summary: dict[str, Any]
    analytics_summary: dict[str, Any]


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3)
    top_k: int = Field(6, ge=1, le=20)
    min_score: float = Field(0.30, ge=0.0, le=1.0)


class QueryResponse(BaseModel):
    query: str
    hits: list[dict[str, Any]]
    total: int
