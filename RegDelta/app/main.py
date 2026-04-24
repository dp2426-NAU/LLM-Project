import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import setup_logging
from api.routes import analyze, ingest, query
from store.vector_store import VectorStore
from store.version_tracker import VersionTracker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info("Initializing RegDelta services")
    app.state.vector_store = VectorStore(settings)
    app.state.version_tracker = VersionTracker(settings.version_db_path)
    app.state.version_tracker.init_db()

    logger.info("RegDelta ready", extra={"env": settings.app_env})
    yield

    logger.info("Shutting down RegDelta")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="RegDelta",
        description="Regulatory Change Impact Analyzer — detect how regulation updates affect internal compliance policies.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(ingest.router, prefix=prefix, tags=["Ingestion"])
    app.include_router(analyze.router, prefix=prefix, tags=["Analysis"])
    app.include_router(query.router, prefix=prefix, tags=["Query"])

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "regdelta"}

    return app


app = create_app()
