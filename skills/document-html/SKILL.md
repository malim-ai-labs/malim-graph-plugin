---
name: document-html
description: >
  Render a PDF as a structured, LLM-readable HTML page with page anchors (#page-N),
  table of contents, entity annotations from a knowledge graph, and full-text search.
triggers:
  - "render HTML"
  - "convert PDF to HTML"
  - "browsable document"
  - "HTML from PDF"
  - "LLM-readable document"
  - "document viewer"
  - "web page from PDF"
skip_if:
  - "knowledge graph"
  - "chunk for RAG"
  - "Neo4j"
---

# Document to HTML

Convert a PDF into a structured, dark-themed HTML document.

## Workflow

```
render_document_html(pdf_path, knowledge_graph_path="./output/knowledge_graph.json",
                     output_path="document.html")
```

## Features

- `<section id="page-N">` anchors — link directly to any page with `#page-5`
- Sidebar table of contents from detected headings
- Entity `<mark>` annotations (requires knowledge_graph.json)
- Sticky search bar — type text or "page N" to jump
- Dark theme, print-friendly CSS, no JS frameworks

## Example

> "Render annual_report.pdf as HTML with entity annotations from ./output/knowledge_graph.json"
