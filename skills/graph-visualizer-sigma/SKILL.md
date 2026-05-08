---
name: graph-visualizer-sigma
description: >
  Visualise a MalimGraph knowledge_graph.json file as an interactive, high-performance
  browser-based graph using Sigma.js and Graphology (the GitNexus stack).
  This visualizer uses WebGL for ultra-smooth rendering of large graphs.
  Trigger on: "visualise graph sigma", "sigma visualization", "high-performance graph",
  "large graph visualization", "open sigma viewer", "gitnexus style graph".
---

# Sigma.js Graph Visualizer Skill

Generate a professional, high-performance interactive browser visualization of any
`knowledge_graph.json` file. Uses **Sigma.js** and **Graphology** for WebGL rendering.

## Quick Start

```bash
python scripts/visualize_sigma.py --input ./output/knowledge_graph.json
```

This will:
1. Read the `knowledge_graph.json`
2. Generate `graph_sigma.html` (self-contained with Sigma.js/Graphology CDNs)
3. Open it automatically in your default browser

---

## Features (GitNexus Stack)

- **WebGL Rendering** — Smoothly handles thousands of nodes and edges.
- **Force-Directed Layout** — Built-in Graphology FA2 (ForceAtlas2) layout support.
- **Node Collision Detection** — Prevents node overlap for better readability.
- **Interactive Details** — Hover and click interactions to inspect entity properties.
- **Themed UI** — Premium dark-mode interface matching MalimGraph aesthetics.

---

## Options

```bash
python scripts/visualize_sigma.py \
  --input  ./output/knowledge_graph.json \
  --output ./output/discovery_map.html \
  --title  "Knowledge Discovery Map"
```

---

## Visualization Mapping

- **Nodes**: Colored by entity type (Organization, Person, etc.) using a curated palette.
- **Edges**: Force-directed connections based on relationship density.
- **Camera**: Adaptive zoom and centering.
