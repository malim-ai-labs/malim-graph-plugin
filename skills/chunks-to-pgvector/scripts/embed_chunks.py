#!/usr/bin/env python3
"""
Embed document chunks and load them into PostgreSQL with pgvector.

Install:
  pip install psycopg2-binary pgvector --break-system-packages
  pip install openai --break-system-packages          # for OpenAI
  pip install voyageai --break-system-packages        # for Voyage AI
  pip install sentence-transformers --break-system-packages  # for local
"""
import argparse
import json
import os
import sys

try:
    from malimgraph.core.embedder import EmbedderConfig, embed_texts
    from malimgraph.core.vector_client import PgVectorClient
    from malimgraph.schemas.chunks import ChunkCollection
    _USE_PACKAGE = True
except ImportError:
    _USE_PACKAGE = False


# ── Inline fallbacks ──────────────────────────────────────────────────────────

def _inline_embed(texts: list[str], provider: str, model: str, api_key: str, batch_size: int = 32) -> list[list[float]]:
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        if provider == "openai":
            try:
                from openai import OpenAI
            except ImportError:
                print("ERROR: pip install openai --break-system-packages", file=sys.stderr)
                sys.exit(1)
            client = OpenAI(api_key=api_key)
            resp = client.embeddings.create(input=[t[:30000] for t in batch], model=model)
            all_embeddings.extend([item.embedding for item in resp.data])

        elif provider == "voyage":
            try:
                import voyageai
            except ImportError:
                print("ERROR: pip install voyageai --break-system-packages", file=sys.stderr)
                sys.exit(1)
            client = voyageai.Client(api_key=api_key)
            result = client.embed(batch, model=model, input_type="document")
            all_embeddings.extend(result.embeddings)

        elif provider == "local":
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                print("ERROR: pip install sentence-transformers --break-system-packages", file=sys.stderr)
                sys.exit(1)
            st_model = SentenceTransformer(model)
            vecs = st_model.encode(batch, normalize_embeddings=True)
            all_embeddings.extend(vecs.tolist())

        progress = min(i + batch_size, len(texts))
        print(f"  Embedded {progress}/{len(texts)} chunks...")

    return all_embeddings


def _model_dimension(model: str) -> int:
    dims = {
        "text-embedding-3-small": 1536, "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536, "voyage-3-large": 1024,
        "voyage-3": 1024, "voyage-3-lite": 512,
        "all-MiniLM-L6-v2": 384, "all-mpnet-base-v2": 768,
        "BAAI/bge-small-en-v1.5": 384, "BAAI/bge-base-en-v1.5": 768,
        "BAAI/bge-large-en-v1.5": 1024,
    }
    return dims.get(model, 1536)


def _default_model(provider: str) -> str:
    return {"openai": "text-embedding-3-small", "voyage": "voyage-3-large", "local": "all-MiniLM-L6-v2"}.get(provider, "text-embedding-3-small")


def _default_api_key(provider: str) -> str:
    env_var = {"openai": "OPENAI_API_KEY", "voyage": "VOYAGE_API_KEY"}.get(provider)
    return os.environ.get(env_var, "") if env_var else ""


def _inline_load(chunks_data: dict, uri: str, table: str, provider: str, model: str,
                 api_key: str, document_id: str, skip_existing: bool) -> dict:
    try:
        import psycopg2
    except ImportError:
        print("ERROR: pip install psycopg2-binary --break-system-packages", file=sys.stderr)
        sys.exit(1)

    dim = _model_dimension(model)
    source_file = chunks_data["metadata"]["source_file"]
    doc_id = document_id or os.path.splitext(source_file)[0]
    chunks = chunks_data.get("chunks", [])

    conn = psycopg2.connect(uri)
    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id              SERIAL PRIMARY KEY,
                chunk_id        TEXT UNIQUE NOT NULL,
                document_id     TEXT NOT NULL,
                source_file     TEXT NOT NULL,
                page_numbers    INTEGER[],
                heading_context TEXT[],
                chunk_text      TEXT NOT NULL,
                token_count     INTEGER,
                has_table       BOOLEAN DEFAULT FALSE,
                has_heading     BOOLEAN DEFAULT FALSE,
                embedding       vector({dim}),
                metadata        JSONB DEFAULT '{{}}',
                created_at      TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS {table}_embedding_hnsw
            ON {table} USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)
        cur.execute(f"CREATE INDEX IF NOT EXISTS {table}_document_id ON {table} (document_id);")

        existing_ids: set[str] = set()
        if skip_existing:
            cur.execute(f"SELECT chunk_id FROM {table} WHERE document_id = %s", (doc_id,))
            existing_ids = {row[0] for row in cur.fetchall()}

    to_embed = [c for c in chunks if c["chunk_id"] not in existing_ids]
    skipped = len(chunks) - len(to_embed)

    if not to_embed:
        conn.close()
        return {"inserted": 0, "updated": 0, "skipped": skipped}

    print(f"  Generating {len(to_embed)} embeddings ({provider}/{model})...")
    texts = [c["text"] for c in to_embed]
    embeddings = _inline_embed(texts, provider, model, api_key)

    inserted = updated = 0
    with conn.cursor() as cur:
        for chunk, embedding in zip(to_embed, embeddings):
            vec_str = f"[{','.join(str(v) for v in embedding)}]"
            meta = json.dumps({
                "position_index": chunk["position"]["index"],
                "position_total": chunk["position"]["total"],
                "start_char": chunk["position"]["start_char"],
                "end_char": chunk["position"]["end_char"],
            })
            cur.execute(f"""
                INSERT INTO {table}
                    (chunk_id, document_id, source_file, page_numbers, heading_context,
                     chunk_text, token_count, has_table, has_heading, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    chunk_text = EXCLUDED.chunk_text,
                    page_numbers = EXCLUDED.page_numbers,
                    heading_context = EXCLUDED.heading_context,
                    token_count = EXCLUDED.token_count,
                    metadata = EXCLUDED.metadata,
                    created_at = NOW()
                RETURNING (xmax = 0) AS is_insert
            """, (
                chunk["chunk_id"], doc_id, source_file,
                chunk["source_pages"], chunk.get("heading_context", []),
                chunk["text"], chunk["token_count"],
                chunk["metadata"].get("has_table", False),
                chunk["metadata"].get("has_heading", False),
                vec_str, meta,
            ))
            row = cur.fetchone()
            if row and row[0]:
                inserted += 1
            else:
                updated += 1

    conn.close()
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


def main():
    parser = argparse.ArgumentParser(description="Embed document chunks and load into pgvector.")
    parser.add_argument("--input", required=True, help="Path to chunks.json")
    parser.add_argument("--uri", default=None, help="PostgreSQL connection URI (or PGVECTOR_URI env var)")
    parser.add_argument("--table", default="document_chunks", help="Target table name.")
    parser.add_argument("--provider", default="openai", choices=["openai", "voyage", "local"])
    parser.add_argument("--model", default=None, help="Embedding model override.")
    parser.add_argument("--document-id", default=None, help="Document namespace (default: source filename).")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--no-skip-existing", dest="skip_existing", action="store_false")
    args = parser.parse_args()

    uri = args.uri or os.environ.get("PGVECTOR_URI", "")
    if not uri:
        print("ERROR: --uri or PGVECTOR_URI environment variable required.", file=sys.stderr)
        sys.exit(1)

    model = args.model or _default_model(args.provider)
    api_key = _default_api_key(args.provider)
    dim = _model_dimension(model)

    if args.provider in ("openai", "voyage") and not api_key:
        env_var = "OPENAI_API_KEY" if args.provider == "openai" else "VOYAGE_API_KEY"
        print(f"ERROR: {env_var} environment variable required for {args.provider}.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        chunks_data = json.load(f)

    total = chunks_data["metadata"]["total_chunks"]
    print(f"Provider: {args.provider} / Model: {model} (dim={dim})")
    print(f"Chunks: {total} total")

    if _USE_PACKAGE:
        config = EmbedderConfig(provider=args.provider, model=model, api_key=api_key or None)
        collection = ChunkCollection.model_validate(chunks_data)
        client = PgVectorClient(uri, table_name=args.table, embedder_config=config)
        try:
            result = client.load_chunks(collection, document_id=args.document_id, skip_existing=args.skip_existing)
        finally:
            client.close()
    else:
        result = _inline_load(chunks_data, uri, args.table, args.provider, model, api_key, args.document_id, args.skip_existing)

    print(f"\n  ✓ Inserted: {result['inserted']}")
    print(f"  ✓ Updated:  {result['updated']}")
    print(f"  - Skipped:  {result['skipped']}")
    print("Done.")


if __name__ == "__main__":
    main()
