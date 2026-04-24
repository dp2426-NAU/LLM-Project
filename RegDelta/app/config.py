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
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    llm_provider: str = "openai"  # "openai" | "ollama"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_store"
    regulations_collection: str = "regulations"
    policies_collection: str = "internal_policies"

    # Version tracker
    version_db_path: str = "./regdelta_versions.db"

    # Chunking
    chunk_size: int = 800
    chunk_overlap: int = 100

    # Retrieval
    retrieval_top_k: int = 8
    min_relevance_score: float = 0.35

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    @property
    def data_dir(self) -> Path:
        return Path(__file__).parent.parent / "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
