import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        obj: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(obj)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root.handlers.clear()
    root.addHandler(handler)

    for noisy in ("chromadb", "sentence_transformers", "httpx", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class AnalyticsCollector:
    """In-process event collector — lightweight alternative to a full metrics stack."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._logger = logging.getLogger("analytics")

    def record(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "event_type": event_type,
            "ts": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        self._events.append(event)
        self._logger.debug("Analytics event: %s", event_type)

    def get_recent(self, limit: int = 100) -> list[dict]:
        return self._events[-limit:]

    def summarize(self) -> dict[str, Any]:
        if not self._events:
            return {"total_events": 0}
        by_type: dict[str, int] = {}
        for e in self._events:
            by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1
        return {
            "total_events": len(self._events),
            "by_type": by_type,
            "oldest": self._events[0]["ts"],
            "newest": self._events[-1]["ts"],
        }
