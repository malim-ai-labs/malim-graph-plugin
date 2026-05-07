---
name: document-to-html
description: >
  Convert PDF documents into structured, LLM-readable HTML pages. Use this skill when the
  user wants to create a browsable HTML version of a PDF, generate a web page from a
  document, or produce an HTML file that an LLM can live-read with page anchors and
  citations. Trigger on: "convert PDF to HTML", "render document as HTML", "make PDF
  browsable", "HTML from PDF", "web page from document", "document viewer", "readable
  HTML", "LLM-readable document", "source document HTML". Produces semantic HTML with
  page anchors (#page-N), table of contents, heading hierarchy, entity annotations from
  knowledge graphs, and search functionality. This skill does NOT handle: knowledge graph
  extraction (use pdf-to-knowledge-graph) or embedding chunks (use pdf-to-chunks).
---

# Document to HTML Skill

Convert any PDF into a structured, dark-themed HTML document with page anchors, table of
contents, entity annotations, and full-text search.

## Dependencies

```bash
pip install pymupdf pydantic --break-system-packages
```

## Quick Start

```bash
# Step 1: Extract text structure from PDF
python extract_text.py --input /path/to/document.pdf --output extracted_text.json

# Step 2: Render to HTML (with optional entity annotations)
python render_html.py \
  --input extracted_text.json \
  --output /mnt/user-data/outputs/document.html \
  --knowledge-graph knowledge_graph.json
```

Without entity annotations:
```bash
python render_html.py --input extracted_text.json --output document.html
```

## Workflow Detail

### Step 1 — `extract_text.py`

Extracts page-by-page text, headings, and block structure from the PDF.

**Flags:**
- `--input PATH` — PDF file path (required)
- `--output PATH` — output JSON path (default: `extracted_text.json`)

### Step 2 — `render_html.py`

Generates a complete single-file HTML document:

**Flags:**
- `--input PATH` — extracted_text.json (required)
- `--output PATH` — output HTML file (default: `document.html`)
- `--knowledge-graph PATH` — knowledge_graph.json for entity `<mark>` annotations (optional)
- `--no-toc` — disable the table of contents sidebar
- `--no-search` — disable the sticky search bar

## HTML Features

### Page Anchors
Every page gets a `<section id="page-N">` element. Jump directly to any page with `#page-5`.

### Table of Contents
A fixed sidebar lists all headings detected in the document, each linking to its page anchor.

### Entity Annotations
When `--knowledge-graph` is provided, entity labels are wrapped in:
```html
<mark
  data-entity-id="e_a1b2c3d4"
  data-entity-type="Organization"
  title="Organization: Malim AI Labs">
  Malim AI Labs
</mark>
```
Hover over highlighted text to see the entity type.

### Search Bar
Sticky search at the top of the page:
- Type text to highlight all matching `<mark>` entities
- Type `page 5` to jump directly to page 5

### Dark Theme
Optimized for extended reading. Print-friendly CSS included (sidebar and search bar hidden in print).

## Output Structure

```html
<body>
  <nav id="toc">              <!-- fixed sidebar with TOC -->
  <main id="main">
    <div id="search-bar">     <!-- sticky search -->
    <section id="page-1">     <!-- page anchor -->
      <div class="page-header">
        <span class="page-label">Page 1</span>
      </div>
      <h2>Document Title</h2>
      <div class="page-content">
        <p>...text with <mark data-entity-id="...">entities</mark> annotated...</p>
      </div>
    </section>
    <section id="page-2"> ...
  </main>
</body>
```

## Edge Cases

- **Very long documents (200+ pages):** HTML file may be large (>5MB). Use `--no-search` for faster rendering.
- **Scanned pages:** Displayed with a "Scanned" badge; text content will be sparse.
- **Documents without headings:** TOC shows "Page N" links instead of heading text.
- **Entity annotations without knowledge graph:** HTML still renders correctly — just no `<mark>` tags.
