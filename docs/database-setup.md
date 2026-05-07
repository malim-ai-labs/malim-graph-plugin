# Database Setup

## Neo4j

### Docker (recommended)
```bash
docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/yourpassword \
  neo4j:latest
```

Browser UI: http://localhost:7474

### Load a graph
```bash
malimgraph db load \
  --input knowledge_graph.json \
  --target neo4j \
  --uri bolt://localhost:7687 \
  --user neo4j \
  --password yourpassword
```

## Apache AGE (PostgreSQL)

### Docker
```bash
docker run -p 5432:5432 \
  -e POSTGRES_PASSWORD=secret \
  apache/age:latest
```

### Load a graph
```bash
malimgraph db load \
  --input knowledge_graph.json \
  --target age \
  --uri "host=localhost dbname=postgres user=postgres password=secret" \
  --graph-name my_graph
```

### Query with AGE
```bash
malimgraph db query \
  --target age \
  --uri "host=localhost dbname=postgres user=postgres password=secret" \
  --graph-name my_graph \
  --query "MATCH (n:Organization) RETURN n.label, n.confidence LIMIT 10"
```

## Environment Variables

Set these to avoid passing credentials on every command:

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=yourpassword
export AGE_CONNECTION_URI="host=localhost dbname=postgres user=postgres password=secret"
```
