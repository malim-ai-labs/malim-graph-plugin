#!/usr/bin/env python3
"""
Manage the pgvector document_chunks table: stats, list documents, delete.

Install: pip install psycopg2-binary pgvector --break-system-packages
"""
import argparse
import json
import os
import sys

try:
    from malimgraph.core.embedder import EmbedderConfig
    from malimgraph.core.vector_client import PgVectorClient
    _USE_PACKAGE = True
except ImportError:
    _USE_PACKAGE = False


def _default_model(provider: str) -> str:
    return {"openai": "text-embedding-3-small", "voyage": "voyage-3-large", "local": "all-MiniLM-L6-v2"}.get(provider, "text-embedding-3-small")


def _get_conn(uri: str):
    try:
        import psycopg2
        conn = psycopg2.connect(uri)
        conn.autocommit = True
        return conn
    except ImportError:
        print("ERROR: pip install psycopg2-binary --break-system-packages", file=sys.stderr)
        sys.exit(1)


def _inline_stats(uri: str, table: str) -> dict:
    conn = _get_conn(uri)
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        total = cur.fetchone()[0]
        cur.execute(f"SELECT document_id, COUNT(*) FROM {table} GROUP BY document_id ORDER BY COUNT(*) DESC")
        by_doc = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute(f"SELECT pg_size_pretty(pg_total_relation_size('{table}'))")
        size = cur.fetchone()[0]
    conn.close()
    return {"table": table, "total_chunks": total, "chunks_by_document": by_doc, "table_size": size}


def _inline_list(uri: str, table: str) -> list:
    conn = _get_conn(uri)
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT document_id, source_file, COUNT(*) AS chunk_count,
                   SUM(token_count) AS total_tokens, MAX(created_at) AS last_updated
            FROM {table}
            GROUP BY document_id, source_file
            ORDER BY last_updated DESC
        """)
        cols = [d[0] for d in cur.description]
        docs = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    return docs


def _inline_delete(uri: str, table: str, document_id: str) -> int:
    conn = _get_conn(uri)
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {table} WHERE document_id = %s RETURNING chunk_id", (document_id,))
        count = cur.rowcount
    conn.close()
    return count


def main():
    parser = argparse.ArgumentParser(description="Manage the pgvector chunks table.")
    parser.add_argument("--action", required=True, choices=["stats", "list", "delete"])
    parser.add_argument("--uri", default=None, help="PostgreSQL connection URI (or PGVECTOR_URI)")
    parser.add_argument("--table", default="document_chunks")
    parser.add_argument("--provider", default="openai", choices=["openai", "voyage", "local"])
    parser.add_argument("--document-id", default=None, help="Required for --action delete.")
    args = parser.parse_args()

    uri = args.uri or os.environ.get("PGVECTOR_URI", "")
    if not uri:
        print("ERROR: --uri or PGVECTOR_URI required.", file=sys.stderr)
        sys.exit(1)

    if args.action == "delete" and not args.document_id:
        print("ERROR: --document-id required for action=delete.", file=sys.stderr)
        sys.exit(1)

    if _USE_PACKAGE:
        config = EmbedderConfig(provider=args.provider, model=_default_model(args.provider))
        client = PgVectorClient(uri, table_name=args.table, embedder_config=config)
        try:
            if args.action == "stats":
                result = client.stats()
            elif args.action == "list":
                result = client.list_documents()
            elif args.action == "delete":
                deleted = client.delete_document(args.document_id)
                result = {"deleted": deleted, "document_id": args.document_id}
        finally:
            client.close()
    else:
        if args.action == "stats":
            result = _inline_stats(uri, args.table)
        elif args.action == "list":
            result = _inline_list(uri, args.table)
        elif args.action == "delete":
            deleted = _inline_delete(uri, args.table, args.document_id)
            result = {"deleted": deleted, "document_id": args.document_id}

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
