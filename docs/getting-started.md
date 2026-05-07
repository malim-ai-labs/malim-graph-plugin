# Getting Started

## Installation

```bash
pip install malimgraph

# With Neo4j support
pip install "malimgraph[neo4j]"

# With Apache AGE support
pip install "malimgraph[age]"

# Everything
pip install "malimgraph[all]"
```

## Set Your API Key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Quick Start — CLI

```bash
# 1. Extract a knowledge graph from a PDF
malimgraph extract --input report.pdf --output ./output/ --format all

# 2. Split PDF into embedding chunks
malimgraph chunk --input report.pdf --output ./chunks/ --chunk-size 512

# 3. Render as structured HTML
malimgraph render --input report.pdf --output document.html

# 4. Load into Neo4j
malimgraph db load --input ./output/knowledge_graph.json --target neo4j \
  --uri bolt://localhost:7687 --user neo4j --password secret
```

## Quick Start — MCP Server

```bash
malimgraph serve
```

See [mcp-server.md](mcp-server.md) for Claude Desktop / claude.ai setup.

## Quick Start — Python API

```python
from malimgraph.core.pdf_reader import extract_text_from_pdf
from malimgraph.core.rule_extractor import extract_by_rules
from malimgraph.core.llm_extractor import extract_by_llm
from malimgraph.core.graph_builder import build_knowledge_graph

doc = extract_text_from_pdf("report.pdf")
rule_entities = extract_by_rules(doc)
llm_entities, llm_rels = extract_by_llm(doc)
kg = build_knowledge_graph(doc, rule_entities, llm_entities, llm_rels)

print(f"Extracted {kg.metadata.total_entities} entities")
```
