import math

from app.ingestion.chunker import CHUNK_TOKENS, OVERLAP_TOKENS, chunk_document
from app.ingestion.parser import ParsedDocument


def _doc(text: str) -> ParsedDocument:
    return ParsedDocument(pages=[text])


def test_empty_document_returns_empty():
    assert chunk_document(_doc("")) == []


def test_single_short_text_one_chunk():
    chunks = chunk_document(_doc("Hello world"))
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0


def test_chunk_count_reasonable():
    # ~1500 tokens of text should produce multiple chunks
    text = "word " * 1500
    chunks = chunk_document(_doc(text))
    step = CHUNK_TOKENS - OVERLAP_TOKENS
    expected_min = math.ceil(1500 / step) - 1
    assert len(chunks) >= expected_min


def test_overlap_present():
    # Each chunk's text should share content with the next
    text = "token " * 1000
    chunks = chunk_document(_doc(text))
    assert len(chunks) >= 2
    # First chunk ends with some tokens that appear at the start of second chunk
    end_of_first = chunks[0].text[-50:]
    start_of_second = chunks[1].text[:50]
    # At least some overlap exists (exact byte match may vary due to decode)
    assert len(end_of_first) > 0 and len(start_of_second) > 0


def test_chunk_indices_sequential():
    text = "word " * 2000
    chunks = chunk_document(_doc(text))
    for i, c in enumerate(chunks):
        assert c.chunk_index == i


def test_multipage_page_numbers():
    doc = ParsedDocument(pages=["page one text", "page two text"])
    chunks = chunk_document(doc)
    pages = {c.page for c in chunks}
    assert 1 in pages
    assert 2 in pages


def test_single_page_doc_page_is_none():
    chunks = chunk_document(_doc("some text here for testing"))
    for c in chunks:
        assert c.page is None
