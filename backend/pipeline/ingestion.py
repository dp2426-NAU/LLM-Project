import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

from backend.config.settings import Settings
from backend.memory.vector_store import CorpusStore

logger = logging.getLogger(__name__)

_SECTION_RE = re.compile(r"\n(?=\d+\.\s|\n#{1,3}\s)", re.MULTILINE)


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    pos = 0
    while pos < len(text):
        end = min(pos + chunk_size, len(text))
        chunk = text[pos:end].strip()
        if len(chunk) >= 60:
            chunks.append(chunk)
        pos += chunk_size - overlap
    return chunks


def _clean(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s{3,}", "  ", text)
    text = re.sub(r"\x00", "", text)
    return text.strip()


class IngestionService:
    def __init__(self, settings: Settings, corpus_store: CorpusStore) -> None:
        self._settings = settings
        self._store = corpus_store

    def ingest_text(self, text: str, source: str, metadata: Optional[dict] = None) -> int:
        cleaned = _clean(text)
        chunks = _chunk_text(cleaned, self._settings.chunk_size, self._settings.chunk_overlap)
        meta_base = {"source": source, **(metadata or {})}
        metadatas = [{**meta_base, "chunk_index": i} for i in range(len(chunks))]
        count = self._store.add_documents(chunks, metadatas)
        logger.info("Ingested %d chunks from source: %s", count, source)
        return count

    def ingest_file(self, file_path: str | Path, source_label: Optional[str] = None) -> int:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()
        source = source_label or path.name

        if suffix == ".txt" or suffix == ".md":
            text = path.read_text(encoding="utf-8", errors="replace")
        elif suffix == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    text = "\n\n".join(
                        page.extract_text() or "" for page in pdf.pages
                    )
            except ImportError:
                raise RuntimeError("pdfplumber required for PDF ingestion: pip install pdfplumber")
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

        return self.ingest_text(text, source)

    def ingest_directory(self, dir_path: str | Path, extensions: tuple[str, ...] = (".txt", ".md", ".pdf")) -> dict[str, int]:
        results = {}
        for f in Path(dir_path).rglob("*"):
            if f.suffix.lower() in extensions:
                try:
                    count = self.ingest_file(f)
                    results[f.name] = count
                except Exception as e:
                    logger.error("Failed to ingest %s: %s", f.name, e)
                    results[f.name] = 0
        return results
