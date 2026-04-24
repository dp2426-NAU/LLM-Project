import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from models.document import RegulationVersion, RegulatoryBody

logger = logging.getLogger(__name__)

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS regulation_versions (
    regulation_id   TEXT NOT NULL,
    body            TEXT NOT NULL,
    title           TEXT NOT NULL,
    version_tag     TEXT NOT NULL,
    effective_date  TEXT,
    ingested_at     TEXT NOT NULL,
    doc_id          TEXT NOT NULL,
    source_url      TEXT,
    PRIMARY KEY (regulation_id, version_tag)
);

CREATE TABLE IF NOT EXISTS impact_reports (
    report_id       TEXT PRIMARY KEY,
    regulation_id   TEXT NOT NULL,
    old_version     TEXT NOT NULL,
    new_version     TEXT NOT NULL,
    generated_at    TEXT NOT NULL,
    risk_level      TEXT NOT NULL,
    report_json     TEXT NOT NULL
);
"""


class VersionTracker:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_CREATE_SQL)
        logger.info("VersionTracker DB initialized at %s", self._db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def register_version(self, version: RegulationVersion) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO regulation_versions
                (regulation_id, body, title, version_tag, effective_date, ingested_at, doc_id, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version.regulation_id,
                    version.body.value,
                    version.title,
                    version.version_tag,
                    version.effective_date,
                    version.ingested_at.isoformat(),
                    version.doc_id,
                    version.source_url,
                ),
            )

    def get_versions(self, regulation_id: str) -> list[RegulationVersion]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM regulation_versions WHERE regulation_id=? ORDER BY ingested_at",
                (regulation_id,),
            ).fetchall()

        return [
            RegulationVersion(
                regulation_id=r["regulation_id"],
                body=RegulatoryBody(r["body"]),
                title=r["title"],
                version_tag=r["version_tag"],
                effective_date=r["effective_date"],
                ingested_at=datetime.fromisoformat(r["ingested_at"]),
                doc_id=r["doc_id"],
                source_url=r["source_url"],
            )
            for r in rows
        ]

    def get_latest_two(self, regulation_id: str) -> tuple[Optional[RegulationVersion], Optional[RegulationVersion]]:
        versions = self.get_versions(regulation_id)
        if len(versions) < 2:
            return (versions[0] if versions else None, None)
        return versions[-2], versions[-1]

    def save_report(self, report_id: str, regulation_id: str, old_v: str, new_v: str, risk: str, report_json: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO impact_reports
                (report_id, regulation_id, old_version, new_version, generated_at, risk_level, report_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    regulation_id,
                    old_v,
                    new_v,
                    datetime.now(timezone.utc).isoformat(),
                    risk,
                    report_json,
                ),
            )

    def get_report(self, report_id: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT report_json FROM impact_reports WHERE report_id=?",
                (report_id,),
            ).fetchone()
        return row["report_json"] if row else None

    def list_reports(self, regulation_id: Optional[str] = None) -> list[dict]:
        with self._connect() as conn:
            if regulation_id:
                rows = conn.execute(
                    "SELECT report_id, regulation_id, old_version, new_version, generated_at, risk_level FROM impact_reports WHERE regulation_id=? ORDER BY generated_at DESC",
                    (regulation_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT report_id, regulation_id, old_version, new_version, generated_at, risk_level FROM impact_reports ORDER BY generated_at DESC"
                ).fetchall()
        return [dict(r) for r in rows]
