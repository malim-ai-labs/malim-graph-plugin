#!/usr/bin/env python3
"""
Split extracted PDF text into embedding-ready chunks.
Step 2 of the pdf-to-chunks skill.

Install: pip install pydantic --break-system-packages
"""
import argparse
import json
import os
import sys
from typing import Optional

try:
    from malimgraph.core.pdf_reader import DocumentContent, PageContent
    from malimgraph.core.chunker import chunk_document
    _USE_PACKAGE = True
except ImportError:
    _USE_PACKAGE = False


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _inline_chunk(doc_data: dict, chunk_size: int, overlap: int) -> dict:
    """Minimal standalone chunker when package is unavailable."""
    pages = doc_data.get("pages", [])
    source_name = os.path.basename(doc_data.get("source_file", "document.pdf"))

    # Build flat paragraph list from blocks or full page text
    paragraphs = []
    heading_stack = []
    char_pos = 0

    for page in pages:
        blocks = page.get("blocks", [])
        if not blocks:
            # Fall back to splitting page text by double newline
            parts = [p.strip() for p in page.get("text", "").split("\n\n") if p.strip()]
            blocks = [{"text": p, "is_heading": False} for p in parts]

        for block in blocks:
            text = block.get("text", "").strip()
            if not text:
                continue
            is_heading = block.get("is_heading", False)
            if is_heading:
                heading_stack = heading_stack[-2:] + [text]

            paragraphs.append({
                "text": text,
                "page": page["page_number"],
                "headings": list(heading_stack),
                "has_table": page.get("has_table", False) and not is_heading,
                "is_heading": is_heading,
                "char_start": char_pos,
            })
            char_pos += len(text) + 1

    # Sliding window chunking
    chunks = []
    i = 0
    chunk_idx = 0

    while i < len(paragraphs):
        chunk_paras = []
        token_count = 0
        j = i

        while j < len(paragraphs):
            para_tokens = _estimate_tokens(paragraphs[j]["text"])
            if token_count + para_tokens > chunk_size and chunk_paras:
                break
            chunk_paras.append(paragraphs[j])
            token_count += para_tokens
            j += 1

        if not chunk_paras:
            chunk_paras = [paragraphs[i]]
            token_count = _estimate_tokens(paragraphs[i]["text"])
            j = i + 1

        chunk_text = "\n\n".join(p["text"] for p in chunk_paras)
        chunk_pages = sorted({p["page"] for p in chunk_paras})
        heading_context = chunk_paras[0]["headings"] if chunk_paras else []
        start_char = chunk_paras[0]["char_start"]
        end_char = chunk_paras[-1]["char_start"] + len(chunk_paras[-1]["text"])

        chunks.append({
            "chunk_id": f"chunk_{chunk_idx:04d}",
            "text": chunk_text,
            "token_count": token_count,
            "source_pages": chunk_pages,
            "page_range": {"start": chunk_pages[0], "end": chunk_pages[-1]},
            "heading_context": heading_context,
            "position": {"index": chunk_idx, "total": 0, "start_char": start_char, "end_char": end_char},
            "metadata": {
                "source_file": source_name,
                "has_table": any(p["has_table"] for p in chunk_paras),
                "has_heading": any(p["is_heading"] for p in chunk_paras),
            },
        })
        chunk_idx += 1

        # Overlap step-back
        overlap_tokens = 0
        step = j - 1
        while step > i and overlap_tokens < overlap:
            overlap_tokens += _estimate_tokens(paragraphs[step]["text"])
            step -= 1
        i = max(i + 1, step + 1)

    total = len(chunks)
    for c in chunks:
        c["position"]["total"] = total

    total_tokens = sum(c["token_count"] for c in chunks)

    return {
        "metadata": {
            "source_file": source_name,
            "total_chunks": total,
            "total_tokens": total_tokens,
            "chunk_config": {"chunk_size": chunk_size, "overlap": overlap},
        },
        "chunks": chunks,
    }


def main():
    parser = argparse.ArgumentParser(description="Chunk extracted PDF text for embeddings.")
    parser.add_argument("--input", required=True, help="extracted_text.json from extract_text.py")
    parser.add_argument("--output-dir", default="./chunks", help="Output directory.")
    parser.add_argument("--chunk-size", type=int, default=512, help="Target tokens per chunk.")
    parser.add_argument("--overlap", type=int, default=64, help="Overlap tokens between chunks.")
    parser.add_argument("--format", default="json", choices=["json", "txt", "md"], help="Output format.")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Loading: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        doc_data = json.load(f)

    print(f"Chunking (size={args.chunk_size}, overlap={args.overlap})...")

    if _USE_PACKAGE:
        pages = [
            PageContent(
                page_number=p["page_number"],
                text=p["text"],
                headings=p.get("headings", []),
                blocks=p.get("blocks", []),
                has_table=p.get("has_table", False),
                is_scanned=p.get("is_scanned", False),
            )
            for p in doc_data["pages"]
        ]
        doc = DocumentContent(
            source_file=doc_data["source_file"],
            total_pages=doc_data["total_pages"],
            title=doc_data.get("title", ""),
            metadata=doc_data.get("metadata", {}),
            pages=pages,
        )
        collection = chunk_document(doc, chunk_size=args.chunk_size, chunk_overlap=args.overlap)
        data = {
            "metadata": collection.metadata.model_dump(),
            "chunks": [c.model_dump() for c in collection.chunks],
        }
    else:
        data = _inline_chunk(doc_data, args.chunk_size, args.overlap)

    total = data["metadata"]["total_chunks"]
    print(f"  → {total} chunks, {data['metadata']['total_tokens']} tokens")

    if args.format == "json":
        out_path = os.path.join(args.output_dir, "chunks.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ {out_path}")

    elif args.format == "txt":
        for chunk in data["chunks"]:
            fname = os.path.join(args.output_dir, f"{chunk['chunk_id']}.txt")
            pos = chunk["position"]
            frontmatter = (
                f"---\nchunk_id: {chunk['chunk_id']}\npages: {chunk['source_pages']}\n"
                f"tokens: {chunk['token_count']}\nheading_context: {chunk['heading_context']}\n"
                f"position: {pos['index'] + 1}/{pos['total']}\n---\n\n"
            )
            with open(fname, "w", encoding="utf-8") as f:
                f.write(frontmatter + chunk["text"])
        print(f"  ✓ {total} .txt files in {args.output_dir}/")

    elif args.format == "md":
        lines = [f"# Chunks — {data['metadata']['source_file']}\n"]
        for chunk in data["chunks"]:
            pos = chunk["position"]
            lines.append(f"## Chunk {pos['index'] + 1} of {pos['total']}")
            lines.append(f"**Pages:** {chunk['source_pages']}  ")
            lines.append(f"**Tokens:** {chunk['token_count']}  ")
            if chunk.get("heading_context"):
                lines.append(f"**Context:** {' > '.join(chunk['heading_context'])}  ")
            lines.append("")
            lines.append(chunk["text"])
            lines.append("\n---\n")
        out_path = os.path.join(args.output_dir, "chunks.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"  ✓ {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
