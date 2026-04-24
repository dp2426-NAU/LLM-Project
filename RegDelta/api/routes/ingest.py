import logging
from fastapi import APIRouter, HTTPException, Request

from api.schemas import IngestPolicyRequest, IngestRegulationRequest, IngestResponse
from ingestion.pipeline import IngestionPipeline

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_pipeline(request: Request) -> IngestionPipeline:
    from app.config import get_settings
    return IngestionPipeline(
        settings=get_settings(),
        vector_store=request.app.state.vector_store,
        version_tracker=request.app.state.version_tracker,
    )


@router.post("/ingest/regulation", response_model=IngestResponse)
async def ingest_regulation(body: IngestRegulationRequest, request: Request) -> IngestResponse:
    if not body.file_path and not body.url:
        raise HTTPException(status_code=422, detail="Either file_path or url is required.")

    pipeline = _get_pipeline(request)
    try:
        version = pipeline.ingest_regulation(
            regulation_id=body.regulation_id,
            body=body.regulatory_body,
            title=body.title,
            version_tag=body.version_tag,
            file_path=body.file_path,
            url=body.url,
            effective_date=body.effective_date,
            source_url=body.source_url,
        )
        stats = request.app.state.vector_store.collection_stats()
        return IngestResponse(
            status="ok",
            doc_id=version.doc_id,
            chunks_indexed=stats["regulations"],
            message=f"Regulation {body.regulation_id} v{body.version_tag} ingested.",
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Ingestion failed for %s", body.regulation_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/policy", response_model=IngestResponse)
async def ingest_policy(body: IngestPolicyRequest, request: Request) -> IngestResponse:
    if not body.file_path and not body.url:
        raise HTTPException(status_code=422, detail="Either file_path or url is required.")

    pipeline = _get_pipeline(request)
    try:
        policy = pipeline.ingest_policy(
            policy_id=body.policy_id,
            title=body.title,
            department=body.department,
            file_path=body.file_path,
            url=body.url,
            tags=body.tags,
        )
        stats = request.app.state.vector_store.collection_stats()
        return IngestResponse(
            status="ok",
            doc_id=policy.doc_id,
            chunks_indexed=stats["policies"],
            message=f"Policy {body.policy_id} ingested.",
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Policy ingestion failed for %s", body.policy_id)
        raise HTTPException(status_code=500, detail=str(e))
