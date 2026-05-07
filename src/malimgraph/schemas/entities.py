from enum import Enum

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExtractionMethod(str, Enum):
    RULE = "rule"
    LLM = "llm"
    HYBRID = "hybrid"


class Citation(BaseModel):
    text: str = Field(description="Verbatim quote from the source document")
    pages: list[int] = Field(description="Page numbers where this quote appears")
    chunk_id: str = Field(default="", description="Processing chunk ID")
    extraction_method: ExtractionMethod = ExtractionMethod.LLM


class Entity(BaseModel):
    id: str = Field(description="Stable hash-based entity ID (e.g., e_a1b2c3d4)")
    label: str = Field(description="Canonical entity name")
    type: str = Field(description="Entity type (e.g., Organization, Person, Regulation)")
    properties: dict = Field(default_factory=dict)
    extraction_method: ExtractionMethod = ExtractionMethod.LLM
    confidence: Confidence = Confidence.MEDIUM
    source_pages: list[int] = Field(default_factory=list)
    source_text: str = Field(default="", description="Primary supporting quote")
    source_chunk_id: str = Field(default="")
    source_chunk_ids: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class Relationship(BaseModel):
    id: str
    source: str = Field(description="Source entity ID")
    target: str = Field(description="Target entity ID")
    type: str = Field(description="UPPER_SNAKE_CASE relationship type")
    properties: dict = Field(default_factory=dict)
    extraction_method: ExtractionMethod = ExtractionMethod.LLM
    confidence: Confidence = Confidence.MEDIUM
    source_pages: list[int] = Field(default_factory=list)
    source_text: str = Field(default="")
    source_chunk_id: str = Field(default="")
    citations: list[Citation] = Field(default_factory=list)


class ChunkIndex(BaseModel):
    chunk_id: str
    pages: list[int]


class GraphMetadata(BaseModel):
    source_file: str
    extracted_at: str
    total_entities: int
    total_relationships: int
    entity_types: list[str]
    relationship_types: list[str] = Field(default_factory=list)
    extraction_config: dict = Field(default_factory=dict)
    chunk_index: dict[str, ChunkIndex] = Field(default_factory=dict)


class KnowledgeGraph(BaseModel):
    metadata: GraphMetadata
    entities: list[Entity]
    relationships: list[Relationship]
