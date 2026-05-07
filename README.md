# MalimGraph

```
███╗   ███╗ █████╗ ██╗     ██╗███╗   ███╗ ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗
████╗ ████║██╔══██╗██║     ██║████╗ ████║██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║
██╔████╔██║███████║██║     ██║██╔████╔██║██║  ███╗██████╔╝███████║██████╔╝███████║
██║╚██╔╝██║██╔══██║██║     ██║██║╚██╔╝██║██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║
██║ ╚═╝ ██║██║  ██║███████╗██║██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║
╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
```

[![PyPI version](https://badge.fury.io/py/malimgraph.svg)](https://badge.fury.io/py/malimgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io)

**From documents to knowledge graphs.**

Transform PDF documents into structured knowledge graphs with full citation provenance. Every entity and relationship traces back to the exact PDF page and verbatim text that supports it.

---

## Features

| Tool | Description |
|------|-------------|
| `extract_knowledge_graph` | Hybrid rule + LLM extraction → entities, relationships, citations |
| `chunk_document` | Token-aware overlapping chunks with heading context for RAG |
| `render_document_html` | Structured HTML with page anchors, entity annotations, TOC + search |
| `manage_graph_db` | Load, query, and manage graphs in Neo4j or PostgreSQL (Apache AGE) |
| `embed_and_store_chunks` | Embed chunks into PostgreSQL pgvector (OpenAI / Voyage / local) |

**Three ways to use:**
- **MCP Server** — connect to Claude Desktop, Claude Code, or claude.ai
- **CLI** — `malimgraph extract`, `chunk`, `render`, `db`
- **Claude Skills** — installable `.skill` packages for claude.ai

---

## Quick Start

```bash
pip install malimgraph
export ANTHROPIC_API_KEY=sk-ant-...

# Extract knowledge graph
malimgraph extract --input report.pdf --output ./output/ --format all

# Chunk for RAG
malimgraph chunk --input report.pdf --output ./chunks/

# Render as HTML
malimgraph render --input report.pdf --output document.html
```

---

## How It Works

```
PDF
 │
 ▼
pdf_reader.py ──────────────────────────────────────────────┐
 │  (PyMuPDF: text, headings, tables, page structure)       │
 ├──────────────────────────────────┐                        │
 ▼                                  ▼                        ▼
rule_extractor.py              llm_extractor.py          chunker.py
 │ (regex: dates, amounts,      │ (Anthropic API:         │ (sliding window
 │  emails, legal refs,         │  semantic entities,     │  with heading
 │  section numbers)            │  relationships,         │  context)
 │                              │  source_text required)  │
 └──────────────┬───────────────┘                         │
                ▼                                          ▼
          graph_builder.py                           chunks.json
           │ (merge + dedup:
           │  hybrid method,
           │  citation accumulation,
           │  stable IDs)
           ▼
     knowledge_graph.json
           │
     ┌─────┴──────┐
     ▼             ▼
 cypher.py     age_sql.py
 (.cypher)      (.sql)
```

---

## Three Ways to Use

### MCP Server

```bash
# stdio (for Claude Desktop / Claude Code)
malimgraph serve

# HTTP (for remote connections / claude.ai)
malimgraph serve --transport http --port 8080
```

**Claude Desktop config** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "malimgraph": {
      "command": "malimgraph",
      "args": ["serve"],
      "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
    }
  }
}
```

**Claude Code:**
```bash
claude mcp add malimgraph -- malimgraph serve
```

### CLI

```bash
# Extract knowledge graph from PDF
malimgraph extract \
  --input report.pdf \
  --output ./output/ \
  --entity-types auto \
  --format all \
  --graph-name my_graph

# Chunk for embeddings
malimgraph chunk \
  --input report.pdf \
  --output ./chunks/ \
  --chunk-size 512 \
  --overlap 64 \
  --format json

# Render as HTML
malimgraph render \
  --input report.pdf \
  --output document.html \
  --knowledge-graph ./output/knowledge_graph.json

# Load into Neo4j
malimgraph db load \
  --input ./output/knowledge_graph.json \
  --target neo4j \
  --uri bolt://localhost:7687 \
  --user neo4j \
  --password secret

# Query
malimgraph db query \
  --target neo4j \
  --uri bolt://localhost:7687 \
  --query "MATCH (n:Organization) RETURN n.label, n.source_pages LIMIT 10"
```

### Claude Skills

Download `.skill` files from [GitHub Releases](https://github.com/AiMalim/malimgraph/releases) and install in claude.ai → Settings → Skills.

| Skill | Trigger phrases |
|-------|----------------|
| `pdf-to-knowledge-graph` | "knowledge graph", "extract entities", "PDF to Cypher" |
| `pdf-to-chunks` | "chunk document", "split for embeddings", "RAG chunks" |
| `document-to-html` | "convert PDF to HTML", "render document", "make PDF browsable" |
| `graph-db-admin` | "load into Neo4j", "Cypher query", "graph statistics" |
| `chunks-to-pgvector` | "store in pgvector", "embed into PostgreSQL", "semantic search", "RAG with PostgreSQL" |

---

## Output Schema — `knowledge_graph.json`

Every entity and relationship carries full citation provenance:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable hash ID: `e_` + MD5(type:label)[:8] |
| `label` | string | Canonical entity name |
| `type` | string | Entity type (Organization, Person, Date, …) |
| `extraction_method` | enum | `rule` / `llm` / `hybrid` |
| `confidence` | enum | `high` / `medium` / `low` |
| `source_pages` | int[] | PDF page numbers where found |
| `source_text` | string | Primary verbatim supporting quote |
| `source_chunk_id` | string | Processing chunk ID |
| `citations[]` | object[] | All supporting quotes with page refs |
| `citation_count` | int | Stored as property in graph DBs |

---

## Database Setup

### Neo4j
```bash
docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/yourpassword neo4j:latest
```

### Apache AGE (PostgreSQL)
```bash
docker run -p 5432:5432 -e POSTGRES_PASSWORD=secret apache/age:latest
```

See [docs/database-setup.md](docs/database-setup.md) for full guides.

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dev deps: `pip install -e ".[dev]"`
4. Run tests: `make test`
5. Lint: `make lint`
6. Submit a PR

---

## Credits

Built by **[Malim AI Labs](https://ailabs.malim.my)** — AI-powered knowledge infrastructure for Southeast Asia.

Malim AI Labs Social Enterprise (003827047-U) · Kuala Lumpur, Malaysia

---

## License

MIT — see [LICENSE](LICENSE)
