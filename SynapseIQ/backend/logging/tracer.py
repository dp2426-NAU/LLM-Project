import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.memory.context_graph import AgentContext, AgentOutput

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_sessions (
    session_id      TEXT PRIMARY KEY,
    query           TEXT NOT NULL,
    output_format   TEXT,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    elapsed_ms      REAL,
    total_tokens    INTEGER,
    verdict         TEXT,
    composite_score REAL,
    error_count     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS agent_traces (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    agent           TEXT NOT NULL,
    stage           TEXT NOT NULL,
    tokens_used     INTEGER,
    latency_ms      REAL,
    success         INTEGER,
    recorded_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_traces_session ON agent_traces(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON pipeline_sessions(started_at);
"""


class PipelineTracer:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def start_session(self, session_id: str, query: str, output_format: str = "standard") -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO pipeline_sessions (session_id, query, output_format, started_at) VALUES (?,?,?,?)",
                (session_id, query, output_format, datetime.now(timezone.utc).isoformat()),
            )

    def record_agent(self, session_id: str, output: AgentOutput) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO agent_traces (session_id, agent, stage, tokens_used, latency_ms, success, recorded_at) VALUES (?,?,?,?,?,?,?)",
                (
                    session_id,
                    output.agent.value,
                    output.stage.value,
                    output.tokens_used,
                    output.latency_ms,
                    int(output.success),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def end_session(
        self,
        session_id: str,
        context: AgentContext,
        verdict: Optional[str] = None,
        composite_score: Optional[float] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """UPDATE pipeline_sessions
                   SET completed_at=?, elapsed_ms=?, total_tokens=?, verdict=?,
                       composite_score=?, error_count=?
                   WHERE session_id=?""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    context.elapsed_ms,
                    context.total_tokens,
                    verdict,
                    composite_score,
                    len(context.errors),
                    session_id,
                ),
            )

    def get_session_analytics(self, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM pipeline_sessions ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_agent_stats(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT agent,
                          COUNT(*) as calls,
                          AVG(latency_ms) as avg_latency_ms,
                          SUM(tokens_used) as total_tokens,
                          SUM(success) as successes
                   FROM agent_traces
                   GROUP BY agent"""
            ).fetchall()
        return [dict(r) for r in rows]

    def get_cost_summary(self, cost_per_1k_in: float, cost_per_1k_out: float) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT SUM(total_tokens) as total, COUNT(*) as sessions FROM pipeline_sessions WHERE completed_at IS NOT NULL"
            ).fetchone()

        total_tokens = row["total"] or 0
        estimated_cost = round((total_tokens / 1000) * ((cost_per_1k_in + cost_per_1k_out) / 2), 6)
        return {
            "total_tokens": total_tokens,
            "total_sessions": row["sessions"],
            "estimated_cost_usd": estimated_cost,
        }
