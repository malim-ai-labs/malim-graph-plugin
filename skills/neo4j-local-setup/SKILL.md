---
name: neo4j-local-setup
description: >
  Set up and populate a local Neo4j instance from a MalimGraph knowledge_graph.json file.
  Use this skill when the user wants to: spin up Neo4j locally, create a new Neo4j database,
  load a knowledge graph into a local Neo4j instance, or browse a graph in Neo4j Browser.
  Trigger on: "create Neo4j instance", "spin up Neo4j", "local Neo4j", "set up graph database",
  "load graph locally", "Neo4j Desktop", "start Neo4j", "run Neo4j", "Neo4j Docker",
  "import graph into Neo4j", "browse graph", "Neo4j Browser".
  This skill handles local database setup only — for cloud/managed Neo4j Aura, use graph-db-admin.
---

# Neo4j Local Instance Skill

Spin up a local Neo4j instance and load a MalimGraph `knowledge_graph.json` into it.

## Prerequisites

Choose **one** of the following installation methods:

### Option A — Docker (recommended, zero installation)

```bash
docker pull neo4j:latest
```

### Option B — Neo4j Desktop (GUI, Windows/macOS/Linux)

Download from: https://neo4j.com/download/

### Option C — Direct binary (Linux/macOS)

```bash
# Download & extract
curl -L https://dist.neo4j.org/neo4j-community-5.20.0-unix.tar.gz | tar xz
# Add to PATH
export PATH=$PWD/neo4j-community-5.20.0/bin:$PATH
```

---

## Step 1 — Start Neo4j

### Docker

```bash
python scripts/start_neo4j.py --method docker --password your_password
```

This runs:

```bash
docker run -d \
  --name malimgraph-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  -v "$PWD/neo4j-data:/data" \
  neo4j:latest
```

The `-v neo4j-data:/data` flag persists the graph to a local folder so data survives restarts.

### Neo4j Desktop

1. Open Neo4j Desktop → **New Project** → **Add** → **Local DBMS**
2. Set a password → **Start**
3. Note the Bolt URI shown (usually `bolt://localhost:7687`)

---

## Step 2 — Wait for Neo4j to be ready

```bash
python scripts/start_neo4j.py --wait --uri bolt://localhost:7687 --password your_password
```

Polls until the DBMS accepts connections (up to 60 seconds).

---

## Step 3 — Load the knowledge graph

```bash
python scripts/load_to_neo4j.py \
  --input ./output/knowledge_graph.json \
  --uri bolt://localhost:7687 \
  --user neo4j \
  --password your_password
```

Creates:
- One **node** per entity (label = entity type, e.g. `:Organization`, `:Person`)
- One **relationship** per entry in `relationships[]`
- Provenance as node/edge properties: `source_text`, `source_pages`, `confidence`
- Uses `MERGE` — safe to run multiple times, no duplicates

---

## Step 4 — Open Neo4j Browser

```
http://localhost:7474
```

Login with `neo4j` / `your_password`.

### Starter Cypher queries

```cypher
// See all entity types and counts
MATCH (n) RETURN labels(n)[0] AS type, count(n) AS total ORDER BY total DESC;

// Find all organizations
MATCH (n:Organization) RETURN n.label, n.confidence, n.source_pages LIMIT 20;

// Find entities on page 3
MATCH (n) WHERE 3 IN n.source_pages RETURN n.label, labels(n)[0] AS type;

// Explore relationships from an entity
MATCH (a {label: 'Malim AI Labs'})-[r]->(b) RETURN a.label, type(r), b.label;

// High-confidence entities only
MATCH (n) WHERE n.confidence = 'high' RETURN n.type, n.label LIMIT 50;
```

---

## Step 5 — Stop Neo4j (Docker)

```bash
docker stop malimgraph-neo4j
docker rm malimgraph-neo4j
```

Data persists in `./neo4j-data/` — restart any time with Step 1.

---

## Environment Variables (optional)

Set these to skip passing flags every time:

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Connection refused` | Neo4j hasn't started yet — re-run `--wait` |
| `Docker not found` | Install Docker Desktop from https://docker.com |
| `Port in use` | Change `-p 7475:7474 -p 7688:7687` and update `NEO4J_URI` port |
| `Auth failed` | Check password matches what was set in `NEO4J_AUTH` |
| `knowledge_graph.json not found` | Run `read_pdf` + `save_knowledge_graph` first to generate it |
