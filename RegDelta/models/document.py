from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class CorpusType(str, Enum):
    REGULATION = "regulation"
    POLICY = "policy"


class RegulatoryBody(str, Enum):
    SEC = "SEC"
    FINRA = "FINRA"
    BASEL = "BASEL"
    FED = "FED"
    OCC = "OCC"
    CFPB = "CFPB"
    OTHER = "OTHER"


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    text: str
    corpus_type: CorpusType
    source: str
    section: Optional[str] = None
    page_number: Optional[int] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class RegulationVersion:
    regulation_id: str
    body: RegulatoryBody
    title: str
    version_tag: str
    effective_date: Optional[str]
    ingested_at: datetime
    doc_id: str
    source_url: Optional[str] = None


@dataclass
class PolicyDocument:
    policy_id: str
    title: str
    department: str
    doc_id: str
    ingested_at: datetime
    file_path: Optional[str] = None
    tags: list[str] = field(default_factory=list)
