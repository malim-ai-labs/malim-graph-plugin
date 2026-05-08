---
name: graph-visualizer
description: >
  Visualise a MalimGraph knowledge_graph.json file as a premium interactive browseable
  map using vis.js. Highly robust, self-contained, and optimized for standalone HTML.
  Trigger on: "visualise graph", "premium visualization", "show map", "open discovery map",
  "interactive explorer". Correctly handles id/label/source/target schema mapping.
---

# Premium Knowledge Graph Visualizer

Generate a high-fidelity, self-contained interactive explorer for your knowledge graphs.
Uses **vis.js** for a robust, physics-powered experience that runs in any browser.

## Quick Start

```bash
python skills/graph-visualizer/scripts/visualize_graph.py --input ./output/knowledge_graph.json
```

## Features
- **Robust Schema Mapping**: Correctly maps MalimGraph's internal `id` and `label` fields.
- **Stable Relationships**: Uses ID-based `source`/`target` links for guaranteed data integrity.
- **Premium Dark Aesthetic**: Neon highlights on a pitch-black background.
- **Physics Engine**: ForceAtlas2-based spatial layout for clear entity distribution.
- **Detail Inspector**: Click any node or edge to see verbatim source evidence and confidence.

## Options
```bash
python skills/graph-visualizer/scripts/visualize_graph.py \
  --input  ./output/knowledge_graph.json \
  --output ./output/discovery_map.html \
  --title  "Knowledge Mapping: [Document Name]"
```
