import logging
from typing import Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import Settings
from models.document import CorpusType

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, settings: Settings) -> None:
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._reg_collection = self._client.get_or_create_collection(
            name=settings.regulations_collection,
            metadata={"hnsw:space": "cosine"},
        )
        self._pol_collection = self._client.get_or_create_collection(
            name=settings.policies_collection,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "VectorStore ready",
            extra={
                "regulations_count": self._reg_collection.count(),
                "policies_count": self._pol_collection.count(),
            },
        )

    def _collection_for(self, corpus_type: CorpusType):
        if corpus_type == CorpusType.REGULATION:
            return self._reg_collection
        return self._pol_collection

    def upsert(
        self,
        corpus_type: CorpusType,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        col = self._collection_for(corpus_type)
        col.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.debug("Upserted %d chunks into %s", len(ids), corpus_type.value)

    def query(
        self,
        corpus_type: CorpusType,
        query_embedding: list[float],
        n_results: int = 8,
        where: Optional[dict] = None,
    ) -> list[dict[str, Any]]:
        col = self._collection_for(corpus_type)
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, col.count() or 1),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = col.query(**kwargs)

        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append(
                {
                    "text": doc,
                    "metadata": meta,
                    "score": round(1 - dist, 4),  # cosine similarity
                }
            )
        return hits

    def delete_by_doc_id(self, corpus_type: CorpusType, doc_id: str) -> None:
        col = self._collection_for(corpus_type)
        col.delete(where={"doc_id": doc_id})
        logger.info("Deleted chunks for doc_id=%s from %s", doc_id, corpus_type.value)

    def collection_stats(self) -> dict[str, int]:
        return {
            "regulations": self._reg_collection.count(),
            "policies": self._pol_collection.count(),
        }
