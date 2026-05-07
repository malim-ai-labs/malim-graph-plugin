"""Merge rule-based and LLM-based extractions into a unified knowledge graph."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from malimgraph.core.pdf_reader import DocumentContent
from malimgraph.schemas.entities import (
    ChunkIndex,
    Confidence,
    Entity,
    ExtractionMethod,
    GraphMetadata,
    KnowledgeGraph,
    Relationship,
)
from malimgraph.utils.hashing import entity_id


def build_knowledge_graph(
    doc: DocumentContent,
    rule_entities: list[Entity],
    llm_entities: list[Entity],
    llm_relationships: list[Relationship],
    graph_name: str = "document_graph",
) -> KnowledgeGraph:
    """
    Merge rule-extracted and LLM-extracted entities, dedup, accumulate citations,
    and return a fully provenance-annotated KnowledgeGraph.
    """
    merged_entities = _merge_entities(rule_entities, llm_entities)
    validated_relationships = _validate_relationships(llm_relationships, merged_entities)
    chunk_index = _build_chunk_index(merged_entities, validated_relationships)

    entity_types = sorted({e.type for e in merged_entities})
    relationship_types = sorted({r.type for r in validated_relationships})

    metadata = GraphMetadata(
        source_file=os.path.basename(doc.source_file),
        extracted_at=datetime.now(timezone.utc).isoformat(),
        total_entities=len(merged_entities),
        total_relationships=len(validated_relationships),
        entity_types=entity_types,
        relationship_types=relationship_types,
        extraction_config={
            "graph_name": graph_name,
            "total_pages": doc.total_pages,
            "document_title": doc.title,
        },
        chunk_index=chunk_index,
    )

    return KnowledgeGraph(
        metadata=metadata,
        entities=merged_entities,
        relationships=validated_relationships,
    )


def _merge_entities(rule_entities: list[Entity], llm_entities: list[Entity]) -> list[Entity]:
    """
    Merge strategy:
    - LLM wins on semantics (type, properties, description)
    - Rule wins on structured data (dates, amounts, legal refs)
    - When both find the same entity → method=HYBRID, confidence=HIGH
    - Citations from both sources accumulate
    """
    merged: dict[str, Entity] = {}

    # Index rule entities first
    for entity in rule_entities:
        merged[entity.id] = entity

    # Merge/override with LLM entities
    for llm_entity in llm_entities:
        if llm_entity.id in merged:
            rule_entity = merged[llm_entity.id]

            # Accumulate pages (union)
            all_pages = sorted(set(rule_entity.source_pages + llm_entity.source_pages))

            # Accumulate citations
            all_citations = rule_entity.citations + llm_entity.citations

            # Accumulate chunk IDs
            all_chunk_ids = list(set(rule_entity.source_chunk_ids + llm_entity.source_chunk_ids))

            # Rule-extracted types override LLM for structured data types
            structured_types = {"Date", "MonetaryAmount", "Percentage", "Email", "URL",
                                "PhoneNumber", "IdentificationNumber", "CompanyRegistration"}
            if rule_entity.type in structured_types:
                winning_type = rule_entity.type
            else:
                winning_type = llm_entity.type  # LLM wins on semantic types

            # Merge properties: LLM properties over rule properties
            merged_props = {**rule_entity.properties, **llm_entity.properties}

            merged[llm_entity.id] = Entity(
                id=llm_entity.id,
                label=llm_entity.label,  # LLM gives better canonical form
                type=winning_type,
                properties=merged_props,
                extraction_method=ExtractionMethod.HYBRID,
                confidence=Confidence.HIGH,
                source_pages=all_pages,
                source_text=llm_entity.source_text or rule_entity.source_text,
                source_chunk_id=llm_entity.source_chunk_id or rule_entity.source_chunk_id,
                source_chunk_ids=all_chunk_ids,
                citations=all_citations,
            )
        else:
            merged[llm_entity.id] = llm_entity

    return list(merged.values())


def _validate_relationships(
    relationships: list[Relationship],
    entities: list[Entity],
) -> list[Relationship]:
    """Remove relationships referencing non-existent entities."""
    entity_ids = {e.id for e in entities}
    valid = [r for r in relationships if r.source in entity_ids and r.target in entity_ids]

    if len(valid) < len(relationships):
        dropped = len(relationships) - len(valid)
        print(f"  [Builder] Dropped {dropped} relationships with unresolved entity references.")

    return valid


def _build_chunk_index(
    entities: list[Entity],
    relationships: list[Relationship],
) -> dict[str, ChunkIndex]:
    """Build a chunk_id → pages index from all provenance data."""
    chunk_pages: dict[str, set[int]] = {}

    for entity in entities:
        for citation in entity.citations:
            cid = citation.chunk_id
            if cid:
                chunk_pages.setdefault(cid, set()).update(citation.pages)

    for rel in relationships:
        for citation in rel.citations:
            cid = citation.chunk_id
            if cid:
                chunk_pages.setdefault(cid, set()).update(citation.pages)

    return {
        cid: ChunkIndex(chunk_id=cid, pages=sorted(pages))
        for cid, pages in chunk_pages.items()
    }
