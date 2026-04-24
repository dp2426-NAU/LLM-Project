from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    agent: str = ""

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class CostReport:
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    by_agent: dict[str, dict] = field(default_factory=dict)
    model: str = "gpt-4o-mini"


MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    "gpt-4o": {"input": 0.0025, "output": 0.010},
    "gpt-4-turbo": {"input": 0.010, "output": 0.030},
    "llama3": {"input": 0.0, "output": 0.0},  # local
}


class SessionCostTracker:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self._model = model
        self._pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])
        self._usages: list[TokenUsage] = []

    def record(self, agent: str, input_tokens: int, output_tokens: int) -> None:
        self._usages.append(
            TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens, agent=agent)
        )

    def report(self) -> CostReport:
        total_in = sum(u.input_tokens for u in self._usages)
        total_out = sum(u.output_tokens for u in self._usages)
        cost = (total_in / 1000 * self._pricing["input"]) + (total_out / 1000 * self._pricing["output"])

        by_agent: dict[str, dict] = {}
        for u in self._usages:
            if u.agent not in by_agent:
                by_agent[u.agent] = {"input": 0, "output": 0}
            by_agent[u.agent]["input"] += u.input_tokens
            by_agent[u.agent]["output"] += u.output_tokens

        return CostReport(
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_tokens=total_in + total_out,
            estimated_cost_usd=round(cost, 6),
            by_agent=by_agent,
            model=self._model,
        )

    def estimate_query_cost(self, estimated_tokens: int) -> float:
        avg_rate = (self._pricing["input"] + self._pricing["output"]) / 2
        return round((estimated_tokens / 1000) * avg_rate, 6)
