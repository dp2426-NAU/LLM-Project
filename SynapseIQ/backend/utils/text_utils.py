import re
import unicodedata


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\x00", "", text)
    return text


def truncate(text: str, max_chars: int, ellipsis: str = "...") -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(ellipsis)].rstrip() + ellipsis


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?]+\s", text))


def extract_bullet_items(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("-", "•", "*", "·")):
            items.append(stripped.lstrip("-•*· ").strip())
    return items


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\-_.]", "_", name)[:80]
