---
name: bibliographic-metadata
description: >
  Extract book bibliographic metadata (ISBN, publisher, author, published date, genre, etc.)
  from PDFs and store them in the knowledge graph.
triggers:
  - "prepare bibliographic metadata"
  - "extract book metadata from"
  - "library cataloging for"
  - "extract ISBN, author, publisher from"
skip_if:
  - "chunk for RAG"
  - "render HTML"
---

# Bibliographic Metadata Extraction Skill

Extract cataloging details (ISBN, Author, Publisher, PublishedDate, Genre, Language, Edition, Description) from documents and represent them structurally in the knowledge graph.

## Workflow

1. **read_pdf(pdf_path)**: Read book PDF text, extracting ISBNs automatically using built-in rule regexes.
2. **Extract Book Entities & Relationships**:
   - Classify/identify entities: `Book`, `Author`, `Publisher`, `Genre`, `ISBN`.
   - Relate them: `Book` -> `WRITTEN_BY` -> `Author`, `Book` -> `PUBLISHED_BY` -> `Publisher`, `Book` -> `HAS_ISBN` -> `ISBN`.
3. **save_knowledge_graph(source_file, entities, relationships)**: Build and save the structured cataloging graph.
