"""MalimGraph CLI — click-based command interface."""

from __future__ import annotations

import asyncio
import json
import os
import sys

import click


@click.group()
@click.version_option(package_name="malimgraph")
def cli():
    """MalimGraph — Transform PDF documents into structured knowledge graphs."""
    pass


@cli.command("extract")
@click.option("--input", "-i", "input_path", required=True, type=click.Path(exists=True), help="Path to the PDF file.")
@click.option("--output", "-o", "output_dir", default="./output", show_default=True, help="Output directory.")
@click.option("--entity-types", default="auto", show_default=True, help="Comma-separated entity types or 'auto'.")
@click.option("--format", "output_format", default="all", show_default=True, type=click.Choice(["json", "cypher", "age_sql", "all"]), help="Output format(s).")
@click.option("--graph-name", default="document_graph", show_default=True, help="Graph name for AGE SQL.")
def extract_cmd(input_path, output_dir, entity_types, output_format, graph_name):
    """Extract a knowledge graph from a PDF document."""
    from malimgraph.core.pdf_reader import extract_text_from_pdf
    from malimgraph.core.rule_extractor import extract_by_rules
    from malimgraph.core.llm_extractor import extract_by_llm
    from malimgraph.core.graph_builder import build_knowledge_graph
    from malimgraph.generators.cypher import generate_cypher
    from malimgraph.generators.age_sql import generate_age_sql

    os.makedirs(output_dir, exist_ok=True)

    etype_list = None
    if entity_types and entity_types.lower() != "auto":
        etype_list = [e.strip() for e in entity_types.split(",") if e.strip()]

    click.echo(f"[extract] Reading: {input_path}")
    doc = extract_text_from_pdf(input_path)
    click.echo(f"  → {doc.total_pages} pages")

    click.echo("[extract] Rule-based extraction...")
    rule_entities = extract_by_rules(doc)
    click.echo(f"  → {len(rule_entities)} entities")

    click.echo("[extract] LLM extraction (requires ANTHROPIC_API_KEY)...")
    try:
        llm_entities, llm_relationships = extract_by_llm(doc, entity_types=etype_list)
        click.echo(f"  → {len(llm_entities)} entities, {len(llm_relationships)} relationships")
    except ValueError as e:
        click.echo(f"  [Warning] Skipped: {e}", err=True)
        llm_entities, llm_relationships = [], []

    kg = build_knowledge_graph(doc, rule_entities, llm_entities, llm_relationships, graph_name)
    click.echo(f"[extract] Graph: {kg.metadata.total_entities} entities, {kg.metadata.total_relationships} relationships")

    # Write JSON
    kg_path = os.path.join(output_dir, "knowledge_graph.json")
    with open(kg_path, "w", encoding="utf-8") as f:
        json.dump(kg.model_dump(), f, indent=2, ensure_ascii=False)
    click.echo(f"  ✓ {kg_path}")

    if output_format in ("cypher", "all"):
        cypher_path = os.path.join(output_dir, "knowledge_graph.cypher")
        with open(cypher_path, "w", encoding="utf-8") as f:
            f.write(generate_cypher(kg))
        click.echo(f"  ✓ {cypher_path}")

    if output_format in ("age_sql", "all"):
        sql_path = os.path.join(output_dir, "knowledge_graph.sql")
        with open(sql_path, "w", encoding="utf-8") as f:
            f.write(generate_age_sql(kg, graph_name=graph_name))
        click.echo(f"  ✓ {sql_path}")

    click.echo("[extract] Done.")


@cli.command("chunk")
@click.option("--input", "-i", "input_path", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", "output_dir", default="./chunks", show_default=True)
@click.option("--chunk-size", default=512, show_default=True, type=int)
@click.option("--overlap", default=64, show_default=True, type=int)
@click.option("--format", "output_format", default="json", show_default=True, type=click.Choice(["json", "txt", "md"]))
def chunk_cmd(input_path, output_dir, chunk_size, overlap, output_format):
    """Split a PDF into embedding-ready text chunks."""
    from malimgraph.core.pdf_reader import extract_text_from_pdf
    from malimgraph.core.chunker import chunk_document

    os.makedirs(output_dir, exist_ok=True)

    click.echo(f"[chunk] Reading: {input_path}")
    doc = extract_text_from_pdf(input_path)
    collection = chunk_document(doc, chunk_size=chunk_size, chunk_overlap=overlap)
    click.echo(f"  → {collection.metadata.total_chunks} chunks, {collection.metadata.total_tokens} tokens")

    if output_format == "json":
        out_path = os.path.join(output_dir, "chunks.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(collection.model_dump(), f, indent=2, ensure_ascii=False)
        click.echo(f"  ✓ {out_path}")

    elif output_format == "txt":
        for chunk in collection.chunks:
            fname = os.path.join(output_dir, f"{chunk.chunk_id}.txt")
            frontmatter = (
                f"---\nchunk_id: {chunk.chunk_id}\npages: {chunk.source_pages}\n"
                f"tokens: {chunk.token_count}\nheading_context: {chunk.heading_context}\n---\n\n"
            )
            with open(fname, "w", encoding="utf-8") as f:
                f.write(frontmatter + chunk.text)
        click.echo(f"  ✓ {collection.metadata.total_chunks} .txt files in {output_dir}/")

    elif output_format == "md":
        lines = [f"# Chunks — {collection.metadata.source_file}\n"]
        for chunk in collection.chunks:
            lines.append(f"## Chunk {chunk.position.index + 1} of {chunk.position.total}")
            lines.append(f"**Pages:** {chunk.source_pages}  ")
            lines.append(f"**Tokens:** {chunk.token_count}  ")
            if chunk.heading_context:
                lines.append(f"**Context:** {' > '.join(chunk.heading_context)}  ")
            lines.append("")
            lines.append(chunk.text)
            lines.append("\n---\n")
        out_path = os.path.join(output_dir, "chunks.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        click.echo(f"  ✓ {out_path}")

    click.echo("[chunk] Done.")


@cli.command("render")
@click.option("--input", "-i", "input_path", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", "output_path", default="document.html", show_default=True)
@click.option("--knowledge-graph", "kg_path", default=None, type=click.Path(), help="knowledge_graph.json for entity annotations.")
@click.option("--toc/--no-toc", default=True, show_default=True)
@click.option("--search/--no-search", default=True, show_default=True)
def render_cmd(input_path, output_path, kg_path, toc, search):
    """Render a PDF as structured, LLM-readable HTML."""
    from malimgraph.core.pdf_reader import extract_text_from_pdf
    from malimgraph.core.html_renderer import render_document_html
    from malimgraph.schemas.entities import KnowledgeGraph

    click.echo(f"[render] Reading: {input_path}")
    doc = extract_text_from_pdf(input_path)

    kg = None
    if kg_path and os.path.exists(kg_path):
        with open(kg_path, "r", encoding="utf-8") as f:
            kg = KnowledgeGraph.model_validate(json.load(f))
        click.echo(f"  → Annotating with {len(kg.entities)} entities from {kg_path}")

    html_content = render_document_html(doc, knowledge_graph=kg, include_toc=toc, include_search=search)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    click.echo(f"  ✓ {output_path}")
    click.echo("[render] Done.")


@cli.group("db")
def db_group():
    """Graph database management (Neo4j / Apache AGE)."""
    pass


@db_group.command("load")
@click.option("--input", "-i", "input_path", required=True, type=click.Path(exists=True), help="knowledge_graph.json to load.")
@click.option("--target", default="neo4j", show_default=True, type=click.Choice(["neo4j", "age"]))
@click.option("--uri", default=None, help="Connection URI.")
@click.option("--user", default=None, help="Neo4j user.")
@click.option("--password", default=None, help="Neo4j password.")
@click.option("--graph-name", default="document_graph", show_default=True)
def db_load(input_path, target, uri, user, password, graph_name):
    """Load a knowledge graph into Neo4j or Apache AGE."""
    from malimgraph.core.db_client import get_client
    from malimgraph.schemas.entities import KnowledgeGraph

    with open(input_path, "r", encoding="utf-8") as f:
        kg = KnowledgeGraph.model_validate(json.load(f))

    kwargs = {"graph_name": graph_name}
    if uri:
        kwargs["uri"] = uri
    if user:
        kwargs["user"] = user
    if password:
        kwargs["password"] = password

    client = get_client(target, **kwargs)
    try:
        result = client.load_graph(kg)
        click.echo(f"  ✓ Loaded: {result}")
    finally:
        client.close()


@db_group.command("query")
@click.option("--target", default="neo4j", show_default=True, type=click.Choice(["neo4j", "age"]))
@click.option("--uri", default=None)
@click.option("--user", default=None)
@click.option("--password", default=None)
@click.option("--graph-name", default="document_graph", show_default=True)
@click.option("--query", "-q", "cypher_query", required=True)
def db_query(target, uri, user, password, graph_name, cypher_query):
    """Run a Cypher query against a graph database."""
    from malimgraph.core.db_client import get_client

    kwargs = {"graph_name": graph_name}
    if uri:
        kwargs["uri"] = uri
    if user:
        kwargs["user"] = user
    if password:
        kwargs["password"] = password

    client = get_client(target, **kwargs)
    try:
        rows = client.query(cypher_query)
        click.echo(json.dumps(rows, indent=2))
    finally:
        client.close()


@db_group.command("stats")
@click.option("--target", default="neo4j", show_default=True, type=click.Choice(["neo4j", "age"]))
@click.option("--uri", default=None)
@click.option("--user", default=None)
@click.option("--password", default=None)
@click.option("--graph-name", default="document_graph", show_default=True)
def db_stats(target, uri, user, password, graph_name):
    """Show graph database statistics."""
    from malimgraph.core.db_client import get_client

    kwargs = {"graph_name": graph_name}
    if uri:
        kwargs["uri"] = uri
    if user:
        kwargs["user"] = user
    if password:
        kwargs["password"] = password

    client = get_client(target, **kwargs)
    try:
        stats = client.stats()
        click.echo(json.dumps(stats, indent=2))
    finally:
        client.close()


@cli.group("vector")
def vector_group():
    """PostgreSQL pgvector — embed and search document chunks."""
    pass


@vector_group.command("load")
@click.option("--input", "-i", "input_path", required=True, type=click.Path(exists=True), help="chunks.json from malimgraph chunk.")
@click.option("--uri", default=None, envvar="PGVECTOR_URI", help="PostgreSQL connection URI.")
@click.option("--table", default="document_chunks", show_default=True, help="Target table name.")
@click.option("--provider", default="openai", show_default=True, type=click.Choice(["openai", "voyage", "local"]), help="Embedding provider.")
@click.option("--model", default=None, help="Embedding model override (uses provider default if omitted).")
@click.option("--document-id", default=None, help="Document namespace (default: source filename).")
@click.option("--skip-existing/--no-skip-existing", default=True, show_default=True, help="Skip chunks already in the table.")
def vector_load(input_path, uri, table, provider, model, document_id, skip_existing):
    """Embed chunks and store them in PostgreSQL with pgvector."""
    from malimgraph.core.embedder import EmbedderConfig
    from malimgraph.core.vector_client import PgVectorClient
    from malimgraph.schemas.chunks import ChunkCollection

    if not uri:
        click.echo("ERROR: --uri or PGVECTOR_URI env var required.", err=True)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        collection = ChunkCollection.model_validate(json.load(f))

    config = EmbedderConfig(provider=provider, model=model)
    click.echo(f"[vector] Provider: {config.provider} / Model: {config.model} (dim={config.dimension})")
    click.echo(f"[vector] Chunks to process: {collection.metadata.total_chunks}")

    client = PgVectorClient(uri, table_name=table, embedder_config=config)
    try:
        result = client.load_chunks(collection, document_id=document_id, skip_existing=skip_existing)
    finally:
        client.close()

    click.echo(f"  ✓ Inserted: {result['inserted']}")
    click.echo(f"  ✓ Updated:  {result['updated']}")
    click.echo(f"  - Skipped:  {result['skipped']}")
    click.echo("[vector] Done.")


@vector_group.command("search")
@click.option("--query", "-q", required=True, help="Search query text.")
@click.option("--uri", default=None, envvar="PGVECTOR_URI")
@click.option("--table", default="document_chunks", show_default=True)
@click.option("--provider", default="openai", show_default=True, type=click.Choice(["openai", "voyage", "local"]))
@click.option("--model", default=None)
@click.option("--top-k", default=10, show_default=True, type=int, help="Number of results to return.")
@click.option("--document-id", default=None, help="Limit search to a specific document.")
@click.option("--min-score", default=0.0, show_default=True, type=float, help="Minimum cosine similarity score.")
def vector_search(query, uri, table, provider, model, top_k, document_id, min_score):
    """Semantic search across embedded chunks."""
    from malimgraph.core.embedder import EmbedderConfig
    from malimgraph.core.vector_client import PgVectorClient

    if not uri:
        click.echo("ERROR: --uri or PGVECTOR_URI env var required.", err=True)
        sys.exit(1)

    config = EmbedderConfig(provider=provider, model=model)
    client = PgVectorClient(uri, table_name=table, embedder_config=config)
    try:
        results = client.similarity_search(query, top_k=top_k, document_id=document_id, min_score=min_score)
    finally:
        client.close()

    click.echo(json.dumps(results, indent=2, default=str))
    click.echo(f"\n{len(results)} result(s) returned.", err=True)


@vector_group.command("stats")
@click.option("--uri", default=None, envvar="PGVECTOR_URI")
@click.option("--table", default="document_chunks", show_default=True)
@click.option("--provider", default="openai", show_default=True, type=click.Choice(["openai", "voyage", "local"]))
def vector_stats(uri, table, provider):
    """Show pgvector table statistics."""
    from malimgraph.core.embedder import EmbedderConfig
    from malimgraph.core.vector_client import PgVectorClient

    if not uri:
        click.echo("ERROR: --uri or PGVECTOR_URI env var required.", err=True)
        sys.exit(1)

    config = EmbedderConfig(provider=provider)
    client = PgVectorClient(uri, table_name=table, embedder_config=config)
    try:
        stats = client.stats()
    finally:
        client.close()

    click.echo(json.dumps(stats, indent=2))


@vector_group.command("list")
@click.option("--uri", default=None, envvar="PGVECTOR_URI")
@click.option("--table", default="document_chunks", show_default=True)
@click.option("--provider", default="openai", show_default=True, type=click.Choice(["openai", "voyage", "local"]))
def vector_list(uri, table, provider):
    """List all indexed documents."""
    from malimgraph.core.embedder import EmbedderConfig
    from malimgraph.core.vector_client import PgVectorClient

    if not uri:
        click.echo("ERROR: --uri or PGVECTOR_URI env var required.", err=True)
        sys.exit(1)

    config = EmbedderConfig(provider=provider)
    client = PgVectorClient(uri, table_name=table, embedder_config=config)
    try:
        docs = client.list_documents()
    finally:
        client.close()

    click.echo(json.dumps(docs, indent=2, default=str))


@vector_group.command("delete")
@click.option("--document-id", required=True, help="Document ID to remove from the table.")
@click.option("--uri", default=None, envvar="PGVECTOR_URI")
@click.option("--table", default="document_chunks", show_default=True)
@click.option("--provider", default="openai", show_default=True, type=click.Choice(["openai", "voyage", "local"]))
def vector_delete(document_id, uri, table, provider):
    """Delete all chunks for a document from the vector table."""
    from malimgraph.core.embedder import EmbedderConfig
    from malimgraph.core.vector_client import PgVectorClient

    if not uri:
        click.echo("ERROR: --uri or PGVECTOR_URI env var required.", err=True)
        sys.exit(1)

    config = EmbedderConfig(provider=provider)
    client = PgVectorClient(uri, table_name=table, embedder_config=config)
    try:
        deleted = client.delete_document(document_id)
    finally:
        client.close()

    click.echo(f"  ✓ Deleted {deleted} chunks for document '{document_id}'.")


@cli.command("serve")
@click.option("--transport", default="stdio", show_default=True, type=click.Choice(["stdio", "http"]))
@click.option("--port", default=8080, show_default=True, type=int)
def serve_cmd(transport, port):
    """Start the MalimGraph MCP server."""
    from malimgraph.server import run_server
    click.echo(f"[serve] Starting MCP server (transport={transport}" + (f", port={port}" if transport == "http" else "") + ")")
    run_server(transport=transport, port=port)


if __name__ == "__main__":
    cli()
