#!/usr/bin/env python3
"""
Render extracted PDF text as structured HTML.
Step 2 of the document-to-html skill.

Install: pip install pydantic --break-system-packages
"""
import argparse
import html as html_lib
import json
import os
import re
import sys
from typing import Optional

try:
    from malimgraph.core.pdf_reader import DocumentContent, PageContent
    from malimgraph.core.html_renderer import render_document_html
    from malimgraph.schemas.entities import KnowledgeGraph
    _USE_PACKAGE = True
except ImportError:
    _USE_PACKAGE = False


# ── Inline HTML renderer ──────────────────────────────────────────────────────

def _inline_render(doc_data: dict, kg_data: Optional[dict], include_toc: bool, include_search: bool) -> str:
    title = html_lib.escape(doc_data.get("title", os.path.basename(doc_data.get("source_file", "document.pdf"))))

    # Build entity page map from kg_data
    entity_page_map: dict[int, list[dict]] = {}
    if kg_data:
        for entity in kg_data.get("entities", []):
            for pnum in entity.get("source_pages", []):
                entity_page_map.setdefault(pnum, []).append(entity)

    toc_items = []
    for page in doc_data["pages"]:
        pnum = page["page_number"]
        headings = page.get("headings", [])
        if headings:
            for h in headings:
                toc_items.append(f'<li><a href="#page-{pnum}"><span class="toc-page">p.{pnum}</span> {html_lib.escape(h[:80])}</a></li>')
        else:
            toc_items.append(f'<li><a href="#page-{pnum}">Page {pnum}</a></li>')

    toc_html = f"""<nav id="toc" aria-label="Table of Contents">
  <h2>Table of Contents</h2>
  <ul>{''.join(toc_items)}</ul>
</nav>""" if include_toc else ""

    sections = []
    for page in doc_data["pages"]:
        pnum = page["page_number"]
        entities = entity_page_map.get(pnum, [])
        text = page.get("text", "")

        # Annotate entities
        if entities:
            annotations = []
            for entity in entities:
                pattern = re.compile(re.escape(entity["label"]), re.IGNORECASE)
                for m in pattern.finditer(text):
                    annotations.append((m.start(), m.end(), entity))
            annotations.sort(key=lambda x: x[0])
            filtered, last_end = [], 0
            for start, end, ent in annotations:
                if start >= last_end:
                    filtered.append((start, end, ent))
                    last_end = end

            parts, cursor = [], 0
            for start, end, ent in filtered:
                if cursor < start:
                    parts.append(html_lib.escape(text[cursor:start]))
                parts.append(
                    f'<mark data-entity-id="{html_lib.escape(ent["id"])}" '
                    f'data-entity-type="{html_lib.escape(ent["type"])}" '
                    f'title="{html_lib.escape(ent["type"])}: {html_lib.escape(ent["label"])}">'
                    f'{html_lib.escape(text[start:end])}</mark>'
                )
                cursor = end
            if cursor < len(text):
                parts.append(html_lib.escape(text[cursor:]))
            annotated = "".join(parts)
        else:
            annotated = html_lib.escape(text)

        paras = annotated.split("\n\n")
        content_html = "\n".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paras if p.strip())

        heading_html = "".join(f"<h2>{html_lib.escape(h)}</h2>\n" for h in page.get("headings", []))
        badges = ""
        if page.get("has_table"):
            badges += '<span class="badge badge-table">Table</span> '
        if page.get("is_scanned"):
            badges += '<span class="badge badge-scanned">Scanned</span> '

        sections.append(f"""<section id="page-{pnum}" class="page-section" data-page="{pnum}">
  <div class="page-header"><span class="page-label">Page {pnum}</span>{badges}</div>
  {heading_html}<div class="page-content">{content_html}</div>
</section>""")

    search_html = """<div id="search-bar">
  <input type="text" id="search-input" placeholder="Search document or type 'page N'..." autocomplete="off">
  <span id="search-count"></span>
</div>""" if include_search else ""

    search_js = """<script>
const input = document.getElementById('search-input');
const countEl = document.getElementById('search-count');
input.addEventListener('input', () => {
  document.querySelectorAll('.search-highlight').forEach(el => el.classList.remove('search-highlight'));
  const query = input.value.trim();
  if (!query) { countEl.textContent = ''; return; }
  const pm = query.match(/^page\\s*(\\d+)$/i);
  if (pm) { document.getElementById('page-' + pm[1])?.scrollIntoView({behavior:'smooth'}); return; }
  let count = 0;
  document.querySelectorAll('mark').forEach(m => {
    if (m.textContent.toLowerCase().includes(query.toLowerCase())) { m.classList.add('search-highlight'); count++; }
  });
  countEl.textContent = count > 0 ? count + ' matches' : 'No matches';
  document.querySelector('.search-highlight')?.scrollIntoView({behavior:'smooth',block:'center'});
});
</script>""" if include_search else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    :root{{--bg:#0f1117;--surface:#1a1d27;--border:#2d3145;--text:#e2e8f0;--muted:#8892a4;--accent:#6366f1;--toc-width:280px;}}
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:15px;line-height:1.7;display:flex;}}
    #toc{{position:fixed;top:0;left:0;width:var(--toc-width);height:100vh;overflow-y:auto;background:var(--surface);border-right:1px solid var(--border);padding:1.5rem 1rem;}}
    #toc h2{{font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);margin-bottom:1rem;}}
    #toc ul{{list-style:none;}}#toc li{{margin-bottom:0.35rem;}}
    #toc a{{color:var(--muted);text-decoration:none;font-size:0.85rem;display:flex;gap:0.5rem;}}
    #toc a:hover{{color:var(--text);}}
    .toc-page{{color:var(--accent);min-width:2.5rem;}}
    #main{{margin-left:var(--toc-width);flex:1;padding:2rem;max-width:900px;}}
    #search-bar{{position:sticky;top:0;background:var(--surface);border-bottom:1px solid var(--border);padding:0.75rem 1rem;margin:-2rem -2rem 2rem;display:flex;align-items:center;gap:1rem;z-index:10;}}
    #search-input{{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:0.5rem 0.75rem;color:var(--text);font-size:0.9rem;}}
    #search-count{{color:var(--muted);font-size:0.8rem;}}
    .page-section{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1.5rem;margin-bottom:1.5rem;}}
    .page-header{{display:flex;align-items:center;gap:0.5rem;margin-bottom:1rem;padding-bottom:0.75rem;border-bottom:1px solid var(--border);}}
    .page-label{{font-size:0.75rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--accent);font-weight:600;}}
    .badge{{font-size:0.7rem;padding:0.2rem 0.5rem;border-radius:4px;}}
    .badge-table{{background:rgba(99,102,241,0.2);color:var(--accent);}}
    .badge-scanned{{background:rgba(234,179,8,0.2);color:#eab308;}}
    h2{{font-size:1.15rem;font-weight:600;margin:1rem 0 0.5rem;color:var(--text);}}
    p{{margin-bottom:0.75rem;color:var(--text);}}
    mark{{background:rgba(99,102,241,0.25);color:var(--text);border-bottom:1px solid #6366f1;border-radius:2px;padding:0 2px;cursor:help;}}
    .search-highlight{{background:rgba(251,191,36,0.3);border-bottom-color:#fbbf24;}}
    @media print{{#toc,#search-bar{{display:none;}}#main{{margin:0;}}.page-section{{break-inside:avoid;}}}}
  </style>
</head>
<body>
  {toc_html}
  <main id="main">
    {search_html}
    <h1 style="margin-bottom:2rem;font-size:1.5rem;">{title}</h1>
    {''.join(sections)}
  </main>
  {search_js}
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Render extracted PDF text as structured HTML.")
    parser.add_argument("--input", required=True, help="extracted_text.json from extract_text.py")
    parser.add_argument("--output", default="document.html", help="Output HTML file path.")
    parser.add_argument("--knowledge-graph", dest="kg_path", default=None, help="Optional knowledge_graph.json for entity annotations.")
    parser.add_argument("--no-toc", action="store_true", help="Disable table of contents.")
    parser.add_argument("--no-search", action="store_true", help="Disable search bar.")
    args = parser.parse_args()

    print(f"Loading: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        doc_data = json.load(f)

    kg_data = None
    if args.kg_path and os.path.exists(args.kg_path):
        with open(args.kg_path, "r", encoding="utf-8") as f:
            kg_data = json.load(f)
        entity_count = len(kg_data.get("entities", []))
        print(f"  → Annotating with {entity_count} entities from {args.kg_path}")

    include_toc = not args.no_toc
    include_search = not args.no_search

    if _USE_PACKAGE:
        pages = [
            PageContent(
                page_number=p["page_number"],
                text=p["text"],
                headings=p.get("headings", []),
                blocks=p.get("blocks", []),
                has_table=p.get("has_table", False),
                is_scanned=p.get("is_scanned", False),
            )
            for p in doc_data["pages"]
        ]
        doc = DocumentContent(
            source_file=doc_data["source_file"],
            total_pages=doc_data["total_pages"],
            title=doc_data.get("title", ""),
            metadata=doc_data.get("metadata", {}),
            pages=pages,
        )
        kg = None
        if kg_data:
            kg = KnowledgeGraph.model_validate(kg_data)
        html_content = render_document_html(doc, knowledge_graph=kg, include_toc=include_toc, include_search=include_search)
    else:
        html_content = _inline_render(doc_data, kg_data, include_toc, include_search)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"  ✓ {args.output} ({len(html_content):,} bytes)")
    print("Done.")


if __name__ == "__main__":
    main()
