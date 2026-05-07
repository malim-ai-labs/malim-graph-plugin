#!/usr/bin/env python3
"""
Generate Cypher and Apache AGE SQL files from a knowledge_graph.json.
Step 3 of the pdf-to-knowledge-graph skill.

Install: pip install pydantic --break-system-packages
"""
import argparse
import json
import os
import sys

try:
    from malimgraph.schemas.entities import KnowledgeGraph
    from malimgraph.generators.cypher import generate_cypher
    from malimgraph.generators.age_sql import generate_age_sql
    _USE_PACKAGE = True
except ImportError:
    _USE_PACKAGE = False


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')


def _dict_to_cypher(d: dict) -> str:
    parts = []
    for k, v in d.items():
        if isinstance(v, str):
            parts.append(f"{k}: '{_escape(v)}'")
        elif isinstance(v, bool):
            parts.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, (int, float)):
            parts.append(f"{k}: {v}")
        elif isinstance(v, list):
            items = ", ".join(f"'{_escape(str(i))}'" if isinstance(i, str) else str(i) for i in v)
            parts.append(f"{k}: [{items}]")
        else:
            parts.append(f"{k}: '{_escape(str(v))}'")
    return "{" + ", ".join(parts) + "}"


def _inline_generate_cypher(data: dict, graph_name: str) -> str:
    meta = data["metadata"]
    lines = [
        f"// MalimGraph — Cypher Import",
        f"// Source: {meta['source_file']}",
        f"// Extracted: {meta.get('extracted_at', '')}",
        f"// Entities: {meta['total_entities']}  Relationships: {meta['total_relationships']}",
        "",
        "// ── Constraints ─────────────────────────────────────",
    ]
    for etype in meta.get("entity_types", []):
        lines.append(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{etype}) REQUIRE n.id IS UNIQUE;")
    lines.append("")
    lines.append("// ── Nodes ─────────────────────────────────────────────")
    for e in data["entities"]:
        props = {
            "id": e["id"], "label": e["label"], "type": e["type"],
            "confidence": e.get("confidence", ""), "extraction_method": e.get("extraction_method", ""),
            "source_pages": e.get("source_pages", []), "source_text": e.get("source_text", "")[:500],
            "source_chunk_id": e.get("source_chunk_id", ""), "citation_count": len(e.get("citations", [])),
            "citation_texts": [c.get("text", "")[:200] for c in e.get("citations", [])[:5]],
        }
        lines.append(f"MERGE (n:{e['type']} {{id: '{_escape(e['id'])}'}}) SET n += {_dict_to_cypher(props)};")
    lines.append("")
    lines.append("// ── Relationships ─────────────────────────────────────")
    for r in data["relationships"]:
        props = {"id": r["id"], "confidence": r.get("confidence", ""), "source_text": r.get("source_text", "")[:300]}
        lines.append(f"MATCH (a {{id: '{_escape(r['source'])}'}}) , (b {{id: '{_escape(r['target'])}'}}) MERGE (a)-[rel:{r['type']} {{id: '{_escape(r['id'])}'}}]->(b) SET rel += {_dict_to_cypher(props)};")
    return "\n".join(lines)


def _inline_generate_age_sql(data: dict, graph_name: str) -> str:
    meta = data["metadata"]
    lines = [
        f"-- MalimGraph — Apache AGE SQL Import",
        f"-- Source: {meta['source_file']}  Graph: {graph_name}",
        "",
        "CREATE EXTENSION IF NOT EXISTS age;",
        "LOAD 'age';",
        "SET search_path = ag_catalog, '$user', public;",
        f"SELECT create_graph('{graph_name}');",
        "",
        "-- ── Nodes ─────────────────────────────────────────────",
    ]
    for e in data["entities"]:
        props_json = json.dumps({"id": e["id"], "label": e["label"], "confidence": e.get("confidence", ""), "source_text": e.get("source_text", "")[:300], "citation_count": len(e.get("citations", []))}, ensure_ascii=False)
        lines.append(f"SELECT * FROM cypher('{graph_name}', $$ MERGE (n:{e['type']} {{id: '{_escape(e['id'])}'}}) SET n += {props_json} RETURN n $$) AS (n agtype);")
    lines.append("")
    lines.append("-- ── Relationships ─────────────────────────────────────")
    for r in data["relationships"]:
        props_json = json.dumps({"id": r["id"], "confidence": r.get("confidence", ""), "source_text": r.get("source_text", "")[:300]}, ensure_ascii=False)
        lines.append(f"SELECT * FROM cypher('{graph_name}', $$ MATCH (a {{id: '{_escape(r['source'])}'}}) , (b {{id: '{_escape(r['target'])}'}}) MERGE (a)-[rel:{r['type']} {{id: '{_escape(r['id'])}'}}]->(b) SET rel += {props_json} RETURN rel $$) AS (rel agtype);")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate Cypher/AGE SQL from knowledge_graph.json.")
    parser.add_argument("--input", required=True, help="Path to knowledge_graph.json")
    parser.add_argument("--output-dir", default=".", help="Output directory for generated files.")
    parser.add_argument("--formats", default="all", help="Comma-separated: cypher, age, all.")
    parser.add_argument("--graph-name", default="document_graph")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Loading: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    formats = {f.strip().lower() for f in args.formats.split(",")}
    if "all" in formats:
        formats = {"cypher", "age"}

    if "cypher" in formats:
        if _USE_PACKAGE:
            kg = KnowledgeGraph.model_validate(data)
            content = generate_cypher(kg)
        else:
            content = _inline_generate_cypher(data, args.graph_name)
        path = os.path.join(args.output_dir, "knowledge_graph.cypher")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✓ {path}")

    if "age" in formats:
        if _USE_PACKAGE:
            kg = KnowledgeGraph.model_validate(data)
            content = generate_age_sql(kg, graph_name=args.graph_name)
        else:
            content = _inline_generate_age_sql(data, args.graph_name)
        path = os.path.join(args.output_dir, "knowledge_graph.sql")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✓ {path}")

    print("Done.")


if __name__ == "__main__":
    main()
