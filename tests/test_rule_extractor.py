"""Tests for rule-based entity extraction."""

from malimgraph.core.pdf_reader import DocumentContent, PageContent
from malimgraph.core.rule_extractor import extract_by_rules
from malimgraph.schemas.entities import ExtractionMethod


def _make_doc(text: str, page_num: int = 1) -> DocumentContent:
    page = PageContent(
        page_number=page_num,
        text=text,
        headings=[],
        blocks=[],
        has_table=False,
        is_scanned=False,
    )
    return DocumentContent(
        source_file="test.pdf", total_pages=1, title="Test", metadata={}, pages=[page]
    )


def test_extracts_email():
    doc = _make_doc("Contact us at hello@malim.my for more info.")
    entities = extract_by_rules(doc)
    labels = [e.label for e in entities]
    assert any("hello@malim.my" in label for label in labels)


def test_extracts_monetary_amount():
    doc = _make_doc("The total budget is RM 1,500,000 for this project.")
    entities = extract_by_rules(doc)
    types = [e.type for e in entities]
    assert "MonetaryAmount" in types


def test_extracts_percentage():
    doc = _make_doc("Growth rate was 23.5% year-on-year.")
    entities = extract_by_rules(doc)
    types = [e.type for e in entities]
    assert "Percentage" in types


def test_extracts_date():
    doc = _make_doc("The agreement was signed on January 15, 2024.")
    entities = extract_by_rules(doc)
    types = [e.type for e in entities]
    assert "Date" in types


def test_extracts_legal_reference():
    doc = _make_doc("This is governed by Act No. 553 of Malaysia.")
    entities = extract_by_rules(doc)
    types = [e.type for e in entities]
    assert "LegalReference" in types


def test_entity_has_provenance():
    doc = _make_doc("Revenue was RM 5,000,000 in Q4.")
    entities = extract_by_rules(doc)
    assert all(e.source_pages for e in entities)
    assert all(e.source_text for e in entities)
    assert all(e.citations for e in entities)


def test_entity_extraction_method_is_rule():
    doc = _make_doc("Email: test@example.com")
    entities = extract_by_rules(doc)
    for e in entities:
        assert e.extraction_method == ExtractionMethod.RULE


def test_deduplication_across_pages():
    """Same entity on multiple pages should be merged with accumulated pages."""
    page1 = PageContent(
        page_number=1,
        text="Revenue: RM 1,000,000",
        headings=[],
        blocks=[],
        has_table=False,
        is_scanned=False,
    )
    page2 = PageContent(
        page_number=2,
        text="Revenue: RM 1,000,000",
        headings=[],
        blocks=[],
        has_table=False,
        is_scanned=False,
    )
    doc = DocumentContent(
        source_file="test.pdf", total_pages=2, title="Test", metadata={}, pages=[page1, page2]
    )

    entities = extract_by_rules(doc)
    amount_entities = [e for e in entities if e.label == "RM 1,000,000"]

    assert len(amount_entities) == 1
    assert 1 in amount_entities[0].source_pages
    assert 2 in amount_entities[0].source_pages


def test_stable_entity_id():
    """Same entity type+label always produces the same ID."""
    doc1 = _make_doc("Email: test@example.com")
    doc2 = _make_doc("Email: test@example.com")

    entities1 = extract_by_rules(doc1)
    entities2 = extract_by_rules(doc2)

    email1 = next((e for e in entities1 if "test@example.com" in e.label), None)
    email2 = next((e for e in entities2 if "test@example.com" in e.label), None)

    assert email1 is not None
    assert email2 is not None
    assert email1.id == email2.id


def test_extracts_isbn():
    doc = _make_doc("The book ISBN-13 is 978-3-16-148410-0 and ISBN-10 is 0-306-40615-2.")
    entities = extract_by_rules(doc)
    isbns = [e.label for e in entities if e.type == "ISBN"]
    assert any("978-3-16-148410-0" in label for label in isbns)
    assert any("0-306-40615-2" in label for label in isbns)
