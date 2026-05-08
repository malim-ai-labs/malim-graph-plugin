"""Load a MalimGraph knowledge_graph.json file into a local Neo4j instance."""
import argparse
import json
import os
import sys


def load_graph(path: str, uri: str, user: str, password: str):
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("ERROR: neo4j driver not installed.\nRun: pip install neo4j", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    entities = data.get("entities", [])
    relationships = data.get("relationships", [])

    print(f"Loaded {len(entities)} entities and {len(relationships)} relationships from {path}")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()

    with driver.session() as session:
        # Load entities
        print("Loading entities...")
        for i, ent in enumerate(entities, 1):
            label = ent.get("type", "Entity").replace(" ", "_")
            props = {
                "id": ent.get("id", ent.get("label", f"entity_{i}")),
                "label": ent.get("label", ""),
                "type": ent.get("type", ""),
                "confidence": ent.get("confidence", "medium"),
                "source_text": ent.get("source_text", ""),
                "source_pages": ent.get("source_pages", []),
                "extraction_method": ent.get("extraction_method", "semantic"),
            }
            # Include any extra properties
            for k, v in ent.get("properties", {}).items():
                props[k] = v

            cypher = (
                f"MERGE (n:`{label}` {{id: $id}}) "
                "SET n += $props"
            )
            session.run(cypher, id=props["id"], props=props)
            if i % 50 == 0:
                print(f"  {i}/{len(entities)} entities loaded")

        print(f"✓ {len(entities)} entities loaded")

        # Load relationships
        print("Loading relationships...")
        for i, rel in enumerate(relationships, 1):
            src_label = rel.get("source_type", "Entity").replace(" ", "_")
            tgt_label = rel.get("target_type", "Entity").replace(" ", "_")
            rel_type = rel.get("type", "RELATED_TO").replace(" ", "_").upper()
            src_id = rel.get("source_label", "")
            tgt_id = rel.get("target_label", "")

            rel_props = {
                "source_text": rel.get("source_text", ""),
                "source_pages": rel.get("source_pages", []),
                "confidence": rel.get("confidence", "medium"),
            }

            cypher = (
                f"MATCH (a:`{src_label}` {{label: $src_id}}), "
                f"(b:`{tgt_label}` {{label: $tgt_id}}) "
                f"MERGE (a)-[r:`{rel_type}`]->(b) "
                "SET r += $props"
            )
            session.run(cypher, src_id=src_id, tgt_id=tgt_id, props=rel_props)
            if i % 50 == 0:
                print(f"  {i}/{len(relationships)} relationships loaded")

        print(f"✓ {len(relationships)} relationships loaded")

    driver.close()
    print(f"\nDone! Open Neo4j Browser at {uri.replace('bolt://', 'http://').replace(':7687', ':7474')}")
    print("Login: neo4j / <your password>")


def main():
    parser = argparse.ArgumentParser(description="Load MalimGraph knowledge_graph.json into local Neo4j")
    parser.add_argument("--input", required=True, help="Path to knowledge_graph.json")
    parser.add_argument("--uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--user", default=os.getenv("NEO4J_USER", "neo4j"))
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", "malimgraph"))
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        print("Run read_pdf + save_knowledge_graph first to generate knowledge_graph.json")
        sys.exit(1)

    load_graph(args.input, args.uri, args.user, args.password)


if __name__ == "__main__":
    main()
