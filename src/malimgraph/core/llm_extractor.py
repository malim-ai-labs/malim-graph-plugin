"""LLM-based entity and relationship extraction via Anthropic API."""

from __future__ import annotations

import json
import os
from typing import Optional

import anthropic

from malimgraph.core.pdf_reader import DocumentContent
from malimgraph.schemas.entities import (
    Citation,
    Confidence,
    Entity,
    ExtractionMethod,
    Relationship,
)
from malimgraph.utils.hashing import entity_id, relationship_id
from malimgraph.utils.text import estimate_tokens

DEFAULT_MODEL = "claude-opus-4-7"
CHUNK_TOKEN_LIMIT = 3000  # chars per LLM chunk to stay within context


EXTRACTION_SYSTEM_PROMPT = """You are an expert knowledge graph extraction system.

Given a passage from a document, extract:
1. ENTITIES — named people, organizations, locations, concepts, regulations, dates, amounts, products, roles, or any other meaningful noun phrases.
2. RELATIONSHIPS — directional connections between entities.

REQUIREMENTS:
- Every entity and relationship MUST include a "source_text" field: a verbatim quote (≤200 chars) from the passage that proves this entity/relationship exists.
- Entity IDs must follow the pattern: e_ + 8 hex chars.
- Relationship types must be UPPER_SNAKE_CASE (e.g., SIGNED_BY, REGULATES, LOCATED_IN).
- Confidence: "high" = explicitly stated, "medium" = clearly implied, "low" = uncertain.
- Do NOT invent relationships not supported by the text.

Respond ONLY with valid JSON matching this schema:
{
  "entities": [
    {
      "label": "string",
      "type": "string",
      "properties": {},
      "confidence": "high|medium|low",
      "source_text": "verbatim quote from the passage"
    }
  ],
  "relationships": [
    {
      "source_label": "string",
      "source_type": "string",
      "target_label": "string",
      "target_type": "string",
      "type": "UPPER_SNAKE_CASE",
      "properties": {},
      "confidence": "high|medium|low",
      "source_text": "verbatim quote proving this relationship"
    }
  ]
}"""


def extract_by_llm(
    doc: DocumentContent,
    entity_types: Optional[list[str]] = None,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
) -> tuple[list[Entity], list[Relationship]]:
    """
    Extract entities and relationships from document chunks using the Anthropic API.
    Returns (entities, relationships) with full citation provenance.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY is required for LLM extraction.")

    client = anthropic.Anthropic(api_key=key)
    chunks = _chunk_document_for_llm(doc)

    entity_map: dict[str, Entity] = {}
    relationship_map: dict[str, Relationship] = {}

    for chunk_text, chunk_pages, chunk_id in chunks:
        print(f"  [LLM] Extracting from chunk {chunk_id} (pages {chunk_pages})...")
        raw = _call_llm(client, model, chunk_text, entity_types)
        if raw is None:
            continue

        _merge_llm_result(raw, chunk_pages, chunk_id, entity_map, relationship_map)

    return list(entity_map.values()), list(relationship_map.values())


def _chunk_document_for_llm(
    doc: DocumentContent,
) -> list[tuple[str, list[int], str]]:
    """Split document pages into LLM-processable chunks."""
    chunks = []
    current_text = ""
    current_pages: list[int] = []

    for page in doc.pages:
        if not page.text.strip():
            continue
        page_text = f"[Page {page.page_number}]\n{page.text}"

        if estimate_tokens(current_text + page_text) > CHUNK_TOKEN_LIMIT and current_text:
            chunk_id = f"llm_p{current_pages[0]}_p{current_pages[-1]}"
            chunks.append((current_text, list(current_pages), chunk_id))
            current_text = page_text
            current_pages = [page.page_number]
        else:
            current_text += "\n\n" + page_text if current_text else page_text
            current_pages.append(page.page_number)

    if current_text:
        chunk_id = f"llm_p{current_pages[0]}_p{current_pages[-1]}"
        chunks.append((current_text, list(current_pages), chunk_id))

    return chunks


def _call_llm(
    client: anthropic.Anthropic,
    model: str,
    text: str,
    entity_types: Optional[list[str]],
) -> Optional[dict]:
    entity_hint = ""
    if entity_types:
        entity_hint = f"\nFocus on these entity types: {', '.join(entity_types)}."

    user_prompt = f"Extract entities and relationships from this document passage:{entity_hint}\n\n---\n{text}\n---"

    try:
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        content = message.content[0].text.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        return json.loads(content)
    except (json.JSONDecodeError, anthropic.APIError, IndexError) as e:
        print(f"  [LLM] Warning: extraction failed — {e}")
        return None


def _merge_llm_result(
    raw: dict,
    chunk_pages: list[int],
    chunk_id: str,
    entity_map: dict[str, Entity],
    relationship_map: dict[str, Relationship],
) -> None:
    label_to_id: dict[tuple[str, str], str] = {}

    for e_raw in raw.get("entities", []):
        label = str(e_raw.get("label", "")).strip()
        etype = str(e_raw.get("type", "Unknown")).strip()
        if not label:
            continue

        eid = entity_id(etype, label)
        label_to_id[(label.lower(), etype.lower())] = eid

        citation = Citation(
            text=e_raw.get("source_text", "")[:500],
            pages=chunk_pages,
            chunk_id=chunk_id,
            extraction_method=ExtractionMethod.LLM,
        )
        confidence_str = e_raw.get("confidence", "medium")
        confidence = Confidence(confidence_str) if confidence_str in Confidence._value2member_map_ else Confidence.MEDIUM

        if eid in entity_map:
            existing = entity_map[eid]
            for p in chunk_pages:
                if p not in existing.source_pages:
                    existing.source_pages.append(p)
            if chunk_id not in existing.source_chunk_ids:
                existing.source_chunk_ids.append(chunk_id)
            existing.citations.append(citation)
            existing.properties.update(e_raw.get("properties", {}))
        else:
            entity_map[eid] = Entity(
                id=eid,
                label=label,
                type=etype,
                properties=e_raw.get("properties", {}),
                extraction_method=ExtractionMethod.LLM,
                confidence=confidence,
                source_pages=list(chunk_pages),
                source_text=e_raw.get("source_text", "")[:500],
                source_chunk_id=chunk_id,
                source_chunk_ids=[chunk_id],
                citations=[citation],
            )

    for r_raw in raw.get("relationships", []):
        src_label = str(r_raw.get("source_label", "")).strip()
        src_type = str(r_raw.get("source_type", "Unknown")).strip()
        tgt_label = str(r_raw.get("target_label", "")).strip()
        tgt_type = str(r_raw.get("target_type", "Unknown")).strip()
        rel_type = str(r_raw.get("type", "RELATED_TO")).strip().upper().replace(" ", "_")

        if not src_label or not tgt_label:
            continue

        src_id = entity_id(src_type, src_label)
        tgt_id = entity_id(tgt_type, tgt_label)
        rid = relationship_id(src_id, rel_type, tgt_id)

        # Ensure referenced entities exist (create stubs if LLM mentioned them)
        for eid, label, etype in [(src_id, src_label, src_type), (tgt_id, tgt_label, tgt_type)]:
            if eid not in entity_map:
                entity_map[eid] = Entity(
                    id=eid,
                    label=label,
                    type=etype,
                    extraction_method=ExtractionMethod.LLM,
                    confidence=Confidence.LOW,
                    source_pages=list(chunk_pages),
                    source_chunk_id=chunk_id,
                    source_chunk_ids=[chunk_id],
                )

        citation = Citation(
            text=r_raw.get("source_text", "")[:500],
            pages=chunk_pages,
            chunk_id=chunk_id,
            extraction_method=ExtractionMethod.LLM,
        )
        confidence_str = r_raw.get("confidence", "medium")
        confidence = Confidence(confidence_str) if confidence_str in Confidence._value2member_map_ else Confidence.MEDIUM

        if rid in relationship_map:
            existing_r = relationship_map[rid]
            existing_r.citations.append(citation)
            for p in chunk_pages:
                if p not in existing_r.source_pages:
                    existing_r.source_pages.append(p)
        else:
            relationship_map[rid] = Relationship(
                id=rid,
                source=src_id,
                target=tgt_id,
                type=rel_type,
                properties=r_raw.get("properties", {}),
                extraction_method=ExtractionMethod.LLM,
                confidence=confidence,
                source_pages=list(chunk_pages),
                source_text=r_raw.get("source_text", "")[:500],
                source_chunk_id=chunk_id,
                citations=[citation],
            )
