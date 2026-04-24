import logging
from fastapi import APIRouter, Request

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/agents/status")
async def agent_status(request: Request) -> dict:
    settings = request.app.state.settings
    prompt_engine = request.app.state.prompt_engine
    corpus_store = request.app.state.corpus_store

    return {
        "llm_provider": settings.llm_provider,
        "llm_model": settings.openai_model if settings.llm_provider == "openai" else settings.ollama_model,
        "embedding_model": settings.embedding_model,
        "agents_enabled": {
            "researcher": True,
            "critic": settings.enable_critic_agent,
            "synthesizer": True,
            "validator": settings.enable_validator_agent,
        },
        "prompt_templates_loaded": prompt_engine.loaded_agents,
        "corpus_chunks": corpus_store.document_count(),
        "pipeline_config": {
            "retrieval_top_k": settings.retrieval_top_k,
            "min_relevance_score": settings.min_relevance_score,
            "chunk_size": settings.chunk_size,
            "max_retries": settings.max_agent_retries,
        },
    }


@router.post("/agents/prompts/reload")
async def reload_prompts(request: Request) -> dict:
    prompt_engine = request.app.state.prompt_engine
    prompt_engine.reload()
    return {"status": "ok", "templates_loaded": prompt_engine.loaded_agents}
