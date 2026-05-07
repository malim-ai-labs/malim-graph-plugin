# Installing MalimGraph in Claude Code

No API key required — Claude does the entity extraction using your existing subscription.

## Install

```bash
pip install malimgraph
```

## Add to Claude Code

```bash
claude mcp add malimgraph -- malimgraph-plugin
```

That's it. Restart Claude Code and the tools are available.

## Verify

In Claude Code, ask:
> "What MalimGraph tools do you have available?"

Claude will list: `read_pdf`, `save_knowledge_graph`, `chunk_document`,
`render_document_html`, `manage_graph_db`, `embed_and_store_chunks`.

## Usage Examples

### Extract a knowledge graph
> "Extract a knowledge graph from /path/to/report.pdf and save it to ./output/"

Claude will:
1. Call `read_pdf` → gets document text + rule entities
2. Analyze the text using its own intelligence
3. Call `save_knowledge_graph` → saves `knowledge_graph.json` + `.cypher` + `.sql`

### Chunk a document for RAG
> "Chunk report.pdf into 512-token overlapping chunks and save to ./chunks/"

### Render as HTML
> "Convert report.pdf to a browsable HTML page at document.html"

### Load into Neo4j
> "Load ./output/knowledge_graph.json into my Neo4j at bolt://localhost:7687"

## Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "malimgraph": {
      "command": "malimgraph-plugin"
    }
  }
}
```

## How It Works

The plugin exposes two tools for knowledge graph extraction:

**`read_pdf`** — Parses the PDF and returns:
- Full text per page with headings
- Rule-extracted entities (dates, amounts, emails, legal refs)
- Instructions for Claude to identify semantic entities

**`save_knowledge_graph`** — Accepts Claude's extracted entities and relationships and:
- Builds provenance-annotated `KnowledgeGraph` objects
- Saves `knowledge_graph.json`, `.cypher`, and `.sql` files
- No API call made — Claude already did the extraction

The `ANTHROPIC_API_KEY` is **not required** for any plugin tool.
It is only needed for the standalone CLI (`malimgraph extract`) where
no Claude instance is running.
