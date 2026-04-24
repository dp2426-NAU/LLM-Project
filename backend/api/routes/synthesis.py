import logging
from fastapi import APIRouter, HTTPException, Request

from backend.api.schemas import (
    AgentOutputSchema,
    EvaluationSchema,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SynthesisRequest,
    SynthesisResponse,
)
from backend.evaluation.evaluator import PipelineEvaluator
from backend.pipeline.ingestion import IngestionService
from backend.pipeline.orchestrator import SynapseOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_response(context, eval_result) -> SynthesisResponse:
    synthesis_content = (
        context.synthesis_output.content if context.synthesis_output else ""
    )
    synthesis_structured = (
        context.synthesis_output.structured if context.synthesis_output else {}
    )

    agent_traces = []
    for ao in [
        context.research_output,
        context.critique_output,
        context.synthesis_output,
        context.validation_output,
    ]:
        if ao:
            agent_traces.append(
                AgentOutputSchema(
                    agent=ao.agent.value,
                    stage=ao.stage.value,
                    content=ao.content[:500] + "..." if len(ao.content) > 500 else ao.content,
                    tokens_used=ao.tokens_used,
                    latency_ms=ao.latency_ms,
                    success=ao.success,
                    error=ao.error,
                )
            )

    return SynthesisResponse(
        session_id=context.session_id,
        query=context.query,
        output_format=context.output_format,
        synthesis=synthesis_content,
        sections=synthesis_structured.get("sections", {}),
        sources_cited=synthesis_structured.get("sources_used", []),
        evaluation=EvaluationSchema(
            coherence_score=eval_result.coherence_score,
            relevance_score=eval_result.relevance_score,
            factuality_score=eval_result.factuality_score,
            completeness_score=eval_result.completeness_score,
            composite_score=eval_result.composite_score,
            verdict=eval_result.verdict,
            fabrication_flags=eval_result.fabrication_flags,
            passed=eval_result.passed,
        ),
        pipeline_summary=context.to_summary(),
        agent_traces=agent_traces,
    )


@router.post("/synthesize", response_model=SynthesisResponse)
async def synthesize(body: SynthesisRequest, request: Request) -> SynthesisResponse:
    orchestrator: SynapseOrchestrator = request.app.state.orchestrator
    evaluator: PipelineEvaluator = request.app.state.evaluator

    try:
        context = orchestrator.run(
            query=body.query,
            output_format=body.output_format,
            citation_style=body.citation_style,
            session_id=body.session_id,
        )
    except Exception as e:
        logger.exception("Pipeline execution failed")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    if context.current_stage.value == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline failed at stage with errors: {context.errors}",
        )

    eval_result = evaluator.evaluate(context)
    return _build_response(context, eval_result)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(body: IngestRequest, request: Request) -> IngestResponse:
    if not body.text and not body.file_path:
        raise HTTPException(status_code=422, detail="Either 'text' or 'file_path' must be provided.")

    ingestion: IngestionService = request.app.state.ingestion
    corpus_store = request.app.state.corpus_store

    try:
        if body.text:
            count = ingestion.ingest_text(body.text, source=body.source_label, metadata=body.metadata)
        else:
            count = ingestion.ingest_file(body.file_path, source_label=body.source_label)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))

    return IngestResponse(
        status="ok",
        source=body.source_label,
        chunks_indexed=count,
        total_corpus_size=corpus_store.document_count(),
    )


@router.post("/query/corpus", response_model=QueryResponse)
async def query_corpus(body: QueryRequest, request: Request) -> QueryResponse:
    corpus_store = request.app.state.corpus_store
    hits = corpus_store.search(body.query, top_k=body.top_k, min_score=body.min_score)
    return QueryResponse(query=body.query, hits=hits, total=len(hits))
