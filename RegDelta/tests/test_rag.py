from unittest.mock import MagicMock, patch

import pytest

from rag.retriever import Retriever


class TestRetriever:
    def test_retrieve_policies_returns_hits(self, mock_vector_store):
        from app.config import get_settings
        settings = get_settings()

        with patch("rag.retriever.Embedder") as MockEmbedder:
            MockEmbedder.return_value.embed_one.return_value = [0.1] * 384
            retriever = Retriever(settings, mock_vector_store)
            hits = retriever.retrieve_policies("record retention requirements")

        assert isinstance(hits, list)
        assert len(hits) > 0
        assert "text" in hits[0]
        assert "score" in hits[0]

    def test_score_filtering(self, mock_vector_store):
        from app.config import get_settings
        settings = get_settings()

        mock_vector_store.query.return_value = [
            {"text": "relevant", "score": 0.85, "metadata": {"policy_id": "P1"}},
            {"text": "irrelevant", "score": 0.10, "metadata": {"policy_id": "P2"}},
        ]

        with patch("rag.retriever.Embedder") as MockEmbedder:
            MockEmbedder.return_value.embed_one.return_value = [0.1] * 384
            retriever = Retriever(settings, mock_vector_store)
            hits = retriever.retrieve_policies("query", min_score=0.35)

        assert all(h["score"] >= 0.35 for h in hits)

    def test_deduplication_keeps_best_score(self, mock_vector_store):
        from app.config import get_settings
        settings = get_settings()

        with patch("rag.retriever.Embedder"):
            retriever = Retriever(settings, mock_vector_store)
            hits = [
                {"text": "chunk A", "score": 0.75, "metadata": {"policy_id": "P1"}},
                {"text": "chunk B", "score": 0.90, "metadata": {"policy_id": "P1"}},
                {"text": "chunk C", "score": 0.60, "metadata": {"policy_id": "P2"}},
            ]
            deduped = retriever.deduplicate_policy_hits(hits)

        policy_ids = [h["metadata"]["policy_id"] for h in deduped]
        assert len(set(policy_ids)) == len(policy_ids)

        p1_hit = next(h for h in deduped if h["metadata"]["policy_id"] == "P1")
        assert p1_hit["score"] == 0.90
