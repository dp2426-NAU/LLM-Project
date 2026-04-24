import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("CHROMA_PERSIST_DIR", tempfile.mkdtemp())
os.environ.setdefault("VERSION_DB_PATH", str(Path(tempfile.mkdtemp()) / "test.db"))


@pytest.fixture(scope="session")
def sample_regulation_text() -> str:
    return """
Section 1.1 Record Retention Requirements
All electronic communications including email, instant messages, and trade confirmations
must be retained for a minimum period of 7 years. Records must be stored in a
non-rewriteable, non-erasable format (WORM) as specified in Exchange Act Rule 17a-4.

Section 1.2 Supervisory Controls
Broker-dealers must establish and maintain written supervisory procedures (WSPs)
that are reasonably designed to achieve compliance with applicable securities laws.
Annual review and update of WSPs is mandatory.

Section 2.1 Customer Due Diligence
Firms must implement a Customer Identification Program (CIP) that verifies the
identity of each customer. Beneficial ownership information must be collected for
legal entity customers with ownership stakes of 25% or more.
"""


@pytest.fixture(scope="session")
def sample_policy_text() -> str:
    return """
Policy: Electronic Records Management (POL-REC-001)
Department: Compliance & Operations

1. Scope
This policy applies to all electronic records generated in the course of business,
including email, trade records, client communications, and internal correspondence.

2. Retention Schedule
Electronic records must be retained for a minimum of 7 years from the date of creation.
Records subject to litigation hold must be retained until legal proceedings conclude.

3. Storage Requirements
All records must be stored in tamper-proof, WORM-compliant storage systems.
Monthly integrity checks must be performed and documented.
"""


@pytest.fixture
def mock_embedder():
    with patch("ingestion.embedder.Embedder") as mock:
        instance = mock.return_value
        instance.embed.return_value = [[0.1] * 384]
        instance.embed_one.return_value = [0.1] * 384
        instance.dimension = 384
        yield instance


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.collection_stats.return_value = {"regulations": 10, "policies": 5}
    store.query.return_value = [
        {
            "text": "Electronic records must be retained for 7 years.",
            "score": 0.87,
            "metadata": {
                "policy_id": "POL-REC-001",
                "title": "Electronic Records Management",
                "department": "Compliance",
            },
        }
    ]
    return store


@pytest.fixture
def mock_version_tracker():
    tracker = MagicMock()
    tracker.get_report.return_value = None
    tracker.list_reports.return_value = []
    return tracker


@pytest.fixture
def test_client(mock_vector_store, mock_version_tracker):
    from app.main import create_app

    application = create_app()
    application.state.vector_store = mock_vector_store
    application.state.version_tracker = mock_version_tracker

    with TestClient(application) as client:
        yield client
