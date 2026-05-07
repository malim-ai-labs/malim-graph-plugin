---
name: graph-query
description: >
  Load knowledge graphs into Neo4j or PostgreSQL Apache AGE, run Cypher queries,
  view statistics, and manage graph instances.
triggers:
  - "load into Neo4j"
  - "load into AGE"
  - "graph database"
  - "Cypher query"
  - "graph statistics"
  - "drop graph"
  - "list graphs"
  - "query the graph"
  - "graph DB admin"
skip_if:
  - "knowledge graph extraction"
  - "chunk for RAG"
  - "render HTML"
---

# Graph Database Operations

Load and query knowledge graphs in Neo4j or Apache AGE.

## Actions

### Load
```
manage_graph_db(action="load", knowledge_graph_path="./output/knowledge_graph.json",
                target="neo4j", connection_uri="bolt://localhost:7687")
```

### Query
```
manage_graph_db(action="query",
                cypher_query="MATCH (n:Organization) RETURN n.label, n.source_pages LIMIT 10",
                target="neo4j", connection_uri="bolt://localhost:7687")
```

### Stats
```
manage_graph_db(action="stats", target="neo4j", connection_uri="bolt://localhost:7687")
```

## Quick Setup

**Neo4j:**
```bash
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest
```

**Apache AGE:**
```bash
docker run -p 5432:5432 -e POSTGRES_PASSWORD=secret apache/age:latest
```

## Environment Variables

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=yourpassword
AGE_CONNECTION_URI=host=localhost dbname=mydb user=postgres password=secret
```
