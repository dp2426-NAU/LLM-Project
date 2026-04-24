import logging
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined, TemplateError

logger = logging.getLogger(__name__)


class PromptTemplate:
    def __init__(self, raw: dict) -> None:
        self.version: str = raw.get("version", "1.0")
        self.agent: str = raw["agent"]
        self.description: str = raw.get("description", "")
        self._system_raw: str = raw["system"]
        self._user_raw: str = raw["user"]
        self.output_schema: dict = raw.get("output_schema", {})

    def render(self, **kwargs: Any) -> tuple[str, str]:
        env = Environment(undefined=StrictUndefined)
        try:
            system = env.from_string(self._system_raw).render(**kwargs)
            user = env.from_string(self._user_raw).render(**kwargs)
        except TemplateError as e:
            raise ValueError(f"Template render error for agent '{self.agent}': {e}") from e
        return system.strip(), user.strip()


class PromptEngine:
    def __init__(self, templates_dir: Path) -> None:
        self._dir = templates_dir
        self._cache: dict[str, PromptTemplate] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not self._dir.exists():
            logger.warning("Prompts directory not found: %s", self._dir)
            return
        for path in self._dir.glob("*.yaml"):
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
                template = PromptTemplate(raw)
                self._cache[template.agent] = template
                logger.debug("Loaded prompt template: %s v%s", template.agent, template.version)
            except Exception as e:
                logger.error("Failed to load template %s: %s", path.name, e)

    def get(self, agent_name: str) -> PromptTemplate:
        if agent_name not in self._cache:
            raise KeyError(f"No prompt template found for agent: '{agent_name}'")
        return self._cache[agent_name]

    def render(self, agent_name: str, **kwargs: Any) -> tuple[str, str]:
        return self.get(agent_name).render(**kwargs)

    def reload(self) -> None:
        self._cache.clear()
        self._load_all()
        logger.info("Prompt templates reloaded (%d loaded)", len(self._cache))

    @property
    def loaded_agents(self) -> list[str]:
        return list(self._cache.keys())
