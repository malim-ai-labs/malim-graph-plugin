# MalimGraph — Claude Code Plugin

> Transform PDF documents into structured knowledge graphs, RAG chunks, and vector embeddings.
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
| `save_knowledge_graph` | Accept your extracted entities/relationships → save .json/.cypher/.sql |
| `chunk_document` | Split PDF → overlapping chunks with heading context |
| `render_document_html` | PDF → structured HTML with page anchors + entity annotations |
| `manage_graph_db` | Load/query/stats on Neo4j or PostgreSQL AGE |
| `embed_and_store_chunks` | Embed chunks → pgvector (OpenAI / Voyage / local) |

## Skill Triggers

Use these phrases to activate specific workflows:

- **"knowledge graph"** / **"extract entities"** / **"PDF to graph"** → `$pdf-to-graph`
- **"chunk for RAG"** / **"prepare embeddings"** / **"vector search"** → `$pdf-to-rag`
- **"load into Neo4j"** / **"Cypher query"** / **"graph database"** → `$graph-query`
- **"render HTML"** / **"browsable document"** → `$document-html`

## Workflows

### 1. PDF → Knowledge Graph (most common)

```
User: "Extract a knowledge graph from report.pdf"

You MUST:
1. Call read_pdf(pdf_path="report.pdf")
2. Read ALL page text returned. Identify entities:
   - Organizations, People, Locations, Regulations, Products, Concepts, Roles, Events
   - Include all rule_extracted_entities already found (dates, amounts, emails, refs)
3. For every entity include:
   - source_text: verbatim quote ≤200 chars proving it exists
   - source_pages: page numbers
   - confidence: "high" | "medium" | "low"
4. Identify relationships between entities (UPPER_SNAKE_CASE type)
5. Call save_knowledge_graph(source_file, entities, relationships, output_dir="./output", output_format="all")
6. Report: entities found, relationships found, files saved
```

### 2. Full Pipeline (KG + RAG)

```
User: "Full pipeline on report.pdf"

Steps:
1. read_pdf("report.pdf")
2. Extract entities + relationships (your intelligence)
3. save_knowledge_graph(..., output_dir="./output", output_format="all")
4. chunk_document("report.pdf", output_dir="./chunks", output_format="json")
5. embed_and_store_chunks("./chunks/chunks.json", ...)   ← needs PGVECTOR_URI
6. render_document_html("report.pdf", knowledge_graph_path="./output/knowledge_graph.json")
7. Report all outputs
```

### 3. RAG Pipeline Only

```
User: "Chunk report.pdf for vector search"

Steps:
1. chunk_document("report.pdf", chunk_size=512, chunk_overlap=64, output_format="json")
2. embed_and_store_chunks("./chunks/chunks.json", embedding_provider="openai")
3. Report: chunks created, embeddings stored
```

### 4. Load Graph to Database

```
User: "Load the knowledge graph into Neo4j"

Steps:
1. manage_graph_db(action="load", knowledge_graph_path="./output/knowledge_graph.json",
                   target="neo4j", connection_uri="bolt://localhost:7687")
2. manage_graph_db(action="stats", target="neo4j")
3. Report: nodes loaded, relationships loaded, graph stats
```

## Entity Extraction Guidelines

When analyzing PDF text from `read_pdf`, extract:

**Entity types:**
- `Organization` — companies, institutions, government bodies
- `Person` — named individuals
- `Location` — countries, cities, addresses
- `Regulation` — laws, acts, directives, standards
- `Product` — goods, software, services
- `Concept` — abstract ideas, methodologies, frameworks
- `Role` — job titles, positions
- `Event` — conferences, incidents, milestones
- `Date` — already extracted by rules, include if semantic context matters
- `MonetaryAmount` — already extracted by rules

**Relationship types (UPPER_SNAKE_CASE):**
`SIGNED_BY`, `GOVERNED_BY`, `LOCATED_IN`, `EMPLOYED_BY`, `REGULATES`,
`PRODUCES`, `PART_OF`, `REFERENCES`, `LED_BY`, `RELATED_TO`

**Quality rules:**
- Every entity MUST have `source_text` — a verbatim quote from the document
- Every relationship MUST have `source_text` — a quote proving the connection
- `confidence: "high"` only for explicitly stated facts
- Do NOT invent entities or relationships not supported by the text

## Output Files

After `save_knowledge_graph`:
- `knowledge_graph.json` — full graph with provenance
- `knowledge_graph.cypher` — Neo4j/Memgraph import script
- `knowledge_graph.sql` — Apache AGE import script

After `chunk_document`:
- `chunks.json` — all chunks with page refs + heading context

## Environment Variables (optional)

```bash
PGVECTOR_URI=postgresql://user:pass@localhost:5432/mydb   # for embed_and_store_chunks
OPENAI_API_KEY=sk-...                                      # for OpenAI embeddings
VOYAGE_API_KEY=pa-...                                      # for Voyage AI embeddings
NEO4J_URI=bolt://localhost:7687                            # for manage_graph_db (neo4j)
NEO4J_USER=neo4j
NEO4J_PASSWORD=yourpassword
AGE_CONNECTION_URI=host=localhost dbname=mydb user=postgres # for manage_graph_db (age)
```
