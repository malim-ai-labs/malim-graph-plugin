#!/usr/bin/env python3
"""
Graph database administration: stats, drop, list_graphs.

Install for Neo4j: pip install neo4j --break-system-packages
Install for AGE:   pip install psycopg2-binary --break-system-packages
"""
import argparse
import json
import os
import sys

try:
    from malimgraph.core.db_client import get_client
    _USE_PACKAGE = True
except ImportError:
    _USE_PACKAGE = False


def _stats_neo4j(uri: str, user: str, password: str) -> dict:
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("ERROR: neo4j not installed. Run: pip install neo4j --break-system-packages", file=sys.stderr)
        sys.exit(1)
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
        labels = [r["label"] for r in session.run("CALL db.labels() YIELD label RETURN label")]
        rel_types = [r["relationshipType"] for r in session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")]
    driver.close()
    return {"node_count": node_count, "relationship_count": rel_count, "node_labels": labels, "relationship_types": rel_types}


def _stats_age(conn_uri: str, graph_name: str) -> dict:
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2-binary not installed. Run: pip install psycopg2-binary --break-system-packages", file=sys.stderr)
        sys.exit(1)
    conn = psycopg2.connect(conn_uri)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("LOAD 'age'; SET search_path = ag_catalog, '$user', public;")
        cur.execute(f"SELECT count(*) FROM cypher('{graph_name}', $$ MATCH (n) RETURN n $$) AS (n agtype);")
        node_count = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM cypher('{graph_name}', $$ MATCH ()-[r]->() RETURN r $$) AS (r agtype);")
        rel_count = cur.fetchone()[0]
    conn.close()
    return {"graph_name": graph_name, "node_count": node_count, "relationship_count": rel_count}


def _drop_age(conn_uri: str, graph_name: str):
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2-binary not installed.", file=sys.stderr)
        sys.exit(1)
    conn = psycopg2.connect(conn_uri)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("LOAD 'age'; SET search_path = ag_catalog, '$user', public;")
        cur.execute(f"SELECT drop_graph('{graph_name}', true);")
    conn.close()


def _list_graphs_age(conn_uri: str) -> list:
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2-binary not installed.", file=sys.stderr)
        sys.exit(1)
    conn = psycopg2.connect(conn_uri)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("LOAD 'age'; SET search_path = ag_catalog, '$user', public;")
        cur.execute("SELECT name FROM ag_catalog.ag_graph;")
        graphs = [row[0] for row in cur.fetchall()]
    conn.close()
    return graphs


def main():
    parser = argparse.ArgumentParser(description="Graph database administration.")
    parser.add_argument("--action", required=True, choices=["stats", "drop", "list_graphs"])
    parser.add_argument("--target", default="neo4j", choices=["neo4j", "age"])
    parser.add_argument("--uri", default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--graph-name", default="document_graph")
    args = parser.parse_args()

    uri = args.uri or os.environ.get("NEO4J_URI" if args.target == "neo4j" else "AGE_CONNECTION_URI", "")
    user = args.user or os.environ.get("NEO4J_USER", "neo4j")
    password = args.password or os.environ.get("NEO4J_PASSWORD", "")

    if not uri:
        print("ERROR: --uri required.", file=sys.stderr)
        sys.exit(1)

    if _USE_PACKAGE:
        kwargs = {"uri": uri, "graph_name": args.graph_name}
        if user:
            kwargs["user"] = user
        if password:
            kwargs["password"] = password
        client = get_client(args.target, **kwargs)
        try:
            if args.action == "stats":
                result = client.stats()
            elif args.action == "drop":
                if not hasattr(client, "drop_graph"):
                    print("drop not supported for neo4j target", file=sys.stderr)
                    sys.exit(1)
                client.drop_graph()
                result = {"dropped": args.graph_name}
            elif args.action == "list_graphs":
                if not hasattr(client, "list_graphs"):
                    print("list_graphs not supported for neo4j target", file=sys.stderr)
                    sys.exit(1)
                result = {"graphs": client.list_graphs()}
        finally:
            client.close()
    else:
        if args.action == "stats":
            result = _stats_neo4j(uri, user, password) if args.target == "neo4j" else _stats_age(uri, args.graph_name)
        elif args.action == "drop":
            if args.target != "age":
                print("drop only supported for age target without package", file=sys.stderr)
                sys.exit(1)
            _drop_age(uri, args.graph_name)
            result = {"dropped": args.graph_name}
        elif args.action == "list_graphs":
            if args.target != "age":
                print("list_graphs only supported for age target without package", file=sys.stderr)
                sys.exit(1)
            result = {"graphs": _list_graphs_age(uri)}

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
