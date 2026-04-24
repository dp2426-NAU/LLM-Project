import logging
from fastapi import APIRouter, Request

from backend.api.schemas import AnalyticsResponse
from backend.config.settings import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(request: Request, limit: int = 50) -> AnalyticsResponse:
    settings = get_settings()
    tracer = request.app.state.tracer
    analytics = request.app.state.analytics

    return AnalyticsResponse(
        recent_sessions=tracer.get_session_analytics(limit=limit),
        agent_stats=tracer.get_agent_stats(),
        cost_summary=tracer.get_cost_summary(
            cost_per_1k_in=settings.cost_per_1k_input_tokens,
            cost_per_1k_out=settings.cost_per_1k_output_tokens,
        ),
        analytics_summary=analytics.summarize(),
    )


@router.get("/analytics/sessions/{session_id}")
async def get_session_detail(session_id: str, request: Request) -> dict:
    tracer = request.app.state.tracer
    sessions = [s for s in tracer.get_session_analytics(limit=500) if s["session_id"] == session_id]
    if not sessions:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return sessions[0]


@router.get("/analytics/corpus")
async def corpus_stats(request: Request) -> dict:
    corpus_store = request.app.state.corpus_store
    return {
        "total_chunks": corpus_store.document_count(),
        "collection": request.app.state.settings.chroma_collection,
    }
