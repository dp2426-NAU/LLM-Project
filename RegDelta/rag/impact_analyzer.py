import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.config import Settings
from models.document import RegulatoryBody
from models.impact_report import AffectedPolicy, ChangedSection, ImpactReport, RiskLevel
from rag.generator import LLMGenerator
from rag.retriever import Retriever
from store.vector_store import VectorStore
from store.version_tracker import VersionTracker
from utils.diff_engine import SectionDiff, compute_section_diffs

logger = logging.getLogger(__name__)

_SIGNIFICANCE_SYSTEM = """You are a regulatory compliance expert. Given a changed section of a regulation,
write a single sentence (max 30 words) explaining what changed and why it matters for a compliance team."""

_SIGNIFICANCE_PROMPT = """Old text: {old}

New text: {new}

Significance (one sentence):"""

_IMPACT_SYSTEM = """You are a senior compliance officer. Given changed regulation sections and matching internal policy excerpts,
produce a JSON impact analysis. Be precise, avoid filler language.

Output format:
{{
  "risk_level": "low|medium|high|critical",
  "executive_summary": "2-3 sentence summary of the regulatory change and its business impact",
  "recommended_actions": ["action 1", "action 2", ...],
  "policy_actions": {{
    "<policy_id>": "specific action required for this policy"
  }}
}}"""

_IMPACT_PROMPT = """Regulatory body: {body}
Regulation: {title}
Changed from version {old_v} to {new_v}

Changed sections:
{sections_text}

Affected internal policies:
{policies_text}

Produce the JSON impact analysis:"""


class ImpactAnalyzer:
    def __init__(
        self,
        settings: Settings,
        vector_store: VectorStore,
        version_tracker: VersionTracker,
    ) -> None:
        self._settings = settings
        self._retriever = Retriever(settings, vector_store)
        self._generator = LLMGenerator(settings)
        self._vt = version_tracker

    def analyze(
        self,
        regulation_id: str,
        old_text: str,
        new_text: str,
        old_version_tag: str,
        new_version_tag: str,
        regulation_title: str,
        regulatory_body: str,
    ) -> ImpactReport:
        logger.info(
            "Starting impact analysis: %s %s -> %s",
            regulation_id,
            old_version_tag,
            new_version_tag,
        )

        diffs = compute_section_diffs(old_text, new_text)
        logger.info("Detected %d changed sections", len(diffs))

        changed_sections = self._annotate_sections(diffs)

        all_policy_hits: dict[str, dict] = {}
        for section in changed_sections:
            query = f"{section.title or ''}\n{section.new_text[:600]}"
            hits = self._retriever.retrieve_policies(query)
            raw_hits = self._retriever.deduplicate_policy_hits(hits)
            for h in raw_hits:
                pid = h["metadata"].get("policy_id", "unknown")
                if pid not in all_policy_hits or h["score"] > all_policy_hits[pid]["score"]:
                    all_policy_hits[pid] = h

        total_policies = len(all_policy_hits)
        logger.info("Identified %d potentially affected policies", total_policies)

        sections_text = self._format_sections_for_prompt(changed_sections)
        policies_text = self._format_policies_for_prompt(list(all_policy_hits.values()))

        llm_result = self._generator.generate_json(
            system_prompt=_IMPACT_SYSTEM,
            user_prompt=_IMPACT_PROMPT.format(
                body=regulatory_body,
                title=regulation_title,
                old_v=old_version_tag,
                new_v=new_version_tag,
                sections_text=sections_text,
                policies_text=policies_text,
            ),
        )

        policy_actions: dict[str, str] = llm_result.get("policy_actions", {})
        affected_policies = [
            AffectedPolicy(
                policy_id=h["metadata"].get("policy_id", "unknown"),
                policy_title=h["metadata"].get("title", "Untitled"),
                department=h["metadata"].get("department", "Unknown"),
                relevance_score=h["score"],
                matched_excerpt=h["text"][:400],
                recommended_action=policy_actions.get(
                    h["metadata"].get("policy_id", ""), "Review for compliance gaps."
                ),
            )
            for h in all_policy_hits.values()
        ]

        risk_str = llm_result.get("risk_level", "medium").lower()
        try:
            risk_level = RiskLevel(risk_str)
        except ValueError:
            risk_level = RiskLevel.MEDIUM

        report = ImpactReport(
            report_id=str(uuid.uuid4()),
            regulation_id=regulation_id,
            old_version=old_version_tag,
            new_version=new_version_tag,
            generated_at=datetime.now(timezone.utc),
            risk_level=risk_level,
            executive_summary=llm_result.get("executive_summary", ""),
            changed_sections=changed_sections,
            affected_policies=affected_policies,
            recommended_actions=llm_result.get("recommended_actions", []),
            total_policies_scanned=total_policies,
        )

        self._vt.save_report(
            report_id=report.report_id,
            regulation_id=regulation_id,
            old_v=old_version_tag,
            new_v=new_version_tag,
            risk=risk_level.value,
            report_json=json.dumps(report.to_dict()),
        )

        return report

    def _annotate_sections(self, diffs: list[SectionDiff]) -> list[ChangedSection]:
        sections = []
        for d in diffs[:10]:  # cap at 10 most significant sections
            if d.change_type == "removed":
                significance = "Section was removed from the regulation."
            else:
                significance = self._generator.generate(
                    system_prompt=_SIGNIFICANCE_SYSTEM,
                    user_prompt=_SIGNIFICANCE_PROMPT.format(
                        old=d.old_text[:400],
                        new=d.new_text[:400],
                    ),
                ).strip()

            sections.append(
                ChangedSection(
                    section_id=d.section_id,
                    title=d.title,
                    old_text=d.old_text,
                    new_text=d.new_text,
                    change_type=d.change_type,
                    significance=significance,
                )
            )
        return sections

    def _format_sections_for_prompt(self, sections: list[ChangedSection]) -> str:
        parts = []
        for s in sections[:5]:
            parts.append(
                f"[{s.change_type.upper()}] {s.title or s.section_id}\n"
                f"Significance: {s.significance}\n"
                f"New text excerpt: {s.new_text[:300]}"
            )
        return "\n\n".join(parts)

    def _format_policies_for_prompt(self, hits: list[dict]) -> str:
        parts = []
        for h in hits[:6]:
            meta = h["metadata"]
            parts.append(
                f"Policy ID: {meta.get('policy_id')}\n"
                f"Title: {meta.get('title')}\n"
                f"Department: {meta.get('department')}\n"
                f"Relevance: {h['score']:.2f}\n"
                f"Excerpt: {h['text'][:250]}"
            )
        return "\n\n".join(parts)
