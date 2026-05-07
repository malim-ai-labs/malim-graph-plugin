"""PDF text and structure extraction using PyMuPDF."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import fitz  # PyMuPDF


@dataclass
class PageContent:
    page_number: int  # 1-indexed
    text: str
    headings: list[str] = field(default_factory=list)
    blocks: list[dict] = field(default_factory=list)
    has_table: bool = False
    is_scanned: bool = False


@dataclass
class DocumentContent:
    source_file: str
    total_pages: int
    title: str
    metadata: dict
    pages: list[PageContent]

    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text)


def extract_text_from_pdf(pdf_path: str) -> DocumentContent:
    """Extract structured text, headings, and metadata from a PDF."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_content = _extract_page(page, page_num + 1)
        pages.append(page_content)

    meta = doc.metadata or {}
    title = meta.get("title", "") or os.path.splitext(os.path.basename(pdf_path))[0]

    doc.close()

    return DocumentContent(
        source_file=os.path.abspath(pdf_path),
        total_pages=len(pages),
        title=title,
        metadata=meta,
        pages=pages,
    )


def _extract_page(page: fitz.Page, page_number: int) -> PageContent:
    blocks_raw = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

    text_parts = []
    headings = []
    blocks_out = []
    has_table = False
    total_chars = 0

    for block in blocks_raw:
        if block["type"] == 1:  # image block
            has_table = True  # images often accompany tables
            continue

        if block["type"] != 0:
            continue

        block_text_parts = []
        is_heading = False
        max_font_size = 0.0

        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = span.get("size", 0)
                flags = span.get("flags", 0)
                span_text = span.get("text", "").strip()
                if not span_text:
                    continue

                block_text_parts.append(span_text)
                total_chars += len(span_text)
                if size > max_font_size:
                    max_font_size = size

                # Bold + larger font = likely heading
                bold = bool(flags & 16)
                if size >= 11 and bold and len(span_text) < 200:
                    is_heading = True

        block_text = " ".join(block_text_parts).strip()
        if not block_text:
            continue

        text_parts.append(block_text)
        block_entry = {
            "text": block_text,
            "bbox": block.get("bbox", []),
            "font_size": max_font_size,
            "is_heading": is_heading,
        }
        blocks_out.append(block_entry)

        if is_heading:
            headings.append(block_text)

    # Detect likely table rows: blocks with many short tab-delimited segments
    for b in blocks_out:
        if "\t" in b["text"] or b["text"].count("  ") > 3:
            has_table = True
            break

    full_text = "\n".join(text_parts)
    is_scanned = total_chars < 50 and len(blocks_raw) > 0

    return PageContent(
        page_number=page_number,
        text=full_text,
        headings=headings,
        blocks=blocks_out,
        has_table=has_table,
        is_scanned=is_scanned,
    )
