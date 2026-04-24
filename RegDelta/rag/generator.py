import json
import logging
from typing import Any

from app.config import Settings

logger = logging.getLogger(__name__)


class LLMGenerator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._provider = settings.llm_provider

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package required: pip install openai")

        client = OpenAI(api_key=self._settings.openai_api_key)
        response = client.chat.completions.create(
            model=self._settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""

    def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx required: pip install httpx")

        payload = {
            "model": self._settings.ollama_model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
        }
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{self._settings.ollama_base_url}/api/generate", json=payload)
            resp.raise_for_status()
        return resp.json().get("response", "")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        logger.debug("LLM generate via provider=%s", self._provider)
        if self._provider == "openai":
            return self._call_openai(system_prompt, user_prompt)
        elif self._provider == "ollama":
            return self._call_ollama(system_prompt, user_prompt)
        raise ValueError(f"Unknown LLM provider: {self._provider}")

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        raw = self.generate(system_prompt, user_prompt)
        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON, wrapping in raw field")
            return {"raw": raw}
