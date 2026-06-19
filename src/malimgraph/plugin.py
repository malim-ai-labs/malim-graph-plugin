"""
MalimGraph Claude Plugin — MCP server for Claude Code / Claude Desktop.

No ANTHROPIC_API_KEY required. Claude itself does entity extraction.

Workflow:
  1. Claude calls read_pdf(pdf_path)
  2. Claude analyzes the returned text and identifies entities + relationships
  3. Claude calls save_knowledge_graph(entities, relationships, ...)
  4. Optionally: chunk_document, render_document_html, manage_graph_db, embed_and_store_chunks
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

mcp = FastMCP(
    "MalimGraph",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    instructions=(
        "MalimGraph converts PDF documents into structured knowledge graphs. "
        "Read CLAUDE.md in the project root for full workflow documentation. "
        "Core workflow: (1) call read_pdf → get page text + rule entities, "
        "(2) analyze text yourself → identify entities + relationships with verbatim source_text, "
        "(3) call save_knowledge_graph → build and save the graph. "
        "No ANTHROPIC_API_KEY needed — you are the intelligence. "
        "This server also functions as an Autonomous Knowledge Core & Self-Evolving Graph Orchestrator. "
        "You can use upsert_node, link_concepts, and classify_domain to dynamically expand and maintain "
        "the knowledge base on every query using ReAct methodology."
    ),
)


@mcp.tool()
async def read_pdf(pdf_path: str) -> dict:
    """
    Read a PDF document and return its full text, structure, and rule-extracted
    entities (dates, amounts, emails, legal references, section numbers).

    After calling this tool, analyze the returned page_text to identify
    semantic entities (Organizations, People, Locations, Concepts, Regulations,
    Products, Roles, Events) and relationships between them. Then call
    save_knowledge_graph with your extracted entities and relationships.

    Every entity you identify must include:
    - source_text: a verbatim quote (≤200 chars) from the document proving it exists
    - source_pages: page numbers where you found it
    - confidence: "high" (explicit), "medium" (implied), "low" (uncertain)

    Args:
        pdf_path: Absolute or relative path to the PDF file.
    """
    from malimgraph.core.pdf_reader import extract_text_from_pdf
    from malimgraph.core.rule_extractor import extract_by_rules

    if not os.path.exists(pdf_path):
        return {"error": f"PDF not found: {pdf_path}"}

    doc = extract_text_from_pdf(pdf_path)
    rule_entities = extract_by_rules(doc)

    pages_out = []
    for page in doc.pages:
        pages_out.append(
            {
                "page": page.page_number,
                "headings": page.headings,
                "text": page.text,
                "has_table": page.has_table,
                "is_scanned": page.is_scanned,
            }
        )

    return {
        "source_file": os.path.basename(doc.source_file),
        "total_pages": doc.total_pages,
        "title": doc.title,
        "pages": pages_out,
        "rule_extracted_entities": [
            {
                "id": e.id,
                "label": e.label,
                "type": e.type,
                "source_pages": e.source_pages,
                "source_text": e.source_text,
                "confidence": e.confidence.value,
            }
            for e in rule_entities
        ],
        "instructions": (
            "Analyze the pages above. Extract named entities (Organizations, People, "
            "Locations, Concepts, Regulations, Dates, MonetaryAmounts, Products, Roles, Events) "
            "and relationships between them. Include the rule_extracted_entities above in your "
            "results — they are already validated. For each additional entity and relationship, "
            "include a verbatim source_text quote from the document. "
            "Then call save_knowledge_graph with your complete entity and relationship lists."
        ),
    }


@mcp.tool()
async def save_knowledge_graph(
    source_file: str,
    entities: list[dict],
    relationships: list[dict],
    output_dir: str = "./output",
    output_format: str = "json",
    graph_name: str = "document_graph",
) -> dict:
    """
    Build and save a knowledge graph from entities and relationships you extracted.
    Call this after analyzing the text from read_pdf.

    Entity format:
    {
      "label": "Malim AI Labs",
      "type": "Organization",
      "source_text": "verbatim quote proving this entity exists",
      "source_pages": [1, 2],
      "confidence": "high",
      "properties": {}
    }

    Relationship format:
    {
      "source_label": "Malim AI Labs",
      "source_type": "Organization",
      "target_label": "Ahmad Fadzillah",
      "target_type": "Person",
      "type": "LED_BY",
      "source_text": "verbatim quote proving this relationship",
      "source_pages": [1],
      "confidence": "high"
    }

    Args:
        source_file: Name of the source PDF file.
        entities: List of entity dicts you extracted.
        relationships: List of relationship dicts you extracted.
        output_dir: Directory to write output files.
        output_format: json | cypher | age_sql | okf | all.
        graph_name: Graph name for AGE SQL output.
    """
    from malimgraph.generators.age_sql import generate_age_sql
    from malimgraph.generators.cypher import generate_cypher
    from malimgraph.generators.okf import write_okf_bundle
    from malimgraph.schemas.entities import (
        Citation,
        Confidence,
        Entity,
        ExtractionMethod,
        GraphMetadata,
        KnowledgeGraph,
        Relationship,
    )
    from malimgraph.utils.hashing import entity_id, relationship_id

    os.makedirs(output_dir, exist_ok=True)

    # Build Entity objects
    entity_map: dict[str, Entity] = {}
    for e_raw in entities:
        label = str(e_raw.get("label", "")).strip()
        etype = str(e_raw.get("type", "Unknown")).strip()
        if not label:
            continue

        # Respect pre-existing IDs (from rule extractor) or generate stable ones
        eid = e_raw.get("id") or entity_id(etype, label)
        conf_str = e_raw.get("confidence", "medium")
        confidence = (
            Confidence(conf_str) if conf_str in Confidence._value2member_map_ else Confidence.MEDIUM
        )
        pages = e_raw.get("source_pages", [])
        source_text = e_raw.get("source_text", "")[:500]

        entity_map[eid] = Entity(
            id=eid,
            label=label,
            type=etype,
            properties=e_raw.get("properties", {}),
            extraction_method=ExtractionMethod.LLM,
            confidence=confidence,
            source_pages=pages,
            source_text=source_text,
            source_chunk_id="claude",
            source_chunk_ids=["claude"],
            citations=[
                Citation(
                    text=source_text,
                    pages=pages,
                    chunk_id="claude",
                    extraction_method=ExtractionMethod.LLM,
                )
            ]
            if source_text
            else [],
        )

    # Build Relationship objects
    rel_list: list[Relationship] = []

    for r_raw in relationships:
        src_label = str(r_raw.get("source_label", "")).strip()
        src_type = str(r_raw.get("source_type", "Unknown")).strip()
        tgt_label = str(r_raw.get("target_label", "")).strip()
        tgt_type = str(r_raw.get("target_type", "Unknown")).strip()
        rel_type = str(r_raw.get("type", "RELATED_TO")).upper().replace(" ", "_")

        if not src_label or not tgt_label:
            continue

        src_id = entity_id(src_type, src_label)
        tgt_id = entity_id(tgt_type, tgt_label)
        rid = relationship_id(src_id, rel_type, tgt_id)
        pages = r_raw.get("source_pages", [])
        source_text = r_raw.get("source_text", "")[:500]
        conf_str = r_raw.get("confidence", "medium")
        confidence = (
            Confidence(conf_str) if conf_str in Confidence._value2member_map_ else Confidence.MEDIUM
        )

        # Auto-create stub entities if Claude referenced labels not already in the map
        for eid, lbl, typ in [(src_id, src_label, src_type), (tgt_id, tgt_label, tgt_type)]:
            if eid not in entity_map:
                entity_map[eid] = Entity(
                    id=eid,
                    label=lbl,
                    type=typ,
                    extraction_method=ExtractionMethod.LLM,
                    confidence=Confidence.LOW,
                    source_pages=pages,
                    source_chunk_id="claude",
                    source_chunk_ids=["claude"],
                )

        rel_list.append(
            Relationship(
                id=rid,
                source=src_id,
                target=tgt_id,
                type=rel_type,
                extraction_method=ExtractionMethod.LLM,
                confidence=confidence,
                source_pages=pages,
                source_text=source_text,
                source_chunk_id="claude",
                citations=[
                    Citation(
                        text=source_text,
                        pages=pages,
                        chunk_id="claude",
                        extraction_method=ExtractionMethod.LLM,
                    )
                ]
                if source_text
                else [],
            )
        )

    entity_list = list(entity_map.values())
    entity_types = sorted({e.type for e in entity_list})
    relationship_types = sorted({r.type for r in rel_list})

    kg = KnowledgeGraph(
        metadata=GraphMetadata(
            source_file=source_file,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            total_entities=len(entity_list),
            total_relationships=len(rel_list),
            entity_types=entity_types,
            relationship_types=relationship_types,
            extraction_config={"graph_name": graph_name, "extraction_mode": "claude-native"},
        ),
        entities=entity_list,
        relationships=rel_list,
    )

    saved_files = []

    kg_path = os.path.join(output_dir, "knowledge_graph.json")
    with open(kg_path, "w", encoding="utf-8") as f:
        json.dump(kg.model_dump(), f, indent=2, ensure_ascii=False)
    saved_files.append(kg_path)

    if output_format in ("cypher", "all"):
        cypher_path = os.path.join(output_dir, "knowledge_graph.cypher")
        with open(cypher_path, "w", encoding="utf-8") as f:
            f.write(generate_cypher(kg))
        saved_files.append(cypher_path)

    if output_format in ("age_sql", "all"):
        sql_path = os.path.join(output_dir, "knowledge_graph.sql")
        with open(sql_path, "w", encoding="utf-8") as f:
            f.write(generate_age_sql(kg, graph_name=graph_name))
        saved_files.append(sql_path)

    if output_format in ("okf", "all"):
        saved_files.extend(write_okf_bundle(kg, output_dir))

    return {
        "status": "success",
        "saved_files": saved_files,
        "metadata": {
            "total_entities": kg.metadata.total_entities,
            "total_relationships": kg.metadata.total_relationships,
            "entity_types": entity_types,
            "relationship_types": relationship_types,
        },
    }


@mcp.tool()
async def chunk_document(
    pdf_path: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    output_dir: str = "./chunks",
    output_format: str = "json",
) -> dict:
    """
    Split a PDF into overlapping text chunks for embedding / RAG pipelines.
    Each chunk includes page references and heading context.

    Args:
        pdf_path: Path to the PDF file.
        chunk_size: Target tokens per chunk (default: 512).
        chunk_overlap: Overlap tokens between chunks (default: 64).
        output_dir: Directory to write chunk files.
        output_format: json | txt | md.
    """
    from malimgraph.core.chunker import chunk_document as _chunk
    from malimgraph.core.pdf_reader import extract_text_from_pdf

    if not os.path.exists(pdf_path):
        return {"error": f"PDF not found: {pdf_path}"}

    os.makedirs(output_dir, exist_ok=True)
    doc = extract_text_from_pdf(pdf_path)
    collection = _chunk(doc, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    if output_format == "json":
        out_path = os.path.join(output_dir, "chunks.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(collection.model_dump(), f, indent=2, ensure_ascii=False)
        return {
            "status": "success",
            "file": out_path,
            "total_chunks": collection.metadata.total_chunks,
            "total_tokens": collection.metadata.total_tokens,
        }

    if output_format == "md":
        lines = [f"# Chunks — {collection.metadata.source_file}\n"]
        for chunk in collection.chunks:
            lines.append(f"## Chunk {chunk.position.index + 1} of {chunk.position.total}")
            lines.append(f"**Pages:** {chunk.source_pages} | **Tokens:** {chunk.token_count}")
            if chunk.heading_context:
                lines.append(f"**Context:** {' > '.join(chunk.heading_context)}")
            lines.append(f"\n{chunk.text}\n\n---\n")
        out_path = os.path.join(output_dir, "chunks.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return {
            "status": "success",
            "file": out_path,
            "total_chunks": collection.metadata.total_chunks,
        }

    # txt — one file per chunk
    for chunk in collection.chunks:
        fname = os.path.join(output_dir, f"{chunk.chunk_id}.txt")
        frontmatter = f"---\nchunk_id: {chunk.chunk_id}\npages: {chunk.source_pages}\ntokens: {chunk.token_count}\nheading_context: {chunk.heading_context}\n---\n\n"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(frontmatter + chunk.text)
    return {
        "status": "success",
        "directory": output_dir,
        "total_chunks": collection.metadata.total_chunks,
    }


@mcp.tool()
async def render_document_html(
    pdf_path: str,
    knowledge_graph_path: Optional[str] = None,
    output_path: str = "document.html",
    include_toc: bool = True,
    include_search: bool = True,
) -> dict:
    """
    Render a PDF as structured HTML with page anchors (#page-N), table of
    contents, entity annotations, and full-text search.

    Args:
        pdf_path: Path to the PDF file.
        knowledge_graph_path: Optional knowledge_graph.json for entity annotations.
        output_path: Output HTML file path.
        include_toc: Include table of contents sidebar.
        include_search: Include sticky search bar.
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
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return {
        "status": "success",
        "file": output_path,
        "page_count": doc.total_pages,
        "size_bytes": len(html_content),
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

    Actions: load | query | stats | drop | list_graphs

    Args:
        action: load | query | stats | drop | list_graphs
        knowledge_graph_path: Path to knowledge_graph.json (required for load).
        target: neo4j | age
        connection_uri: bolt://... for Neo4j, postgresql://... for AGE.
        graph_name: Graph name (for AGE).
        cypher_query: Cypher string (required for query).
        user: Neo4j username (or NEO4J_USER env var).
        password: Neo4j password (or NEO4J_PASSWORD env var).
    """
    from malimgraph.core.db_client import get_client
    from malimgraph.schemas.entities import KnowledgeGraph

    if action not in {"load", "query", "stats", "drop", "list_graphs"}:
        return {"error": f"Invalid action '{action}'. Use: load, query, stats, drop, list_graphs"}

    kwargs: dict = {"graph_name": graph_name}
    if connection_uri:
        kwargs["uri"] = connection_uri
    if user:
        kwargs["user"] = user
    if password:
        kwargs["password"] = password

    try:
        client = get_client(target, **kwargs)
    except Exception as e:
        return {"error": str(e)}

    try:
        if action == "load":
            if not knowledge_graph_path or not os.path.exists(knowledge_graph_path):
                return {"error": "knowledge_graph_path required for load"}
            with open(knowledge_graph_path, "r", encoding="utf-8") as f:
                kg = KnowledgeGraph.model_validate(json.load(f))
            return {"status": "success", **client.load_graph(kg)}
        elif action == "query":
            if not cypher_query:
                return {"error": "cypher_query required for query"}
            rows = client.query(cypher_query)
            return {"status": "success", "rows": rows, "count": len(rows)}
        elif action == "stats":
            return {"status": "success", **client.stats()}
        elif action == "drop":
            if hasattr(client, "drop_graph"):
                client.drop_graph()
                return {"status": "success", "dropped": graph_name}
            return {"error": "drop not supported for neo4j"}
        elif action == "list_graphs":
            if hasattr(client, "list_graphs"):
                return {"status": "success", "graphs": client.list_graphs()}
            return {"error": "list_graphs not supported for neo4j"}
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
    Generate embeddings for chunks and store in PostgreSQL with pgvector.

    Supports: openai (OPENAI_API_KEY), voyage (VOYAGE_API_KEY), local (no key).

    Args:
        chunks_path: Path to chunks.json from chunk_document.
        connection_uri: PostgreSQL URI (or PGVECTOR_URI env var).
        table_name: Target table name.
        embedding_provider: openai | voyage | local.
        embedding_model: Model override (uses provider default if omitted).
        document_id: Document namespace (default: source filename).
        skip_existing: Skip chunks already in the table.
    """
    from malimgraph.core.embedder import EmbedderConfig
    from malimgraph.core.vector_client import PgVectorClient
    from malimgraph.schemas.chunks import ChunkCollection

    if not os.path.exists(chunks_path):
        return {"error": f"chunks.json not found: {chunks_path}"}

    uri = connection_uri or os.environ.get("PGVECTOR_URI", "")
    if not uri:
        return {"error": "connection_uri or PGVECTOR_URI environment variable required."}

    with open(chunks_path, "r", encoding="utf-8") as f:
        collection = ChunkCollection.model_validate(json.load(f))

    config = EmbedderConfig(provider=embedding_provider, model=embedding_model)

    try:
        client = PgVectorClient(uri, table_name=table_name, embedder_config=config)
    except Exception as e:
        return {"error": f"Database connection failed: {e}"}

    try:
        import asyncio

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, client.load_chunks, collection, document_id, skip_existing
        )
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
            "relationship_types": [],
        },
        "entities": [],
        "relationships": [],
    }


def _save_kg(output_dir: str, kg_data: dict):
    kg_path = os.path.join(output_dir, "knowledge_graph.json")
    kg_data["metadata"]["total_entities"] = len(kg_data.get("entities", []))
    kg_data["metadata"]["total_relationships"] = len(kg_data.get("relationships", []))
    kg_data["metadata"]["entity_types"] = sorted(
        list({e["type"] for e in kg_data.get("entities", []) if "type" in e})
    )
    kg_data["metadata"]["relationship_types"] = sorted(
        list({r["type"] for r in kg_data.get("relationships", []) if "type" in r})
    )
    kg_data["metadata"]["extracted_at"] = datetime.now(timezone.utc).isoformat()
    with open(kg_path, "w", encoding="utf-8") as f:
        json.dump(kg_data, f, indent=2, ensure_ascii=False)


def _sync_to_db(kg_data: dict):
    from malimgraph.core.db_client import get_client
    from malimgraph.schemas.entities import KnowledgeGraph

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
        return {
            "status": "error",
            "message": "Properties must include a concise, minimalist 'definition' or 'description'.",
        }

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
        "citations": [],
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
            "citations": [],
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
            "citations": [],
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
        "citations": [],
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
        "citations": [],
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


@mcp.tool()
async def list_workflows() -> dict:
    """
    List all available MalimGraph workflows, their trigger phrases, and tool sequences.
    Call this if you are unsure which tools to use for a given task.
    """
    return {
        "plugin": "malimgraph",
        "version": "0.2.1",
        "no_api_key_required": True,
        "install": "pip install malimgraph && claude mcp add malimgraph -- malimgraph-plugin",
        "workflows": [
            {
                "name": "self-evolving-orchestrator",
                "description": "Maintain, expand, and self-correct a dynamic network of concepts on every API call.",
                "triggers": [
                    "orchestrator",
                    "self-evolving",
                    "knowledge core",
                    "upsert node",
                    "link concepts",
                    "classify domain",
                ],
                "steps": [
                    "upsert_node",
                    "link_concepts",
                    "classify_domain",
                ],
                "outputs": [
                    "knowledge_graph.json",
                ],
            },
            {
                "name": "pdf-to-graph",
                "description": "Extract entities and relationships from a PDF into a knowledge graph.",
                "triggers": [
                    "knowledge graph",
                    "extract entities",
                    "PDF to graph",
                    "PDF to Cypher",
                    "PDF to Neo4j",
                ],
                "steps": [
                    "read_pdf",
                    "(you extract entities+relationships)",
                    "save_knowledge_graph",
                ],
                "outputs": [
                    "knowledge_graph.json",
                    "knowledge_graph.cypher",
                    "knowledge_graph.sql",
                ],
            },
            {
                "name": "pdf-to-rag",
                "description": "Chunk a PDF and store embeddings in pgvector for semantic search.",
                "triggers": ["chunk for RAG", "prepare embeddings", "vector search", "pgvector"],
                "steps": ["chunk_document", "embed_and_store_chunks"],
                "outputs": ["chunks.json", "pgvector table"],
                "requires_env": ["PGVECTOR_URI", "OPENAI_API_KEY or VOYAGE_API_KEY"],
            },
            {
                "name": "full-pipeline",
                "description": "Complete end-to-end PDF processing: graph + chunks + embeddings + HTML.",
                "triggers": ["full pipeline", "extract and embed", "complete workflow"],
                "steps": [
                    "read_pdf",
                    "(you extract entities+relationships)",
                    "save_knowledge_graph",
                    "chunk_document",
                    "embed_and_store_chunks",
                    "render_document_html",
                ],
                "outputs": [
                    "knowledge_graph.json",
                    ".cypher",
                    ".sql",
                    "chunks.json",
                    "document.html",
                ],
            },
            {
                "name": "graph-query",
                "description": "Load, query, and manage graphs in Neo4j or Apache AGE.",
                "triggers": [
                    "load into Neo4j",
                    "Cypher query",
                    "graph database",
                    "graph statistics",
                ],
                "steps": ["manage_graph_db"],
                "actions": ["load", "query", "stats", "drop", "list_graphs"],
            },
            {
                "name": "document-html",
                "description": "Render PDF as structured HTML with page anchors and entity annotations.",
                "triggers": ["render HTML", "convert PDF to HTML", "browsable document"],
                "steps": ["render_document_html"],
                "outputs": ["document.html"],
            },
        ],
    }


def run():
    import argparse

    parser = argparse.ArgumentParser(description="MalimGraph MCP Plugin Server")
    parser.add_argument(
        "--transport",
        default=os.environ.get("MALIMGRAPH_TRANSPORT", "stdio"),
        choices=["stdio", "http"],
        help="Transport mode: stdio (local) or http (hosted)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 8080)),
        help="Port for HTTP transport (default: $PORT or 8080)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "0.0.0.0"),
        help="Host for HTTP transport (default: 0.0.0.0)",
    )
    args = parser.parse_args()

    if args.transport == "http":
        print(f"MalimGraph MCP server starting on http://{args.host}:{args.port}")
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
