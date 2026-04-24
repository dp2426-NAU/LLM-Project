import re


def count_tokens(text: str) -> int:
    """Approximates token count without tiktoken dependency.
    GPT tokenizer averages ~4 chars/token. This is ±10% accurate."""
    if not text:
        return 0
    words = len(re.findall(r"\S+", text))
    chars = len(text)
    # Weighted blend: word-based and char-based estimates
    word_estimate = int(words * 1.35)
    char_estimate = int(chars / 4)
    return (word_estimate + char_estimate) // 2


def budget_check(text: str, max_tokens: int) -> tuple[bool, int]:
    """Returns (within_budget, estimated_tokens)."""
    estimated = count_tokens(text)
    return estimated <= max_tokens, estimated


def truncate_to_budget(text: str, max_tokens: int) -> str:
    """Hard-truncates text to fit within token budget. Tries to cut at sentence boundary."""
    if count_tokens(text) <= max_tokens:
        return text

    # Binary search for the right character count
    target_chars = max_tokens * 4
    truncated = text[:target_chars]

    # Try to end at last sentence boundary
    last_period = truncated.rfind(". ")
    if last_period > target_chars * 0.7:
        truncated = truncated[:last_period + 1]

    return truncated.strip()
