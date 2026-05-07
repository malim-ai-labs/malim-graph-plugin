"""Tests for the document chunker."""
import pytest

from malimgraph.core.pdf_reader import DocumentContent, PageContent
from malimgraph.core.chunker import chunk_document, _extract_paragraphs


def _make_doc(pages_text: list[str]) -> DocumentContent:
    pages = [
        PageContent(
            page_number=i + 1,
            text=text,
            headings=[],
            blocks=[{"text": t, "is_heading": False, "font_size": 12.0, "bbox": []} for t in text.split("\n\n") if t],
            has_table=False,
            is_scanned=False,
        )
        for i, text in enumerate(pages_text)
    ]
    return DocumentContent(source_file="test.pdf", total_pages=len(pages), title="Test", metadata={}, pages=pages)


def test_chunk_document_produces_chunks():
    doc = _make_doc(["First paragraph.\n\nSecond paragraph.\n\nThird paragraph."])
    collection = chunk_document(doc, chunk_size=512, chunk_overlap=0)
    assert collection.metadata.total_chunks >= 1
    assert len(collection.chunks) == collection.metadata.total_chunks


def test_chunk_ids_are_unique():
    doc = _make_doc(["First paragraph.\n\nSecond paragraph.\n\nThird paragraph."] * 3)
    collection = chunk_document(doc, chunk_size=50, chunk_overlap=0)
    ids = [c.chunk_id for c in collection.chunks]
    assert len(ids) == len(set(ids))


def test_chunk_positions_are_correct():
    doc = _make_doc(["A B C D E F G H I J.\n\nAnother paragraph here.\n\nThird block of text."])
    collection = chunk_document(doc, chunk_size=10, chunk_overlap=0)
    for i, chunk in enumerate(collection.chunks):
        assert chunk.position.index == i
        assert chunk.position.total == collection.metadata.total_chunks


def test_chunk_source_pages_set():
    doc = _make_doc(["Page one text.\n\nMore page one.", "Page two content.\n\nMore page two."])
    collection = chunk_document(doc, chunk_size=512, chunk_overlap=0)
    all_pages = {p for c in collection.chunks for p in c.source_pages}
    assert 1 in all_pages
    assert 2 in all_pages


def test_chunk_overlap_produces_more_chunks():
    doc = _make_doc(["Chunk me.\n\nAnd again.\n\nThird section.\n\nFourth section.\n\nFifth."])
    no_overlap = chunk_document(doc, chunk_size=15, chunk_overlap=0)
    with_overlap = chunk_document(doc, chunk_size=15, chunk_overlap=5)
    # Overlap should produce >= chunks compared to no overlap
    assert with_overlap.metadata.total_chunks >= no_overlap.metadata.total_chunks


def test_chunk_total_tokens_matches_sum():
    doc = _make_doc(["Hello world.\n\nSecond paragraph.\n\nThird."])
    collection = chunk_document(doc)
    token_sum = sum(c.token_count for c in collection.chunks)
    assert token_sum == collection.metadata.total_tokens


def test_chunk_metadata_source_file():
    doc = _make_doc(["Some text."])
    collection = chunk_document(doc)
    assert collection.metadata.source_file == "test.pdf"
    for c in collection.chunks:
        assert c.metadata.source_file == "test.pdf"
