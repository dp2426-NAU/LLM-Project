from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ChangedSection:
    section_id: str
    title: Optional[str]
    old_text: str
    new_text: str
    change_type: str  # "added" | "modified" | "removed"
    significance: str  # brief LLM-generated note


@dataclass
class AffectedPolicy:
    policy_id: str
    policy_title: str
    department: str
    relevance_score: float
    matched_excerpt: str
    recommended_action: str


@dataclass
class ImpactReport:
    report_id: str
    regulation_id: str
    old_version: str
    new_version: str
    generated_at: datetime
    risk_level: RiskLevel
    executive_summary: str
    changed_sections: list[ChangedSection] = field(default_factory=list)
    affected_policies: list[AffectedPolicy] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    total_policies_scanned: int = 0

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "regulation_id": self.regulation_id,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "generated_at": self.generated_at.isoformat(),
            "risk_level": self.risk_level.value,
            "executive_summary": self.executive_summary,
            "total_policies_scanned": self.total_policies_scanned,
            "affected_policies_count": len(self.affected_policies),
            "changed_sections": [
                {
                    "section_id": s.section_id,
                    "title": s.title,
                    "change_type": s.change_type,
                    "significance": s.significance,
                    "old_text": s.old_text[:500],
                    "new_text": s.new_text[:500],
                }
                for s in self.changed_sections
            ],
            "affected_policies": [
                {
                    "policy_id": p.policy_id,
                    "title": p.policy_title,
                    "department": p.department,
                    "relevance_score": round(p.relevance_score, 3),
                    "matched_excerpt": p.matched_excerpt[:300],
                    "recommended_action": p.recommended_action,
                }
                for p in self.affected_policies
            ],
            "recommended_actions": self.recommended_actions,
        }
