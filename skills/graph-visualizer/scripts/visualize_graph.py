"""
visualize_graph.py — Generate a self-contained interactive browser visualization
of a MalimGraph knowledge_graph.json file using vis.js Network.

Usage:
    python visualize_graph.py --input knowledge_graph.json
    python visualize_graph.py --input knowledge_graph.json --output my_graph.html --title "My Graph"
"""

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

# ── Entity type → colour mapping ──────────────────────────────────────────────
TYPE_COLORS = {
    "Organization": "#4e79a7",
    "Person":       "#f28e2b",
    "Location":     "#59a14f",
    "Regulation":   "#e15759",
    "Concept":      "#76b7b2",
    "Product":      "#edc948",
    "Event":        "#b07aa1",
    "Role":         "#ff9da7",
    "Date":         "#bab0ac",
}
DEFAULT_COLOR = "#9c755f"


def make_html(graph: dict, title: str) -> str:
    """Return a fully self-contained HTML page with the graph embedded."""

    entities = graph.get("entities", [])
    rels      = graph.get("relationships", [])

    # Build id → index lookup
    label_to_id: dict[str, int] = {}
    nodes_data = []
    for i, ent in enumerate(entities):
        label = ent.get("label", f"entity_{i}")
        ent_type = ent.get("type", "Other")
        color = TYPE_COLORS.get(ent_type, DEFAULT_COLOR)
        label_to_id[label] = i
        nodes_data.append({
            "id":    i,
            "label": label,
            "type":  ent_type,
            "color": {"background": color, "border": color,
                      "highlight": {"background": "#ffffff", "border": color}},
            "confidence":   ent.get("confidence", "medium"),
            "source_text":  ent.get("source_text", ""),
            "source_pages": ent.get("source_pages", []),
            "font":  {"color": "#ffffff", "size": 13},
            "shape": "dot",
            "size":  12,
        })

    edges_data = []
    for i, rel in enumerate(rels):
        src = label_to_id.get(rel.get("source_label", ""))
        tgt = label_to_id.get(rel.get("target_label", ""))
        if src is None or tgt is None:
            continue
        edges_data.append({
            "id":     i,
            "from":   src,
            "to":     tgt,
            "label":  rel.get("type", ""),
            "arrows": "to",
            "color":  {"color": "#555555", "highlight": "#ffffff"},
            "font":   {"color": "#aaaaaa", "size": 10, "align": "middle"},
            "source_text":  rel.get("source_text", ""),
            "source_pages": rel.get("source_pages", []),
            "confidence":   rel.get("confidence", "medium"),
        })

    # Collect unique types for the legend/filter
    all_types = sorted({n["type"] for n in nodes_data})
    type_colors_json = json.dumps({t: TYPE_COLORS.get(t, DEFAULT_COLOR) for t in all_types})
    nodes_json = json.dumps(nodes_data)
    edges_json = json.dumps(edges_data)
    source_file = graph.get("source_file", "")
    n_entities = len(nodes_data)
    n_rels = len(edges_data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0a0a0a; color: #e0e0e0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    height: 100vh; display: flex; flex-direction: column; overflow: hidden;
  }}

  /* ── Top bar ── */
  header {{
    display: flex; align-items: center; gap: 1rem;
    padding: 0.6rem 1.2rem; background: #111; border-bottom: 1px solid #1e1e1e;
    flex-shrink: 0; flex-wrap: wrap;
  }}
  .title {{ font-size: 0.95rem; font-weight: 600; color: #fff; white-space: nowrap; }}
  .stats {{ font-size: 0.75rem; color: #666; white-space: nowrap; }}
  .search-wrap {{ flex: 1; min-width: 160px; max-width: 320px; position: relative; }}
  .search-wrap input {{
    width: 100%; background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 4px;
    color: #e0e0e0; font-size: 0.82rem; padding: 0.35rem 0.7rem;
    outline: none; transition: border-color 0.2s;
  }}
  .search-wrap input:focus {{ border-color: #555; }}
  .conf-filter {{ display: flex; gap: 0.4rem; align-items: center; font-size: 0.75rem; color: #777; }}
  .conf-filter select {{
    background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 4px;
    color: #e0e0e0; font-size: 0.75rem; padding: 0.3rem 0.5rem; cursor: pointer;
  }}

  /* ── Main layout ── */
  .layout {{ flex: 1; display: flex; overflow: hidden; }}

  /* ── Sidebar ── */
  .sidebar {{
    width: 210px; flex-shrink: 0; background: #0d0d0d; border-right: 1px solid #1a1a1a;
    display: flex; flex-direction: column; overflow: hidden;
  }}
  .sidebar-section {{ padding: 0.75rem 1rem; border-bottom: 1px solid #1a1a1a; }}
  .sidebar-section h3 {{ font-size: 0.7rem; color: #555; text-transform: uppercase;
    letter-spacing: 0.1em; margin-bottom: 0.5rem; }}
  .type-item {{
    display: flex; align-items: center; gap: 0.5rem; padding: 0.22rem 0;
    cursor: pointer; border-radius: 3px; font-size: 0.78rem; color: #ccc;
    user-select: none;
  }}
  .type-item:hover {{ color: #fff; }}
  .type-item.hidden {{ opacity: 0.35; }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
  .type-count {{ margin-left: auto; font-size: 0.7rem; color: #555; }}

  /* ── Canvas ── */
  #graph {{ flex: 1; background: #0a0a0a; }}

  /* ── Detail panel ── */
  .detail {{
    width: 260px; flex-shrink: 0; background: #0d0d0d; border-left: 1px solid #1a1a1a;
    display: flex; flex-direction: column; overflow: hidden; font-size: 0.8rem;
  }}
  .detail-header {{
    padding: 0.75rem 1rem; border-bottom: 1px solid #1a1a1a;
    font-size: 0.7rem; color: #555; text-transform: uppercase; letter-spacing: 0.1em;
  }}
  .detail-body {{ padding: 1rem; flex: 1; overflow-y: auto; }}
  .detail-body.empty {{ display: flex; align-items: center; justify-content: center;
    color: #333; text-align: center; }}
  .detail-label {{ font-size: 1rem; font-weight: 600; color: #fff; margin-bottom: 0.5rem; }}
  .badge {{
    display: inline-block; padding: 0.15rem 0.5rem; border-radius: 3px;
    font-size: 0.7rem; font-weight: 600; margin-bottom: 0.75rem; color: #000;
  }}
  .field-name {{ color: #555; font-size: 0.68rem; text-transform: uppercase;
    letter-spacing: 0.08em; margin-top: 0.75rem; margin-bottom: 0.25rem; }}
  .field-value {{ color: #ccc; line-height: 1.5; word-break: break-word; }}
  .pages {{ display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.25rem; }}
  .page-chip {{
    background: #1e1e1e; border: 1px solid #2a2a2a; border-radius: 3px;
    padding: 0.1rem 0.4rem; font-size: 0.7rem; color: #888;
  }}
  .conf-badge {{
    font-size: 0.68rem; padding: 0.1rem 0.4rem; border-radius: 3px; font-weight: 600;
    margin-top: 0.5rem; display: inline-block;
  }}
  .conf-high   {{ background: #1c3a1c; color: #4caf50; }}
  .conf-medium {{ background: #3a2e1c; color: #ff9800; }}
  .conf-low    {{ background: #3a1c1c; color: #f44336; }}

  /* scrollbar */
  ::-webkit-scrollbar {{ width: 5px; }} ::-webkit-scrollbar-track {{ background: #111; }}
  ::-webkit-scrollbar-thumb {{ background: #2a2a2a; border-radius: 3px; }}
</style>
</head>
<body>

<!-- Top bar -->
<header>
  <div class="title">{title}</div>
  <div class="stats">{n_entities} entities · {n_rels} relationships{f' · {source_file}' if source_file else ''}</div>
  <div class="search-wrap">
    <input type="search" id="searchBox" placeholder="Search entities…" oninput="filterBySearch(this.value)">
  </div>
  <div class="conf-filter">
    Confidence
    <select onchange="filterByConf(this.value)">
      <option value="all">All</option>
      <option value="high">High</option>
      <option value="medium">Medium</option>
      <option value="low">Low</option>
    </select>
  </div>
</header>

<div class="layout">
  <!-- Sidebar: type legend / filter -->
  <nav class="sidebar">
    <div class="sidebar-section">
      <h3>Entity Types</h3>
      <div id="typeList"></div>
    </div>
  </nav>

  <!-- Graph canvas -->
  <div id="graph"></div>

  <!-- Detail panel -->
  <aside class="detail">
    <div class="detail-header">Selection</div>
    <div class="detail-body empty" id="detailBody">
      <span>Click a node or edge<br>to see details</span>
    </div>
  </aside>
</div>

<script>
const RAW_NODES = {nodes_json};
const RAW_EDGES = {edges_json};
const TYPE_COLORS = {type_colors_json};

// ── Build vis datasets ─────────────────────────────────────────────────────
const nodesDS = new vis.DataSet(RAW_NODES.map(n => ({{
  ...n,
  title: n.label,  // tooltip
}})));
const edgesDS = new vis.DataSet(RAW_EDGES);

const container = document.getElementById('graph');
const network = new vis.Network(container, {{ nodes: nodesDS, edges: edgesDS }}, {{
  physics: {{
    enabled: true,
    barnesHut: {{ gravitationalConstant: -8000, centralGravity: 0.3, springLength: 140 }},
    stabilization: {{ iterations: 200 }},
  }},
  interaction: {{
    hover: true, tooltipDelay: 200,
    navigationButtons: false, keyboard: false,
  }},
  edges: {{
    smooth: {{ type: 'continuous', roundness: 0.4 }},
    width: 1.2,
  }},
}});

// Scale node size by degree after network stabilises
network.on('stabilizationIterationsDone', () => {{
  network.setOptions({{ physics: {{ enabled: false }} }});
  const degrees = {{}};
  RAW_EDGES.forEach(e => {{
    degrees[e.from] = (degrees[e.from] || 0) + 1;
    degrees[e.to]   = (degrees[e.to]   || 0) + 1;
  }});
  nodesDS.forEach(n => {{
    nodesDS.update({{ id: n.id, size: 10 + Math.min((degrees[n.id] || 0) * 2, 20) }});
  }});
}});

// ── Legend / type filter ───────────────────────────────────────────────────
const hiddenTypes = new Set();
const typeList = document.getElementById('typeList');
const typeCounts = {{}};
RAW_NODES.forEach(n => {{ typeCounts[n.type] = (typeCounts[n.type] || 0) + 1; }});

Object.entries(TYPE_COLORS).forEach(([type, color]) => {{
  if (!typeCounts[type]) return;
  const item = document.createElement('div');
  item.className = 'type-item';
  item.innerHTML = `<span class="dot" style="background:${{color}}"></span>
    ${{type}}<span class="type-count">${{typeCounts[type]}}</span>`;
  item.onclick = () => toggleType(type, item);
  typeList.appendChild(item);
}});

function toggleType(type, el) {{
  if (hiddenTypes.has(type)) {{ hiddenTypes.delete(type); el.classList.remove('hidden'); }}
  else {{ hiddenTypes.add(type); el.classList.add('hidden'); }}
  applyFilters();
}}

// ── Filters ────────────────────────────────────────────────────────────────
let searchTerm = '';
let confFilter = 'all';

function filterBySearch(val) {{ searchTerm = val.toLowerCase().trim(); applyFilters(); }}
function filterByConf(val)   {{ confFilter = val; applyFilters(); }}

function applyFilters() {{
  const updates = RAW_NODES.map(n => {{
    const hidden =
      hiddenTypes.has(n.type) ||
      (confFilter !== 'all' && n.confidence !== confFilter) ||
      (searchTerm && !n.label.toLowerCase().includes(searchTerm));
    return {{ id: n.id, hidden }};
  }});
  nodesDS.update(updates);

  // Hide edges to/from hidden nodes
  const hiddenIds = new Set(updates.filter(u => u.hidden).map(u => u.id));
  edgesDS.update(RAW_EDGES.map(e => ({{
    id: e.id,
    hidden: hiddenIds.has(e.from) || hiddenIds.has(e.to),
  }})));
}}

// ── Detail panel ───────────────────────────────────────────────────────────
const detailBody = document.getElementById('detailBody');

function confClass(c) {{ return `conf-${{c}}`; }}

function showNodeDetail(nodeId) {{
  const n = RAW_NODES[nodeId];
  if (!n) return;
  const color = TYPE_COLORS[n.type] || '#9c755f';
  const pages = (n.source_pages || []).map(p => `<span class="page-chip">p.${{p}}</span>`).join('');
  detailBody.className = 'detail-body';
  detailBody.innerHTML = `
    <div class="detail-label">${{n.label}}</div>
    <span class="badge" style="background:${{color}}">${{n.type}}</span>
    ${{n.confidence ? `<span class="conf-badge ${{confClass(n.confidence)}}">${{n.confidence}}</span>` : ''}}
    ${{n.source_text ? `<div class="field-name">Source text</div>
      <div class="field-value">"${{n.source_text}}"</div>` : ''}}
    ${{pages ? `<div class="field-name">Pages</div><div class="pages">${{pages}}</div>` : ''}}
  `;
}}

function showEdgeDetail(edgeId) {{
  const e = RAW_EDGES[edgeId];
  if (!e) return;
  const src = RAW_NODES[e.from]?.label ?? '';
  const tgt = RAW_NODES[e.to]?.label ?? '';
  const pages = (e.source_pages || []).map(p => `<span class="page-chip">p.${{p}}</span>`).join('');
  detailBody.className = 'detail-body';
  detailBody.innerHTML = `
    <div class="field-name">Relationship</div>
    <div class="detail-label">${{e.label || 'RELATED_TO'}}</div>
    <div class="field-name">From</div><div class="field-value">${{src}}</div>
    <div class="field-name">To</div><div class="field-value">${{tgt}}</div>
    ${{e.confidence ? `<span class="conf-badge ${{confClass(e.confidence)}}">${{e.confidence}}</span>` : ''}}
    ${{e.source_text ? `<div class="field-name">Source text</div>
      <div class="field-value">"${{e.source_text}}"</div>` : ''}}
    ${{pages ? `<div class="field-name">Pages</div><div class="pages">${{pages}}</div>` : ''}}
  `;
}}

network.on('selectNode', p => p.nodes.length && showNodeDetail(p.nodes[0]));
network.on('selectEdge', p => !p.nodes.length && p.edges.length && showEdgeDetail(p.edges[0]));
network.on('deselectNode', () => {{
  detailBody.className = 'detail-body empty';
  detailBody.innerHTML = '<span>Click a node or edge<br>to see details</span>';
}});
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Visualise a MalimGraph knowledge_graph.json in the browser")
    parser.add_argument("--input",   required=True, help="Path to knowledge_graph.json")
    parser.add_argument("--output",  default="graph_visualization.html", help="Output HTML file path")
    parser.add_argument("--title",   default="Knowledge Graph", help="Page title")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, encoding="utf-8") as f:
        graph = json.load(f)

    n_entities = len(graph.get("entities", []))
    n_rels     = len(graph.get("relationships", []))
    print(f"Loaded {n_entities} entities and {n_rels} relationships from {args.input}")

    html = make_html(graph, args.title)
    out  = Path(args.output)
    out.write_text(html, encoding="utf-8")
    print(f"Visualization saved → {out.resolve()}")

    if not args.no_open:
        url = out.resolve().as_uri()
        print(f"Opening browser: {url}")
        webbrowser.open(url)


if __name__ == "__main__":
    main()
