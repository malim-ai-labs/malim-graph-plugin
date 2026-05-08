"""
visualize_sigma.py - High-performance graph visualization using Sigma.js and Graphology.
Generates a self-contained HTML file for large-scale knowledge graph exploration.
"""

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

# Mapping of entity types to curated colors (GitNexus/Sigma style)
COLOR_PALETTE = {
    "Organization": "#1abc9c", # Turquoise
    "Person":       "#3498db", # Summer Sky
    "Location":     "#9b59b6", # Amethyst
    "Regulation":   "#e67e22", # Carrot
    "Concept":      "#e74c3c", # Alizarin
    "Product":      "#f1c40f", # Sunflower
    "Event":        "#2ecc71", # Emerald
    "Role":         "#34495e", # Wet Asphalt
    "Date":         "#95a5a6", # Asbestos
}
DEFAULT_COLOR = "#7f8c8d"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <!-- Sigma.js & Graphology Stack -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/graphology/0.25.1/graphology.ogdf.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/graphology/0.25.1/graphology.library.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/sigma@2.4.0/build/sigma.min.js"></script>
    <style>
        body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; background: #0b0e14; overflow: hidden; font-family: 'Inter', sans-serif; }}
        #container {{ width: 100%; height: 100%; }}
        #overlay {{ position: absolute; top: 20px; left: 20px; z-index: 10; color: #fff; pointer-events: none; }}
        h1 {{ font-size: 1.2rem; margin: 0; font-weight: 400; color: #cbd5e1; opacity: 0.8; }}
        #info-panel {{ 
            position: absolute; right: 20px; top: 20px; width: 300px;
            background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(51, 65, 85, 0.5);
            border-radius: 12px; padding: 20px; color: #e2e8f0; font-size: 0.9rem;
            backdrop-filter: blur(10px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            display: none;
        }}
        .label {{ color: #94a3b8; text-transform: uppercase; font-size: 0.7rem; margin-top: 15px; letter-spacing: 0.05em; }}
        .value {{ margin-top: 4px; line-height: 1.4; }}
        .confidence {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-top: 8px; font-weight: 600; }}
        .high {{ background: #059669; color: #ecfdf5; }}
        .medium {{ background: #d97706; color: #fffbeb; }}
        .low {{ background: #dc2626; color: #fef2f2; }}
    </style>
</head>
<body>
    <div id="overlay">
        <h1>{title}</h1>
    </div>
    <div id="info-panel">
        <h2 id="p-label" style="margin-top:0"></h2>
        <div id="p-type" style="font-weight: 600; color: #38bdf8;"></div>
        <div id="p-conf" class="confidence"></div>
        <div class="label">Source Text</div>
        <div id="p-text" class="value"></div>
        <div class="label">Source Pages</div>
        <div id="p-pages" class="value"></div>
    </div>
    <div id="container"></div>

    <script>
        const graphData = {data_json};
        const colorPalette = {color_palette_json};
        const defaultColor = "{default_color}";

        const graph = new graphology.Graph();

        // 1. Add Nodes
        graphData.entities.forEach((ent, i) => {{
            const type = ent.type || "Other";
            graph.addNode(ent.label, {{
                x: Math.random() * 100,
                y: Math.random() * 100,
                size: 10,
                label: ent.label,
                color: colorPalette[type] || defaultColor,
                type: type,
                confidence: ent.confidence || "medium",
                sourceText: ent.source_text || "N/A",
                sourcePages: (ent.source_pages || []).join(", ")
            }});
        }});

        // 2. Add Edges
        graphData.relationships.forEach((rel) => {{
            if (graph.hasNode(rel.source_label) && graph.hasNode(rel.target_label)) {{
                graph.addEdge(rel.source_label, rel.target_label, {{
                    label: rel.type,
                    size: 1,
                    color: "#334155"
                }});
            }}
        }});

        // 3. Simple Force Atlas Layout
        graphology.library.layout.forceAtlas2.assign(graph, {{
            iterations: 100,
            settings: {{
                gravity: 1,
                linLogMode: true,
                scalingRatio: 10
            }}
        }});

        // 4. Initialize Sigma
        const container = document.getElementById("container");
        const renderer = new Sigma(graph, container, {{
            renderEdgeLabels: true,
            labelSizeRatio: 1
        }});

        // 5. Interactions
        const panel = document.getElementById("info-panel");
        
        renderer.on("enterNode", ({{ node }}) => {{
            const attr = graph.getNodeAttributes(node);
            document.getElementById("p-label").innerText = attr.label;
            document.getElementById("p-type").innerText = attr.type;
            document.getElementById("p-text").innerText = attr.sourceText;
            document.getElementById("p-pages").innerText = attr.sourcePages;
            
            const conf = document.getElementById("p-conf");
            conf.innerText = attr.confidence.toUpperCase();
            conf.className = "confidence " + attr.confidence;
            
            panel.style.display = "block";
        }});

        renderer.on("clickStage", () => {{
            panel.style.display = "none";
        }});
    </script>
</body>
</html>
"""

def main():
    parser = argparse.ArgumentParser(description="Generate Sigma.js graph visualization")
    parser.add_argument("--input", required=True, help="Path to knowledge_graph.json")
    parser.add_argument("--output", default="graph_sigma.html", help="Output HTML file")
    parser.add_argument("--title", default="MalimGraph Visualizer (Sigma)", help="Page title")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found.")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    html_content = HTML_TEMPLATE.format(
        title=args.title,
        data_json=json.dumps(data),
        color_palette_json=json.dumps(COLOR_PALETTE),
        default_color=DEFAULT_COLOR
    )

    output_path = Path(args.output)
    output_path.write_text(html_content, encoding="utf-8")
    
    print(f"Visualization generated: {output_path.absolute()}")
    webbrowser.open(output_path.absolute().as_uri())

if __name__ == "__main__":
    main()
