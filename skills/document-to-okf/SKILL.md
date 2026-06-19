---
name: document-to-okf
description: >
  Convert a PDF document into an Open Knowledge Format (OKF) bundle — a portable,
  vendor-neutral set of cross-linked Markdown files with YAML frontmatter, one file
  per entity, organized by entity type. Trigger on: "OKF", "open knowledge format",
  "markdown knowledge bundle", "linked markdown graph", "agent-readable knowledge files",
  "export to OKF", "knowledge catalog format". This skill does NOT handle: Cypher/AGE
  SQL generation (use pdf-to-knowledge-graph), HTML rendering (use document-to-html),
  or chunking for embeddings (use pdf-to-chunks).
---

# Document to OKF Skill

Convert any PDF into an [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog)
bundle: plain Markdown files with YAML frontmatter, cross-linked into a graph via
relative Markdown links. Unlike `knowledge_graph.json` (a single file) or Cypher/AGE
SQL (database import scripts), an OKF bundle is human-readable, git-friendly, and
consumable by any agent or tool without a database or proprietary SDK.

## Two Ways to Run This

### A. Via the MCP tool (recommended — works directly from the attached document)

```
1. Call read_pdf(pdf_path="document.pdf")
2. Read the page text, identify entities (Organization, Person, Concept, etc.)
   and relationships (UPPER_SNAKE_CASE) with verbatim source_text, per CLAUDE.md.
3. Call save_knowledge_graph(
     source_file="document.pdf",
     entities=[...],
     relationships=[...],
     output_dir="./output",
     output_format="okf"          # or "all" to also get json/cypher/age_sql
   )
4. Report the path to ./output/okf/index.md as the bundle entry point.
```

`output_format="okf"` writes the bundle directly from the entities/relationships
you extracted — no intermediate file needed.

### B. Standalone script (from an existing `knowledge_graph.json`)

If you already have a `knowledge_graph.json` (e.g. from the `pdf-to-knowledge-graph`
skill), render it as OKF without re-extracting:

```bash
python skills/document-to-okf/scripts/generate_okf.py \
  --input knowledge_graph.json \
  --output-dir ./output
```

**Flags:**
- `--input PATH` — path to `knowledge_graph.json` (required)
- `--output-dir DIR` — directory under which an `okf/` bundle is written (default: `.`)

## Bundle Structure

```
output/okf/
├── index.md                       # bundle root — links to every type index
├── organization/
│   ├── index.md                   # all Organization entities
│   └── malim-ai-labs.md
├── person/
│   ├── index.md
│   └── ahmad-fadzillah.md
└── regulation/
    ├── index.md
    └── data-protection-act-2010.md
```

Folder names are slugified entity types; file names are slugified entity labels.
Collisions (two entities with the same label and type) get a `-2`, `-3`, ... suffix.

## Entity File Format

```markdown
---
type: Organization
title: Malim AI Labs
description: "Malim AI Labs Social Enterprise was incorporated in 2023..."
confidence: high
extraction_method: hybrid
source_pages: [1, 3]
tags: [Organization]
---
# Malim AI Labs

> Malim AI Labs Social Enterprise was incorporated in 2023...

## Relationships
- **LED_BY** → [Ahmad Fadzillah](../person/ahmad-fadzillah.md)
- **REGULATES** ← [Data Protection Act 2010](../regulation/data-protection-act-2010.md)

## Citations
- p.1: "...verbatim quote from page 1..."
```

Only `type` is required by the OKF spec — everything else (`title`, `description`,
`tags`, `source_pages`, etc.) is producer-defined metadata MalimGraph adds for
provenance. Relationships render as direction-aware Markdown links (`→` outgoing,
`←` incoming) so the bundle is browseable as a graph in any Markdown viewer
(including GitHub) and re-parseable by other OKF-aware agents.

## Edge Cases

- **No relationships for an entity:** the `## Relationships` section is omitted.
- **Entity referenced but never extracted as a node:** falls back to plain text
  instead of a broken link (shouldn't happen via `save_knowledge_graph`, which
  auto-creates stub entities for referenced labels).
- **Very large graphs:** one file per entity scales fine for Markdown tooling;
  for graphs with thousands of entities, consider filtering `entity_types` at
  extraction time first.
- **Re-running:** the bundle is regenerated wholesale each run; it does not
  merge with a previously hand-edited bundle.
