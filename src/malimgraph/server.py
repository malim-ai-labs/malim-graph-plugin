"""FastMCP server exposing all 4 MalimGraph tools."""

from __future__ import annotations

import json
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MalimGraph")


@mcp.tool()
async def extract_knowledge_graph(
    pdf_path: str,
    entity_types: str = "auto",
    output_format: str = "json",
    graph_name: str = "document_graph",
) -> dict:
    """
    Extract entities and relationships from a PDF document using hybrid
    extraction (rule-based + LLM). Returns a structured knowledge graph
    with full citation provenance.

    Every entity and relationship includes:
    - source_pages: PDF page numbers where it was found
    - source_text: verbatim supporting quote from the document
    - source_chunk_id: processing chunk ID for traceability
    - citations: array of all supporting text snippets
    - confidence: high (explicit/hybrid), medium (inferred), low (uncertain)
    - extraction_method: rule, llm, or hybrid (both agreed)

    Args:
        pdf_path: Absolute path to the PDF file.
        entity_types: Comma-separated entity types to focus on, or "auto" for all.
        output_format: Output format — json | cypher | age_sql | all.
        graph_name: Graph name used in AGE SQL output.
    """
    from malimgraph.core.graph_builder import build_knowledge_graph
    from malimgraph.core.pdf_reader import extract_text_from_pdf
    from malimgraph.core.rule_extractor import extract_by_rules
    from malimgraph.generators.age_sql import generate_age_sql
    from malimgraph.generators.cypher import generate_cypher

    if not os.path.exists(pdf_path):
        return {"error": f"PDF not found: {pdf_path}"}

    etype_list: Optional[list[str]] = None
    if entity_types and entity_types.lower() != "auto":
        etype_list = [e.strip() for e in entity_types.split(",") if e.strip()]

    print(f"[MalimGraph] Reading PDF: {pdf_path}")
    doc = extract_text_from_pdf(pdf_path)

    print("[MalimGraph] Running rule-based extraction...")
    rule_entities = extract_by_rules(doc)
    print(f"  → {len(rule_entities)} entities via rules")

    print("[MalimGraph] Running LLM extraction...")
    try:
        llm_entities, llm_relationships = await _run_llm(doc, etype_list)
        print(f"  → {len(llm_entities)} entities, {len(llm_relationships)} relationships via LLM")
    except ValueError as e:
        print(f"  [Warning] LLM extraction skipped: {e}")
        llm_entities, llm_relationships = [], []

    print("[MalimGraph] Building knowledge graph...")
    kg = build_knowledge_graph(doc, rule_entities, llm_entities, llm_relationships, graph_name)

    result: dict = {
        "status": "success",
        "metadata": kg.metadata.model_dump(),
        "knowledge_graph": kg.model_dump(),
    }

    if output_format in ("cypher", "all"):
        result["cypher"] = generate_cypher(kg)

    if output_format in ("age_sql", "all"):
        result["age_sql"] = generate_age_sql(kg, graph_name=graph_name)

    return result


@mcp.tool()
async def chunk_document(
    pdf_path: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    output_format: str = "json",
) -> dict:
    """
    Split a PDF document into overlapping text chunks optimized for
    embedding and vector search. Each chunk includes page references,
    heading context, and positional metadata for RAG pipelines.

    Args:
        pdf_path: Absolute path to the PDF file.
        chunk_size: Target tokens per chunk (default: 512).
        chunk_overlap: Overlap tokens between adjacent chunks (default: 64).
        output_format: Output format — json | txt | md.
    """
    from malimgraph.core.chunker import chunk_document as _chunk
    from malimgraph.core.pdf_reader import extract_text_from_pdf

    if not os.path.exists(pdf_path):
        return {"error": f"PDF not found: {pdf_path}"}

    doc = extract_text_from_pdf(pdf_path)
    collection = _chunk(doc, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    if output_format == "md":
        content = _chunks_to_markdown(collection)
        return {
            "status": "success",
            "format": "md",
            "content": content,
            "metadata": collection.metadata.model_dump(),
        }

    if output_format == "txt":
        files = _chunks_to_txt_map(collection)
        return {
            "status": "success",
            "format": "txt",
            "files": files,
            "metadata": collection.metadata.model_dump(),
        }

    return {
        "status": "success",
        "format": "json",
        "metadata": collection.metadata.model_dump(),
        "chunks": [c.model_dump() for c in collection.chunks],
    }


@mcp.tool()
async def render_document_html(
    pdf_path: str,
    knowledge_graph_path: Optional[str] = None,
    include_toc: bool = True,
    include_search: bool = True,
) -> dict:
    """
    Render a PDF as a structured HTML document with page anchors (#page-N),
    heading hierarchy, table of contents, and optional entity annotations
    from a knowledge graph. Optimized for LLM live-reading and citation.

    Args:
        pdf_path: Absolute path to the PDF file.
        knowledge_graph_path: Optional path to knowledge_graph.json for entity annotations.
        include_toc: Whether to include a table of contents sidebar.
        include_search: Whether to include a sticky search bar.
    """
    from malimgraph.core.html_renderer import render_document_html as _render
    from malimgraph.core.pdf_reader import extract_text_from_pdf
    from malimgraph.schemas.entities import KnowledgeGraph

    if not os.path.exists(pdf_path):
        return {"error": f"PDF not found: {pdf_path}"}

    doc = extract_text_from_pdf(pdf_path)

    kg = None
    if knowledge_graph_path and os.path.exists(knowledge_graph_path):
        with open(knowledge_graph_path, "r", encoding="utf-8") as f:
            kg = KnowledgeGraph.model_validate(json.load(f))

    html_content = _render(
        doc, knowledge_graph=kg, include_toc=include_toc, include_search=include_search
    )

    return {
        "status": "success",
        "html": html_content,
        "page_count": doc.total_pages,
        "title": doc.title,
    }


@mcp.tool()
async def manage_graph_db(
    action: str,
    knowledge_graph_path: Optional[str] = None,
    target: str = "neo4j",
    connection_uri: Optional[str] = None,
    graph_name: str = "document_graph",
    cypher_query: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> dict:
    """
    Load, query, and manage knowledge graphs in Neo4j or PostgreSQL (Apache AGE).
    Run Cypher queries, view graph statistics, or manage graph instances.

    Args:
        action: One of — load | query | stats | drop | list_graphs.
        knowledge_graph_path: Path to knowledge_graph.json (required for action=load).
        target: Database target — neo4j | age.
        connection_uri: Connection URI (bolt://... for Neo4j, postgresql://... for AGE).
        graph_name: Graph name (for AGE).
        cypher_query: Cypher query string (required for action=query).
        user: Neo4j username (or use NEO4J_USER env var).
        password: Neo4j password (or use NEO4J_PASSWORD env var).
    """
    from malimgraph.core.db_client import get_client
    from malimgraph.schemas.entities import KnowledgeGraph

    valid_actions = {"load", "query", "stats", "drop", "list_graphs"}
    if action not in valid_actions:
        return {"error": f"Invalid action '{action}'. Valid: {sorted(valid_actions)}"}

    client_kwargs: dict = {"graph_name": graph_name}
    if connection_uri:
        client_kwargs["uri"] = connection_uri
    if user:
        client_kwargs["user"] = user
    if password:
        client_kwargs["password"] = password

    try:
        client = get_client(target, **client_kwargs)
    except (ImportError, Exception) as e:
        return {"error": str(e)}

    try:
        if action == "load":
            if not knowledge_graph_path or not os.path.exists(knowledge_graph_path):
                return {"error": "knowledge_graph_path required for action=load"}
            with open(knowledge_graph_path, "r", encoding="utf-8") as f:
                kg = KnowledgeGraph.model_validate(json.load(f))
            result = client.load_graph(kg)
            return {"status": "success", "action": "load", **result}

        elif action == "query":
            if not cypher_query:
                return {"error": "cypher_query required for action=query"}
            rows = client.query(cypher_query)
            return {"status": "success", "action": "query", "rows": rows, "count": len(rows)}

        elif action == "stats":
            stats = client.stats()
            return {"status": "success", "action": "stats", **stats}

        elif action == "drop":
            if hasattr(client, "drop_graph"):
                client.drop_graph()
                return {"status": "success", "action": "drop", "graph": graph_name}
            return {"error": "drop not supported for this target"}

        elif action == "list_graphs":
            if hasattr(client, "list_graphs"):
                graphs = client.list_graphs()
                return {"status": "success", "graphs": graphs}
            return {"error": "list_graphs not supported for this target"}

    finally:
        client.close()

    return {"error": "Unknown error"}


@mcp.tool()
async def embed_and_store_chunks(
    chunks_path: str,
    connection_uri: Optional[str] = None,
    table_name: str = "document_chunks",
    embedding_provider: str = "openai",
    embedding_model: Optional[str] = None,
    document_id: Optional[str] = None,
    skip_existing: bool = True,
) -> dict:
    """
    Generate embeddings for chunks from a chunks.json file and store them
    in a PostgreSQL database with the pgvector extension. Enables semantic
    search over document chunks via cosine similarity (HNSW index).

    Supports three embedding providers:
    - openai: text-embedding-3-small (1536-d), text-embedding-3-large (3072-d)
    - voyage: voyage-3-large (1024-d), voyage-3-lite (512-d)
    - local: any sentence-transformers model (runs on CPU, no API key needed)

    Args:
        chunks_path: Path to chunks.json produced by chunk_document.
        connection_uri: PostgreSQL URI (or use PGVECTOR_URI env var).
        table_name: Target table name (default: document_chunks).
        embedding_provider: openai | voyage | local.
        embedding_model: Model name override (uses provider default if omitted).
        document_id: Document identifier for namespacing (default: source filename).
        skip_existing: Skip chunks already in the table (default: True).
    """
    from malimgraph.core.embedder import EmbedderConfig
    from malimgraph.core.vector_client import PgVectorClient
    from malimgraph.schemas.chunks import ChunkCollection

    if not os.path.exists(chunks_path):
        return {"error": f"chunks.json not found: {chunks_path}"}

    uri = connection_uri or os.environ.get("PGVECTOR_URI", "")
    if not uri:
        return {"error": "connection_uri or PGVECTOR_URI environment variable required."}

    import json as _json

    with open(chunks_path, "r", encoding="utf-8") as f:
        collection = ChunkCollection.model_validate(_json.load(f))

    config = EmbedderConfig(
        provider=embedding_provider,
        model=embedding_model,
    )

    try:
        client = PgVectorClient(uri, table_name=table_name, embedder_config=config)
    except Exception as e:
        return {"error": f"Database connection failed: {e}"}

    try:
        result = await _run_in_executor(client.load_chunks, collection, document_id, skip_existing)
    finally:
        client.close()

    return {
        "status": "success",
        "table": table_name,
        "source_file": collection.metadata.source_file,
        "total_chunks": collection.metadata.total_chunks,
        "embedding_model": config.model,
        "embedding_dimension": config.dimension,
        **result,
    }


def _load_or_init_kg(output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    kg_path = os.path.join(output_dir, "knowledge_graph.json")
    if os.path.exists(kg_path):
        try:
            with open(kg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "metadata": {
            "source_file": "autonomous_orchestrator.json",
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "total_entities": 0,
            "total_relationships": 0,
            "entity_types": [],
            "relationship_types": []
        },
        "entities": [],
        "relationships": []
    }


def _save_kg(output_dir: str, kg_data: dict):
    kg_path = os.path.join(output_dir, "knowledge_graph.json")
    kg_data["metadata"]["total_entities"] = len(kg_data.get("entities", []))
    kg_data["metadata"]["total_relationships"] = len(kg_data.get("relationships", []))
    kg_data["metadata"]["entity_types"] = sorted(list({e["type"] for e in kg_data.get("entities", []) if "type" in e}))
    kg_data["metadata"]["relationship_types"] = sorted(list({r["type"] for r in kg_data.get("relationships", []) if "type" in r}))
    kg_data["metadata"]["extracted_at"] = datetime.now(timezone.utc).isoformat()
    with open(kg_path, "w", encoding="utf-8") as f:
        json.dump(kg_data, f, indent=2, ensure_ascii=False)


def _sync_to_db(kg_data: dict):
    from malimgraph.schemas.entities import KnowledgeGraph
    from malimgraph.core.db_client import get_client
    
    try:
        kg = KnowledgeGraph.model_validate(kg_data)
    except Exception as e:
        print(f"[Orchestrator] Schema validation failed during DB sync: {e}")
        return
    
    neo4j_uri = os.environ.get("NEO4J_URI")
    if neo4j_uri:
        try:
            client = get_client("neo4j")
            client.load_graph(kg)
            client.close()
        except Exception as e:
            print(f"[Orchestrator] Failed to sync to Neo4j: {e}")
            
    age_uri = os.environ.get("AGE_CONNECTION_URI")
    if age_uri:
        try:
            client = get_client("age")
            client.load_graph(kg)
            client.close()
        except Exception as e:
            print(f"[Orchestrator] Failed to sync to AGE: {e}")


@mcp.tool()
async def upsert_node(
    node_id: str,
    label: str,
    category: str,
    properties: dict,
    output_dir: str = "./output",
) -> dict:
    """
    Create or update a concept node in the knowledge base. Properties must include a concise, minimalist definition.

    Args:
        node_id: Unique stable identifier for the concept.
        label: Canonical human-readable name of the concept.
        category: Structural/taxonomic type of the node.
        properties: Additional properties. MUST include 'definition' or 'description'.
        output_dir: Directory where the knowledge_graph.json is stored.
    """
    if not properties or not (properties.get("definition") or properties.get("description")):
        return {"status": "error", "message": "Properties must include a concise, minimalist 'definition' or 'description'."}

    kg_data = _load_or_init_kg(output_dir)
    
    existing_idx = None
    for idx, entity in enumerate(kg_data["entities"]):
        if entity["id"] == node_id:
            existing_idx = idx
            break
            
    new_entity = {
        "id": node_id,
        "label": label,
        "type": category,
        "properties": properties,
        "extraction_method": "llm",
        "confidence": "high",
        "source_pages": [1],
        "source_text": properties.get("definition") or properties.get("description") or "",
        "citations": []
    }
    
    if existing_idx is not None:
        kg_data["entities"][existing_idx] = new_entity
        action = "updated"
    else:
        kg_data["entities"].append(new_entity)
        action = "created"
        
    _save_kg(output_dir, kg_data)
    _sync_to_db(kg_data)
    
    return {"status": "success", "action": action, "node_id": node_id}


@mcp.tool()
async def link_concepts(
    source_id: str,
    target_id: str,
    relation_type: str,
    context_justification: str,
    output_dir: str = "./output",
) -> dict:
    """
    Forge a directional edge between two concepts with context justification.

    Args:
        source_id: Source concept node ID.
        target_id: Target concept node ID.
        relation_type: UPPER_SNAKE_CASE relationship type (e.g. OPTIMIZES, LED_BY).
        context_justification: Explanation/quote justifying the link.
        output_dir: Directory where the knowledge_graph.json is stored.
    """
    kg_data = _load_or_init_kg(output_dir)
    
    entity_ids = {e["id"] for e in kg_data["entities"]}
    if source_id not in entity_ids:
        stub = {
            "id": source_id,
            "label": source_id.replace("_", " ").title(),
            "type": "Concept",
            "properties": {"description": "Auto-created concept stub"},
            "extraction_method": "llm",
            "confidence": "low",
            "source_pages": [],
            "source_text": "",
            "citations": []
        }
        kg_data["entities"].append(stub)
        
    if target_id not in entity_ids:
        stub = {
            "id": target_id,
            "label": target_id.replace("_", " ").title(),
            "type": "Concept",
            "properties": {"description": "Auto-created concept stub"},
            "extraction_method": "llm",
            "confidence": "low",
            "source_pages": [],
            "source_text": "",
            "citations": []
        }
        kg_data["entities"].append(stub)

    from malimgraph.utils.hashing import relationship_id
    rid = relationship_id(source_id, relation_type, target_id)
    
    existing_idx = None
    for idx, rel in enumerate(kg_data["relationships"]):
        if rel["id"] == rid:
            existing_idx = idx
            break
            
    new_rel = {
        "id": rid,
        "source": source_id,
        "target": target_id,
        "type": relation_type.upper().replace(" ", "_"),
        "properties": {"context_justification": context_justification},
        "extraction_method": "llm",
        "confidence": "high",
        "source_pages": [1],
        "source_text": context_justification,
        "citations": []
    }
    
    if existing_idx is not None:
        kg_data["relationships"][existing_idx] = new_rel
        action = "updated"
    else:
        kg_data["relationships"].append(new_rel)
        action = "created"
        
    _save_kg(output_dir, kg_data)
    _sync_to_db(kg_data)
    
    return {"status": "success", "action": action, "relationship_id": rid}


@mcp.tool()
async def classify_domain(
    category_id: str,
    description: str,
    output_dir: str = "./output",
) -> dict:
    """
    Register a macro-level category or taxonomic class to group dense sub-nodes.

    Args:
        category_id: Unique identifier/name for the category.
        description: Description of the category/domain.
        output_dir: Directory where the knowledge_graph.json is stored.
    """
    kg_data = _load_or_init_kg(output_dir)
    
    node_id = f"cat_{category_id.lower().replace(' ', '_')}"
    
    existing_idx = None
    for idx, entity in enumerate(kg_data["entities"]):
        if entity["id"] == node_id:
            existing_idx = idx
            break
            
    new_entity = {
        "id": node_id,
        "label": category_id,
        "type": "Category",
        "properties": {"description": description},
        "extraction_method": "llm",
        "confidence": "high",
        "source_pages": [1],
        "source_text": description,
        "citations": []
    }
    
    if existing_idx is not None:
        kg_data["entities"][existing_idx] = new_entity
        action = "updated"
    else:
        kg_data["entities"].append(new_entity)
        action = "created"
        
    _save_kg(output_dir, kg_data)
    _sync_to_db(kg_data)
    
    return {"status": "success", "action": action, "category_id": category_id, "node_id": node_id}


async def _run_llm(doc, entity_types):
    """Run LLM extraction in thread pool to avoid blocking the event loop."""
    import asyncio

    from malimgraph.core.llm_extractor import extract_by_llm

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, extract_by_llm, doc, entity_types)


async def _run_in_executor(fn, *args):
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn, *args)


def _chunks_to_markdown(collection) -> str:
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
    return "\n".join(lines)


def _chunks_to_txt_map(collection) -> dict[str, str]:
    files = {}
    for chunk in collection.chunks:
        filename = f"{chunk.chunk_id}.txt"
        frontmatter = (
            f"---\nchunk_id: {chunk.chunk_id}\npages: {chunk.source_pages}\n"
            f"tokens: {chunk.token_count}\nheading_context: {chunk.heading_context}\n---\n\n"
        )
        files[filename] = frontmatter + chunk.text
    return files


def run_server(transport: str = "stdio", port: int = 8080):
    if transport == "http":
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
