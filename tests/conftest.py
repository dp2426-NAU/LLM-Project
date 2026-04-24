import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("CHROMA_PERSIST_DIR", tempfile.mkdtemp())
os.environ.setdefault("ANALYTICS_DB_PATH", str(Path(tempfile.mkdtemp()) / "test.db"))


@pytest.fixture(scope="session")
def settings():
    from backend.config.settings import Settings
    return Settings()


@pytest.fixture
def sample_query() -> str:
    return "What are the key principles of transformer-based language models?"


@pytest.fixture
def sample_chunks() -> list[dict]:
    return [
        {
            "text": "Transformer models rely on self-attention mechanisms that allow each token to attend to all other tokens in the sequence, enabling parallel processing and long-range dependency capture.",
            "source": "attention_paper.pdf",
            "score": 0.91,
        },
        {
            "text": "The feed-forward network in each transformer layer applies non-linear transformations independently to each position, increasing representational capacity without attending across positions.",
            "source": "transformer_architecture.txt",
            "score": 0.84,
        },
        {
            "text": "Positional encodings inject sequence order information since transformers are inherently permutation-invariant. Both learned and sinusoidal encodings are used in practice.",
            "source": "positional_encoding.md",
            "score": 0.78,
        },
    ]


@pytest.fixture
def mock_llm_response():
    return (
        "CORE FINDINGS\n"
        "- Self-attention allows parallel token processing\n"
        "- Feed-forward layers add non-linear capacity\n"
        "- Positional encodings address sequence order\n"
        "\nKEY CONCEPTS\n"
        "Self-attention: mechanism for token-to-token weighting\n"
        "\nEVIDENCE GAPS\n"
        "- Training dynamics not covered in retrieved text\n"
        "\nSOURCE QUALITY\n"
        "Sources appear to be from academic papers, high reliability.",
        150,
        320.5,
    )


@pytest.fixture
def mock_corpus_store(sample_chunks):
    store = MagicMock()
    store.search.return_value = sample_chunks
    store.document_count.return_value = len(sample_chunks)
    store.add_documents.return_value = len(sample_chunks)
    return store


@pytest.fixture
def mock_prompt_engine():
    engine = MagicMock()
    engine.render.return_value = ("You are a researcher.", "Research this query.")
    engine.loaded_agents = ["researcher", "critic", "synthesizer", "validator"]
    return engine


@pytest.fixture
def agent_context(sample_query):
    from backend.memory.context_graph import AgentContext, RetrievedChunk
    ctx = AgentContext(session_id="test-session-001", query=sample_query)
    ctx.retrieved_chunks = [
        RetrievedChunk(
            text="Transformer models use self-attention for parallel computation.",
            source="paper.pdf",
            score=0.88,
        )
    ]
    return ctx


@pytest.fixture
def test_client(mock_corpus_store, mock_prompt_engine):
    from fastapi.testclient import TestClient
    from backend.main import create_app

    app = create_app()
    # Override state with mocks
    app.state.corpus_store = mock_corpus_store
    app.state.prompt_engine = mock_prompt_engine

    with TestClient(app) as client:
        yield client
