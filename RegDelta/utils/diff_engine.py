import difflib
import hashlib
import re
from dataclasses import dataclass
from typing import Optional


_SECTION_RE = re.compile(
    r"^(?:Section|SECTION|§|Article|ARTICLE|Rule|RULE)\s+[\d\.A-Z]+",
    re.MULTILINE,
)


@dataclass
class SectionDiff:
    section_id: str
    title: Optional[str]
    old_text: str
    new_text: str
    change_type: str  # "added" | "modified" | "removed"
    similarity: float


def _split_sections(text: str) -> dict[str, str]:
    """Split document text into a {section_id: content} mapping."""
    boundaries = [m.start() for m in _SECTION_RE.finditer(text)]

    if not boundaries:
        # Fallback: split into ~1000-char chunks and label them
        chunks = {}
        size = 1000
        for i in range(0, len(text), size):
            chunk = text[i : i + size]
            cid = f"chunk_{i // size}"
            chunks[cid] = chunk
        return chunks

    sections: dict[str, str] = {}
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(text)
        chunk = text[start:end].strip()
        # Use first line as key, fallback to hash
        first_line = chunk.splitlines()[0][:80].strip()
        key = re.sub(r"\s+", "_", first_line) or hashlib.md5(chunk.encode()).hexdigest()[:8]
        sections[key] = chunk

    return sections


def compute_section_diffs(old_text: str, new_text: str) -> list[SectionDiff]:
    old_sections = _split_sections(old_text)
    new_sections = _split_sections(new_text)

    all_keys = set(old_sections) | set(new_sections)
    diffs: list[SectionDiff] = []

    for key in all_keys:
        old = old_sections.get(key, "")
        new = new_sections.get(key, "")

        if old == new:
            continue

        if not old:
            change_type = "added"
            similarity = 0.0
        elif not new:
            change_type = "removed"
            similarity = 0.0
        else:
            similarity = difflib.SequenceMatcher(None, old, new).ratio()
            change_type = "modified"

        title = new.splitlines()[0][:100].strip() if new else (old.splitlines()[0][:100].strip() if old else None)

        diffs.append(
            SectionDiff(
                section_id=key,
                title=title,
                old_text=old,
                new_text=new,
                change_type=change_type,
                similarity=round(similarity, 3),
            )
        )

    # Sort: most changed first (lowest similarity)
    diffs.sort(key=lambda d: d.similarity)
    return diffs


def unified_diff_text(old_text: str, new_text: str, context_lines: int = 3) -> str:
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, fromfile="v_old", tofile="v_new", n=context_lines)
    return "".join(diff)
