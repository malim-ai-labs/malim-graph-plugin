"""Neo4j and Apache AGE (PostgreSQL) graph database client."""

from __future__ import annotations

import json
import os

from malimgraph.schemas.entities import KnowledgeGraph


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise ImportError("Install neo4j: pip install malimgraph[neo4j]")

        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def load_graph(self, kg: KnowledgeGraph) -> dict:
        """Load all entities and relationships into Neo4j."""
        nodes_created = 0
        rels_created = 0

        with self._driver.session() as session:
            # Create constraints for entity IDs (idempotent)
            entity_types = {e.type for e in kg.entities}
            for etype in entity_types:
                try:
                    session.run(
                        f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{etype}) REQUIRE n.id IS UNIQUE"
                    )
                except Exception:
                    pass  # Constraint may already exist

            # Load entities
            for entity in kg.entities:
                props = {
                    "id": entity.id,
                    "label": entity.label,
                    "confidence": entity.confidence.value,
                    "extraction_method": entity.extraction_method.value,
                    "source_pages": entity.source_pages,
                    "source_text": entity.source_text[:500],
                    "citation_count": len(entity.citations),
                    "citation_texts": [c.text[:200] for c in entity.citations[:5]],
                    **{
                        k: str(v) if not isinstance(v, (str, int, float, bool, list)) else v
                        for k, v in entity.properties.items()
                    },
                }
                session.run(
                    f"MERGE (n:{entity.type} {{id: $id}}) SET n += $props",
                    id=entity.id,
                    props=props,
                )
                nodes_created += 1

            # Load relationships
            for rel in kg.relationships:
                session.run(
                    f"""
                    MATCH (a {{id: $src}}), (b {{id: $tgt}})
                    MERGE (a)-[r:{rel.type} {{id: $rid}}]->(b)
                    SET r += $props
                    """,
                    src=rel.source,
                    tgt=rel.target,
                    rid=rel.id,
                    props={
                        "id": rel.id,
                        "confidence": rel.confidence.value,
                        "extraction_method": rel.extraction_method.value,
                        "source_pages": rel.source_pages,
                        "source_text": rel.source_text[:500],
                        "citation_count": len(rel.citations),
                    },
                )
                rels_created += 1

        return {"nodes_created": nodes_created, "relationships_created": rels_created}

    def query(self, cypher: str) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(cypher)
            return [dict(record) for record in result]

    def stats(self) -> dict:
        with self._driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
            labels = [r["label"] for r in session.run("CALL db.labels() YIELD label RETURN label")]
            rel_types = [
                r["relationshipType"]
                for r in session.run(
                    "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
                )
            ]
        return {
            "node_count": node_count,
            "relationship_count": rel_count,
            "node_labels": labels,
            "relationship_types": rel_types,
        }


class AGEClient:
    def __init__(self, connection_uri: str, graph_name: str = "document_graph"):
        try:
            import psycopg2

            self._psycopg2 = psycopg2
        except ImportError:
            raise ImportError("Install psycopg2: pip install malimgraph[age]")

        self._conn_uri = connection_uri
        self.graph_name = graph_name
        self._conn = psycopg2.connect(connection_uri)
        self._conn.autocommit = True
        self._ensure_age_extension()

    def _ensure_age_extension(self):
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS age;")
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")
            cur.execute(
                f"SELECT create_graph('{self.graph_name}') WHERE NOT EXISTS "
                f"(SELECT 1 FROM ag_catalog.ag_graph WHERE name = '{self.graph_name}');"
            )

    def close(self):
        self._conn.close()

    def load_graph(self, kg: KnowledgeGraph) -> dict:
        nodes_created = 0
        rels_created = 0

        with self._conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")

            for entity in kg.entities:
                props_json = json.dumps(
                    {
                        "id": entity.id,
                        "label": entity.label,
                        "confidence": entity.confidence.value,
                        "extraction_method": entity.extraction_method.value,
                        "source_text": entity.source_text[:500],
                        "citation_count": len(entity.citations),
                    }
                )
                cur.execute(
                    f"SELECT * FROM cypher('{self.graph_name}', $$ "
                    f"MERGE (n:{entity.type} {{id: '{entity.id}'}}) SET n += {props_json} RETURN n "
                    f"$$) AS (n agtype);"
                )
                nodes_created += 1

            for rel in kg.relationships:
                props_json = json.dumps(
                    {
                        "id": rel.id,
                        "confidence": rel.confidence.value,
                        "source_text": rel.source_text[:500],
                    }
                )
                cur.execute(
                    f"SELECT * FROM cypher('{self.graph_name}', $$ "
                    f"MATCH (a {{id: '{rel.source}'}}), (b {{id: '{rel.target}'}}) "
                    f"MERGE (a)-[r:{rel.type} {props_json}]->(b) RETURN r "
                    f"$$) AS (r agtype);"
                )
                rels_created += 1

        return {"nodes_created": nodes_created, "relationships_created": rels_created}

    def query(self, cypher: str) -> list[dict]:
        results = []
        with self._conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")
            cur.execute(
                f"SELECT * FROM cypher('{self.graph_name}', $$ {cypher} $$) AS (result agtype);"
            )
            for row in cur.fetchall():
                results.append({"result": str(row[0])})
        return results

    def stats(self) -> dict:
        with self._conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")
            cur.execute(
                f"SELECT count(*) FROM cypher('{self.graph_name}', $$ MATCH (n) RETURN n $$) AS (n agtype);"
            )
            node_count = cur.fetchone()[0]
            cur.execute(
                f"SELECT count(*) FROM cypher('{self.graph_name}', $$ MATCH ()-[r]->() RETURN r $$) AS (r agtype);"
            )
            rel_count = cur.fetchone()[0]
        return {
            "graph_name": self.graph_name,
            "node_count": node_count,
            "relationship_count": rel_count,
        }

    def drop_graph(self):
        with self._conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")
            cur.execute(f"SELECT drop_graph('{self.graph_name}', true);")

    def list_graphs(self) -> list[str]:
        with self._conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")
            cur.execute("SELECT name FROM ag_catalog.ag_graph;")
            return [row[0] for row in cur.fetchall()]


def get_client(target: str, **kwargs):
    """Factory — returns the right client for the given target."""
    if target == "neo4j":
        return Neo4jClient(
            uri=kwargs.get("uri", os.environ.get("NEO4J_URI", "bolt://localhost:7687")),
            user=kwargs.get("user", os.environ.get("NEO4J_USER", "neo4j")),
            password=kwargs.get("password", os.environ.get("NEO4J_PASSWORD", "")),
        )
    elif target == "age":
        return AGEClient(
            connection_uri=kwargs.get("uri", os.environ.get("AGE_CONNECTION_URI", "")),
            graph_name=kwargs.get("graph_name", "document_graph"),
        )
    else:
        raise ValueError(f"Unknown target '{target}'. Use 'neo4j' or 'age'.")
