# MalimGraph (v0.2.0) — Claude Code Plugin

> Transform PDF documents into structured knowledge graphs, RAG chunks, and interactive discovery maps.
> No `ANTHROPIC_API_KEY` needed — Claude extracts entities using its own intelligence.

## Quick Install

```bash
pip install malimgraph
claude mcp add malimgraph -- malimgraph-plugin
```

## Available Tools

| Tool | Purpose |
|------|---------|
| `read_pdf` | Parse PDF → page text + rule entities. Always call first. |
| `save_knowledge_graph` | Accept your extracted entities/relationships → save .json/.cypher/.sql/OKF bundle |
| `chunk_document` | Split PDF → overlapping chunks with heading context |
| `render_document_html` | PDF → structured HTML with page anchors + entity annotations |
| `manage_graph_db` | Load/query/stats on Neo4j or PostgreSQL AGE |
| `embed_and_store_chunks` | Embed chunks → pgvector (OpenAI / Voyage / local) |

## Skill Triggers

Use these phrases to activate specific workflows:

- **"knowledge graph"** / **"extract entities"** → `$pdf-to-graph`
- **"visualise graph"** / **"discovery map"** → `visual-discovery`
- **"chunk for RAG"** / **"vector search"** → `$pdf-to-rag`
- **"load into Neo4j"** → `neo4j-local`
- **"OKF"** / **"open knowledge format"** / **"markdown knowledge bundle"** → `document-to-okf`

## Workflows

### 1. PDF → Knowledge Graph + Visualisation (Core Workflow)

```
User: "Extract a knowledge graph from report.pdf"

You MUST:
1. Call read_pdf(pdf_path="report.pdf")
2. Read ALL page text. Identify entities (Org, Person, Concept, etc.) with verbatim source_text.
3. Identify relationships (UPPER_SNAKE_CASE).
4. Call save_knowledge_graph(entities, relationships, output_format="all")
5. CALL THE VISUALIZER: 
   python skills/graph-visualizer/scripts/visualize_graph.py --input output/knowledge_graph.json
6. Report: entities found, relationships found, and the path to the Discovery Map.
```

### 2. PDF → Open Knowledge Format (OKF) Bundle

```
User: "Export report.pdf as OKF" / "convert this document to open knowledge format"

You MUST:
1. Call read_pdf(pdf_path="report.pdf")
2. Read ALL page text. Identify entities and relationships with verbatim source_text,
   same as the core workflow above.
3. Call save_knowledge_graph(entities, relationships, output_format="okf")
4. Report the path to output/okf/index.md as the bundle entry point.
```

See `skills/document-to-okf/SKILL.md` for the bundle structure and frontmatter schema.

## Entity Extraction Guidelines

**Entity types:**
- `Organization`, `Person`, `Location`, `Regulation`, `Product`, `Concept`, `Role`, `Event`

**Relationship types:**
- `SIGNED_BY`, `GOVERNED_BY`, `LOCATED_IN`, `EMPLOYED_BY`, `REGULATES`, `PRODUCES`, `PART_OF`, `LED_BY`, `RELATED_TO`

## Output Files

- `output/knowledge_graph.json` — full graph
- `output/discovery_map.html` — interactive explorer (vis.js)
- `output/knowledge_graph.cypher` — Neo4j script
- `output/knowledge_graph.sql` — Apache AGE script
- `output/okf/` — Open Knowledge Format bundle (cross-linked Markdown, one file per entity)
