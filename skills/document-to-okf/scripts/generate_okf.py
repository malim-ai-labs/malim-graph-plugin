#!/usr/bin/env python3
"""
Generate an Open Knowledge Format (OKF) bundle from a knowledge_graph.json.

OKF (https://github.com/GoogleCloudPlatform/knowledge-catalog) represents
knowledge as plain Markdown files with YAML frontmatter, cross-linked into
a graph. This script renders MalimGraph's knowledge_graph.json as such a
bundle: one folder per entity type, one Markdown file per entity, with
relationships expressed as Markdown links between files.

Install: pip install pydantic --break-system-packages
"""
import argparse
import json
import os
import re
import sys

try:
    from malimgraph.schemas.entities import KnowledgeGraph
    from malimgraph.generators.okf import write_okf_bundle
    _USE_PACKAGE = True
except ImportError:
    _USE_PACKAGE = False

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-") or "untitled"


def _unique_slug(base: str, used: set) -> str:
    slug = base
    n = 2
    while slug in used:
        slug = f"{base}-{n}"
        n += 1
    used.add(slug)
    return slug


def _yaml_scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return '"' + str(v).replace('"', '\\"') + '"'


def _frontmatter(fields: dict) -> str:
    lines = ["---"]
    for k, v in fields.items():
        if v in (None, "", [], {}):
            continue
        if isinstance(v, list):
            lines.append(f"{k}: [" + ", ".join(_yaml_scalar(i) for i in v) + "]")
        else:
            lines.append(f"{k}: {_yaml_scalar(v)}")
    lines.append("---")
    return "\n".join(lines)


def _inline_generate_okf(data: dict) -> dict:
    """Standalone re-implementation of malimgraph.generators.okf.generate_okf."""
    entities = data["entities"]
    relationships = data["relationships"]
    meta = data["metadata"]

    used_per_type = {}
    paths = {}
    for e in entities:
        type_slug = _slugify(e["type"])
        used = used_per_type.setdefault(type_slug, set())
        entity_slug = _unique_slug(_slugify(e["label"]), used)
        paths[e["id"]] = (type_slug, entity_slug)

    by_id = {e["id"]: e for e in entities}
    files = {}

    # Root index
    counts = {}
    for e in entities:
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    lines = [
        _frontmatter({
            "type": "Knowledge Graph Bundle",
            "title": f"{meta['source_file']} — Open Knowledge Format Bundle",
            "description": f"OKF export of a MalimGraph knowledge graph extracted from {meta['source_file']}.",
            "timestamp": meta.get("extracted_at", ""),
        }),
        "",
        f"# {meta['source_file']}",
        "",
        f"- Entities: {meta['total_entities']}",
        f"- Relationships: {meta['total_relationships']}",
        "",
        "## Entity Types",
        "",
    ]
    for type_name in sorted(counts):
        lines.append(f"- [{type_name}]({_slugify(type_name)}/index.md) ({counts[type_name]})")
    files["index.md"] = "\n".join(lines).rstrip() + "\n"

    # Per-type index + entity files
    by_type = {}
    for e in entities:
        by_type.setdefault(e["type"], []).append(e)

    for type_name, type_entities in by_type.items():
        type_slug = _slugify(type_name)

        idx_lines = [
            _frontmatter({
                "type": "Index",
                "title": f"{type_name} Index",
                "description": f"All {type_name} entities extracted from the source document.",
            }),
            "",
            f"# {type_name}",
            "",
        ]
        for e in sorted(type_entities, key=lambda e: e["label"].lower()):
            _, slug = paths[e["id"]]
            summary = (e.get("source_text") or "")[:100].strip()
            suffix = f" — {summary}" if summary else ""
            idx_lines.append(f"- [{e['label']}]({slug}.md){suffix}")
        files[f"{type_slug}/index.md"] = "\n".join(idx_lines).rstrip() + "\n"

        for e in type_entities:
            _, slug = paths[e["id"]]
            outgoing = [r for r in relationships if r["source"] == e["id"]]
            incoming = [r for r in relationships if r["target"] == e["id"]]

            body = [
                _frontmatter({
                    "type": e["type"],
                    "title": e["label"],
                    "description": (e.get("source_text") or "")[:280],
                    "confidence": e.get("confidence", ""),
                    "extraction_method": e.get("extraction_method", ""),
                    "source_pages": e.get("source_pages", []),
                    "tags": [e["type"]],
                }),
                "",
                f"# {e['label']}",
                "",
            ]
            if e.get("source_text"):
                body.append(f"> {e['source_text']}")
                body.append("")

            if e.get("properties"):
                body.append("## Properties")
                body.append("")
                for k, v in e["properties"].items():
                    body.append(f"- **{k}**: {v}")
                body.append("")

            if outgoing or incoming:
                body.append("## Relationships")
                body.append("")
                for r in outgoing:
                    other = by_id.get(r["target"])
                    label = other["label"] if other else r["target"]
                    link = paths.get(r["target"])
                    if link:
                        body.append(f"- **{r['type']}** → [{label}](../{link[0]}/{link[1]}.md)")
                    else:
                        body.append(f"- **{r['type']}** → {label}")
                for r in incoming:
                    other = by_id.get(r["source"])
                    label = other["label"] if other else r["source"]
                    link = paths.get(r["source"])
                    if link:
                        body.append(f"- **{r['type']}** ← [{label}](../{link[0]}/{link[1]}.md)")
                    else:
                        body.append(f"- **{r['type']}** ← {label}")
                body.append("")

            if e.get("citations"):
                body.append("## Citations")
                body.append("")
                for c in e["citations"]:
                    pages = ", ".join(str(p) for p in c.get("pages", [])) or "?"
                    body.append(f"- p.{pages}: \"{(c.get('text') or '')[:300]}\"")
                body.append("")

            files[f"{type_slug}/{slug}.md"] = "\n".join(body).rstrip() + "\n"

    return files


def main():
    parser = argparse.ArgumentParser(description="Generate an OKF Markdown bundle from knowledge_graph.json.")
    parser.add_argument("--input", required=True, help="Path to knowledge_graph.json")
    parser.add_argument("--output-dir", default=".", help="Directory under which an okf/ bundle is written.")
    args = parser.parse_args()

    print(f"Loading: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    if _USE_PACKAGE:
        kg = KnowledgeGraph.model_validate(data)
        written = write_okf_bundle(kg, args.output_dir)
    else:
        files = _inline_generate_okf(data)
        bundle_root = os.path.join(args.output_dir, "okf")
        written = []
        for rel_path, content in files.items():
            full_path = os.path.join(bundle_root, *rel_path.split("/"))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            written.append(full_path)

    for path in written:
        print(f"  ✓ {path}")
    print(f"Done. {len(written)} files written under {os.path.join(args.output_dir, 'okf')}")


if __name__ == "__main__":
    main()
