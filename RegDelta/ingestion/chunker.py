import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class TextChunk:
    text: str
    char_start: int
    char_end: int
    section_hint: Optional[str] = None


_SECTION_BOUNDARY_RE = re.compile(
    r"\n(?=(?:Section|SECTION|§|Article|ARTICLE|Rule|RULE|Part|PART)\s+[\d\.A-Z]+)",
)


def _split_on_sections(text: str) -> list[tuple[str, int]]:
    """Returns list of (section_text, start_char_offset)."""
    boundaries = [0] + [m.end() for m in _SECTION_BOUNDARY_RE.finditer(text)] + [len(text)]
    parts = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        segment = text[start:end]
        if segment.strip():
            parts.append((segment, start))
    return parts


def _recursive_split(text: str, max_size: int, overlap: int, offset: int) -> list[tuple[str, int]]:
    if len(text) <= max_size:
        return [(text, offset)]

    # Try splitting on double newlines first, then single, then spaces
    for sep in ["\n\n", "\n", ". ", " "]:
        mid = len(text) // 2
        split_pos = text.rfind(sep, 0, mid)
        if split_pos == -1:
            split_pos = text.find(sep, mid)
        if split_pos != -1:
            left = text[: split_pos + len(sep)]
            right = text[max(0, split_pos + len(sep) - overlap) :]
            return _recursive_split(left, max_size, overlap, offset) + _recursive_split(
                right, max_size, overlap, offset + split_pos
            )

    # Hard split as last resort
    chunks = []
    pos = 0
    while pos < len(text):
        end = min(pos + max_size, len(text))
        chunks.append((text[pos:end], offset + pos))
        pos += max_size - overlap
    return chunks


def chunk_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[TextChunk]:
    sections = _split_on_sections(text)
    chunks: list[TextChunk] = []

    for section_text, section_offset in sections:
        section_hint = section_text.splitlines()[0][:100].strip() if section_text.strip() else None
        raw_chunks = _recursive_split(section_text, chunk_size, chunk_overlap, section_offset)

        for chunk_text_str, char_start in raw_chunks:
            stripped = chunk_text_str.strip()
            if len(stripped) < 50:
                continue
            chunks.append(
                TextChunk(
                    text=stripped,
                    char_start=char_start,
                    char_end=char_start + len(chunk_text_str),
                    section_hint=section_hint,
                )
            )

    return chunks
