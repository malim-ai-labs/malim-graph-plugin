"""PostgreSQL pgvector client — store, search, and manage embedded chunks."""

from __future__ import annotations

import json
import os
from typing import Optional

from malimgraph.core.embedder import EmbedderConfig, embed_texts
from malimgraph.schemas.chunks import ChunkCollection


class PgVectorClient:
    """
    Manages chunk embeddings in a PostgreSQL database with the pgvector extension.

    Schema per collection table:
        id              SERIAL PRIMARY KEY
        chunk_id        TEXT UNIQUE
        document_id     TEXT            (source filename without extension)
        source_file     TEXT
        page_numbers    INTEGER[]
        heading_context TEXT[]
        chunk_text      TEXT
        token_count     INTEGER
        has_table       BOOLEAN
        has_heading     BOOLEAN
        embedding       vector(N)       (dimension = embedder model)
        metadata        JSONB
        created_at      TIMESTAMP
    """

    def __init__(
        self,
        connection_uri: str,
        table_name: str = "document_chunks",
        embedder_config: Optional[EmbedderConfig] = None,
    ):
        try:
            import psycopg2
            import psycopg2.extras

            self._psycopg2 = psycopg2
        except ImportError:
            raise ImportError("Install psycopg2: pip install psycopg2-binary")

        self._conn_uri = connection_uri
        self.table_name = table_name
        self.embedder_config = embedder_config or EmbedderConfig()
        self._conn = psycopg2.connect(connection_uri)
        self._conn.autocommit = True
        self._ensure_schema()

    def _ensure_schema(self):
        dim = self.embedder_config.dimension
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
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
            # HNSW index for fast approximate nearest-neighbour search
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_hnsw
                ON {self.table_name}
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """)
            # Indexes for filtering
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {self.table_name}_document_id ON {self.table_name} (document_id);"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {self.table_name}_source_file ON {self.table_name} (source_file);"
            )

    def close(self):
        self._conn.close()

    def load_chunks(
        self,
        collection: ChunkCollection,
        document_id: Optional[str] = None,
        skip_existing: bool = True,
    ) -> dict:
        """
        Embed all chunks in a ChunkCollection and upsert them into pgvector.
        Returns a dict with counts of inserted, updated, and skipped chunks.
        """
        chunks = collection.chunks
        if not chunks:
            return {"inserted": 0, "updated": 0, "skipped": 0}

        doc_id = document_id or os.path.splitext(collection.metadata.source_file)[0]

        # Check which chunk_ids already exist
        existing_ids: set[str] = set()
        if skip_existing:
            with self._conn.cursor() as cur:
                cur.execute(
                    f"SELECT chunk_id FROM {self.table_name} WHERE document_id = %s",
                    (doc_id,),
                )
                existing_ids = {row[0] for row in cur.fetchall()}

        to_embed = [c for c in chunks if c.chunk_id not in existing_ids]
        skipped = len(chunks) - len(to_embed)

        if not to_embed:
            return {"inserted": 0, "updated": 0, "skipped": skipped}

        print(
            f"  [pgvector] Generating {len(to_embed)} embeddings via {self.embedder_config.provider}/{self.embedder_config.model}..."
        )
        texts = [c.text for c in to_embed]
        embeddings = embed_texts(texts, self.embedder_config)

        inserted = 0
        updated = 0

        with self._conn.cursor() as cur:
            for chunk, embedding in zip(to_embed, embeddings):
                vec_str = f"[{','.join(str(v) for v in embedding)}]"
                meta = {
                    "position_index": chunk.position.index,
                    "position_total": chunk.position.total,
                    "start_char": chunk.position.start_char,
                    "end_char": chunk.position.end_char,
                    "chunk_config": collection.metadata.chunk_config,
                }

                cur.execute(
                    f"""
                    INSERT INTO {self.table_name}
                        (chunk_id, document_id, source_file, page_numbers, heading_context,
                         chunk_text, token_count, has_table, has_heading, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        embedding       = EXCLUDED.embedding,
                        chunk_text      = EXCLUDED.chunk_text,
                        page_numbers    = EXCLUDED.page_numbers,
                        heading_context = EXCLUDED.heading_context,
                        token_count     = EXCLUDED.token_count,
                        metadata        = EXCLUDED.metadata,
                        created_at      = NOW()
                    RETURNING (xmax = 0) AS inserted
                """,
                    (
                        chunk.chunk_id,
                        doc_id,
                        collection.metadata.source_file,
                        chunk.source_pages,
                        chunk.heading_context,
                        chunk.text,
                        chunk.token_count,
                        chunk.metadata.has_table,
                        chunk.metadata.has_heading,
                        vec_str,
                        json.dumps(meta),
                    ),
                )
                row = cur.fetchone()
                if row and row[0]:
                    inserted += 1
                else:
                    updated += 1

        return {"inserted": inserted, "updated": updated, "skipped": skipped}

    def similarity_search(
        self,
        query: str,
        top_k: int = 10,
        document_id: Optional[str] = None,
        min_score: float = 0.0,
    ) -> list[dict]:
        """
        Semantic search: embed the query, find nearest chunks by cosine similarity.
        Returns a list of result dicts sorted by descending similarity score.
        """
        [query_embedding] = embed_texts([query], self.embedder_config)
        vec_str = f"[{','.join(str(v) for v in query_embedding)}]"

        with self._conn.cursor() as cur:
            if document_id:
                cur.execute(
                    f"""
                    SELECT
                        chunk_id, document_id, source_file, page_numbers,
                        heading_context, chunk_text, token_count, has_table, has_heading,
                        metadata,
                        1 - (embedding <=> %s::vector) AS score
                    FROM {self.table_name}
                    WHERE document_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """,
                    [vec_str, document_id, vec_str, top_k],
                )
            else:
                cur.execute(
                    f"""
                    SELECT
                        chunk_id, document_id, source_file, page_numbers,
                        heading_context, chunk_text, token_count, has_table, has_heading,
                        metadata,
                        1 - (embedding <=> %s::vector) AS score
                    FROM {self.table_name}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """,
                    [vec_str, vec_str, top_k],
                )

            cols = [d[0] for d in cur.description]
            results = []
            for row in cur.fetchall():
                result = dict(zip(cols, row))
                if result["score"] >= min_score:
                    results.append(result)

        return results

    def stats(self) -> dict:
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            total_chunks = cur.fetchone()[0]
            cur.execute(
                f"SELECT document_id, COUNT(*) FROM {self.table_name} GROUP BY document_id ORDER BY COUNT(*) DESC"
            )
            by_document = {row[0]: row[1] for row in cur.fetchall()}
            cur.execute(f"SELECT pg_size_pretty(pg_total_relation_size('{self.table_name}'))")
            table_size = cur.fetchone()[0]

        return {
            "table": self.table_name,
            "total_chunks": total_chunks,
            "chunks_by_document": by_document,
            "table_size": table_size,
            "embedding_model": self.embedder_config.model,
            "embedding_dimension": self.embedder_config.dimension,
        }

    def delete_document(self, document_id: str) -> int:
        with self._conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self.table_name} WHERE document_id = %s RETURNING chunk_id",
                (document_id,),
            )
            return cur.rowcount

    def list_documents(self) -> list[dict]:
        with self._conn.cursor() as cur:
            cur.execute(f"""
                SELECT document_id, source_file, COUNT(*) AS chunk_count,
                       SUM(token_count) AS total_tokens, MAX(created_at) AS last_updated
                FROM {self.table_name}
                GROUP BY document_id, source_file
                ORDER BY last_updated DESC
            """)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
