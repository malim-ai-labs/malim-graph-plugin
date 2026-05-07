"""Tests for the HTML renderer."""

from malimgraph.core.html_renderer import _build_entity_page_map, render_document_html
from malimgraph.core.pdf_reader import DocumentContent, PageContent


def _make_doc(pages_text: list[str], headings_per_page: list[list[str]] = None) -> DocumentContent:
    headings_per_page = headings_per_page or [[] for _ in pages_text]
    pages = [
        PageContent(
            page_number=i + 1,
            text=text,
            headings=headings_per_page[i],
            blocks=[],
            has_table=False,
            is_scanned=False,
        )
        for i, text in enumerate(pages_text)
    ]
    return DocumentContent(
        source_file="test.pdf",
        total_pages=len(pages),
        title="Test Document",
        metadata={},
        pages=pages,
    )


def test_render_produces_html(sample_kg):
    doc = _make_doc(["Hello world. Malim AI Labs is here."])
    html = render_document_html(doc, knowledge_graph=sample_kg)
    assert "<!DOCTYPE html>" in html
    assert "<html" in html


def test_render_includes_page_anchors():
    doc = _make_doc(["Page one.", "Page two."])
    html = render_document_html(doc)
    assert 'id="page-1"' in html
    assert 'id="page-2"' in html


def test_render_includes_toc():
    doc = _make_doc(["Content."], headings_per_page=[["Introduction"]])
    html = render_document_html(doc, include_toc=True)
    assert "toc" in html
    assert "Introduction" in html


def test_render_no_toc():
    doc = _make_doc(["Content."])
    html = render_document_html(doc, include_toc=False)
    assert 'id="toc"' not in html


def test_render_includes_search():
    doc = _make_doc(["Content."])
    html = render_document_html(doc, include_search=True)
    assert "search-input" in html
    assert "search-bar" in html


def test_render_no_search():
    doc = _make_doc(["Content."])
    html = render_document_html(doc, include_search=False)
    assert 'id="search-bar"' not in html


def test_render_entity_annotations(sample_kg):
    doc = _make_doc(["Malim AI Labs is an organization. Kuala Lumpur is a city."])
    html = render_document_html(doc, knowledge_graph=sample_kg)
    assert "data-entity-id" in html or "mark" in html.lower()


def test_entity_page_map_built_correctly(sample_kg):
    page_map = _build_entity_page_map(sample_kg)
    # sample_entity is on pages [1, 3]
    assert 1 in page_map
    assert 3 in page_map


def test_render_escapes_html_special_chars():
    doc = _make_doc(['Text with <script>alert("xss")</script> injection.'])
    # Disable search so the page has no legitimate <script> tag
    html = render_document_html(doc, include_search=False)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
