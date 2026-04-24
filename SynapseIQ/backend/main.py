import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import agents, analytics, synthesis
from backend.config.settings import Settings, get_settings
from backend.evaluation.evaluator import PipelineEvaluator
from backend.logging.analytics import AnalyticsCollector, configure_logging
from backend.logging.tracer import PipelineTracer
from backend.memory.vector_store import CorpusStore
from backend.pipeline.ingestion import IngestionService
from backend.pipeline.orchestrator import SynapseOrchestrator
from backend.prompts.engine import PromptEngine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings: Settings = app.state.settings
    configure_logging(settings.log_level)

    logger.info("Initializing SynapseIQ services")

    prompt_engine = PromptEngine(settings.prompts_dir)
    corpus_store = CorpusStore(
        persist_dir=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection,
        model_name=settings.embedding_model,
        device=settings.embedding_device,
    )
    tracer = PipelineTracer(settings.analytics_db_path)
    analytics = AnalyticsCollector()
    ingestion = IngestionService(settings, corpus_store)
    orchestrator = SynapseOrchestrator(settings, corpus_store, prompt_engine, tracer)
    evaluator = PipelineEvaluator(settings)

    app.state.prompt_engine = prompt_engine
    app.state.corpus_store = corpus_store
    app.state.tracer = tracer
    app.state.analytics = analytics
    app.state.ingestion = ingestion
    app.state.orchestrator = orchestrator
    app.state.evaluator = evaluator

    logger.info("SynapseIQ ready | env=%s | corpus=%d chunks", settings.app_env, corpus_store.document_count())
    yield
    logger.info("SynapseIQ shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="SynapseIQ",
        description="Multi-Agent Research Intelligence & Synthesis Platform",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(synthesis.router, prefix=prefix, tags=["Synthesis"])
    app.include_router(agents.router, prefix=prefix, tags=["Agents"])
    app.include_router(analytics.router, prefix=prefix, tags=["Analytics"])

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "env": settings.app_env,
        }

    return app


app = create_app()
