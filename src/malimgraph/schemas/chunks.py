from pydantic import BaseModel, Field


class ChunkPosition(BaseModel):
    index: int
    total: int
    start_char: int
    end_char: int


class ChunkMetadata(BaseModel):
    source_file: str
    has_table: bool = False
    has_heading: bool = False
    language: str = "en"


class Chunk(BaseModel):
    chunk_id: str
    text: str
    token_count: int
    source_pages: list[int]
    page_range: dict[str, int] = Field(description="{'start': N, 'end': M}")
    heading_context: list[str] = Field(default_factory=list)
    position: ChunkPosition
    metadata: ChunkMetadata


class CollectionMetadata(BaseModel):
    source_file: str
    total_chunks: int
    total_tokens: int
    chunk_config: dict


class ChunkCollection(BaseModel):
    metadata: CollectionMetadata
    chunks: list[Chunk]
