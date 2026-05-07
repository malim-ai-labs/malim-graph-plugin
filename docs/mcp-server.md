# MCP Server Setup

MalimGraph exposes all 4 tools as an MCP server, compatible with Claude Desktop, Claude Code, and claude.ai connectors.

## Installation

```bash
pip install malimgraph
```

## Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "malimgraph": {
      "command": "malimgraph",
      "args": ["serve"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

## Claude Code

```bash
claude mcp add malimgraph -- malimgraph serve
```

## Remote HTTP Mode (claude.ai connector)

```bash
malimgraph serve --transport http --port 8080
```

Connect via claude.ai → Settings → Connectors → Add MCP Server → `http://your-host:8080`.

## Available Tools

| Tool | Description |
|------|-------------|
| `extract_knowledge_graph` | PDF → structured knowledge graph with citation provenance |
| `chunk_document` | PDF → embedding-ready chunks for RAG pipelines |
| `render_document_html` | PDF → structured HTML with page anchors and entity annotations |
| `manage_graph_db` | Load, query, and manage graphs in Neo4j or Apache AGE |
