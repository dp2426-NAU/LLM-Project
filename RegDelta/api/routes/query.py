import json
import logging
from fastapi import APIRouter, HTTPException, Request

from api.schemas import QueryHit, QueryRequest, QueryResponse, ReportSummary
from models.document import CorpusType
from rag.retriever import Retriever

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=QueryResponse)
async def semantic_query(body: QueryRequest, request: Request) -> QueryResponse:
    from app.config import get_settings

    settings = get_settings()
    retriever = Retriever(settings, request.app.state.vector_store)

    corpus_map = {"policies": CorpusType.POLICY, "regulations": CorpusType.REGULATION}
    if body.corpus not in corpus_map:
        raise HTTPException(status_code=422, detail="corpus must be 'policies' or 'regulations'")

    try:
        if body.corpus == "policies":
            hits = retriever.retrieve_policies(body.query, top_k=body.top_k)
        else:
            hits = retriever.retrieve_regulation_chunks(
                body.query,
                regulation_id=body.regulation_id,
                version_tag=body.version_tag,
                top_k=body.top_k,
            )
    except Exception as e:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=str(e))

    return QueryResponse(
        query=body.query,
        hits=[QueryHit(text=h["text"], score=h["score"], metadata=h["metadata"]) for h in hits],
        total=len(hits),
    )


@router.get("/reports/{report_id}")
async def get_report(report_id: str, request: Request) -> dict:
    vt = request.app.state.version_tracker
    raw = vt.get_report(report_id)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")
    return json.loads(raw)


@router.get("/reports", response_model=list[ReportSummary])
async def list_reports(request: Request, regulation_id: str | None = None) -> list[ReportSummary]:
    vt = request.app.state.version_tracker
    rows = vt.list_reports(regulation_id=regulation_id)
    return [ReportSummary(**r) for r in rows]


@router.get("/regulations/{regulation_id}/versions")
async def list_versions(regulation_id: str, request: Request) -> list[dict]:
    vt = request.app.state.version_tracker
    versions = vt.get_versions(regulation_id)
    if not versions:
        raise HTTPException(status_code=404, detail=f"No versions found for '{regulation_id}'.")
    return [
        {
            "regulation_id": v.regulation_id,
            "body": v.body.value,
            "title": v.title,
            "version_tag": v.version_tag,
            "effective_date": v.effective_date,
            "ingested_at": v.ingested_at.isoformat(),
            "doc_id": v.doc_id,
        }
        for v in versions
    ]
