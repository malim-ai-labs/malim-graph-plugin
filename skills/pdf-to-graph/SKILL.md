---
name: pdf-to-graph
description: >
  Extract a structured knowledge graph from a PDF document. Claude reads the PDF,
  identifies entities and relationships with verbatim source citations, and saves
  the graph as JSON, Cypher, and Apache AGE SQL. No API key required.
triggers:
  - "knowledge graph"
  - "extract entities"
  - "PDF to graph"
  - "PDF to Neo4j"
  - "PDF to Cypher"
  - "entity extraction"
  - "relationship mapping"
  - "build a graph from"
  - "map out the entities"
skip_if:
  - "chunk for RAG"
  - "render HTML"
  - "load into database"
---

# PDF to Knowledge Graph

Extract entities and relationships from a PDF with full citation provenance.

## Workflow

```
1. read_pdf(pdf_path)
2. [Claude analyzes text → identifies entities + relationships]
3. save_knowledge_graph(source_file, entities, relationships, output_format="all")
```

## Example

> "Extract a knowledge graph from annual_report.pdf and save to ./output/"

Claude will:
- Parse the PDF and run rule-based extraction (dates, amounts, emails)
- Identify semantic entities: Organizations, People, Regulations, etc.
- Map relationships between entities with verbatim source quotes
- Save `knowledge_graph.json`, `knowledge_graph.cypher`, `knowledge_graph.sql`

## Output

```
./output/
├── knowledge_graph.json    # Full graph with provenance
├── knowledge_graph.cypher  # Neo4j/Memgraph import
└── knowledge_graph.sql     # Apache AGE import
```

## Notes

- Every entity includes `source_text` (verbatim quote) + `source_pages`
- Confidence: `high` = explicit, `medium` = implied, `low` = uncertain
- Stable entity IDs: same entity always gets same ID across runs (safe for incremental updates)
