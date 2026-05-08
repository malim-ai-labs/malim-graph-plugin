---
name: graph-visualizer
description: >
  Visualise a MalimGraph knowledge_graph.json file as an interactive, browser-based
  force-directed graph. Use when the user wants to explore, browse, or present a
  knowledge graph visually. Trigger on: "visualise graph", "visualize knowledge graph",
  "show graph in browser", "interactive graph", "graph explorer", "open graph viewer",
  "browse entities", "network diagram", "force graph", "d3 graph", "vis.js graph",
  "explore relationships visually". No external dependencies — generates a single
  self-contained HTML file and opens it. Does NOT require Neo4j or any database.
---

# Graph Visualizer Skill

Generate an interactive, self-contained browser visualization of any `knowledge_graph.json`
file produced by MalimGraph. Zero external dependencies — runs entirely in the browser.

## Quick Start

```bash
python scripts/visualize_graph.py --input ./output/knowledge_graph.json
```

This will:
1. Read the `knowledge_graph.json`
2. Generate `graph_visualization.html` (self-contained, all JS embedded)
3. Open it automatically in your default browser

---

## Options

```bash
python scripts/visualize_graph.py \
  --input  ./output/knowledge_graph.json \   # path to graph JSON (required)
  --output ./output/graph_vis.html \         # output HTML path (default: graph_visualization.html)
  --title  "My Knowledge Graph" \            # page title
  --no-open                                  # generate HTML without opening browser
```

---

## What the Visualization Shows

- **Nodes** — one per entity, colored by type:
  | Type | Color |
  |------|-------|
  | Organization | `#4e79a7` (blue) |
  | Person | `#f28e2b` (orange) |
  | Location | `#59a14f` (green) |
  | Regulation | `#e15759` (red) |
  | Concept | `#76b7b2` (teal) |
  | Product | `#edc948` (yellow) |
  | Event | `#b07aa1` (purple) |
  | Role | `#ff9da7` (pink) |
  | Other | `#9c755f` (brown) |

- **Edges** — labeled with relationship type (e.g. `LED_BY`, `GOVERNED_BY`)
- **Node size** — scales with connection count (more connected = larger)
- **Click a node** — shows a details panel with `source_text`, `source_pages`, `confidence`

---

## Interaction Controls

| Action | Result |
|--------|--------|
| Drag a node | Reposition it |
| Scroll | Zoom in / out |
| Click node | Show entity details panel |
| Click edge | Highlight connected nodes |
| Double-click canvas | Reset zoom |
| Search box (top) | Filter nodes by label |

---

## Filters (in the UI)

- **Entity type filter** — toggle individual types on/off
- **Confidence filter** — show only high / medium / low
- **Min connections** — hide isolated or low-degree nodes

---

## Output

The generated HTML file is fully self-contained — share it as a single file with no server
needed. Open with any modern browser (Chrome, Firefox, Edge, Safari).
