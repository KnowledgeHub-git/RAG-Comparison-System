"""
Graph Visualizer — converts LightRAG .graphml to a beautiful Vis.js interactive HTML file.
"""

import os
import sys
from pathlib import Path
import networkx as nx

# Ensure project root is on PYTHONPATH when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config


def generate_interactive_graph(
    graphml_path: str = None,
    output_html_path: str = None,
) -> str:
    """
    Read the LightRAG GraphML file and generate a beautiful, interactive Vis.js HTML dashboard.
    
    Returns the path to the generated HTML file.
    """
    if graphml_path is None:
        graphml_path = os.path.join(Config.LIGHTRAG_DIR, "graph_chunk_entity_relation.graphml")
    
    if output_html_path is None:
        output_html_path = os.path.join(Config.LIGHTRAG_DIR, "interactive_graph.html")
        
    if not os.path.exists(graphml_path):
        # Return a simple placeholder HTML if the graph doesn't exist yet
        placeholder = """
        <html>
        <body style="background:#121212; color:#fff; font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh;">
            <h3>🕸️ Knowledge Graph not indexed yet. Please run ingestion first.</h3>
        </body>
        </html>
        """
        os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(placeholder)
        return output_html_path

    # Load graph using networkx
    G = nx.read_graphml(graphml_path)
    
    # Calculate degree centrality to scale nodes
    degrees = dict(G.degree())
    max_degree = max(degrees.values()) if degrees else 1
    
    # Map entity types to distinct, aesthetic colors
    # We use sleek, tailored HSL values for premium visual aesthetics
    COLOR_MAP = {
        "ORGANIZATION": "#3b82f6", # Vibrant Blue
        "COMPANY": "#3b82f6",
        "PERSON": "#ec4899",       # Pink
        "GEO": "#10b981",          # Emerald Green
        "LOCATION": "#10b981",
        "CONCEPT": "#8b5cf6",       # Royal Purple
        "EVENT": "#f59e0b",         # Amber/Orange
        "TECHNOLOGY": "#06b6d4",    # Cyan
        "UNKNOWN": "#6b7280",       # Slate Grey
    }
    
    nodes_js = []
    for node, data in G.nodes(data=True):
        entity_type = data.get("entity_type", "UNKNOWN").upper()
        # Default to UNKNOWN color if entity_type is not in COLOR_MAP
        color = COLOR_MAP.get(entity_type, COLOR_MAP.get(entity_type.split("_")[0], COLOR_MAP["UNKNOWN"]))
        
        # Calculate size based on connections (degrees)
        deg = degrees.get(node, 1)
        size = 15 + (deg / max_degree) * 35  # dynamic scaling between 15 and 50
        
        # Format custom tooltip (HTML supported)
        desc = data.get("description", "No description available.")
        tooltip_desc = desc.replace('"', '\\"').replace('\n', '<br>')
        tooltip = f"<strong>{node}</strong><br><span style='color:#a78bfa;'>Type: {entity_type}</span><br><br><span style='font-size:12px; color:#cbd5e1;'>{tooltip_desc}</span>"
        
        nodes_js.append({
            "id": node,
            "label": node,
            "title": tooltip,
            "value": size,
            "color": {
                "background": color,
                "border": color,
                "highlight": {
                    "background": "#ffffff",
                    "border": color
                }
            },
            "font": {
                "color": "#e2e8f0",
                "size": 14,
                "face": "system-ui"
            }
        })
        
    edges_js = []
    for u, v, data in G.edges(data=True):
        desc = data.get("description", "").replace('"', '\\"').replace('\n', '<br>')
        weight = float(data.get("weight", 1.0))
        tooltip = f"<strong>{u} &rarr; {v}</strong><br><span style='font-size:12px; color:#cbd5e1;'>{desc}</span>"
        
        edges_js.append({
            "from": u,
            "to": v,
            "title": tooltip,
            "width": max(1, min(weight, 5)), # scale weight to visual width
            "color": {
                "color": "#475569", # Elegant subtle connecting lines
                "highlight": "#cbd5e1"
            },
            "arrows": "to" # Directed relationship flows
        })

    # Output HTML template leveraging Tailwind + Vis.js
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LightRAG Interactive Knowledge Graph</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style type="text/css">
        #network {{
            width: 100%;
            height: calc(100vh - 80px);
            background-color: #0b0f19;
        }}
        /* Custom vis tooltips styling */
        div.vis-network div.vis-tooltip {{
            background-color: #1e293b !important;
            border: 1px solid #475569 !important;
            color: #cbd5e1 !important;
            font-family: system-ui, sans-serif !important;
            border-radius: 8px !important;
            padding: 12px !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5) !important;
            max-width: 300px !important;
            white-space: normal !important;
        }}
    </style>
</head>
<body class="bg-[#0b0f19] text-slate-100 font-sans overflow-hidden">

    <!-- Header bar -->
    <div class="h-20 bg-[#0f172a] border-b border-[#1e293b] flex items-center justify-between px-6 z-10 relative">
        <div class="flex items-center gap-3">
            <span class="text-2xl">🕸️</span>
            <div>
                <h1 class="font-bold text-lg leading-tight">LightRAG Knowledge Graph</h1>
                <p class="text-xs text-slate-400">Interactive Entity-Relationship visualization ({len(nodes_js)} entities, {len(edges_js)} relationships)</p>
            </div>
        </div>
        
        <!-- Controls & Search -->
        <div class="flex items-center gap-4">
            <!-- Search Input -->
            <div class="relative">
                <input type="text" id="search-input" placeholder="Search entity..." 
                       class="w-64 bg-[#1e293b] border border-[#334155] rounded-lg px-4 py-1.5 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-slate-100">
                <button onclick="searchNode()" class="absolute right-3 top-2 text-slate-400 hover:text-white">🔍</button>
            </div>
            
            <!-- Toggle Physics -->
            <button onclick="togglePhysics()" id="physics-btn" 
                    class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-colors">
                Freeze Physics
            </button>
        </div>
    </div>

    <!-- Network container -->
    <div id="network"></div>

    <script type="text/javascript">
        // Embed parsed Python data structures
        const nodesData = {nodes_js};
        const edgesData = {edges_js};

        // Create vis datasets
        const nodes = new vis.DataSet(nodesData);
        const edges = new vis.DataSet(edgesData);

        // Network configuration options
        let physicsEnabled = true;
        const container = document.getElementById('network');
        const data = {{ nodes: nodes, edges: edges }};
        
        const options = {{
            nodes: {{
                shape: 'dot',
                scaling: {{
                    min: 10,
                    max: 40
                }},
                borderWidth: 2,
                shadow: true
            }},
            edges: {{
                smooth: {{
                    type: 'continuous',
                    roundness: 0.5
                }},
                shadow: true
            }},
            physics: {{
                stabilization: {{
                    enabled: true,
                    iterations: 150
                }},
                barnesHut: {{
                    gravitationalConstant: -8000,
                    springConstant: 0.04,
                    springLength: 95
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200,
                navigationButtons: true,
                keyboard: true
            }}
        }};

        // Initialize vis network graph
        const network = new vis.Network(container, data, options);

        // Toggle physics button handler
        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
            const btn = document.getElementById('physics-btn');
            if (physicsEnabled) {{
                btn.innerText = 'Freeze Physics';
                btn.className = 'bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-colors';
            }} else {{
                btn.innerText = 'Release Physics';
                btn.className = 'bg-slate-700 hover:bg-slate-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-colors';
            }}
        }}

        // Search box handler
        function searchNode() {{
            const searchVal = document.getElementById('search-input').value.trim().toLowerCase();
            if (!searchVal) return;
            
            const matchedNode = nodesData.find(n => n.label.toLowerCase().includes(searchVal));
            if (matchedNode) {{
                network.focus(matchedNode.id, {{
                    scale: 1.2,
                    animation: {{
                        duration: 1000,
                        easingFunction: 'easeInOutQuad'
                    }}
                }});
                network.selectNodes([matchedNode.id]);
            }} else {{
                alert('Entity not found in current knowledge graph.');
            }}
        }}

        // Trigger search on Enter key press
        document.getElementById('search-input').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                searchNode();
            }}
        }});
    </script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(output_html_path), exist_ok=True)
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"    Graph Visualizer: Saved Vis.js interactive graph to {output_html_path}")
    return output_html_path


if __name__ == "__main__":
    generate_interactive_graph()
