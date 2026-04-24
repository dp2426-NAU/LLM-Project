import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from backend.config.constants import AgentRole, AGENT_TOKEN_BUDGETS
from backend.config.settings import Settings
from backend.memory.context_graph import AgentContext, AgentOutput
from backend.prompts.engine import PromptEngine
from backend.utils.token_counter import count_tokens

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def chat(self, system: str, user: str, max_tokens: int = 1500) -> tuple[str, int, int]:
        """Returns (content, input_tokens, output_tokens)."""
        if self._settings.llm_provider == "openai":
            return self._openai_chat(system, user, max_tokens)
        return self._ollama_chat(system, user, max_tokens)

    def _openai_chat(self, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
        from openai import OpenAI
        client = OpenAI(api_key=self._settings.openai_api_key)
        resp = client.chat.completions.create(
            model=self._settings.openai_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=self._settings.openai_temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content or ""
        usage = resp.usage
        return content, usage.prompt_tokens, usage.completion_tokens

    def _ollama_chat(self, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
        import httpx
        payload = {
            "model": self._settings.ollama_model,
            "prompt": f"{system}\n\n{user}",
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{self._settings.ollama_base_url}/api/generate", json=payload)
            resp.raise_for_status()
        data = resp.json()
        content = data.get("response", "")
        prompt_tokens = count_tokens(system + user)
        output_tokens = count_tokens(content)
        return content, prompt_tokens, output_tokens

    def extract_json(self, raw: str) -> dict[str, Any]:
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("JSON parse failed, returning raw text in 'raw' field")
            return {"raw": raw}


class BaseAgent(ABC):
    def __init__(self, role: AgentRole, settings: Settings, prompt_engine: PromptEngine) -> None:
        self.role = role
        self._settings = settings
        self._prompt_engine = prompt_engine
        self._llm = LLMClient(settings)
        self._max_tokens = AGENT_TOKEN_BUDGETS.get(role, 1000)
        self._logger = logging.getLogger(f"agent.{role.value}")

    @abstractmethod
    def run(self, context: AgentContext) -> AgentOutput:
        ...

    def _timed_llm_call(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
    ) -> tuple[str, int, float]:
        max_tokens = max_tokens or self._max_tokens
        t0 = time.time()
        content, input_tok, output_tok = self._llm.chat(system, user, max_tokens)
        latency_ms = round((time.time() - t0) * 1000, 1)
        total_tokens = input_tok + output_tok
        self._logger.info(
            "LLM call complete: tokens=%d, latency=%.0fms",
            total_tokens,
            latency_ms,
        )
        return content, total_tokens, latency_ms

    def _safe_run(self, context: AgentContext) -> AgentOutput:
        from backend.config.constants import PipelineStage
        retries = self._settings.max_agent_retries
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                return self.run(context)
            except Exception as e:
                last_error = e
                self._logger.warning("Agent %s attempt %d failed: %s", self.role.value, attempt + 1, e)

        return AgentOutput(
            agent=self.role,
            stage=PipelineStage.FAILED,
            content="",
            success=False,
            error=str(last_error),
        )
