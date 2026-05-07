---
name: pdf-to-chunks
description: >
  Split PDF documents into embedding-ready text chunks with metadata. Use this skill when
  the user wants to prepare a document for vector search, RAG pipelines, semantic search,
  or embedding storage. Trigger on: "chunk document", "split PDF for embeddings",
  "prepare for vector database", "RAG chunks", "text chunks", "chunk for Pinecone",
  "chunk for Weaviate", "embedding chunks", "split into passages", "tokenize document".
  Outputs JSON, TXT, or Markdown chunks with page references, heading context, and
  positional metadata. This skill does NOT handle: knowledge graph extraction
  (use pdf-to-knowledge-graph) or HTML rendering (use document-to-html).
---

# PDF to Chunks Skill

Split any PDF into embedding-ready text chunks optimized for RAG pipelines and vector databases.

## Dependencies

```bash
pip install pymupdf pydantic --break-system-packages
```

## Quick Start

```bash
# Step 1: Extract text structure from PDF
python extract_text.py --input /path/to/document.pdf --output extracted_text.json

# Step 2: Chunk the document
python chunk_document.py \
  --input extracted_text.json \
  --output-dir /mnt/user-data/outputs/ \
  --chunk-size 512 \
  --overlap 64 \
  --format json
```

## Workflow Detail

### Step 1 — `extract_text.py`

Reads the PDF using PyMuPDF and outputs a page-by-page JSON structure with text blocks,
headings, table detection, and scanned-page flags.

**Flags:**
- `--input PATH` — PDF file path (required)
- `--output PATH` — output JSON path (default: `extracted_text.json`)

### Step 2 — `chunk_document.py`

Splits extracted text into overlapping chunks using a sliding window algorithm:
- Groups paragraphs/blocks until the token target is reached
- Overlaps by stepping back `overlap` tokens before each new chunk
- Inherits heading context from the nearest preceding heading
- Respects paragraph boundaries (never splits mid-paragraph if avoidable)

**Flags:**
- `--input PATH` — extracted_text.json from Step 1 (required)
- `--output-dir DIR` — directory for output files (default: `./chunks`)
- `--chunk-size N` — target tokens per chunk (default: 512)
- `--overlap N` — overlap tokens between chunks (default: 64)
- `--format json|txt|md` — output format (default: json)

## Output Formats

### JSON (`chunks.json`)
Single file with all chunks and collection metadata. Best for programmatic use.

```json
{
  "metadata": {
    "source_file": "report.pdf",
    "total_chunks": 42,
    "total_tokens": 18234,
    "chunk_config": {"chunk_size": 512, "overlap": 64}
  },
  "chunks": [
    {
      "chunk_id": "chunk_0007",
      "text": "The actual chunk text content...",
      "token_count": 498,
      "source_pages": [12, 13],
      "page_range": {"start": 12, "end": 13},
      "heading_context": ["Chapter 3", "3.2 Risk Assessment"],
      "position": {
        "index": 6,
        "total": 42,
        "start_char": 15420,
        "end_char": 17890
      },
      "metadata": {
        "source_file": "report.pdf",
        "has_table": false,
        "has_heading": true
      }
    }
  ]
}
```

### TXT (`chunk_0000.txt`, `chunk_0001.txt`, ...)
One file per chunk with YAML frontmatter. Ideal for direct file upload to vector DBs.

```
---
chunk_id: chunk_0007
pages: [12, 13]
tokens: 498
heading_context: ["Chapter 3", "3.2 Risk Assessment"]
---

The actual chunk text content...
```

### Markdown (`chunks.md`)
All chunks in a single `.md` file with `## Chunk N` headers and metadata blocks.
Good for human review or feeding to LLMs as document context.

## Chunking Strategy

Token estimation uses ~4 chars/token (English text average). Chunk boundaries respect:
1. Paragraph breaks (double newlines)
2. Heading blocks (kept intact, never split)
3. Table blocks (kept with surrounding context)

For more precise token counts, pipe through a tokenizer after chunking.

## Edge Cases

- **Very short PDFs (1-5 pages):** May produce fewer chunks than expected. Adjust `--chunk-size` down.
- **Scanned pages:** Included as single-chunk placeholders with a note. Pre-process with OCR first.
- **Large tables:** Tables are kept with their surrounding paragraph for context preservation.
- **Overlapping pages:** Chunks spanning page boundaries include both page numbers in `source_pages`.
