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
[![CI](https://github.com/malim-ai-labs/malim-graph-plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/malim-ai-labs/malim-graph-plugin/actions/workflows/ci.yml)

**From documents to knowledge graphs.**

Agentic knowledge graph plugin for Claude Code, Claude Desktop, and Codex.
Extract entities, build graphs, chunk for RAG, render HTML, and load into Neo4j or pgvector —
all orchestrated by Claude using its own intelligence. No `ANTHROPIC_API_KEY` required.

---

## Install

```bash
pip install malimgraph
claude mcp add malimgraph -- malimgraph-plugin
```

Then just ask Claude naturally:

> *"Extract a knowledge graph from report.pdf"*
> *"Chunk annual_report.pdf for RAG and store in pgvector"*
> *"Full pipeline on this document"*

---

## How It Works

```
You: "Extract a knowledge graph from report.pdf"
        │
        ▼
Claude calls  read_pdf("report.pdf")
        │     ← returns page text + rule entities (dates, amounts, emails…)
        │
        ▼
Claude analyzes text   ← uses YOUR Claude subscription, no extra API key
        │     identifies: Organizations, People, Regulations, Events…
        │     maps: relationships with verbatim source_text evidence
        │
        ▼
Claude calls  save_knowledge_graph(entities, relationships, output_format="all")
        │     ← builds KnowledgeGraph, saves files
        ▼
  ./output/
    ├── knowledge_graph.json    ← full graph with provenance
    ├── knowledge_graph.cypher  ← Neo4j import
    └── knowledge_graph.sql     ← Apache AGE import
```

---

## Skill Triggers

Say these phrases to activate built-in workflows:

| Phrase | Workflow | Tools |
|--------|---------|-------|
| "knowledge graph" / "extract entities" | `$pdf-to-graph` | `read_pdf` → `save_knowledge_graph` |
| "chunk for RAG" / "vector search" / "pgvector" | `$pdf-to-rag` | `chunk_document` → `embed_and_store_chunks` |
| "full pipeline" / "extract and embed" | Full pipeline | All tools in sequence |
| "load into Neo4j" / "Cypher query" | `$graph-query` | `manage_graph_db` |
| "render HTML" / "browsable document" | `$document-html` | `render_document_html` |

---

## Available Tools

| Tool | Description |
|------|-------------|
| `read_pdf` | Parse PDF → page text + rule entities. First step of any KG workflow. |
| `save_knowledge_graph` | Accept Claude-extracted entities/relationships → save .json/.cypher/.sql |
| `chunk_document` | Token-aware overlapping chunks with heading context for RAG |
| `render_document_html` | Structured HTML with page anchors, entity annotations, TOC + search |
| `manage_graph_db` | Load, query, and manage graphs in Neo4j or Apache AGE |
| `embed_and_store_chunks` | Embed chunks into PostgreSQL pgvector (OpenAI / Voyage / local) |
| `list_workflows` | List all available workflows, triggers, and tool sequences |

---

## Runtimes

| Runtime | Install |
|---------|---------|
| **Claude Code** | `claude mcp add malimgraph -- malimgraph-plugin` |
| **Claude Desktop** | See config below |
| **Codex / OpenAI Agents** | See `AGENTS.md` for function schemas |
| **Any MCP runtime** | `{"command": "malimgraph-plugin"}` |
| **Vercel (Serverless)** | See *Deploying to Vercel* below |

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "malimgraph": {
      "command": "malimgraph-plugin"
    }
  }
}
```

---

## Deploying to Vercel (HTTP SSE)

MalimGraph can be natively deployed as a Serverless Application on Vercel over an HTTP SSE (Server-Sent Events) endpoint.

1. Clone the repository and connect it to your Vercel dashboard.
2. Configure your environment variables in the Vercel dashboard (e.g. `PGVECTOR_URI`, `OPENAI_API_KEY`).
3. Deploy! Vercel will wrap the server into a standard function using `@vercel/python`.

Remote agents and clients can connect to the deployed stream at:
`https://mcpserver.malim.my/api/sse`

---

## CLI (standalone, requires `ANTHROPIC_API_KEY`)

```bash
export ANTHROPIC_API_KEY=sk-ant-...

# Full pipeline
malimgraph extract --input report.pdf --output ./output/ --format all
malimgraph chunk --input report.pdf --output ./chunks/
malimgraph render --input report.pdf --output document.html

# pgvector
export PGVECTOR_URI="postgresql://user:pass@localhost:5432/mydb"
export OPENAI_API_KEY=sk-...
malimgraph vector load --input ./chunks/chunks.json

# Graph database
malimgraph db load --input ./output/knowledge_graph.json \
  --target neo4j --uri bolt://localhost:7687 --user neo4j --password secret
malimgraph db query --target neo4j --uri bolt://localhost:7687 \
  --query "MATCH (n:Organization) RETURN n.label, n.source_pages LIMIT 10"
```

---

## Installation Options

```bash
pip install malimgraph                    # core
pip install "malimgraph[neo4j]"           # + Neo4j driver
pip install "malimgraph[pgvector,openai]" # + pgvector + OpenAI embeddings
pip install "malimgraph[pgvector,voyage]" # + pgvector + Voyage AI
pip install "malimgraph[pgvector,local]"  # + pgvector + local CPU embeddings
pip install "malimgraph[all]"             # everything
```

---

## Output Schema

Every entity and relationship carries full citation provenance:

| Field | Description |
|-------|-------------|
| `id` | Stable hash: `e_` + MD5(type:label)[:8] |
| `label` | Canonical entity name |
| `type` | Organization / Person / Location / Regulation / … |
| `source_text` | Verbatim quote from the document |
| `source_pages` | PDF page numbers |
| `confidence` | `high` / `medium` / `low` |
| `extraction_method` | `rule` / `llm` / `hybrid` |
| `citations[]` | All supporting quotes with page refs |

---

## pgvector Embedding Providers

| Provider | Default model | Dimension | Requires |
|----------|--------------|-----------|---------|
| `openai` | `text-embedding-3-small` | 1536-d | `OPENAI_API_KEY` |
| `voyage` | `voyage-3-large` | 1024-d | `VOYAGE_API_KEY` |
| `local` | `all-MiniLM-L6-v2` | 384-d | none (CPU) |

---

## Database Setup

```bash
# Neo4j
docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/yourpassword neo4j:latest

# Apache AGE
docker run -p 5432:5432 -e POSTGRES_PASSWORD=secret apache/age:latest

# pgvector
docker run -p 5432:5432 -e POSTGRES_PASSWORD=secret pgvector/pgvector:pg17
```

See [docs/database-setup.md](docs/database-setup.md) for full guides.

---

## Contributing

```bash
git clone https://github.com/malim-ai-labs/malim-graph-plugin
pip install -e ".[dev]"
make test
make lint
```

---

## Credits

Built by **[Malim AI Labs](https://ailabs.malim.my)** — AI-powered knowledge infrastructure for Southeast Asia.

Malim AI Labs Social Enterprise (003827047-U) · Kuala Lumpur, Malaysia

---

## License

MIT — see [LICENSE](LICENSE)
