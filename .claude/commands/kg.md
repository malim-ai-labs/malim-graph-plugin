---
name: kg
description: Build and traverse explicit semantic knowledge graphs using MalimGraph pipelines.
---

# 🕸️ MalimGraph Knowledge Operations (`/kg`)

You are equipped with MalimGraph, the agentic engine for extracting knowledge from PDFs.

## Primary Workflow

When explicitly instructed to perform knowledge graph operations (or when typing `/kg`), execute the MCP tools systematically:

1. **Information Extraction**: Call `read_pdf` to pull document content and automatically extract rule-based entities.
2. **Analysis**: Synthesize the parsed text to identify Organizations, People, Concepts, and their Relationships natively. Every entity and relationship strictly requires a verbatim `source_text` citation.
3. **Build & Export**: Call `save_knowledge_graph` with your structured lists, targeting the appropriate format output (`json`, `cypher`, `age_sql`, or `all`).
4. **Visualization**: Run the **Premium Visualizer** skill to generate a robust interactive map:
   ```bash
   python skills/graph-visualizer/scripts/visualize_graph.py --input output/knowledge_graph.json
   ```

## Advanced Workflows

Ensure you utilize the following sub-skills seamlessly if queried:
- **Premium Visualization**: Use `skills/graph-visualizer/scripts/visualize_graph.py` for the most robust, self-contained experience.
- **High-Performance (Sigma)**: Use `skills/graph-visualizer-sigma/scripts/visualize_sigma.py` for WebGL-powered rendering of very large graphs (requires manual layout management).
- **Vector Pipeline**: Run `chunk_document` followed by `embed_and_store_chunks` to mount RAG data schemas natively into PostgreSQL pgvector databases.
- **Graph Management**: Run `manage_graph_db` with specific Cypher strings to execute localized graph operations across Neo4j or Postgres Apache AGE.
- **Semantic Exporting**: Use `render_document_html` to emit browseable semantic web exports of a raw input PDF file with full table of contents anchors mapping the parsed entities.
