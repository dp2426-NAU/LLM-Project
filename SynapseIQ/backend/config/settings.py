from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.3
    llm_provider: str = "openai"          # "openai" | "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_store"
    chroma_collection: str = "synapseiq_corpus"

    # Chunking
    chunk_size: int = 700
    chunk_overlap: int = 80

    # Retrieval
    retrieval_top_k: int = 6
    min_relevance_score: float = 0.30

    # Pipeline
    max_agent_retries: int = 2
    agent_timeout_seconds: int = 90
    enable_critic_agent: bool = True
    enable_validator_agent: bool = True

    # Evaluation
    coherence_threshold: float = 0.65
    relevance_threshold: float = 0.60
    min_factuality_score: float = 0.55

    # Cost tracking
    cost_per_1k_input_tokens: float = 0.00015    # gpt-4o-mini
    cost_per_1k_output_tokens: float = 0.00060   # gpt-4o-mini

    # App
    app_name: str = "SynapseIQ"
    app_version: str = "1.0.0"
    app_env: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]

    # Analytics
    analytics_db_path: str = "./synapseiq_analytics.db"
    max_session_history: int = 100

    @property
    def prompts_dir(self) -> Path:
        return Path(__file__).parent.parent / "prompts" / "templates"

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent.parent


@lru_cache
def get_settings() -> Settings:
    return Settings()
