from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class IngestRegulationRequest(BaseModel):
    regulation_id: str = Field(..., description="Stable identifier, e.g. 'SEC-17a-4'")
    regulatory_body: str = Field(..., description="SEC | FINRA | BASEL | FED | OCC | CFPB | OTHER")
    title: str
    version_tag: str = Field(..., description="e.g. '2024-Q1' or 'v3.2'")
    effective_date: Optional[str] = None
    file_path: Optional[str] = None
    url: Optional[str] = None
    source_url: Optional[str] = None

    @field_validator("regulatory_body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        allowed = {"SEC", "FINRA", "BASEL", "FED", "OCC", "CFPB", "OTHER"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"regulatory_body must be one of {allowed}")
        return upper


class IngestPolicyRequest(BaseModel):
    policy_id: str = Field(..., description="e.g. 'POL-AML-001'")
    title: str
    department: str
    file_path: Optional[str] = None
    url: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class IngestResponse(BaseModel):
    status: str
    doc_id: str
    chunks_indexed: int = 0
    message: str = ""


class AnalyzeDeltaRequest(BaseModel):
    regulation_id: str
    old_version_tag: str
    new_version_tag: str


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=5)
    corpus: str = Field("policies", description="'policies' | 'regulations'")
    top_k: int = Field(8, ge=1, le=20)
    regulation_id: Optional[str] = None
    version_tag: Optional[str] = None


class QueryHit(BaseModel):
    text: str
    score: float
    metadata: dict[str, Any]


class QueryResponse(BaseModel):
    query: str
    hits: list[QueryHit]
    total: int


class ReportSummary(BaseModel):
    report_id: str
    regulation_id: str
    old_version: str
    new_version: str
    generated_at: str
    risk_level: str
