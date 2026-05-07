#!/usr/bin/env python3
"""
Run Cypher queries against Neo4j or Apache AGE.

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


def _query_neo4j(uri: str, user: str, password: str, cypher: str) -> list:
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("ERROR: neo4j not installed. Run: pip install neo4j --break-system-packages", file=sys.stderr)
        sys.exit(1)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        result = session.run(cypher)
        rows = [dict(record) for record in result]
    driver.close()
    return rows


def _query_age(conn_uri: str, graph_name: str, cypher: str) -> list:
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2-binary not installed. Run: pip install psycopg2-binary --break-system-packages", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(conn_uri)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, '$user', public;")
        cur.execute(f"SELECT * FROM cypher('{graph_name}', $$ {cypher} $$) AS (result agtype);")
        rows = [{"result": str(row[0])} for row in cur.fetchall()]
    conn.close()
    return rows


def main():
    parser = argparse.ArgumentParser(description="Run a Cypher query against a graph database.")
    parser.add_argument("--target", default="neo4j", choices=["neo4j", "age"])
    parser.add_argument("--uri", default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--graph-name", default="document_graph")
    parser.add_argument("--query", "-q", required=True, help="Cypher query to run.")
    parser.add_argument("--output", default=None, help="Optional JSON file to write results to.")
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
            rows = client.query(args.query)
        finally:
            client.close()
    elif args.target == "neo4j":
        rows = _query_neo4j(uri, user, password, args.query)
    else:
        rows = _query_age(uri, args.graph_name, args.query)

    output_str = json.dumps(rows, indent=2, ensure_ascii=False)
    print(output_str)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_str)
        print(f"\n  ✓ Results saved to {args.output}", file=sys.stderr)

    print(f"\n{len(rows)} row(s) returned.", file=sys.stderr)


if __name__ == "__main__":
    main()
