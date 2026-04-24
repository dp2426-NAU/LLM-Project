import re
import unicodedata


_HEADER_FOOTER_PATTERNS = [
    r"^\s*Page\s+\d+\s+of\s+\d+\s*$",
    r"^\s*CONFIDENTIAL\s*$",
    r"^\s*DRAFT\s*$",
    r"^\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$",
    r"^\s*©.*$",
    r"^\s*www\.\S+\s*$",
]
_HEADER_FOOTER_RE = re.compile(
    "|".join(_HEADER_FOOTER_PATTERNS), re.IGNORECASE | re.MULTILINE
)

_WHITESPACE_RE = re.compile(r"\s{3,}")
_BULLET_RE = re.compile(r"^[\s]*[•\-–—►▪]\s+", re.MULTILINE)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    return text


def strip_headers_footers(text: str) -> str:
    return _HEADER_FOOTER_RE.sub("", text)


def collapse_whitespace(text: str) -> str:
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _WHITESPACE_RE.sub("  ", text)
    return text.strip()


def normalize_bullets(text: str) -> str:
    return _BULLET_RE.sub("- ", text)


def clean(text: str) -> str:
    text = normalize(text)
    text = strip_headers_footers(text)
    text = normalize_bullets(text)
    text = collapse_whitespace(text)
    return text


def extract_section_title(text: str) -> str | None:
    """Best-effort extraction of a section heading from the first non-empty line."""
    for line in text.splitlines():
        line = line.strip()
        if line and len(line) < 120:
            return line
    return None
