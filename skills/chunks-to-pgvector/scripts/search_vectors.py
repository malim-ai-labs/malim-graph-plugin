#!/usr/bin/env python3
"""
Semantic search over embedded chunks in PostgreSQL pgvector.

Install:
  pip install psycopg2-binary pgvector --break-system-packages
  pip install openai --break-system-packages   (or voyageai / sentence-transformers)
"""
import argparse
import json
import os
import sys

try:
    from malimgraph.core.embedder import EmbedderConfig, embed_texts
    from malimgraph.core.vector_client import PgVectorClient
    _USE_PACKAGE = True
except ImportError:
    _USE_PACKAGE = False


def _default_model(provider: str) -> str:
    return {"openai": "text-embedding-3-small", "voyage": "voyage-3-large", "local": "all-MiniLM-L6-v2"}.get(provider, "text-embedding-3-small")


def _default_api_key(provider: str) -> str:
    env_var = {"openai": "OPENAI_API_KEY", "voyage": "VOYAGE_API_KEY"}.get(provider)
    return os.environ.get(env_var, "") if env_var else ""


def _inline_embed_query(query: str, provider: str, model: str, api_key: str) -> list[float]:
    if provider == "openai":
        try:
            from openai import OpenAI
        except ImportError:
            print("ERROR: pip install openai --break-system-packages", file=sys.stderr)
            sys.exit(1)
        client = OpenAI(api_key=api_key)
        resp = client.embeddings.create(input=[query], model=model)
        return resp.data[0].embedding

    elif provider == "voyage":
        try:
            import voyageai
        except ImportError:
            print("ERROR: pip install voyageai --break-system-packages", file=sys.stderr)
            sys.exit(1)
        client = voyageai.Client(api_key=api_key)
        result = client.embed([query], model=model, input_type="query")
        return result.embeddings[0]

    elif provider == "local":
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print("ERROR: pip install sentence-transformers --break-system-packages", file=sys.stderr)
            sys.exit(1)
        st_model = SentenceTransformer(model)
        return st_model.encode([query], normalize_embeddings=True)[0].tolist()

    raise ValueError(f"Unknown provider: {provider}")


def _inline_search(query: str, uri: str, table: str, provider: str, model: str,
                   api_key: str, top_k: int, document_id: str | None, min_score: float) -> list[dict]:
    try:
        import psycopg2
    except ImportError:
        print("ERROR: pip install psycopg2-binary --break-system-packages", file=sys.stderr)
        sys.exit(1)

    embedding = _inline_embed_query(query, provider, model, api_key)
    vec_str = f"[{','.join(str(v) for v in embedding)}]"

    conn = psycopg2.connect(uri)
    conn.autocommit = True

    with conn.cursor() as cur:
        if document_id:
            cur.execute(f"""
                SELECT chunk_id, document_id, source_file, page_numbers,
                       heading_context, chunk_text, token_count, has_table, has_heading,
                       metadata, 1 - (embedding <=> %s::vector) AS score
                FROM {table}
                WHERE document_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, [vec_str, document_id, vec_str, top_k])
        else:
            cur.execute(f"""
                SELECT chunk_id, document_id, source_file, page_numbers,
                       heading_context, chunk_text, token_count, has_table, has_heading,
                       metadata, 1 - (embedding <=> %s::vector) AS score
                FROM {table}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, [vec_str, vec_str, top_k])

        cols = [d[0] for d in cur.description]
        results = []
        for row in cur.fetchall():
            r = dict(zip(cols, row))
            if float(r["score"]) >= min_score:
                results.append(r)

    conn.close()
    return results


def main():
    parser = argparse.ArgumentParser(description="Semantic search over pgvector chunks.")
    parser.add_argument("--query", "-q", required=True, help="Search query text.")
    parser.add_argument("--uri", default=None, help="PostgreSQL connection URI (or PGVECTOR_URI)")
    parser.add_argument("--table", default="document_chunks", help="Table to search.")
    parser.add_argument("--provider", default="openai", choices=["openai", "voyage", "local"])
    parser.add_argument("--model", default=None, help="Embedding model (must match what was used for loading).")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results.")
    parser.add_argument("--document-id", default=None, help="Limit search to one document.")
    parser.add_argument("--min-score", type=float, default=0.0, help="Minimum cosine similarity (0.0–1.0).")
    parser.add_argument("--output", default=None, help="Optional JSON output file.")
    args = parser.parse_args()

    uri = args.uri or os.environ.get("PGVECTOR_URI", "")
    if not uri:
        print("ERROR: --uri or PGVECTOR_URI required.", file=sys.stderr)
        sys.exit(1)

    model = args.model or _default_model(args.provider)
    api_key = _default_api_key(args.provider)

    if args.provider in ("openai", "voyage") and not api_key:
        env_var = "OPENAI_API_KEY" if args.provider == "openai" else "VOYAGE_API_KEY"
        print(f"ERROR: {env_var} required.", file=sys.stderr)
        sys.exit(1)

    print(f"Searching: '{args.query}' (provider={args.provider}, top_k={args.top_k})")

    if _USE_PACKAGE:
        config = EmbedderConfig(provider=args.provider, model=model, api_key=api_key or None)
        client = PgVectorClient(uri, table_name=args.table, embedder_config=config)
        try:
            results = client.similarity_search(
                args.query, top_k=args.top_k,
                document_id=args.document_id, min_score=args.min_score,
            )
        finally:
            client.close()
    else:
        results = _inline_search(
            args.query, uri, args.table, args.provider, model, api_key,
            args.top_k, args.document_id, args.min_score,
        )

    output_str = json.dumps(results, indent=2, default=str)
    print(output_str)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str)

    print(f"\n{len(results)} result(s) returned.", file=sys.stderr)

    # Print a human-friendly summary to stderr
    for i, r in enumerate(results, 1):
        score = r.get("score", 0)
        pages = r.get("page_numbers", [])
        snippet = str(r.get("chunk_text", ""))[:120].replace("\n", " ")
        print(f"  [{i}] score={score:.3f} pages={pages} — {snippet}...", file=sys.stderr)


if __name__ == "__main__":
    main()
