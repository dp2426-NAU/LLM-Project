import logging
from pathlib import Path
from typing import Optional

import httpx

from utils.pdf_parser import extract_full_text, extract_text_from_html
from utils.text_cleaner import clean

logger = logging.getLogger(__name__)


def load_from_file(file_path: str | Path) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        raw = extract_full_text(path)
    elif suffix in {".txt", ".md"}:
        raw = path.read_text(encoding="utf-8", errors="replace")
    elif suffix in {".html", ".htm"}:
        html = path.read_text(encoding="utf-8", errors="replace")
        raw = extract_text_from_html(html)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    return clean(raw)


def load_from_url(url: str, timeout: int = 30) -> str:
    logger.info("Fetching document from URL: %s", url)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")

    if "pdf" in content_type or url.endswith(".pdf"):
        # Write to temp file and parse
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        try:
            return clean(extract_full_text(tmp_path))
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    else:
        return clean(extract_text_from_html(response.text))


def load_document(file_path: Optional[str] = None, url: Optional[str] = None) -> str:
    if file_path:
        return load_from_file(file_path)
    if url:
        return load_from_url(url)
    raise ValueError("Either file_path or url must be provided")
