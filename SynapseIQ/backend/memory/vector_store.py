import hashlib
import logging
from pathlib import Path
from typing import Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class CorpusStore:
    """ChromaDB-backed vector store for the research corpus."""

    def __init__(self, persist_dir: str, collection_name: str, model_name: str, device: str = "cpu") -> None:
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._model = self._load_model(model_name, device)
        logger.info(
            "CorpusStore ready: collection=%s, docs=%d",
            collection_name,
            self._collection.count(),
        )

    @staticmethod
    def _load_model(model_name: str, device: str) -> SentenceTransformer:
        logger.info("Loading embedding model: %s", model_name)
        return SentenceTransformer(model_name, device=device)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def add_documents(self, texts: list[str], metadatas: list[dict]) -> int:
        if not texts:
            return 0
        embeddings = self._embed(texts)
        ids = [hashlib.sha256(t.encode()).hexdigest()[:16] for t in texts]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.debug("Indexed %d document chunks", len(texts))
        return len(texts)

    def search(
        self,
        query: str,
        top_k: int = 6,
        min_score: float = 0.30,
        where: Optional[dict] = None,
    ) -> list[dict[str, Any]]:
        query_vec = self._embed([query])[0]
        count = self._collection.count()
        if count == 0:
            return []

        kwargs: dict[str, Any] = {
            "query_embeddings": [query_vec],
            "n_results": min(top_k, count),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)
        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = round(1 - dist, 4)
            if score >= min_score:
                hits.append({"text": doc, "source": meta.get("source", "unknown"), "score": score, "metadata": meta})

        return sorted(hits, key=lambda h: h["score"], reverse=True)

    def document_count(self) -> int:
        return self._collection.count()

    def clear(self) -> None:
        self._collection.delete(where={"source": {"$ne": "__never__"}})
        logger.warning("Corpus store cleared")
