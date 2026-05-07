"""Render PDF content as structured, LLM-readable HTML with entity annotations."""

from __future__ import annotations

import html
import os
from typing import Optional

from malimgraph.core.pdf_reader import DocumentContent
from malimgraph.schemas.entities import Entity, KnowledgeGraph


def render_document_html(
    doc: DocumentContent,
    knowledge_graph: Optional[KnowledgeGraph] = None,
    include_toc: bool = True,
    include_search: bool = True,
) -> str:
    """
    Render a DocumentContent as semantic HTML with page anchors, TOC,
    entity annotations, and optional search bar.
    Returns the complete HTML string.
    """
    entity_map = _build_entity_page_map(knowledge_graph) if knowledge_graph else {}

    toc_html = _build_toc(doc) if include_toc else ""
    pages_html = _build_pages(doc, entity_map)
    search_html = _build_search_bar() if include_search else ""

    return _wrap_document(
        title=html.escape(doc.title or os.path.basename(doc.source_file)),
        toc_html=toc_html,
        pages_html=pages_html,
        search_html=search_html,
        include_search=include_search,
    )


def _build_entity_page_map(kg: KnowledgeGraph) -> dict[int, list[Entity]]:
    """Map page_number → list of entities found on that page."""
    page_map: dict[int, list[Entity]] = {}
    for entity in kg.entities:
        for page in entity.source_pages:
            page_map.setdefault(page, []).append(entity)
    return page_map


def _build_toc(doc: DocumentContent) -> str:
    items = []
    for page in doc.pages:
        for heading in page.headings:
            anchor = f"page-{page.page_number}"
            items.append(
                f'<li><a href="#{anchor}">'
                f'<span class="toc-page">p.{page.page_number}</span> '
                f"{html.escape(heading[:80])}</a></li>"
            )

    if not items:
        items = [
            f'<li><a href="#page-{p.page_number}">Page {p.page_number}</a></li>' for p in doc.pages
        ]

    return f"""
<nav id="toc" aria-label="Table of Contents">
  <h2>Table of Contents</h2>
  <ul>
    {"".join(items)}
  </ul>
</nav>"""


def _build_pages(doc: DocumentContent, entity_map: dict[int, list[Entity]]) -> str:
    sections = []
    for page in doc.pages:
        entities_on_page = entity_map.get(page.page_number, [])
        section = _build_page_section(page, entities_on_page)
        sections.append(section)
    return "\n".join(sections)


def _build_page_section(page, entities: list[Entity]) -> str:
    page_text = page.text
    annotated = _annotate_entities(page_text, entities)

    heading_tags = ""
    for h in page.headings:
        heading_tags += f"<h2>{html.escape(h)}</h2>\n"

    badges = ""
    if page.has_table:
        badges += '<span class="badge badge-table">Table</span> '
    if page.is_scanned:
        badges += '<span class="badge badge-scanned">Scanned</span> '

    return f"""<section id="page-{page.page_number}" class="page-section" data-page="{page.page_number}">
  <div class="page-header">
    <span class="page-label">Page {page.page_number}</span>
    {badges}
  </div>
  {heading_tags}
  <div class="page-content">{annotated}</div>
</section>"""


def _annotate_entities(text: str, entities: list[Entity]) -> str:
    """Insert <mark> annotations around entity mentions in the text."""
    if not entities:
        return f"<p>{html.escape(text)}</p>"

    # Build a list of (start, end, entity) for all matches
    import re

    annotations: list[tuple[int, int, Entity]] = []

    for entity in entities:
        pattern = re.compile(re.escape(entity.label), re.IGNORECASE)
        for m in pattern.finditer(text):
            annotations.append((m.start(), m.end(), entity))

    # Sort by start position, resolve overlaps (keep longest)
    annotations.sort(key=lambda x: x[0])
    filtered: list[tuple[int, int, Entity]] = []
    last_end = 0
    for start, end, entity in annotations:
        if start >= last_end:
            filtered.append((start, end, entity))
            last_end = end

    # Build annotated string
    parts = []
    cursor = 0
    for start, end, entity in filtered:
        if cursor < start:
            parts.append(html.escape(text[cursor:start]))
        parts.append(
            f'<mark data-entity-id="{html.escape(entity.id)}" '
            f'data-entity-type="{html.escape(entity.type)}" '
            f'title="{html.escape(entity.type)}: {html.escape(entity.label)}">'
            f"{html.escape(text[start:end])}</mark>"
        )
        cursor = end

    if cursor < len(text):
        parts.append(html.escape(text[cursor:]))

    annotated = "".join(parts)
    # Wrap paragraphs
    paragraphs = annotated.split("\n\n")
    return "\n".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs if p.strip())


def _build_search_bar() -> str:
    return """<div id="search-bar">
  <input type="text" id="search-input" placeholder="Search document or type 'page N' to jump..." autocomplete="off">
  <span id="search-count"></span>
</div>"""


def _wrap_document(
    title: str,
    toc_html: str,
    pages_html: str,
    search_html: str,
    include_search: bool,
) -> str:
    search_js = _search_js() if include_search else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0f1117;
      --surface: #1a1d27;
      --border: #2d3145;
      --text: #e2e8f0;
      --muted: #8892a4;
      --accent: #6366f1;
      --mark-bg: rgba(99,102,241,0.25);
      --mark-border: #6366f1;
      --toc-width: 280px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Segoe UI', system-ui, sans-serif;
      font-size: 15px;
      line-height: 1.7;
      display: flex;
    }}
    #toc {{
      position: fixed;
      top: 0; left: 0;
      width: var(--toc-width);
      height: 100vh;
      overflow-y: auto;
      background: var(--surface);
      border-right: 1px solid var(--border);
      padding: 1.5rem 1rem;
    }}
    #toc h2 {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 1rem; }}
    #toc ul {{ list-style: none; }}
    #toc li {{ margin-bottom: 0.35rem; }}
    #toc a {{ color: var(--muted); text-decoration: none; font-size: 0.85rem; display: flex; gap: 0.5rem; }}
    #toc a:hover {{ color: var(--text); }}
    .toc-page {{ color: var(--accent); font-variant-numeric: tabular-nums; min-width: 2.5rem; }}
    #main {{
      margin-left: var(--toc-width);
      flex: 1;
      padding: 2rem;
      max-width: 900px;
    }}
    #search-bar {{
      position: sticky;
      top: 0;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 0.75rem 1rem;
      margin: -2rem -2rem 2rem;
      display: flex;
      align-items: center;
      gap: 1rem;
      z-index: 10;
    }}
    #search-input {{
      flex: 1;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.5rem 0.75rem;
      color: var(--text);
      font-size: 0.9rem;
    }}
    #search-count {{ color: var(--muted); font-size: 0.8rem; }}
    .page-section {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }}
    .page-header {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--border);
    }}
    .page-label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--accent); font-weight: 600; }}
    .badge {{ font-size: 0.7rem; padding: 0.2rem 0.5rem; border-radius: 4px; }}
    .badge-table {{ background: rgba(99,102,241,0.2); color: var(--accent); }}
    .badge-scanned {{ background: rgba(234,179,8,0.2); color: #eab308; }}
    h2 {{ font-size: 1.15rem; font-weight: 600; margin: 1rem 0 0.5rem; color: var(--text); }}
    p {{ margin-bottom: 0.75rem; color: var(--text); }}
    mark {{
      background: var(--mark-bg);
      color: var(--text);
      border-bottom: 1px solid var(--mark-border);
      border-radius: 2px;
      padding: 0 2px;
      cursor: help;
    }}
    .search-highlight {{ background: rgba(251,191,36,0.3); border-bottom-color: #fbbf24; }}
    @media print {{
      #toc, #search-bar {{ display: none; }}
      #main {{ margin: 0; }}
      .page-section {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  {toc_html}
  <main id="main">
    {search_html}
    <h1 style="margin-bottom:2rem;font-size:1.5rem;">{title}</h1>
    {pages_html}
  </main>
  {search_js}
</body>
</html>"""


def _search_js() -> str:
    return """<script>
const input = document.getElementById('search-input');
const countEl = document.getElementById('search-count');

input.addEventListener('input', () => {
  // Clear previous highlights
  document.querySelectorAll('.search-highlight').forEach(el => {
    el.classList.remove('search-highlight');
  });

  const query = input.value.trim();
  if (!query) { countEl.textContent = ''; return; }

  // Jump to page
  const pageMatch = query.match(/^page\\s*(\\d+)$/i);
  if (pageMatch) {
    const target = document.getElementById('page-' + pageMatch[1]);
    if (target) { target.scrollIntoView({ behavior: 'smooth' }); countEl.textContent = ''; }
    return;
  }

  // Text search
  const marks = document.querySelectorAll('mark');
  let count = 0;
  marks.forEach(m => {
    if (m.textContent.toLowerCase().includes(query.toLowerCase())) {
      m.classList.add('search-highlight');
      count++;
    }
  });

  // Also search plain text in paragraphs
  countEl.textContent = count > 0 ? count + ' matches' : 'No matches';
  if (count > 0) {
    document.querySelector('.search-highlight')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
});
</script>"""
