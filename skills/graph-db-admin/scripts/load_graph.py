#!/usr/bin/env python3
"""
Load a knowledge_graph.json into Neo4j or Apache AGE.

Install for Neo4j: pip install neo4j --break-system-packages
Install for AGE:   pip install psycopg2-binary --break-system-packages
"""
import argparse
import json
import os
import sys

try:
    from malimgraph.core.db_client import get_client
    from malimgraph.schemas.entities import KnowledgeGraph
    _USE_PACKAGE = True
except ImportError:
    _USE_PACKAGE = False


def _load_neo4j(data: dict, uri: str, user: str, password: str):
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("ERROR: neo4j not installed. Run: pip install neo4j --break-system-packages", file=sys.stderr)
        sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    nodes_created = 0
    rels_created = 0

    with driver.session() as session:
        for etype in data["metadata"].get("entity_types", []):
            try:
                session.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{etype}) REQUIRE n.id IS UNIQUE")
            except Exception:
                pass

        for e in data["entities"]:
            props = {
                "id": e["id"], "label": e["label"], "type": e["type"],
                "confidence": e.get("confidence", ""), "extraction_method": e.get("extraction_method", ""),
                "source_pages": e.get("source_pages", []), "source_text": e.get("source_text", "")[:500],
                "source_chunk_id": e.get("source_chunk_id", ""), "citation_count": len(e.get("citations", [])),
                "citation_texts": [c.get("text", "")[:200] for c in e.get("citations", [])[:5]],
            }
            session.run(f"MERGE (n:{e['type']} {{id: $id}}) SET n += $props", id=e["id"], props=props)
            nodes_created += 1
            if nodes_created % 50 == 0:
                print(f"  Loaded {nodes_created} nodes...")

        for r in data["relationships"]:
            session.run(
                f"MATCH (a {{id: $src}}), (b {{id: $tgt}}) MERGE (a)-[rel:{r['type']} {{id: $rid}}]->(b) SET rel += $props",
                src=r["source"], tgt=r["target"], rid=r["id"],
                props={"id": r["id"], "confidence": r.get("confidence", ""), "source_text": r.get("source_text", "")[:300]},
            )
            rels_created += 1

    driver.close()
    return {"nodes_created": nodes_created, "relationships_created": rels_created}


def _load_age(data: dict, conn_uri: str, graph_name: str):
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2-binary not installed. Run: pip install psycopg2-binary --break-system-packages", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(conn_uri)
    conn.autocommit = True
    nodes_created = 0
    rels_created = 0

    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS age;")
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, '$user', public;")
        try:
            cur.execute(f"SELECT create_graph('{graph_name}');")
        except Exception:
            pass  # Graph may already exist

        for e in data["entities"]:
            eid = e["id"].replace("'", "\\'")
            props_json = json.dumps({
                "id": e["id"], "label": e["label"], "confidence": e.get("confidence", ""),
                "source_text": e.get("source_text", "")[:300], "citation_count": len(e.get("citations", [])),
            }, ensure_ascii=False)
            cur.execute(f"SELECT * FROM cypher('{graph_name}', $$ MERGE (n:{e['type']} {{id: '{eid}'}}) SET n += {props_json} RETURN n $$) AS (n agtype);")
            nodes_created += 1
            if nodes_created % 50 == 0:
                print(f"  Loaded {nodes_created} nodes...")

        for r in data["relationships"]:
            src = r["source"].replace("'", "\\'")
            tgt = r["target"].replace("'", "\\'")
            rid = r["id"].replace("'", "\\'")
            props_json = json.dumps({"id": r["id"], "confidence": r.get("confidence", ""), "source_text": r.get("source_text", "")[:300]}, ensure_ascii=False)
            cur.execute(f"SELECT * FROM cypher('{graph_name}', $$ MATCH (a {{id: '{src}'}}), (b {{id: '{tgt}'}}) MERGE (a)-[rel:{r['type']} {{id: '{rid}'}}]->(b) SET rel += {props_json} RETURN rel $$) AS (rel agtype);")
            rels_created += 1

    conn.close()
    return {"nodes_created": nodes_created, "relationships_created": rels_created}


def main():
    parser = argparse.ArgumentParser(description="Load a knowledge graph into Neo4j or Apache AGE.")
    parser.add_argument("--input", required=True, help="Path to knowledge_graph.json")
    parser.add_argument("--target", default="neo4j", choices=["neo4j", "age"])
    parser.add_argument("--uri", default=None, help="Connection URI (bolt:// or postgresql://)")
    parser.add_argument("--user", default=None, help="Neo4j username")
    parser.add_argument("--password", default=None, help="Neo4j password")
    parser.add_argument("--graph-name", default="document_graph", help="Graph name (for AGE)")
    args = parser.parse_args()

    uri = args.uri or os.environ.get("NEO4J_URI" if args.target == "neo4j" else "AGE_CONNECTION_URI", "")
    user = args.user or os.environ.get("NEO4J_USER", "neo4j")
    password = args.password or os.environ.get("NEO4J_PASSWORD", "")

    if not uri:
        print(f"ERROR: --uri or {'NEO4J_URI' if args.target == 'neo4j' else 'AGE_CONNECTION_URI'} required.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Target: {args.target} @ {uri}")

    if _USE_PACKAGE:
        kwargs = {"uri": uri, "graph_name": args.graph_name}
        if user:
            kwargs["user"] = user
        if password:
            kwargs["password"] = password
        kg = KnowledgeGraph.model_validate(data)
        client = get_client(args.target, **kwargs)
        try:
            result = client.load_graph(kg)
        finally:
            client.close()
    elif args.target == "neo4j":
        result = _load_neo4j(data, uri, user, password)
    else:
        result = _load_age(data, uri, args.graph_name)

    print(f"  ✓ Nodes loaded: {result['nodes_created']}")
    print(f"  ✓ Relationships loaded: {result['relationships_created']}")
    print("Done.")


if __name__ == "__main__":
    main()
