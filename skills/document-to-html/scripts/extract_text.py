#!/usr/bin/env python3
"""
Extract text structure from a PDF file.
Step 1 of the document-to-html skill.

Install: pip install pymupdf --break-system-packages
"""
import argparse
import json
import sys

try:
    from malimgraph.core.pdf_reader import extract_text_from_pdf
    _USE_PACKAGE = True
except ImportError:
    _USE_PACKAGE = False


def _inline_extract(pdf_path: str) -> dict:
    try:
        import fitz
    except ImportError:
        print("ERROR: PyMuPDF not installed. Run: pip install pymupdf --break-system-packages", file=sys.stderr)
        sys.exit(1)

    import os
    doc = fitz.open(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks_raw = page.get_text("dict")["blocks"]
        text_parts = []
        headings = []
        blocks_out = []
        has_table = False
        total_chars = 0

        for block in blocks_raw:
            if block["type"] != 0:
                continue
            block_text_parts = []
            is_heading = False
            max_size = 0.0
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = span.get("size", 0)
                    flags = span.get("flags", 0)
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    block_text_parts.append(text)
                    total_chars += len(text)
                    if size > max_size:
                        max_size = size
                    if size >= 11 and (flags & 16) and len(text) < 200:
                        is_heading = True
            block_text = " ".join(block_text_parts).strip()
            if not block_text:
                continue
            text_parts.append(block_text)
            if is_heading:
                headings.append(block_text)
            if "\t" in block_text or block_text.count("  ") > 3:
                has_table = True
            blocks_out.append({"text": block_text, "is_heading": is_heading, "font_size": max_size, "bbox": block.get("bbox", [])})

        pages.append({
            "page_number": page_num + 1,
            "text": "\n".join(text_parts),
            "headings": headings,
            "blocks": blocks_out,
            "has_table": has_table,
            "is_scanned": total_chars < 50 and len(blocks_raw) > 0,
        })

    meta = doc.metadata or {}
    doc.close()
    return {
        "source_file": os.path.abspath(pdf_path),
        "total_pages": len(pages),
        "title": meta.get("title", "") or os.path.splitext(os.path.basename(pdf_path))[0],
        "metadata": meta,
        "pages": pages,
    }


def main():
    parser = argparse.ArgumentParser(description="Extract text structure from a PDF.")
    parser.add_argument("--input", required=True, help="Path to the PDF file.")
    parser.add_argument("--output", default="extracted_text.json", help="Output JSON path.")
    args = parser.parse_args()

    print(f"Reading: {args.input}")

    if _USE_PACKAGE:
        doc = extract_text_from_pdf(args.input)
        data = {
            "source_file": doc.source_file,
            "total_pages": doc.total_pages,
            "title": doc.title,
            "metadata": doc.metadata,
            "pages": [
                {
                    "page_number": p.page_number,
                    "text": p.text,
                    "headings": p.headings,
                    "blocks": p.blocks,
                    "has_table": p.has_table,
                    "is_scanned": p.is_scanned,
                }
                for p in doc.pages
            ],
        }
    else:
        data = _inline_extract(args.input)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Extracted {data['total_pages']} pages → {args.output}")


if __name__ == "__main__":
    main()
