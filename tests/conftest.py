"""Shared fixtures for MalimGraph tests."""

from pathlib import Path

import pytest

from malimgraph.schemas.chunks import (
    Chunk,
    ChunkCollection,
    ChunkMetadata,
    ChunkPosition,
    CollectionMetadata,
)
from malimgraph.schemas.entities import (
    Citation,
    Confidence,
    Entity,
    ExtractionMethod,
    GraphMetadata,
    KnowledgeGraph,
    Relationship,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_entity() -> Entity:
    return Entity(
        id="e_aabbccdd",
        label="Malim AI Labs",
        type="Organization",
        extraction_method=ExtractionMethod.HYBRID,
        confidence=Confidence.HIGH,
        source_pages=[1, 3],
        source_text="Malim AI Labs Social Enterprise was incorporated in 2023.",
        source_chunk_id="llm_p1_p2",
        source_chunk_ids=["page_1", "llm_p1_p2"],
        citations=[
            Citation(
                text="Malim AI Labs Social Enterprise was incorporated in 2023.",
                pages=[1],
                chunk_id="page_1",
                extraction_method=ExtractionMethod.RULE,
            )
        ],
    )


@pytest.fixture
def sample_relationship(sample_entity) -> Relationship:
    return Relationship(
        id="r_11223344",
        source="e_aabbccdd",
        target="e_11223344",
        type="LOCATED_IN",
        extraction_method=ExtractionMethod.LLM,
        confidence=Confidence.MEDIUM,
        source_pages=[2],
        source_text="Malim AI Labs is located in Kuala Lumpur.",
        citations=[
            Citation(
                text="Malim AI Labs is located in Kuala Lumpur.",
                pages=[2],
                chunk_id="llm_p2_p3",
                extraction_method=ExtractionMethod.LLM,
            )
        ],
    )


@pytest.fixture
def sample_kg(sample_entity, sample_relationship) -> KnowledgeGraph:
    target_entity = Entity(
        id="e_11223344",
        label="Kuala Lumpur",
        type="Location",
        extraction_method=ExtractionMethod.LLM,
        confidence=Confidence.HIGH,
        source_pages=[2],
        source_text="...located in Kuala Lumpur...",
    )
    return KnowledgeGraph(
        metadata=GraphMetadata(
            source_file="test.pdf",
            extracted_at="2025-01-01T00:00:00Z",
            total_entities=2,
            total_relationships=1,
            entity_types=["Location", "Organization"],
            relationship_types=["LOCATED_IN"],
        ),
        entities=[sample_entity, target_entity],
        relationships=[sample_relationship],
    )


@pytest.fixture
def sample_chunk() -> Chunk:
    return Chunk(
        chunk_id="chunk_0000",
        text="This is the first chunk of text from the document.",
        token_count=12,
        source_pages=[1],
        page_range={"start": 1, "end": 1},
        heading_context=["Introduction"],
        position=ChunkPosition(index=0, total=5, start_char=0, end_char=50),
        metadata=ChunkMetadata(source_file="test.pdf", has_table=False, has_heading=True),
    )


@pytest.fixture
def sample_collection(sample_chunk) -> ChunkCollection:
    return ChunkCollection(
        metadata=CollectionMetadata(
            source_file="test.pdf",
            total_chunks=1,
            total_tokens=12,
            chunk_config={"chunk_size": 512, "overlap": 64},
        ),
        chunks=[sample_chunk],
    )
