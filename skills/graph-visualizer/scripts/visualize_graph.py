"""
visualize_graph.py — Premium interactive knowledge graph visualization using vis.js.
Generates a self-contained, high-fidelity browser explorer.
"""

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

# Premium Neon Palette
TYPE_COLORS = {
    "Organization": "#00f2ff", # Cyan
    "Person":       "#ff00ea", # Magenta
    "Location":     "#70ff00", # Lime
    "Regulation":   "#ff9d00", # Orange
    "Concept":      "#0078ff", # Royal Blue
    "Product":      "#ffe600", # Yellow
    "Event":        "#ff3c00", # Red-Orange
    "Role":         "#8a2be2", # Violet
    "Date":         "#ffffff", # White
}
DEFAULT_COLOR = "#a0a0a0"

def make_html(graph: dict, title: str) -> str:
    entities = graph.get("entities", [])
    rels = graph.get("relationships", [])

    nodes_data = []
    for ent in entities:
        etype = ent.get("type", "Other")
        color = TYPE_COLORS.get(etype, DEFAULT_COLOR)
        nodes_data.append({
            "id": ent.get("id"),
            "label": ent.get("label") or ent.get("name") or "Unknown",
            "type": etype,
            "color": {
                "background": "#121212",
                "border": color,
                "highlight": {"background": color, "border": "#ffffff"}
            },
            "font": {"color": "#ffffff", "size": 14},
            "confidence": ent.get("confidence", "medium"),
            "source_text": ent.get("source_text", ""),
            "source_pages": ent.get("source_pages", []),
            "shadow": {"enabled": True, "color": color, "size": 10}
        })

    edges_data = []
    for rel in rels:
        edges_data.append({
            "from": rel.get("source"),
            "to": rel.get("target"),
            "label": rel.get("type", "").replace("_", " "),
            "arrows": "to",
            "color": {"color": "#444444", "highlight": "#ffffff", "opacity": 0.6},
            "font": {"color": "#888888", "size": 10, "strokeWidth": 0},
            "source_text": rel.get("source_text", ""),
            "source_pages": rel.get("source_pages", []),
            "confidence": rel.get("confidence", "medium")
        })

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        body, html {{ margin: 0; padding: 0; height: 100%; background: #000; color: #fff; font-family: 'Inter', sans-serif; overflow: hidden; }}
        #mynetwork {{ width: 100%; height: 100%; }}
        #header {{ position: absolute; top: 20px; left: 20px; z-index: 10; pointer-events: none; opacity: 0.8; }}
        #header h1 {{ font-size: 1.1rem; font-weight: 300; letter-spacing: 0.1em; color: #aaa; text-transform: uppercase; margin: 0; }}
        #details {{ 
            position: absolute; right: 20px; top: 20px; width: 320px;
            background: rgba(10, 10, 10, 0.95); border-left: 3px solid #333;
            padding: 25px; height: calc(100% - 40px); overflow-y: auto;
            transition: transform 0.3s ease; box-shadow: -20px 0 50px rgba(0,0,0,0.5);
            display: none;
        }}
        .field {{ margin-bottom: 25px; }}
        .label {{ color: #555; text-transform: uppercase; font-size: 0.65rem; font-weight: 700; letter-spacing: 0.15em; margin-bottom: 8px; }}
        .content {{ color: #e0e0e0; font-size: 0.9rem; line-height: 1.5; }}
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; margin-right: 8px; }}
        .high {{ background: #00ffaa22; color: #00ffaa; border: 1px solid #00ffaa; }}
        .medium {{ background: #ffaa0022; color: #ffaa00; border: 1px solid #ffaa00; }}
        .low {{ background: #ff440022; color: #ff4400; border: 1px solid #ff4400; }}
    </style>
</head>
<body>
    <div id="header"><h1>{title}</h1></div>
    <div id="details">
        <div id="details-content"></div>
    </div>
    <div id="mynetwork"></div>

    <script type="text/javascript">
        const nodes = new vis.DataSet({json.dumps(nodes_data)});
        const edges = new vis.DataSet({json.dumps(edges_data)});

        const container = document.getElementById('mynetwork');
        const data = {{ nodes, edges }};
        const options = {{
            nodes: {{ shape: 'dot', size: 16, borderWith: 2, scaling: {{ min: 10, max: 30 }} }},
            edges: {{ width: 1, smooth: {{ type: 'continuous' }} }},
            physics: {{
                forceAtlas2Based: {{ gravitationalConstant: -100, centralGravity: 0.01, springLength: 100, springConstant: 0.08 }},
                maxVelocity: 50, solver: 'forceAtlas2Based', stabilization: {{ iterations: 150 }}
            }},
            interaction: {{ hover: true, tooltipDelay: 200 }}
        }};

        const network = new vis.Network(container, data, options);
        const details = document.getElementById('details');
        const detailsContent = document.getElementById('details-content');

        network.on("click", function (params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                showDetails(node, "entity");
            }} else if (params.edges.length > 0) {{
                const edgeId = params.edges[0];
                const edge = edges.get(edgeId);
                showDetails(edge, "relationship");
            }} else {{
                details.style.display = "none";
            }}
        }});

        function showDetails(item, category) {{
            let html = `
                <div style="font-size: 1.4rem; font-weight: 600; margin-bottom: 20px;">${{item.label}}</div>
                <div class="field">
                    <div class="label">Classification</div>
                    <span class="badge" style="border: 1px solid ${{item.color?.border}}; color: ${{item.color?.border}}">${{item.type || category}}</span>
                    <span class="badge ${{item.confidence}}">${{item.confidence.toUpperCase()}} CONFIDENCE</span>
                </div>
            `;

            if (item.source_text) {{
                html += `
                    <div class="field">
                        <div class="label">Source Evidence</div>
                        <div class="content">"${{item.source_text}}"</div>
                    </div>
                `;
            }}

            if (item.source_pages && item.source_pages.length > 0) {{
                html += `
                    <div class="field">
                        <div class="label">Page Numbers</div>
                        <div class="content">${{item.source_pages.join(', ')}}</div>
                    </div>
                `;
            }}

            detailsContent.innerHTML = html;
            details.style.display = "block";
        }}
    </script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Premium Knowledge Graph Visualizer")
    parser.add_argument("--input", required=True, help="Path to knowledge_graph.json")
    parser.add_argument("--output", default="graph_premium.html", help="Output file")
    parser.add_argument("--title", default="MalimGraph Visual Discovery", help="Title")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found.")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    html = make_html(data, args.title)
    output_path = Path(args.output)
    output_path.write_text(html, encoding="utf-8")
    
    print(f"Discovery map created: {output_path.absolute()}")
    webbrowser.open(output_path.absolute().as_uri())

if __name__ == "__main__":
    main()
