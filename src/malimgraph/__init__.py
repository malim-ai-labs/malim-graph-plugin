"""MalimGraph — Transform PDF documents into structured knowledge graphs."""

__version__ = "0.1.6"
__author__ = "Malim AI Labs"
__email__ = "hello@malim.my"

from malimgraph.schemas.chunks import Chunk, ChunkCollection
from malimgraph.schemas.entities import (
    Citation,
    Confidence,
    Entity,
    ExtractionMethod,
    GraphMetadata,
    KnowledgeGraph,
    Relationship,
)

__all__ = [
    "Citation",
    "Chunk",
    "ChunkCollection",
    "Confidence",
    "Entity",
    "ExtractionMethod",
    "GraphMetadata",
    "KnowledgeGraph",
    "Relationship",
    "__version__",
]
