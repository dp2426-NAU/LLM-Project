import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import Settings
from ingestion.chunker import chunk_text
from ingestion.document_loader import load_document
from ingestion.embedder import Embedder
from models.document import CorpusType, DocumentChunk, PolicyDocument, RegulationVersion, RegulatoryBody
from store.vector_store import VectorStore
from store.version_tracker import VersionTracker

logger = logging.getLogger(__name__)


def _doc_id_from_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class IngestionPipeline:
    def __init__(self, settings: Settings, vector_store: VectorStore, version_tracker: VersionTracker) -> None:
        self._settings = settings
        self._vs = vector_store
        self._vt = version_tracker
        self._embedder = Embedder(settings.embedding_model, settings.embedding_device)

    def ingest_regulation(
        self,
        regulation_id: str,
        body: str,
        title: str,
        version_tag: str,
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        effective_date: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> RegulationVersion:
        logger.info("Ingesting regulation: %s v%s", regulation_id, version_tag)

        text = load_document(file_path=file_path, url=url)
        doc_id = _doc_id_from_content(text)

        chunks = chunk_text(text, self._settings.chunk_size, self._settings.chunk_overlap)
        logger.info("Produced %d chunks for %s", len(chunks), regulation_id)

        chunk_texts = [c.text for c in chunks]
        embeddings = self._embedder.embed(chunk_texts)

        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "doc_id": doc_id,
                "regulation_id": regulation_id,
                "version_tag": version_tag,
                "body": body,
                "section": c.section_hint or "",
                "corpus_type": CorpusType.REGULATION.value,
            }
            for c in chunks
        ]

        self._vs.upsert(
            corpus_type=CorpusType.REGULATION,
            ids=ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
        )

        version = RegulationVersion(
            regulation_id=regulation_id,
            body=RegulatoryBody(body.upper()) if body.upper() in RegulatoryBody._value2member_map_ else RegulatoryBody.OTHER,
            title=title,
            version_tag=version_tag,
            effective_date=effective_date,
            ingested_at=datetime.now(timezone.utc),
            doc_id=doc_id,
            source_url=source_url or url,
        )
        self._vt.register_version(version)
        return version

    def ingest_policy(
        self,
        policy_id: str,
        title: str,
        department: str,
        file_path: Optional[str] = None,
        url: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> PolicyDocument:
        logger.info("Ingesting policy: %s", policy_id)

        text = load_document(file_path=file_path, url=url)
        doc_id = _doc_id_from_content(text)

        chunks = chunk_text(text, self._settings.chunk_size, self._settings.chunk_overlap)

        chunk_texts = [c.text for c in chunks]
        embeddings = self._embedder.embed(chunk_texts)

        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "doc_id": doc_id,
                "policy_id": policy_id,
                "title": title,
                "department": department,
                "section": c.section_hint or "",
                "corpus_type": CorpusType.POLICY.value,
                "tags": ",".join(tags or []),
            }
            for c in chunks
        ]

        self._vs.upsert(
            corpus_type=CorpusType.POLICY,
            ids=ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
        )

        return PolicyDocument(
            policy_id=policy_id,
            title=title,
            department=department,
            doc_id=doc_id,
            ingested_at=datetime.now(timezone.utc),
            file_path=file_path,
            tags=tags or [],
        )
