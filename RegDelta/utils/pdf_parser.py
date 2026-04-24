import logging
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


def extract_pages(file_path: str | Path) -> Iterator[tuple[int, str]]:
    """Yields (page_number, text) tuples from a PDF."""
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("pdfplumber is required: pip install pdfplumber")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if text and text.strip():
                yield i, text
            else:
                logger.debug("Empty page %d in %s, skipping", i, path.name)


def extract_full_text(file_path: str | Path) -> str:
    pages = list(extract_pages(file_path))
    if not pages:
        raise ValueError(f"No extractable text in {file_path}")
    return "\n\n".join(text for _, text in pages)


def extract_text_from_html(html_content: str) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("beautifulsoup4 is required: pip install beautifulsoup4")

    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    return text
