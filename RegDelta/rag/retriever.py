import logging
from typing import Any, Optional

from app.config import Settings
from ingestion.embedder import Embedder
from models.document import CorpusType
from store.vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(self, settings: Settings, vector_store: VectorStore) -> None:
        self._settings = settings
        self._vs = vector_store
        self._embedder = Embedder(settings.embedding_model, settings.embedding_device)

    def retrieve_policies(
        self,
        query_text: str,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        k = top_k or self._settings.retrieval_top_k
        threshold = min_score if min_score is not None else self._settings.min_relevance_score

        embedding = self._embedder.embed_one(query_text)
        hits = self._vs.query(
            corpus_type=CorpusType.POLICY,
            query_embedding=embedding,
            n_results=k,
        )
        filtered = [h for h in hits if h["score"] >= threshold]
        logger.debug(
            "Policy retrieval: query_len=%d, raw_hits=%d, after_filter=%d",
            len(query_text),
            len(hits),
            len(filtered),
        )
        return filtered

    def retrieve_regulation_chunks(
        self,
        query_text: str,
        regulation_id: Optional[str] = None,
        version_tag: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        k = top_k or self._settings.retrieval_top_k
        embedding = self._embedder.embed_one(query_text)

        where: dict = {}
        if regulation_id:
            where["regulation_id"] = regulation_id
        if version_tag:
            where["version_tag"] = version_tag

        hits = self._vs.query(
            corpus_type=CorpusType.REGULATION,
            query_embedding=embedding,
            n_results=k,
            where=where if where else None,
        )
        return hits

    def deduplicate_policy_hits(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Collapse multiple chunks from same policy_id, keeping best score."""
        seen: dict[str, dict] = {}
        for hit in hits:
            pid = hit["metadata"].get("policy_id", "unknown")
            if pid not in seen or hit["score"] > seen[pid]["score"]:
                seen[pid] = hit
        return sorted(seen.values(), key=lambda h: h["score"], reverse=True)
