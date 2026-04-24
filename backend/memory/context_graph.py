import time
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.config.constants import AgentRole, PipelineStage


@dataclass
class AgentOutput:
    agent: AgentRole
    stage: PipelineStage
    content: str
    structured: dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class RetrievedChunk:
    text: str
    source: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Shared mutable context passed through the agent pipeline."""

    session_id: str
    query: str
    output_format: str = "standard"
    citation_style: str = "inline"

    # Populated by ingestion stage
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)

    # Populated sequentially by agents
    research_output: Optional[AgentOutput] = None
    critique_output: Optional[AgentOutput] = None
    synthesis_output: Optional[AgentOutput] = None
    validation_output: Optional[AgentOutput] = None

    # Tracking
    pipeline_start_ms: float = field(default_factory=lambda: time.time() * 1000)
    total_tokens: int = 0
    errors: list[str] = field(default_factory=list)
    current_stage: PipelineStage = PipelineStage.INGESTION

    def record_agent_output(self, output: AgentOutput) -> None:
        if output.agent == AgentRole.RESEARCHER:
            self.research_output = output
        elif output.agent == AgentRole.CRITIC:
            self.critique_output = output
        elif output.agent == AgentRole.SYNTHESIZER:
            self.synthesis_output = output
        elif output.agent == AgentRole.VALIDATOR:
            self.validation_output = output

        self.total_tokens += output.tokens_used
        if output.error:
            self.errors.append(f"[{output.agent}] {output.error}")

    @property
    def elapsed_ms(self) -> float:
        return round(time.time() * 1000 - self.pipeline_start_ms, 2)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def to_summary(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "query": self.query,
            "current_stage": self.current_stage.value,
            "total_tokens": self.total_tokens,
            "elapsed_ms": self.elapsed_ms,
            "errors": self.errors,
            "chunks_retrieved": len(self.retrieved_chunks),
            "agents_completed": [
                a.value
                for a, o in [
                    (AgentRole.RESEARCHER, self.research_output),
                    (AgentRole.CRITIC, self.critique_output),
                    (AgentRole.SYNTHESIZER, self.synthesis_output),
                    (AgentRole.VALIDATOR, self.validation_output),
                ]
                if o is not None
            ],
        }
