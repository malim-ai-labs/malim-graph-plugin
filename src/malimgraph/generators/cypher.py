"""Generate Cypher import scripts from a KnowledgeGraph."""

from __future__ import annotations

from typing import Any

from malimgraph.schemas.entities import KnowledgeGraph
from malimgraph.utils.text import escape_cypher_string


def generate_cypher(kg: KnowledgeGraph) -> str:
    """
    Generate a complete Cypher script (for Neo4j / Memgraph) that creates
    all nodes and relationships, with provenance as queryable properties.
    """
    lines: list[str] = []

    lines.append("// MalimGraph — Generated Cypher Import Script")
    lines.append(f"// Source: {kg.metadata.source_file}")
    lines.append(f"// Extracted: {kg.metadata.extracted_at}")
    lines.append(f"// Entities: {kg.metadata.total_entities}")
    lines.append(f"// Relationships: {kg.metadata.total_relationships}")
    lines.append("")

    # Create uniqueness constraints
    entity_types = kg.metadata.entity_types
    lines.append("// ── Constraints ─────────────────────────────────────────────────────────")
    for etype in entity_types:
        lines.append(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{etype}) REQUIRE n.id IS UNIQUE;")
    lines.append("")

    # Create entity nodes
    lines.append("// ── Nodes ────────────────────────────────────────────────────────────────")
    for entity in kg.entities:
        props = _entity_props(entity)
        props_cypher = _dict_to_cypher(props)
        lines.append(
            f"MERGE (n:{entity.type} {{id: '{escape_cypher_string(entity.id)}'}})"
            f" SET n += {props_cypher};"
        )
    lines.append("")

    # Create relationships
    lines.append("// ── Relationships ────────────────────────────────────────────────────────")
    for rel in kg.relationships:
        props = _relationship_props(rel)
        props_cypher = _dict_to_cypher(props)
        lines.append(
            f"MATCH (a {{id: '{escape_cypher_string(rel.source)}'}}), "
            f"(b {{id: '{escape_cypher_string(rel.target)}'}})"
        )
        lines.append(
            f"MERGE (a)-[r:{rel.type} {{id: '{escape_cypher_string(rel.id)}'}}]->(b)"
            f" SET r += {props_cypher};"
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


def _dict_to_cypher(d: dict[str, Any]) -> str:
    """Serialize a Python dict to a Cypher property map literal."""
    parts = []
    for key, value in d.items():
        if isinstance(value, str):
            escaped = escape_cypher_string(value)
            parts.append(f"{key}: '{escaped}'")
        elif isinstance(value, bool):
            parts.append(f"{key}: {str(value).lower()}")
        elif isinstance(value, (int, float)):
            parts.append(f"{key}: {value}")
        elif isinstance(value, list):
            # Cypher list literal
            items = ", ".join(
                f"'{escape_cypher_string(str(i))}'" if isinstance(i, str) else str(i) for i in value
            )
            parts.append(f"{key}: [{items}]")
        else:
            parts.append(f"{key}: '{escape_cypher_string(str(value))}'")
    return "{" + ", ".join(parts) + "}"
