"""Generate an Open Knowledge Format (OKF) bundle from a KnowledgeGraph.

OKF (https://github.com/GoogleCloudPlatform/knowledge-catalog) represents
knowledge as plain Markdown files with YAML frontmatter, cross-linked into a
graph. This module renders a MalimGraph KnowledgeGraph as such a bundle:
one folder per entity type, one Markdown file per entity, with relationships
expressed as Markdown links between files.
"""

from __future__ import annotations

import os
import re
from typing import Any

from malimgraph.schemas.entities import Entity, KnowledgeGraph

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug or "untitled"


def _yaml_value(value: Any) -> str:
    if isinstance(value, list):
        items = ", ".join(_yaml_scalar(v) for v in value)
        return f"[{items}]"
    return _yaml_scalar(value)


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace('"', '\\"')
    return f'"{text}"'


def _frontmatter(fields: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if value in (None, "", [], {}):
            continue
        lines.append(f"{key}: {_yaml_value(value)}")
    lines.append("---")
    return "\n".join(lines)


def _unique_slug(base: str, used: set[str]) -> str:
    slug = base
    suffix = 2
    while slug in used:
        slug = f"{base}-{suffix}"
        suffix += 1
    used.add(slug)
    return slug


def _entity_paths(entities: list[Entity]) -> dict[str, tuple[str, str]]:
    """Map entity id -> (type_slug, entity_slug)."""
    used_per_type: dict[str, set[str]] = {}
    paths: dict[str, tuple[str, str]] = {}
    for entity in entities:
        type_slug = _slugify(entity.type)
        used = used_per_type.setdefault(type_slug, set())
        entity_slug = _unique_slug(_slugify(entity.label), used)
        paths[entity.id] = (type_slug, entity_slug)
    return paths


def _relative_link(paths: dict[str, tuple[str, str]], entity_id: str) -> str | None:
    target = paths.get(entity_id)
    if not target:
        return None
    type_slug, entity_slug = target
    return f"../{type_slug}/{entity_slug}.md"


def _entity_markdown(
    entity: Entity,
    kg: KnowledgeGraph,
    paths: dict[str, tuple[str, str]],
) -> str:
    outgoing = [r for r in kg.relationships if r.source == entity.id]
    incoming = [r for r in kg.relationships if r.target == entity.id]

    front = _frontmatter(
        {
            "type": entity.type,
            "title": entity.label,
            "description": entity.source_text[:280],
            "confidence": entity.confidence.value,
            "extraction_method": entity.extraction_method.value,
            "source_pages": entity.source_pages,
            "tags": [entity.type],
        }
    )

    body = [front, "", f"# {entity.label}", ""]

    if entity.source_text:
        body.append(f"> {entity.source_text}")
        body.append("")

    if entity.properties:
        body.append("## Properties")
        body.append("")
        for key, value in entity.properties.items():
            body.append(f"- **{key}**: {value}")
        body.append("")

    if outgoing or incoming:
        body.append("## Relationships")
        body.append("")
        for rel in outgoing:
            link = _relative_link(paths, rel.target)
            other = next((e for e in kg.entities if e.id == rel.target), None)
            label = other.label if other else rel.target
            if link:
                body.append(f"- **{rel.type}** → [{label}]({link})")
            else:
                body.append(f"- **{rel.type}** → {label}")
        for rel in incoming:
            link = _relative_link(paths, rel.source)
            other = next((e for e in kg.entities if e.id == rel.source), None)
            label = other.label if other else rel.source
            if link:
                body.append(f"- **{rel.type}** ← [{label}]({link})")
            else:
                body.append(f"- **{rel.type}** ← {label}")
        body.append("")

    if entity.citations:
        body.append("## Citations")
        body.append("")
        for citation in entity.citations:
            pages = ", ".join(str(p) for p in citation.pages) or "?"
            body.append(f'- p.{pages}: "{citation.text[:300]}"')
        body.append("")

    return "\n".join(body).rstrip() + "\n"


def _type_index_markdown(
    type_name: str, entities: list[Entity], paths: dict[str, tuple[str, str]]
) -> str:
    front = _frontmatter(
        {
            "type": "Index",
            "title": f"{type_name} Index",
            "description": f"All {type_name} entities extracted from the source document.",
        }
    )
    lines = [front, "", f"# {type_name}", ""]
    for entity in sorted(entities, key=lambda e: e.label.lower()):
        _, entity_slug = paths[entity.id]
        summary = entity.source_text[:100].strip()
        suffix = f" — {summary}" if summary else ""
        lines.append(f"- [{entity.label}]({entity_slug}.md){suffix}")
    return "\n".join(lines).rstrip() + "\n"


def _root_index_markdown(kg: KnowledgeGraph) -> str:
    front = _frontmatter(
        {
            "type": "Knowledge Graph Bundle",
            "title": f"{kg.metadata.source_file} — Open Knowledge Format Bundle",
            "description": (
                f"OKF export of a MalimGraph knowledge graph extracted from "
                f"{kg.metadata.source_file}."
            ),
            "timestamp": kg.metadata.extracted_at,
        }
    )
    lines = [
        front,
        "",
        f"# {kg.metadata.source_file}",
        "",
        f"- Entities: {kg.metadata.total_entities}",
        f"- Relationships: {kg.metadata.total_relationships}",
        "",
        "## Entity Types",
        "",
    ]
    counts: dict[str, int] = {}
    for entity in kg.entities:
        counts[entity.type] = counts.get(entity.type, 0) + 1
    for type_name in sorted(counts):
        type_slug = _slugify(type_name)
        lines.append(f"- [{type_name}]({type_slug}/index.md) ({counts[type_name]})")
    return "\n".join(lines).rstrip() + "\n"


def generate_okf(kg: KnowledgeGraph) -> dict[str, str]:
    """
    Render a KnowledgeGraph as an OKF bundle.

    Returns a dict mapping relative file paths (using "/" separators) to
    Markdown file contents. Callers write these under a bundle root
    directory (e.g. `<output_dir>/okf/`).
    """
    paths = _entity_paths(kg.entities)
    files: dict[str, str] = {"index.md": _root_index_markdown(kg)}

    by_type: dict[str, list[Entity]] = {}
    for entity in kg.entities:
        by_type.setdefault(entity.type, []).append(entity)

    for type_name, entities in by_type.items():
        type_slug = _slugify(type_name)
        files[f"{type_slug}/index.md"] = _type_index_markdown(type_name, entities, paths)
        for entity in entities:
            _, entity_slug = paths[entity.id]
            files[f"{type_slug}/{entity_slug}.md"] = _entity_markdown(entity, kg, paths)

    return files


def write_okf_bundle(kg: KnowledgeGraph, output_dir: str) -> list[str]:
    """Write an OKF bundle to `<output_dir>/okf/` and return the written paths."""
    bundle_root = os.path.join(output_dir, "okf")
    files = generate_okf(kg)
    written: list[str] = []
    for rel_path, content in files.items():
        full_path = os.path.join(bundle_root, *rel_path.split("/"))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(full_path)
    return written
