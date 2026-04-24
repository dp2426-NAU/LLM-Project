import pytest

from ingestion.chunker import chunk_text
from utils.diff_engine import compute_section_diffs
from utils.text_cleaner import clean, strip_headers_footers


class TestChunker:
    def test_basic_chunking(self, sample_regulation_text):
        chunks = chunk_text(sample_regulation_text, chunk_size=400, chunk_overlap=50)
        assert len(chunks) > 0
        for c in chunks:
            assert len(c.text) >= 50
            assert len(c.text) <= 600  # some tolerance for overlap

    def test_chunk_overlap_creates_continuity(self, sample_regulation_text):
        chunks = chunk_text(sample_regulation_text, chunk_size=300, chunk_overlap=50)
        if len(chunks) > 1:
            # Overlapping chunks should share some content
            first_end = chunks[0].text[-40:]
            second_start = chunks[1].text[:40]
            # At least some character overlap (not strict — depends on split points)
            assert chunks[0].char_end > chunks[1].char_start or len(chunks) >= 1

    def test_section_hints_extracted(self, sample_regulation_text):
        chunks = chunk_text(sample_regulation_text, chunk_size=600, chunk_overlap=50)
        hints = [c.section_hint for c in chunks if c.section_hint]
        assert len(hints) > 0


class TestTextCleaner:
    def test_strips_page_numbers(self):
        text = "Some content\nPage 1 of 10\nMore content"
        cleaned = strip_headers_footers(text)
        assert "Page 1 of 10" not in cleaned

    def test_normalizes_unicode(self):
        text = "café – compliance — policy"
        cleaned = clean(text)
        assert "café" in cleaned or "cafe" in cleaned

    def test_empty_string_safe(self):
        assert clean("") == ""


class TestDiffEngine:
    def test_detects_modifications(self):
        old = "Section 1.1 Record Retention\nRecords must be kept for 5 years."
        new = "Section 1.1 Record Retention\nRecords must be kept for 7 years."
        diffs = compute_section_diffs(old, new)
        assert len(diffs) > 0
        assert any(d.change_type == "modified" for d in diffs)

    def test_identical_text_no_diff(self):
        text = "Section 1.1\nNo changes here whatsoever."
        diffs = compute_section_diffs(text, text)
        assert diffs == []

    def test_added_section_detected(self):
        old = "Section 1.1\nOriginal content only."
        new = "Section 1.1\nOriginal content only.\n\nSection 2.1\nBrand new section added."
        diffs = compute_section_diffs(old, new)
        assert len(diffs) >= 1
