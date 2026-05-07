---
name: chunks-to-pgvector
description: >
  Export document chunks to PostgreSQL with pgvector for semantic search and RAG pipelines.
  Use this skill when the user wants to store PDF chunks as embeddings in a PostgreSQL
  vector database, enable semantic search over documents, build a RAG pipeline with
  PostgreSQL as the vector store, or index documents for similarity search. Trigger on:
  "store in pgvector", "embed into PostgreSQL", "vector search", "semantic search",
  "RAG with PostgreSQL", "pgvector", "embed chunks", "vector database", "similarity search",
  "index for RAG", "export embeddings", "store embeddings in postgres", "chunk embeddings".
  Supports OpenAI, Voyage AI, and local sentence-transformers as embedding providers.
  This skill does NOT handle: chunking (use pdf-to-chunks first to produce chunks.json),
  Neo4j/AGE graph loading (use graph-db-admin), or knowledge graph extraction
  (use pdf-to-knowledge-graph).
---

# Chunks to PostgreSQL pgvector Skill

Export PDF chunk embeddings into PostgreSQL with the pgvector extension for semantic
search, RAG pipelines, and cosine similarity queries.

## Dependencies

```bash
# Core (required)
pip install psycopg2-binary pgvector --break-system-packages

# Choose ONE embedding provider:

# Option A — OpenAI (recommended, requires OPENAI_API_KEY)
pip install openai --break-system-packages

# Option B — Voyage AI (requires VOYAGE_API_KEY)
pip install voyageai --break-system-packages

# Option C — Local / offline (no API key, runs on CPU)
pip install sentence-transformers --break-system-packages
```

## Environment Variables

```bash
# PostgreSQL connection
export PGVECTOR_URI="postgresql://user:password@localhost:5432/mydb"

# Embedding API keys (set whichever provider you use)
export OPENAI_API_KEY=sk-...
export VOYAGE_API_KEY=pa-...
```

## Quick Start

```bash
# Step 1: Chunk your PDF first (produces chunks.json)
#   Use the pdf-to-chunks skill or:
python /path/to/pdf-to-chunks/scripts/extract_text.py --input document.pdf --output extracted.json
python /path/to/pdf-to-chunks/scripts/chunk_document.py --input extracted.json --output-dir ./chunks/

# Step 2: Embed chunks and load into pgvector
python embed_chunks.py \
  --input ./chunks/chunks.json \
  --uri "postgresql://user:pass@localhost:5432/mydb" \
  --provider openai \
  --table document_chunks

# Step 3: Semantic search
python search_vectors.py \
  --query "What are the financial risks?" \
  --uri "postgresql://user:pass@localhost:5432/mydb" \
  --top-k 5

# Step 4: Database management
python manage_vectors.py --action stats --uri "postgresql://..."
python manage_vectors.py --action list --uri "postgresql://..."
python manage_vectors.py --action delete --document-id "annual_report_2024" --uri "postgresql://..."
```

## Workflow Detail

### Step 1 — Get chunks.json

Run the `pdf-to-chunks` skill first to produce `chunks.json`. Each chunk must have:
- `chunk_id`, `text`, `source_pages`, `heading_context`, `token_count`

### Step 2 — `embed_chunks.py`

Reads `chunks.json`, generates embeddings in batches, and upserts into PostgreSQL.

Auto-creates the table and HNSW index if they don't exist.

**Flags:**
- `--input PATH` — chunks.json (required)
- `--uri URI` — PostgreSQL connection string (or PGVECTOR_URI env var)
- `--table NAME` — table name (default: document_chunks)
- `--provider openai|voyage|local` — embedding provider (default: openai)
- `--model NAME` — model override (uses provider default if omitted)
- `--document-id ID` — namespace for this document (default: source filename)
- `--skip-existing / --no-skip-existing` — skip chunks already in table

**Provider defaults:**
| Provider | Default model | Dimension |
|----------|--------------|-----------|
| openai   | text-embedding-3-small | 1536 |
| voyage   | voyage-3-large | 1024 |
| local    | all-MiniLM-L6-v2 | 384 |

### Step 3 — `search_vectors.py`

Embeds the query and returns the top-k most similar chunks with their page references.

**Flags:**
- `--query TEXT` — search query (required)
- `--uri URI` — PostgreSQL connection string
- `--table NAME` — table name (default: document_chunks)
- `--provider openai|voyage|local` — must match what was used for embedding
- `--model NAME` — must match embedding model
- `--top-k N` — number of results (default: 10)
- `--document-id ID` — limit search to one document
- `--min-score FLOAT` — minimum cosine similarity (0.0–1.0, default: 0.0)

### Step 4 — `manage_vectors.py`

**Actions:**
- `stats` — row count, chunks by document, table size, embedding model info
- `list` — all indexed documents with chunk counts and last-updated timestamp
- `delete` — remove all chunks for a specific document_id

## Database Schema

```sql
CREATE TABLE document_chunks (
    id              SERIAL PRIMARY KEY,
    chunk_id        TEXT UNIQUE NOT NULL,
    document_id     TEXT NOT NULL,           -- source filename (without extension)
    source_file     TEXT NOT NULL,
    page_numbers    INTEGER[],               -- PDF pages this chunk spans
    heading_context TEXT[],                  -- heading breadcrumb ["Ch1", "1.2 Risk"]
    chunk_text      TEXT NOT NULL,
    token_count     INTEGER,
    has_table       BOOLEAN DEFAULT FALSE,
    has_heading     BOOLEAN DEFAULT FALSE,
    embedding       vector(1536),            -- dimension = model output
    metadata        JSONB DEFAULT '{}',      -- position, chunk_config
    created_at      TIMESTAMP DEFAULT NOW()
);

-- HNSW index for fast cosine similarity search
CREATE INDEX document_chunks_embedding_hnsw
ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

## Search Result Schema

```json
[
  {
    "chunk_id": "chunk_0007",
    "document_id": "annual_report_2024",
    "source_file": "annual_report_2024.pdf",
    "page_numbers": [12, 13],
    "heading_context": ["Chapter 3", "3.2 Risk Assessment"],
    "chunk_text": "The financial risks identified include...",
    "token_count": 498,
    "has_table": false,
    "has_heading": true,
    "score": 0.921
  }
]
```

## PostgreSQL Setup

### Docker
```bash
docker run -p 5432:5432 \
  -e POSTGRES_PASSWORD=secret \
  pgvector/pgvector:pg17
```

### Cloud (Supabase, Neon, AlloyDB, etc.)
pgvector is available on Supabase, Neon, and Google AlloyDB. Enable via:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Enable manually on existing PostgreSQL
```sql
-- Connect as superuser
CREATE EXTENSION IF NOT EXISTS vector;
```

## Edge Cases

- **Mixed model dimensions:** Each table must have a single embedding dimension. Use different `--table` names for different models.
- **Large documents (1000+ chunks):** Embedding is done in batches of 32. For OpenAI, this is ~3 API calls per 100 chunks.
- **Offline / air-gapped environments:** Use `--provider local` with sentence-transformers — no API key required.
- **Re-indexing with a new model:** Set `--no-skip-existing` to re-embed all chunks, or use a new `--table` name.
- **Multi-document RAG:** Load multiple documents into the same table — use `--document-id` to namespace them, and `--document-id` in search to filter.
