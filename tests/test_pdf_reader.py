"""Tests for pdf_reader module."""

from unittest.mock import MagicMock

import pytest

from malimgraph.core.pdf_reader import (
    DocumentContent,
    PageContent,
    _extract_page,
    extract_text_from_pdf,
)


def test_extract_page_basic():
    """_extract_page returns a PageContent with text extracted from blocks."""
    mock_page = MagicMock()
    mock_page.get_text.return_value = {
        "blocks": [
            {
                "type": 0,
                "bbox": [0, 0, 100, 20],
                "lines": [
                    {
                        "spans": [
                            {
                                "text": "This is a sufficiently long paragraph to avoid scanned detection.",
                                "size": 12,
                                "flags": 0,
                            }
                        ]
                    }
                ],
            }
        ]
    }

    result = _extract_page(mock_page, 1)

    assert result.page_number == 1
    assert "sufficiently long paragraph" in result.text
    assert result.is_scanned is False


def test_extract_page_heading_detection():
    """Bold + large text is classified as a heading."""
    mock_page = MagicMock()
    mock_page.get_text.return_value = {
        "blocks": [
            {
                "type": 0,
                "bbox": [0, 0, 100, 20],
                "lines": [
                    {"spans": [{"text": "Chapter 1: Introduction", "size": 14, "flags": 16}]}
                ],
            }
        ]
    }

    result = _extract_page(mock_page, 1)

    assert "Chapter 1: Introduction" in result.headings


def test_extract_page_scanned_detection():
    """Pages with very little text and non-zero blocks are flagged as scanned."""
    mock_page = MagicMock()
    mock_page.get_text.return_value = {
        "blocks": [
            {
                "type": 0,
                "bbox": [0, 0, 100, 20],
                "lines": [{"spans": [{"text": "x", "size": 10, "flags": 0}]}],
            }
        ]
    }

    result = _extract_page(mock_page, 1)

    assert result.is_scanned is True


def test_extract_text_from_pdf_file_not_found():
    """FileNotFoundError raised for missing PDF."""
    with pytest.raises(FileNotFoundError):
        extract_text_from_pdf("/nonexistent/path/document.pdf")


def test_document_content_full_text():
    """full_text() joins page text with double newlines."""
    pages = [
        PageContent(
            page_number=1,
            text="Page one text.",
            headings=[],
            blocks=[],
            has_table=False,
            is_scanned=False,
        ),
        PageContent(
            page_number=2,
            text="Page two text.",
            headings=[],
            blocks=[],
            has_table=False,
            is_scanned=False,
        ),
    ]
    doc = DocumentContent(
        source_file="test.pdf", total_pages=2, title="Test", metadata={}, pages=pages
    )
    full = doc.full_text()

    assert "Page one text." in full
    assert "Page two text." in full
