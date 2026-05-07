---
name: pdf-to-rag
description: >
  Split a PDF into embedding-ready chunks and store them in PostgreSQL pgvector
  for semantic search and RAG pipelines. Supports OpenAI, Voyage AI, and local
  sentence-transformers. No Anthropic API key required.
triggers:
  - "chunk for RAG"
  - "prepare embeddings"
  - "vector search"
  - "semantic search"
  - "split for vector database"
  - "embed document"
  - "pgvector"
  - "RAG pipeline"
  - "chunk and embed"
skip_if:
  - "knowledge graph"
  - "render HTML"
  - "load into Neo4j"
---

# PDF to RAG Pipeline

Chunk a PDF and store embeddings in PostgreSQL pgvector.

## Workflow

```
1. chunk_document(pdf_path, chunk_size=512, chunk_overlap=64, output_format="json")
2. embed_and_store_chunks(chunks_path, embedding_provider="openai")
```

## Example

> "Chunk report.pdf for semantic search and store in my pgvector database"

## Required Environment

```bash
PGVECTOR_URI=postgresql://user:pass@localhost:5432/mydb
OPENAI_API_KEY=sk-...   # or VOYAGE_API_KEY or use provider=local
```

## Embedding Providers

| Provider | Model | Dimension | Requires |
|----------|-------|-----------|---------|
| `openai` | text-embedding-3-small | 1536 | OPENAI_API_KEY |
| `voyage` | voyage-3-large | 1024 | VOYAGE_API_KEY |
| `local` | all-MiniLM-L6-v2 | 384 | none (CPU) |

## Search After Loading

> "Search my documents for 'financial risk assessment'"

Claude calls `embed_and_store_chunks` with a query — returns top-k chunks with page refs.
