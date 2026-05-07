"""PDF → embedding-ready text chunks with heading context and positional metadata."""

from __future__ import annotations

import os

from malimgraph.core.pdf_reader import DocumentContent
from malimgraph.schemas.chunks import (
    Chunk,
    ChunkCollection,
    ChunkMetadata,
    ChunkPosition,
    CollectionMetadata,
)
from malimgraph.utils.text import clean_text, estimate_tokens


def chunk_document(
    doc: DocumentContent,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> ChunkCollection:
    """
    Split a DocumentContent into overlapping text chunks optimized for embedding.
    Respects paragraph and heading boundaries when possible.
    """
    paragraphs = _extract_paragraphs(doc)
    chunks = _sliding_window_chunks(paragraphs, chunk_size, chunk_overlap, doc)

    total_tokens = sum(c.token_count for c in chunks)
    source_name = os.path.basename(doc.source_file)

    collection_meta = CollectionMetadata(
        source_file=source_name,
        total_chunks=len(chunks),
        total_tokens=total_tokens,
        chunk_config={"chunk_size": chunk_size, "overlap": chunk_overlap},
    )

    return ChunkCollection(metadata=collection_meta, chunks=chunks)


def _extract_paragraphs(doc: DocumentContent) -> list[dict]:
    """
    Extract paragraphs from pages, annotated with page number, heading context,
    and table/heading flags.
    """
    paragraphs = []
    heading_stack: list[str] = []

    for page in doc.pages:
        if page.is_scanned:
            # Still include scanned pages as single paragraphs for awareness
            paragraphs.append(
                {
                    "text": f"[Scanned page {page.page_number} — text may be incomplete]",
                    "page": page.page_number,
                    "headings": list(heading_stack),
                    "has_table": page.has_table,
                    "is_heading": False,
                    "char_start": 0,
                }
            )
            continue

        # Track accumulated character offset within the full document
        for block in page.blocks:
            text = clean_text(block.get("text", ""))
            if not text:
                continue

            is_heading = block.get("is_heading", False)

            if is_heading:
                # Update heading context stack (simple: just accumulate)
                heading_stack = heading_stack[-2:] + [text]

            paragraphs.append(
                {
                    "text": text,
                    "page": page.page_number,
                    "headings": list(heading_stack),
                    "has_table": page.has_table and not is_heading,
                    "is_heading": is_heading,
                    "char_start": 0,  # filled in below
                }
            )

    # Assign character offsets across the full document
    char_pos = 0
    for para in paragraphs:
        para["char_start"] = char_pos
        char_pos += len(para["text"]) + 1  # +1 for separator

    return paragraphs


def _sliding_window_chunks(
    paragraphs: list[dict],
    chunk_size: int,
    chunk_overlap: int,
    doc: DocumentContent,
) -> list[Chunk]:
    """
    Build chunks using a sliding window over paragraphs.
    Each chunk respects the target token count and carries heading context.
    """
    chunks: list[Chunk] = []
    source_name = os.path.basename(doc.source_file)

    i = 0
    chunk_index = 0

    while i < len(paragraphs):
        chunk_paras: list[dict] = []
        token_count = 0

        j = i
        while j < len(paragraphs):
            para = paragraphs[j]
            para_tokens = estimate_tokens(para["text"])

            if token_count + para_tokens > chunk_size and chunk_paras:
                break

            chunk_paras.append(para)
            token_count += para_tokens
            j += 1

        if not chunk_paras:
            # Single paragraph larger than chunk_size — include it alone
            chunk_paras = [paragraphs[i]]
            token_count = estimate_tokens(paragraphs[i]["text"])
            j = i + 1

        chunk_text = "\n\n".join(p["text"] for p in chunk_paras)
        chunk_pages = sorted({p["page"] for p in chunk_paras})
        heading_context = chunk_paras[0]["headings"] if chunk_paras else []
        has_table = any(p["has_table"] for p in chunk_paras)
        has_heading = any(p["is_heading"] for p in chunk_paras)

        start_char = chunk_paras[0]["char_start"]
        end_char = chunk_paras[-1]["char_start"] + len(chunk_paras[-1]["text"])

        chunk = Chunk(
            chunk_id=f"chunk_{chunk_index:04d}",
            text=chunk_text,
            token_count=token_count,
            source_pages=chunk_pages,
            page_range={"start": chunk_pages[0], "end": chunk_pages[-1]},
            heading_context=heading_context,
            position=ChunkPosition(
                index=chunk_index,
                total=0,  # filled after all chunks are built
                start_char=start_char,
                end_char=end_char,
            ),
            metadata=ChunkMetadata(
                source_file=source_name,
                has_table=has_table,
                has_heading=has_heading,
            ),
        )
        chunks.append(chunk)
        chunk_index += 1

        # Advance with overlap: step back by overlap tokens
        overlap_tokens = 0
        step = j - 1
        while step > i and overlap_tokens < chunk_overlap:
            overlap_tokens += estimate_tokens(paragraphs[step]["text"])
            step -= 1
        i = max(i + 1, step + 1)

    # Patch total into all positions
    total = len(chunks)
    for c in chunks:
        c.position = ChunkPosition(
            index=c.position.index,
            total=total,
            start_char=c.position.start_char,
            end_char=c.position.end_char,
        )

    return chunks
