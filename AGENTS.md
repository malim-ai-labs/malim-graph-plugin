# MalimGraph — Agent Configuration

> Agentic knowledge graph plugin for Claude Code, Codex, and OpenClaw.
> Compatible with any agent runtime that supports MCP tools or function calling.

## Setup

```bash
pip install malimgraph
```

**Claude Code / Claude Desktop:**
```bash
claude mcp add malimgraph -- malimgraph-plugin
```

**Codex / OpenAI Agents SDK:**
```python
from openai import OpenAI
import subprocess, json

# Start MalimGraph MCP server
# malimgraph-plugin runs in stdio mode, wrap with your MCP client adapter
```

**Any MCP-compatible runtime:**
```json
{
  "mcpServers": {
    "malimgraph": {
      "command": "malimgraph-plugin"
    }
  }
}
```

## Agent Definitions

### KnowledgeGraphAgent

**Purpose:** Extract structured knowledge graphs from PDF documents.

**Trigger phrases:**
- "extract knowledge graph from [file]"
- "build a graph from this PDF"
- "map out the entities in [file]"
- "PDF to Neo4j / PDF to Cypher"

**Decision tree:**
```
Input: PDF path
  ├── Call read_pdf(pdf_path)
  ├── Analyze returned page_text for entities and relationships
  │     ├── Use rule_extracted_entities as baseline
  │     └── Add semantic entities with source_text evidence
  ├── Call save_knowledge_graph(entities, relationships, output_format="all")
  └── Return: knowledge_graph.json, .cypher, .sql paths + summary stats
```

**Required tool sequence:** `read_pdf` → *(agent extraction)* → `save_knowledge_graph`

**No API key required.** Agent intelligence handles semantic extraction.

---

### RAGAgent

**Purpose:** Prepare PDF documents for semantic search and RAG pipelines.

**Trigger phrases:**
- "chunk for RAG"
- "prepare for vector database"
- "embed document for semantic search"
- "split PDF for Pinecone / Weaviate / pgvector"

**Decision tree:**
```
Input: PDF path, optional embedding config
  ├── Call chunk_document(pdf_path, chunk_size=512, chunk_overlap=64)
  ├── If PGVECTOR_URI available:
  │     └── Call embed_and_store_chunks(chunks_path, embedding_provider)
  └── Return: chunks saved, embeddings stored (if configured)
```

**Required tool sequence:** `chunk_document` → `embed_and_store_chunks` (optional)

---

### GraphDBAgent

**Purpose:** Load, query, and manage knowledge graphs in graph databases.

**Trigger phrases:**
- "load into Neo4j / Apache AGE"
- "run Cypher query"
- "graph database statistics"
- "drop graph / list graphs"

**Decision tree:**
```
Input: action, connection params, optional query
  ├── load   → manage_graph_db(action="load", knowledge_graph_path, target, connection_uri)
  ├── query  → manage_graph_db(action="query", cypher_query, target, connection_uri)
  ├── stats  → manage_graph_db(action="stats", target, connection_uri)
  ├── drop   → manage_graph_db(action="drop", graph_name, target, connection_uri)
  └── list   → manage_graph_db(action="list_graphs", target, connection_uri)
```

---

### DocumentHTMLAgent

**Purpose:** Convert PDFs into structured, LLM-readable HTML pages.

**Trigger phrases:**
- "render PDF as HTML"
- "convert document to web page"
- "make PDF browsable"
- "LLM-readable document"

**Decision tree:**
```
Input: PDF path, optional knowledge_graph.json
  ├── Call render_document_html(pdf_path, knowledge_graph_path, output_path)
  └── Return: HTML file path, page count, size
```

---

### FullPipelineAgent

**Purpose:** End-to-end PDF processing — graph + chunks + embeddings + HTML.

**Trigger phrases:**
- "full pipeline on [file]"
- "extract and embed [file]"
- "complete knowledge graph workflow"

**Decision tree:**
```
Input: PDF path, output config
  ├── Step 1: read_pdf(pdf_path)
  ├── Step 2: *(agent)* extract entities + relationships
  ├── Step 3: save_knowledge_graph(..., output_format="all")
  ├── Step 4: chunk_document(pdf_path, output_format="json")
  ├── Step 5: embed_and_store_chunks(...) [if PGVECTOR_URI set]
  ├── Step 6: render_document_html(pdf_path, knowledge_graph_path)
  └── Return: all output paths + stats
```

---

### SelfEvolvingOrchestratorAgent

**Purpose:** Autonomous Knowledge Core & Self-Evolving Graph Orchestrator. Maintain, expand, and self-correct a dynamic network of concepts ($G = (V, E)$) on every single API call.

**Trigger phrases:**
- "orchestrator"
- "self-evolving graph"
- "knowledge core"
- "dynamic network of concepts"
- "upsert concept / link concept / classify domain"

**System Prompt / Operational Environment:**
- **[USER_QUERY]:** The semantic question or instruction from the user.
- **[VECTOR_CONTEXT]:** Closely matched text snippets from a vector database ($pgvector$).
- **[GRAPH_CONTEXT]:** Local subgraphs, current categories, and neighboring nodes matching the query keywords.

**Decision Tree / Internal Monologue:**
1. **Analyze Context gaps:** Identify missing connections or edges between concepts mentioned together in `[VECTOR_CONTEXT]` that aren't in `[GRAPH_CONTEXT]`.
2. **Evaluate Taxonomy:** Introduce new sub-categories or macro-cluster nodes if concepts are becoming too broad.
3. **Resolve Contradictions:** Update, clarify, or override older properties on existing concept nodes.

**Required tool sequence:** `upsert_node` / `link_concepts` / `classify_domain` (as needed based on context analysis)

---

### BibliographicMetadataAgent

**Purpose:** Extract book bibliographic metadata (ISBN, publisher, author, published date, genre, etc.) for library cataloging in the knowledge graph.

**Trigger phrases:**
- "prepare bibliographic metadata"
- "extract book metadata from [file]"
- "library cataloging for [file]"
- "extract ISBN, author, publisher from [file]"

**Decision tree:**
```
Input: PDF path
  ├── Call read_pdf(pdf_path)
  ├── Analyze returned text and rule_extracted_entities (e.g. ISBNs)
  ├── Extract book bibliographic metadata (Book, Author, Publisher, PublishedDate, Genre, Language, Edition, Description)
  ├── Call save_knowledge_graph(entities, relationships, output_format="all")
  └── Return: bibliographic_metadata + summary stats
```

**Required tool sequence:** `read_pdf` → *(agent extraction)* → `save_knowledge_graph`

## Tool Schemas (OpenAI Function Calling Format)

```json
[
  {
    "name": "read_pdf",
    "description": "Read a PDF and return page text, headings, and rule-extracted entities (dates, amounts, emails, legal references). Call this first. Analyze the returned text to extract semantic entities and relationships, then call save_knowledge_graph.",
    "parameters": {
      "type": "object",
      "properties": {
        "pdf_path": {"type": "string", "description": "Absolute or relative path to the PDF file"}
      },
      "required": ["pdf_path"]
    }
  },
  {
    "name": "save_knowledge_graph",
    "description": "Build and save a knowledge graph from entities and relationships you extracted. Every entity and relationship must include source_text (verbatim quote from document) and source_pages.",
    "parameters": {
      "type": "object",
      "properties": {
        "source_file": {"type": "string", "description": "PDF filename"},
        "entities": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "label": {"type": "string"},
              "type": {"type": "string", "description": "Organization, Person, Location, Regulation, Product, Concept, Role, Event"},
              "source_text": {"type": "string", "description": "Verbatim quote ≤200 chars"},
              "source_pages": {"type": "array", "items": {"type": "integer"}},
              "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
              "properties": {"type": "object"}
            },
            "required": ["label", "type", "source_text", "source_pages", "confidence"]
          }
        },
        "relationships": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "source_label": {"type": "string"},
              "source_type": {"type": "string"},
              "target_label": {"type": "string"},
              "target_type": {"type": "string"},
              "type": {"type": "string", "description": "UPPER_SNAKE_CASE e.g. LED_BY, GOVERNED_BY"},
              "source_text": {"type": "string", "description": "Verbatim quote proving this relationship"},
              "source_pages": {"type": "array", "items": {"type": "integer"}},
              "confidence": {"type": "string", "enum": ["high", "medium", "low"]}
            },
            "required": ["source_label", "source_type", "target_label", "target_type", "type", "source_text"]
          }
        },
        "output_dir": {"type": "string", "default": "./output"},
        "output_format": {"type": "string", "enum": ["json", "cypher", "age_sql", "all"], "default": "all"},
        "graph_name": {"type": "string", "default": "document_graph"}
      },
      "required": ["source_file", "entities", "relationships"]
    }
  },
  {
    "name": "chunk_document",
    "description": "Split a PDF into overlapping text chunks for RAG / embedding pipelines.",
    "parameters": {
      "type": "object",
      "properties": {
        "pdf_path": {"type": "string"},
        "chunk_size": {"type": "integer", "default": 512},
        "chunk_overlap": {"type": "integer", "default": 64},
        "output_dir": {"type": "string", "default": "./chunks"},
        "output_format": {"type": "string", "enum": ["json", "txt", "md"], "default": "json"}
      },
      "required": ["pdf_path"]
    }
  },
  {
    "name": "render_document_html",
    "description": "Render a PDF as structured HTML with page anchors, TOC, and entity annotations.",
    "parameters": {
      "type": "object",
      "properties": {
        "pdf_path": {"type": "string"},
        "knowledge_graph_path": {"type": "string"},
        "output_path": {"type": "string", "default": "document.html"},
        "include_toc": {"type": "boolean", "default": true},
        "include_search": {"type": "boolean", "default": true}
      },
      "required": ["pdf_path"]
    }
  },
  {
    "name": "manage_graph_db",
    "description": "Load, query, and manage knowledge graphs in Neo4j or Apache AGE (PostgreSQL).",
    "parameters": {
      "type": "object",
      "properties": {
        "action": {"type": "string", "enum": ["load", "query", "stats", "drop", "list_graphs"]},
        "knowledge_graph_path": {"type": "string"},
        "target": {"type": "string", "enum": ["neo4j", "age"], "default": "neo4j"},
        "connection_uri": {"type": "string"},
        "graph_name": {"type": "string", "default": "document_graph"},
        "cypher_query": {"type": "string"},
        "user": {"type": "string"},
        "password": {"type": "string"}
      },
      "required": ["action"]
    }
  },
  {
    "name": "embed_and_store_chunks",
    "description": "Generate embeddings for document chunks and store in PostgreSQL pgvector.",
    "parameters": {
      "type": "object",
      "properties": {
        "chunks_path": {"type": "string", "description": "Path to chunks.json"},
        "connection_uri": {"type": "string"},
        "table_name": {"type": "string", "default": "document_chunks"},
        "embedding_provider": {"type": "string", "enum": ["openai", "voyage", "local"], "default": "openai"},
        "embedding_model": {"type": "string"},
        "document_id": {"type": "string"},
        "skip_existing": {"type": "boolean", "default": true}
      },
      "required": ["chunks_path"]
    }
  },
  {
    "name": "upsert_node",
    "description": "Create or update a concept node in the knowledge base. Properties must include a concise, minimalist definition.",
    "parameters": {
      "type": "object",
      "properties": {
        "node_id": {"type": "string", "description": "Unique stable identifier for the concept"},
        "label": {"type": "string", "description": "Canonical human-readable name of the concept"},
        "category": {"type": "string", "description": "Structural/taxonomic type of the node"},
        "properties": {
          "type": "object",
          "description": "Properties dictionary. MUST include 'definition' or 'description'"
        },
        "output_dir": {"type": "string", "default": "./output"}
      },
      "required": ["node_id", "label", "category", "properties"]
    }
  },
  {
    "name": "link_concepts",
    "description": "Forge a directional edge between two concepts with context justification.",
    "parameters": {
      "type": "object",
      "properties": {
        "source_id": {"type": "string", "description": "Source concept node ID"},
        "target_id": {"type": "string", "description": "Target concept node ID"},
        "relation_type": {"type": "string", "description": "UPPER_SNAKE_CASE relationship type (e.g. OPTIMIZES, LED_BY)"},
        "context_justification": {"type": "string", "description": "Explanation/quote justifying the link"},
        "output_dir": {"type": "string", "default": "./output"}
      },
      "required": ["source_id", "target_id", "relation_type", "context_justification"]
    }
  },
  {
    "name": "classify_domain",
    "description": "Register a macro-level category or taxonomic class to group dense sub-nodes.",
    "parameters": {
      "type": "object",
      "properties": {
        "category_id": {"type": "string", "description": "Unique identifier/name for the category"},
        "description": {"type": "string", "description": "Description of the category/domain"},
        "output_dir": {"type": "string", "default": "./output"}
      },
      "required": ["category_id", "description"]
    }
  }
]
```

## Agentic Principles

1. **Evidence-first:** Every extracted fact requires `source_text` — a verbatim quote from the document. Never invent entities.
2. **Parallel where possible:** chunk_document and render_document_html can run in parallel after read_pdf.
3. **Incremental output:** Save outputs after each step so partial results survive failures.
4. **Provenance chain:** `source_pages` + `source_text` + `chunk_id` must be traceable end-to-end.
5. **No hallucination:** If confidence is "low", mark it — do not omit or upgrade without evidence.
