# MalimGraph (v0.2.1)

```
███╗   ███╗ █████╗ ██╗     ██╗███╗   ███╗ ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗
████╗ ████║██╔══██╗██║     ██║████╗ ████║██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║
██╔████╔██║███████║██║     ██║██╔████╔██║██║  ███╗██████╔╝███████║██████╔╝███████║
██║╚██╔╝██║██╔══██║██║     ██║██║╚██╔╝██║██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║
██║ ╚═╝ ██║██║  ██║███████╗██║██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║
╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
```

[![PyPI version](https://img.shields.io/pypi/v/malimgraph?color=blue&label=pypi)](https://pypi.org/project/malimgraph/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/malimgraph?color=green&label=downloads%2Fmonth)](https://pypi.org/project/malimgraph/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://modelcontextprotocol.io)
[![CI](https://github.com/malim-ai-labs/malim-graph-plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/malim-ai-labs/malim-graph-plugin/actions/workflows/ci.yml)

[![Claude Code](https://img.shields.io/badge/Claude%20Code-Plugin-D97757?style=for-the-badge&logoColor=white&logo=anthropic)]([https://github.com/malim-ai=labs/malimgraph](https://github.com/malim-ai-labs/malim-graph-plugin))

**From documents to interactive knowledge discovery.**

MalimGraph is an agentic knowledge graph engine for Claude Code and Claude Desktop.
Extract entities, build graphs, and visualize discovery maps — all orchestrated by Claude
using its own intelligence. No `ANTHROPIC_API_KEY` required.

---

## 🚀 Claude Code Integration (Native)

MalimGraph v0.2.1 is a first-class plugin for Claude Code. It features auto-discovery
and a native orchestration command.

### Installation
```bash
pip install malimgraph
claude mcp add malimgraph -- malimgraph-plugin
```

### The `/kg` Command
Initialize a full discovery workflow by typing `/kg` in your Claude terminal:
1. **Extract**: Parses PDF text via `read_pdf`.
2. **Analyze**: Claude identifies entities and relationships with verbatim evidence.
3. **Build**: Generates a standard Knowledge Graph (`.json`, `.cypher`, `.sql`).
4. **Visualize**: Launches the **Premium Visual Discovery Map** immediately.

---

## 🎨 Visual Discovery Suite

Explore your data through high-fidelity, interactive browser visualizations.

### 1. Premium Visualizer (vis.js) — Recommended
A robust, self-contained explorer with a pitch-black neon aesthetic.
```bash
python skills/graph-visualizer/scripts/visualize_graph.py --input output/knowledge_graph.json
```
- **Robust Mapping**: Reliable handling of `id`, `label`, and relationship IDs.
- **Physics-Powered**: ForceAtlas2 layout for optimal spatial clarity.
- **Detail Inspector**: Click nodes to see verbatim citations and confidence.

### 2. High-Performance Explorer (Sigma.js)
WebGL-powered rendering for exceptionally large graphs (thousands of nodes).
```bash
python skills/graph-visualizer-sigma/scripts/visualize_sigma.py --input output/knowledge_graph.json
```

---

## 🕸️ Skill Triggers

MalimGraph provides specialized agentic skills. Trigger them via natural language:

- **"knowledge graph"** — Full extraction and export
- **"visualise graph"** — Launch visual explorer
- **"chunk for RAG"** — Prepare document for vector embeddings
- **"load into Neo4j"** — Import to local graph database

---

## 🛠️ Tools & Capabilities

- `read_pdf`: PDF → text + rule-extracted metadata.
- `save_knowledge_graph`: Stable CID-based graph construction.
- `chunk_document`: Token-aware overlapping chunks for RAG.
- `manage_graph_db`: Load and query Neo4j or PostgreSQL (Apache AGE).
- `embed_and_store_chunks`: Native pgvector integration.

---

## ☁️ MCP Server Endpoint
Deploy MalimGraph as a serverless MCP endpoint on:
`https://mcpserver.malim.my/mcp` (Streamable HTTP)

---

## Credits
Built by **[Malim AI Labs](https://ailabs.malim.my)** — AI-powered knowledge infrastructure.
MIT License © 2026.
