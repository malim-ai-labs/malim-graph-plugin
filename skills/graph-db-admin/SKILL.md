---
name: graph-db-admin
description: >
  Load, query, and manage knowledge graphs in Neo4j or PostgreSQL with Apache AGE.
  Use this skill when the user wants to import a knowledge graph into a database, run
  Cypher queries, check graph statistics, or manage graph instances. Trigger on:
  "load into Neo4j", "import graph", "load knowledge graph into database",
  "query graph database", "Cypher query", "graph DB", "Apache AGE", "AGE SQL",
  "connect to Neo4j", "graph statistics", "drop graph", "list graphs",
  "load into PostgreSQL graph", "graph database admin". This skill does NOT handle:
  knowledge graph extraction (use pdf-to-knowledge-graph) — it only manages the
  database side: loading, querying, and administering.
---

# Graph DB Admin Skill

Load, query, and manage knowledge graphs in Neo4j or PostgreSQL with Apache AGE.

## Dependencies

For Neo4j:
```bash
pip install neo4j --break-system-packages
```

For Apache AGE (PostgreSQL):
```bash
pip install psycopg2-binary --break-system-packages
```

## Environment Variables

```bash
# Neo4j
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password

# Apache AGE
export AGE_CONNECTION_URI="host=localhost dbname=mydb user=postgres password=secret"
```

## Quick Start

### Load into Neo4j
```bash
python load_graph.py \
  --input knowledge_graph.json \
  --target neo4j \
  --uri bolt://localhost:7687 \
  --user neo4j \
  --password your_password
```

### Load into Apache AGE (PostgreSQL)
```bash
python load_graph.py \
  --input knowledge_graph.json \
  --target age \
  --uri "host=localhost dbname=mydb user=postgres password=secret" \
  --graph-name doc_graph
```

### Run a Cypher Query
```bash
python query_graph.py \
  --target neo4j \
  --uri bolt://localhost:7687 \
  --user neo4j --password your_password \
  --query "MATCH (n:Organization) RETURN n.label, n.source_pages LIMIT 10"
```

### Graph Statistics
```bash
python manage_graph.py \
  --action stats \
  --target neo4j \
  --uri bolt://localhost:7687
```

### Drop a Graph (AGE only)
```bash
python manage_graph.py \
  --action drop \
  --target age \
  --uri "host=localhost dbname=mydb user=postgres" \
  --graph-name doc_graph
```

### List All Graphs (AGE only)
```bash
python manage_graph.py \
  --action list_graphs \
  --target age \
  --uri "host=localhost dbname=mydb user=postgres"
```

## Workflow Detail

### `load_graph.py`

Reads `knowledge_graph.json` and creates:
- **Nodes**: one node per entity, with type as node label, and all provenance as properties
- **Edges**: one relationship per item in `relationships[]`, with type as relationship type
- Uses `MERGE` (not `CREATE`) for idempotent loading — safe to run multiple times

Provenance properties stored on every node/edge:
- `id`, `label`, `confidence`, `extraction_method`
- `source_pages` (list), `source_text`, `source_chunk_id`
- `citation_count`, `citation_texts` (first 5)

**Flags:**
- `--input PATH` — knowledge_graph.json (required)
- `--target neo4j|age` — database target (default: neo4j)
- `--uri URI` — connection URI (or use env var)
- `--user USER` — Neo4j username (or use NEO4J_USER)
- `--password PASS` — Neo4j password (or use NEO4J_PASSWORD)
- `--graph-name NAME` — graph name for AGE (default: document_graph)

### `query_graph.py`

Runs arbitrary Cypher queries and returns formatted JSON results.

**Flags:**
- `--target neo4j|age`
- `--uri`, `--user`, `--password`, `--graph-name` — same as above
- `--query CYPHER` — Cypher query string (required)
- `--output PATH` — optional JSON file to write results to

### `manage_graph.py`

Graph administration actions.

**Flags:**
- `--action stats|drop|list_graphs` (required)
- `--target neo4j|age`
- `--uri`, `--user`, `--password`, `--graph-name` — same as above

## Useful Cypher Queries

```cypher
-- Find all organizations
MATCH (n:Organization) RETURN n.label, n.confidence, n.source_pages LIMIT 20;

-- Find entities on a specific page
MATCH (n) WHERE 5 IN n.source_pages RETURN n.label, n.type;

-- Find all relationships from an entity
MATCH (a {label: 'Malim AI Labs'})-[r]->(b) RETURN a.label, type(r), b.label;

-- Find high-confidence entities only
MATCH (n) WHERE n.confidence = 'high' RETURN n.type, count(n) ORDER BY count(n) DESC;

-- Find entities with multiple citations
MATCH (n) WHERE n.citation_count > 2 RETURN n.label, n.type, n.citation_count ORDER BY n.citation_count DESC;
```

## Database Setup Guides

### Neo4j (Local)
```bash
docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest
```
Open Neo4j Browser at http://localhost:7474

### Apache AGE (PostgreSQL with AGE extension)
```bash
docker run -p 5432:5432 \
  -e POSTGRES_PASSWORD=secret \
  apache/age:latest
```
Connect: `psql -h localhost -U postgres`

## Edge Cases

- **Auth failures:** Check URI format and credentials. Neo4j: `bolt://host:7687`. AGE: standard psycopg2 DSN.
- **Missing AGE extension:** Run `CREATE EXTENSION IF NOT EXISTS age;` as superuser first.
- **Network access in claude.ai sandbox:** Use a publicly accessible database instance or ngrok tunnel.
- **Large graphs:** Loading 10,000+ nodes may take a few minutes. The script prints progress per entity.
