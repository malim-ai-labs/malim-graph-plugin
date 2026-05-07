"""Tests for graph_builder merge and dedup logic."""
import pytest

from malimgraph.core.pdf_reader import DocumentContent, PageContent
from malimgraph.core.graph_builder import (
    _merge_entities,
    _validate_relationships,
    build_knowledge_graph,
)
from malimgraph.schemas.entities import (
    Citation,
    Confidence,
    Entity,
    ExtractionMethod,
    Relationship,
)
from malimgraph.utils.hashing import entity_id


def _make_entity(label: str, etype: str, method: ExtractionMethod, page: int = 1) -> Entity:
    eid = entity_id(etype, label)
    return Entity(
        id=eid,
        label=label,
        type=etype,
        extraction_method=method,
        confidence=Confidence.MEDIUM,
        source_pages=[page],
        source_text=f"...{label}...",
        source_chunk_id=f"page_{page}",
        source_chunk_ids=[f"page_{page}"],
        citations=[
            Citation(
                text=f"...{label}...",
                pages=[page],
                chunk_id=f"page_{page}",
                extraction_method=method,
            )
        ],
    )


def _make_doc() -> DocumentContent:
    page = PageContent(page_number=1, text="Test content.", headings=[], blocks=[], has_table=False, is_scanned=False)
    return DocumentContent(source_file="test.pdf", total_pages=1, title="Test", metadata={}, pages=[page])


def test_merge_entities_llm_wins_on_semantics():
    """When same entity from both sources, LLM label/type takes precedence for semantic types."""
    rule_ent = _make_entity("malim ai labs", "Organization", ExtractionMethod.RULE)
    llm_ent = _make_entity("malim ai labs", "Organization", ExtractionMethod.LLM)
    llm_ent.label = "Malim AI Labs"  # Better canonical form

    merged = _merge_entities([rule_ent], [llm_ent])

    assert len(merged) == 1
    assert merged[0].label == "Malim AI Labs"
    assert merged[0].extraction_method == ExtractionMethod.HYBRID
    assert merged[0].confidence == Confidence.HIGH


def test_merge_entities_accumulates_citations():
    """Merged entity has citations from both rule and LLM sources."""
    rule_ent = _make_entity("January 2024", "Date", ExtractionMethod.RULE, page=1)
    llm_ent = _make_entity("January 2024", "Date", ExtractionMethod.LLM, page=2)

    merged = _merge_entities([rule_ent], [llm_ent])

    assert len(merged) == 1
    assert len(merged[0].citations) == 2


def test_merge_entities_rule_wins_for_structured_types():
    """For dates/amounts, rule extraction type is kept."""
    rule_ent = _make_entity("RM 1,000,000", "MonetaryAmount", ExtractionMethod.RULE)
    llm_ent = _make_entity("RM 1,000,000", "MonetaryAmount", ExtractionMethod.LLM)

    merged = _merge_entities([rule_ent], [llm_ent])

    assert merged[0].type == "MonetaryAmount"


def test_merge_entities_unique_pages():
    """Merged entity source_pages is a sorted union."""
    rule_ent = _make_entity("Malim AI Labs", "Organization", ExtractionMethod.RULE, page=1)
    llm_ent = _make_entity("Malim AI Labs", "Organization", ExtractionMethod.LLM, page=3)

    merged = _merge_entities([rule_ent], [llm_ent])

    assert 1 in merged[0].source_pages
    assert 3 in merged[0].source_pages


def test_validate_relationships_removes_dangling():
    """Relationships referencing non-existent entities are dropped."""
    ent = _make_entity("Malim AI Labs", "Organization", ExtractionMethod.LLM)
    valid_rel = Relationship(
        id="r_valid",
        source=ent.id,
        target=ent.id,  # self-loop for test simplicity
        type="SELF_REFERENCES",
        extraction_method=ExtractionMethod.LLM,
        confidence=Confidence.LOW,
        source_pages=[1],
    )
    dangling_rel = Relationship(
        id="r_dangling",
        source="e_nonexistent1",
        target="e_nonexistent2",
        type="CONNECTED_TO",
        extraction_method=ExtractionMethod.LLM,
        confidence=Confidence.LOW,
        source_pages=[1],
    )

    valid = _validate_relationships([valid_rel, dangling_rel], [ent])

    assert len(valid) == 1
    assert valid[0].id == "r_valid"


def test_build_knowledge_graph_metadata():
    """build_knowledge_graph produces correct metadata."""
    doc = _make_doc()
    rule_entities = [_make_entity("January 2024", "Date", ExtractionMethod.RULE)]
    llm_entities = [_make_entity("Malim AI Labs", "Organization", ExtractionMethod.LLM)]

    kg = build_knowledge_graph(doc, rule_entities, llm_entities, [], "my_graph")

    assert kg.metadata.total_entities == 2
    assert kg.metadata.total_relationships == 0
    assert "Date" in kg.metadata.entity_types
    assert "Organization" in kg.metadata.entity_types
    assert kg.metadata.extraction_config["graph_name"] == "my_graph"
