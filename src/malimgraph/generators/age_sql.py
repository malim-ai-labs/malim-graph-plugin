"""Generate Apache AGE SQL import scripts from a KnowledgeGraph."""

from __future__ import annotations

import json
from typing import Any

from malimgraph.schemas.entities import KnowledgeGraph
from malimgraph.utils.text import escape_cypher_string


def generate_age_sql(kg: KnowledgeGraph, graph_name: str = "document_graph") -> str:
    """
    Generate a PostgreSQL + Apache AGE SQL script that creates a graph,
    loads all nodes and edges, with provenance as properties.
    """
    lines: list[str] = []

    lines.append("-- MalimGraph — Generated Apache AGE SQL Import Script")
    lines.append(f"-- Source: {kg.metadata.source_file}")
    lines.append(f"-- Extracted: {kg.metadata.extracted_at}")
    lines.append(f"-- Graph: {graph_name}")
    lines.append("")

    # Setup
    lines.append("-- ── Setup ───────────────────────────────────────────────────────────────")
    lines.append("CREATE EXTENSION IF NOT EXISTS age;")
    lines.append("LOAD 'age';")
    lines.append("SET search_path = ag_catalog, '$user', public;")
    lines.append("")

    # Create graph
    lines.append("-- ── Create Graph ────────────────────────────────────────────────────────")
    lines.append(f"SELECT create_graph('{graph_name}');")
    lines.append("")

    # Insert nodes
    lines.append("-- ── Nodes ────────────────────────────────────────────────────────────────")
    for entity in kg.entities:
        props = _entity_props(entity)
        props_json = json.dumps(props, ensure_ascii=False)
        lines.append(
            f"SELECT * FROM cypher('{graph_name}', $$"
            f"  MERGE (n:{entity.type} {{id: '{escape_cypher_string(entity.id)}'}}) "
            f"  SET n += {props_json} "
            f"  RETURN n"
            f"$$) AS (n agtype);"
        )
    lines.append("")

    # Insert edges
    lines.append("-- ── Relationships ────────────────────────────────────────────────────────")
    for rel in kg.relationships:
        props = _relationship_props(rel)
        props_json = json.dumps(props, ensure_ascii=False)
        lines.append(
            f"SELECT * FROM cypher('{graph_name}', $$"
            f"  MATCH (a {{id: '{escape_cypher_string(rel.source)}'}}), "
            f"  (b {{id: '{escape_cypher_string(rel.target)}'}}) "
            f"  MERGE (a)-[r:{rel.type} {{id: '{escape_cypher_string(rel.id)}'}}]->(b) "
            f"  SET r += {props_json} "
            f"  RETURN r"
            f"$$) AS (r agtype);"
        )
    lines.append("")

    return "\n".join(lines)


def _entity_props(entity) -> dict[str, Any]:
    return {
        "id": entity.id,
        "label": entity.label,
        "type": entity.type,
        "confidence": entity.confidence.value,
        "extraction_method": entity.extraction_method.value,
        "source_pages": entity.source_pages,
        "source_text": entity.source_text[:500],
        "source_chunk_id": entity.source_chunk_id,
        "citation_count": len(entity.citations),
        "citation_texts": [c.text[:200] for c in entity.citations[:5]],
        **{k: v for k, v in entity.properties.items() if isinstance(v, (str, int, float, bool))},
    }


def _relationship_props(rel) -> dict[str, Any]:
    return {
        "id": rel.id,
        "type": rel.type,
        "confidence": rel.confidence.value,
        "extraction_method": rel.extraction_method.value,
        "source_pages": rel.source_pages,
        "source_text": rel.source_text[:500],
        "source_chunk_id": rel.source_chunk_id,
        "citation_count": len(rel.citations),
    }
