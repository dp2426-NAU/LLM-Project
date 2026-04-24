import logging
from fastapi import APIRouter, HTTPException, Request

from api.schemas import AnalyzeDeltaRequest
from ingestion.document_loader import load_document
from rag.impact_analyzer import ImpactAnalyzer
from store.version_tracker import VersionTracker

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/analyze/delta")
async def analyze_delta(body: AnalyzeDeltaRequest, request: Request) -> dict:
    vt: VersionTracker = request.app.state.version_tracker
    versions = vt.get_versions(body.regulation_id)

    version_map = {v.version_tag: v for v in versions}

    if body.old_version_tag not in version_map:
        raise HTTPException(
            status_code=404,
            detail=f"Version '{body.old_version_tag}' not found for regulation '{body.regulation_id}'.",
        )
    if body.new_version_tag not in version_map:
        raise HTTPException(
            status_code=404,
            detail=f"Version '{body.new_version_tag}' not found for regulation '{body.regulation_id}'.",
        )

    old_version = version_map[body.old_version_tag]
    new_version = version_map[body.new_version_tag]

    try:
        from app.config import get_settings
        from store.vector_store import VectorStore
        settings = get_settings()
        vs: VectorStore = request.app.state.vector_store

        # Re-fetch raw text by querying regulation chunks for each version
        old_hits = vs.query(
            corpus_type=__import__("models.document", fromlist=["CorpusType"]).CorpusType.REGULATION,
            query_embedding=[0.0] * 384,  # placeholder — we pull by metadata filter
            n_results=500,
            where={"doc_id": old_version.doc_id},
        )
        new_hits = vs.query(
            corpus_type=__import__("models.document", fromlist=["CorpusType"]).CorpusType.REGULATION,
            query_embedding=[0.0] * 384,
            n_results=500,
            where={"doc_id": new_version.doc_id},
        )

        old_text = "\n\n".join(h["text"] for h in old_hits)
        new_text = "\n\n".join(h["text"] for h in new_hits)

    except Exception as e:
        logger.exception("Failed to retrieve regulation text for diff")
        raise HTTPException(status_code=500, detail=f"Text retrieval failed: {e}")

    try:
        analyzer = ImpactAnalyzer(
            settings=get_settings(),
            vector_store=request.app.state.vector_store,
            version_tracker=vt,
        )
        report = analyzer.analyze(
            regulation_id=body.regulation_id,
            old_text=old_text,
            new_text=new_text,
            old_version_tag=body.old_version_tag,
            new_version_tag=body.new_version_tag,
            regulation_title=new_version.title,
            regulatory_body=new_version.body.value,
        )
        return report.to_dict()
    except Exception as e:
        logger.exception("Impact analysis failed")
        raise HTTPException(status_code=500, detail=str(e))
