---
name: pdf-to-knowledge-graph
description: >
  Extract structured knowledge graphs from PDF documents. Use this skill whenever the user
  wants to convert a PDF into entities and relationships, produce a knowledge graph dataset,
  generate Cypher for Neo4j/Memgraph, or Apache AGE SQL for PostgreSQL. Trigger on:
  "knowledge graph", "extract entities from PDF", "PDF to Cypher", "PDF to Neo4j",
  "entity extraction", "relationship mapping", "PDF to graph", "PDF to AGE",
  "graph dataset from document", "build a graph from this PDF", "map out the entities",
  "entity relationship diagram from document". This skill does NOT handle: embedding chunks
  (use pdf-to-chunks), HTML rendering (use document-to-html), or database loading
  (use graph-db-admin).
---

# PDF to Knowledge Graph Skill

Convert any PDF into a structured knowledge graph with full citation provenance.

## Dependencies

```bash
pip install pymupdf anthropic pydantic --break-system-packages
```

Set your API key:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Quick Start

```bash
# Step 1: Extract text structure from PDF
python extract_text.py --input /path/to/document.pdf --output extracted_text.json

# Step 2: Build knowledge graph (rule-based + LLM)
python build_knowledge_graph.py \
  --input extracted_text.json \
  --output knowledge_graph.json \
  --entity-types auto

# Step 3: Generate Cypher and AGE SQL files
python generate_graph_files.py \
  --input knowledge_graph.json \
  --output-dir /mnt/user-data/outputs/ \
  --formats cypher,age
```

## Workflow Detail

### Step 1 — `extract_text.py`

Reads the PDF using PyMuPDF and outputs a page-by-page JSON with:
- `text`: full extracted text per page
- `headings`: detected heading strings (bold + larger font)
- `has_table`: whether a table was detected
- `is_scanned`: whether the page appears to be a scanned image

**Flags:**
- `--input PATH` — PDF file path (required)
- `--output PATH` — output JSON path (default: `extracted_text.json`)

### Step 2 — `build_knowledge_graph.py`

Two-pass hybrid extraction:
1. **Rule pass** — regex patterns for dates, amounts, emails, legal references, section numbers
2. **LLM pass** — Anthropic API (claude-opus-4-7) for semantic entities + relationships

Merging rules:
- Same entity ID (hash of type+label) from both passes → `extraction_method: hybrid`, `confidence: high`
- LLM wins on semantic typing; rules win on structured data (dates, amounts)
- All citations accumulated in `citations[]` array

**Flags:**
- `--input PATH` — extracted_text.json from Step 1
- `--output PATH` — output knowledge_graph.json
- `--entity-types auto|TYPE1,TYPE2` — focus on specific types or let the LLM decide
- `--graph-name NAME` — graph name embedded in metadata

### Step 3 — `generate_graph_files.py`

Converts `knowledge_graph.json` into:
- `.cypher` — Neo4j/Memgraph import script with MERGE statements and all provenance as properties
- `.sql` — Apache AGE (PostgreSQL) import script

**Flags:**
- `--input PATH` — knowledge_graph.json
- `--output-dir DIR` — directory for output files
- `--formats cypher,age` — comma-separated: `cypher`, `age`, or `all`
- `--graph-name NAME` — graph name for AGE SQL

## Output Schema — `knowledge_graph.json`

```json
{
  "metadata": {
    "source_file": "document.pdf",
    "extracted_at": "2025-01-01T00:00:00Z",
    "total_entities": 42,
    "total_relationships": 18,
    "entity_types": ["Organization", "Person", "Date", "Regulation"],
    "relationship_types": ["SIGNED_BY", "REGULATES", "LOCATED_IN"]
  },
  "entities": [
    {
      "id": "e_a1b2c3d4",
      "label": "Malim AI Labs",
      "type": "Organization",
      "properties": {},
      "extraction_method": "hybrid",
      "confidence": "high",
      "source_pages": [1, 3],
      "source_text": "Malim AI Labs Social Enterprise was incorporated in 2023...",
      "source_chunk_id": "llm_p1_p2",
      "source_chunk_ids": ["page_1", "llm_p1_p2"],
      "citations": [
        {
          "text": "...verbatim quote from page 1...",
          "pages": [1],
          "chunk_id": "page_1",
          "extraction_method": "rule"
        }
      ]
    }
  ],
  "relationships": [
    {
      "id": "r_ff1e2d3c",
      "source": "e_a1b2c3d4",
      "target": "e_b2c3d4e5",
      "type": "SIGNED_BY",
      "confidence": "high",
      "extraction_method": "llm",
      "source_pages": [2],
      "source_text": "The agreement was signed by...",
      "citations": [...]
    }
  ]
}
```

### Provenance Fields Reference

| Field | On | Description |
|-------|-----|-------------|
| `source_pages` | Entity, Relationship | PDF page numbers where found |
| `source_text` | Entity, Relationship | Verbatim primary quote (≤500 chars) |
| `source_chunk_id` | Entity, Relationship | Processing chunk ID |
| `citations[]` | Entity, Relationship | All supporting quotes with page refs |
| `confidence` | Entity, Relationship | `high` / `medium` / `low` |
| `extraction_method` | Entity, Relationship | `rule` / `llm` / `hybrid` |
| `citation_count` | Node property in graph DB | Number of supporting citations |

## Entity Types

Default auto-detected types include: Organization, Person, Location, Date, Regulation,
LegalReference, MonetaryAmount, Percentage, Product, Role, Concept, Event, Email, URL.

Override with `--entity-types "Organization,Person,Contract,Clause"`.

## Edge Cases

- **Large PDFs (100+ pages):** Processing happens page-by-page. Each LLM chunk covers 2-4 pages. Expect ~1 min per 10 pages.
- **Scanned PDFs:** Pages with `is_scanned: true` will have minimal text. Use OCR (e.g., `ocrmypdf`) to pre-process.
- **Confidential documents:** The Anthropic API sees document text. Use `--entity-types` to restrict scope if needed.
- **No ANTHROPIC_API_KEY:** Rule-based extraction still runs and produces a partial graph.
