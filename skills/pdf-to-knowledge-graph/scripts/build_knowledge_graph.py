#!/usr/bin/env python3
"""
Build a knowledge graph from extracted PDF text.
Step 2 of the pdf-to-knowledge-graph skill.

Install: pip install pymupdf anthropic pydantic --break-system-packages
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional

try:
    from malimgraph.core.pdf_reader import DocumentContent, PageContent
    from malimgraph.core.rule_extractor import extract_by_rules
    from malimgraph.core.llm_extractor import extract_by_llm
    from malimgraph.core.graph_builder import build_knowledge_graph
    _USE_PACKAGE = True
except ImportError:
    _USE_PACKAGE = False

# ── Inline fallbacks ──────────────────────────────────────────────────────────

def _load_doc_from_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if _USE_PACKAGE:
        pages = [
            PageContent(
                page_number=p["page_number"],
                text=p["text"],
                headings=p.get("headings", []),
                blocks=[],
                has_table=p.get("has_table", False),
                is_scanned=p.get("is_scanned", False),
            )
            for p in data["pages"]
        ]
        return DocumentContent(
            source_file=data["source_file"],
            total_pages=data["total_pages"],
            title=data.get("title", ""),
            metadata=data.get("metadata", {}),
            pages=pages,
        )
    return data  # return raw dict for inline path


def _inline_rule_extract(doc_data: dict) -> list[dict]:
    """Minimal inline rule extraction when package unavailable."""
    import re
    import hashlib

    PATTERNS = [
        ("Date", re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b", re.I)),
        ("Date", re.compile(r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b")),
        ("Email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b")),
        ("MonetaryAmount", re.compile(r"(?:USD|MYR|RM|EUR|GBP|\$|€|£)\s*[\d,]+(?:\.\d{2})?", re.I)),
        ("Percentage", re.compile(r"\b\d+(?:\.\d+)?%\b")),
        ("LegalReference", re.compile(r"\b(?:Act|Regulation|Directive)\s+(?:No\.?\s*)?\d+[\w\s]*\b", re.I)),
    ]

    entities = {}
    for page in doc_data["pages"]:
        text = page["text"]
        pnum = page["page_number"]
        for etype, pattern in PATTERNS:
            for m in pattern.finditer(text):
                label = m.group(0).strip()
                if not label or len(label) < 2:
                    continue
                key = f"{etype}:{label}".lower()
                eid = "e_" + __import__("hashlib").md5(key.encode()).hexdigest()[:8]
                start = max(0, m.start() - 100)
                end = min(len(text), m.end() + 100)
                snippet = text[start:end].strip()

                if eid not in entities:
                    entities[eid] = {
                        "id": eid, "label": label, "type": etype,
                        "extraction_method": "rule", "confidence": "high",
                        "source_pages": [pnum], "source_text": snippet,
                        "source_chunk_id": f"page_{pnum}", "source_chunk_ids": [f"page_{pnum}"],
                        "citations": [{"text": snippet, "pages": [pnum], "chunk_id": f"page_{pnum}", "extraction_method": "rule"}],
                        "properties": {},
                    }
                elif pnum not in entities[eid]["source_pages"]:
                    entities[eid]["source_pages"].append(pnum)

    return list(entities.values())


def _inline_llm_extract(doc_data: dict, entity_types: Optional[list], api_key: str) -> tuple:
    """Minimal inline LLM extraction when package unavailable."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic not installed. Run: pip install anthropic --break-system-packages", file=sys.stderr)
        sys.exit(1)

    import hashlib, re

    client = anthropic.Anthropic(api_key=api_key)
    entities = {}
    relationships = {}

    SYSTEM = """Extract entities and relationships from this document passage. Respond ONLY with JSON:
{"entities":[{"label":"str","type":"str","confidence":"high|medium|low","source_text":"verbatim quote"}],
 "relationships":[{"source_label":"str","source_type":"str","target_label":"str","target_type":"str","type":"UPPER_SNAKE_CASE","confidence":"high|medium|low","source_text":"verbatim quote"}]}"""

    # Chunk pages 2-3 at a time
    pages = doc_data["pages"]
    i = 0
    while i < len(pages):
        chunk_pages = pages[i:i+3]
        chunk_text = "\n\n".join(f"[Page {p['page_number']}]\n{p['text']}" for p in chunk_pages if p["text"].strip())
        if not chunk_text.strip():
            i += 3
            continue

        page_nums = [p["page_number"] for p in chunk_pages]
        chunk_id = f"llm_p{page_nums[0]}_p{page_nums[-1]}"
        hint = f"\nFocus on: {', '.join(entity_types)}." if entity_types else ""

        try:
            msg = client.messages.create(
                model="claude-opus-4-7", max_tokens=4096,
                system=SYSTEM,
                messages=[{"role": "user", "content": f"Extract from:{hint}\n\n{chunk_text}"}],
            )
            content = msg.content[0].text.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            raw = json.loads(content.strip())
        except Exception as e:
            print(f"  [LLM] chunk {chunk_id} failed: {e}")
            i += 3
            continue

        for e in raw.get("entities", []):
            label, etype = e.get("label", "").strip(), e.get("type", "Unknown").strip()
            if not label:
                continue
            key = f"{etype}:{label}".lower()
            eid = "e_" + hashlib.md5(key.encode()).hexdigest()[:8]
            if eid not in entities:
                entities[eid] = {
                    "id": eid, "label": label, "type": etype,
                    "extraction_method": "llm", "confidence": e.get("confidence", "medium"),
                    "source_pages": list(page_nums), "source_text": e.get("source_text", "")[:500],
                    "source_chunk_id": chunk_id, "source_chunk_ids": [chunk_id],
                    "citations": [{"text": e.get("source_text", "")[:300], "pages": list(page_nums), "chunk_id": chunk_id, "extraction_method": "llm"}],
                    "properties": {},
                }

        for r in raw.get("relationships", []):
            sl, st = r.get("source_label", "").strip(), r.get("source_type", "Unknown").strip()
            tl, tt = r.get("target_label", "").strip(), r.get("target_type", "Unknown").strip()
            rtype = r.get("type", "RELATED_TO").strip().upper().replace(" ", "_")
            if not sl or not tl:
                continue
            sid = "e_" + hashlib.md5(f"{st}:{sl}".lower().encode()).hexdigest()[:8]
            tid = "e_" + hashlib.md5(f"{tt}:{tl}".lower().encode()).hexdigest()[:8]
            rid = "r_" + hashlib.md5(f"{sid}:{rtype}:{tid}".lower().encode()).hexdigest()[:8]
            for eid, lbl, typ in [(sid, sl, st), (tid, tl, tt)]:
                if eid not in entities:
                    entities[eid] = {"id": eid, "label": lbl, "type": typ, "extraction_method": "llm", "confidence": "low", "source_pages": list(page_nums), "source_text": "", "source_chunk_id": chunk_id, "source_chunk_ids": [chunk_id], "citations": [], "properties": {}}
            if rid not in relationships:
                relationships[rid] = {"id": rid, "source": sid, "target": tid, "type": rtype, "properties": {}, "extraction_method": "llm", "confidence": r.get("confidence", "medium"), "source_pages": list(page_nums), "source_text": r.get("source_text", "")[:500], "source_chunk_id": chunk_id, "citations": []}

        i += 3

    return list(entities.values()), list(relationships.values())


def main():
    parser = argparse.ArgumentParser(description="Build a knowledge graph from extracted PDF text.")
    parser.add_argument("--input", required=True, help="extracted_text.json from extract_text.py")
    parser.add_argument("--output", default="knowledge_graph.json", help="Output JSON path.")
    parser.add_argument("--entity-types", default="auto", help="Comma-separated entity types or 'auto'.")
    parser.add_argument("--graph-name", default="document_graph")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    etype_list = None
    if args.entity_types and args.entity_types.lower() != "auto":
        etype_list = [e.strip() for e in args.entity_types.split(",") if e.strip()]

    print(f"Loading: {args.input}")
    doc_data = _load_doc_from_json(args.input)

    print("Running rule-based extraction...")
    if _USE_PACKAGE:
        rule_entities = extract_by_rules(doc_data)
        print(f"  → {len(rule_entities)} entities via rules")
    else:
        rule_entities = _inline_rule_extract(doc_data)
        print(f"  → {len(rule_entities)} entities via rules (inline)")

    llm_entities, llm_relationships = [], []
    if api_key:
        print("Running LLM extraction...")
        if _USE_PACKAGE:
            llm_entities, llm_relationships = extract_by_llm(doc_data, entity_types=etype_list, api_key=api_key)
        else:
            llm_entities, llm_relationships = _inline_llm_extract(doc_data, etype_list, api_key)
        print(f"  → {len(llm_entities)} entities, {len(llm_relationships)} relationships via LLM")
    else:
        print("  [Warning] No ANTHROPIC_API_KEY — skipping LLM extraction.")

    if _USE_PACKAGE:
        kg = build_knowledge_graph(doc_data, rule_entities, llm_entities, llm_relationships, args.graph_name)
        output = kg.model_dump()
    else:
        # Inline merge: simple dict-based merge
        entity_map = {e["id"]: e for e in rule_entities}
        for e in llm_entities:
            if e["id"] in entity_map:
                ex = entity_map[e["id"]]
                ex["source_pages"] = sorted(set(ex["source_pages"] + e["source_pages"]))
                ex["citations"].extend(e["citations"])
                ex["extraction_method"] = "hybrid"
                ex["confidence"] = "high"
                ex["properties"].update(e.get("properties", {}))
            else:
                entity_map[e["id"]] = e

        entity_ids = set(entity_map.keys())
        valid_rels = [r for r in llm_relationships if r["source"] in entity_ids and r["target"] in entity_ids]

        source_file = doc_data.get("source_file", args.input) if isinstance(doc_data, dict) else args.input
        entities = list(entity_map.values())
        output = {
            "metadata": {
                "source_file": os.path.basename(str(source_file)),
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "total_entities": len(entities),
                "total_relationships": len(valid_rels),
                "entity_types": sorted({e["type"] for e in entities}),
                "relationship_types": sorted({r["type"] for r in valid_rels}),
                "extraction_config": {"graph_name": args.graph_name},
                "chunk_index": {},
            },
            "entities": entities,
            "relationships": valid_rels,
        }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Knowledge graph saved → {args.output}")
    print(f"  Entities: {output['metadata']['total_entities']}")
    print(f"  Relationships: {output['metadata']['total_relationships']}")


if __name__ == "__main__":
    main()
