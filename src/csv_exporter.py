"""
CSV Exporter — Exports LightRAG GraphML knowledge graph nodes and edges into separate standard CSV files.
"""

import os
import sys
import csv
import networkx as nx

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config


def export_graph_to_csv(graphml_path: str = None, output_dir: str = None) -> dict:
    """
    Reads the GraphML knowledge graph and writes nodes and edges to standard CSVs.
    """
    if graphml_path is None:
        graphml_path = os.path.join(Config.LIGHTRAG_DIR, "graph_chunk_entity_relation.graphml")
        
    if output_dir is None:
        output_dir = Config.LIGHTRAG_DIR

    if not os.path.exists(graphml_path):
        print(f"[-] GraphML file not found at: {graphml_path}")
        return {"status": "Error: GraphML file not found"}

    os.makedirs(output_dir, exist_ok=True)
    nodes_csv_path = os.path.join(output_dir, "graph_nodes.csv")
    rels_csv_path = os.path.join(output_dir, "graph_relationships.csv")

    print(f"[*] Reading GraphML file: {graphml_path}...")
    G = nx.read_graphml(graphml_path)
    print(f"[+] Loaded graph with {len(G.nodes)} nodes and {len(G.edges)} edges.")

    # 1. Export Nodes
    print(f"[*] Exporting nodes to: {nodes_csv_path}...")
    with open(nodes_csv_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        # Header
        writer.writerow(["id", "entity_type", "description"])
        for node_name, data in G.nodes(data=True):
            entity_type = data.get("entity_type", "UNKNOWN")
            description = data.get("description", "")
            writer.writerow([str(node_name), str(entity_type), str(description)])

    # 2. Export Relationships
    print(f"[*] Exporting relationships to: {rels_csv_path}...")
    with open(rels_csv_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        # Header
        writer.writerow(["source", "target", "weight", "description", "keywords"])
        for source, target, data in G.edges(data=True):
            weight = data.get("weight", 1.0)
            description = data.get("description", "")
            keywords = data.get("keywords", "")
            writer.writerow([str(source), str(target), float(weight), str(description), str(keywords)])

    print("[+] Export complete!")
    return {
        "status": "Success",
        "nodes_csv": nodes_csv_path,
        "relationships_csv": rels_csv_path,
        "nodes_count": len(G.nodes),
        "relationships_count": len(G.edges)
    }


if __name__ == "__main__":
    res = export_graph_to_csv()
    print("Export Summary:", res)
