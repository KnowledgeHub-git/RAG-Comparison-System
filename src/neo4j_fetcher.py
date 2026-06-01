"""
Neo4j Fetcher — Connects to your live Neo4j AuraDB instance and fetches node/relationship summaries.
"""

import os
import sys
from neo4j import GraphDatabase

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config


def fetch_auradb_graph_summary() -> dict:
    """
    Connects to the configured Neo4j AuraDB instance and fetches graph statistics
    including total counts, counts by label, and a few sample connections.
    """
    if not Config.NEO4J_URI or not Config.NEO4J_PASSWORD:
        print("[-] Neo4j AuraDB coordinates are missing in .env.")
        return {"status": "Error: Missing coordinates"}

    print(f"[*] Connecting to Neo4j AuraDB at {Config.NEO4J_URI}...")
    
    summary = {
        "status": "Disconnected",
        "total_nodes": 0,
        "total_relationships": 0,
        "labels": {},
        "sample_relationships": []
    }

    try:
        driver = GraphDatabase.driver(
            Config.NEO4J_URI, 
            auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD)
        )
        
        with driver.session(database=Config.NEO4J_DATABASE) as session:
            # 1. Total Nodes
            total_n_res = session.run("MATCH (n) RETURN count(n) as count").single()
            summary["total_nodes"] = total_n_res["count"] if total_n_res else 0
            
            # 2. Total Relationships
            total_r_res = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()
            summary["total_relationships"] = total_r_res["count"] if total_r_res else 0
            
            # 3. Label Breakdown
            label_res = session.run("""
            MATCH (n) 
            UNWIND labels(n) as label 
            RETURN label, count(*) as count 
            ORDER BY count DESC
            """)
            summary["labels"] = {record["label"]: record["count"] for record in label_res}
            
            # 4. Fetch 5 Sample Relationships
            sample_res = session.run("""
            MATCH (a:Entity)-[r:RELATED_TO]->(b:Entity)
            RETURN a.name as source, labels(a) as source_labels, 
                   b.name as target, labels(b) as target_labels, 
                   r.description as description, r.weight as weight
            LIMIT 5
            """)
            for record in sample_res:
                # Filter out the generic "Entity" label for cleaner display
                src_labels = [l for l in record["source_labels"] if l != "Entity"]
                tgt_labels = [l for l in record["target_labels"] if l != "Entity"]
                
                summary["sample_relationships"].append({
                    "source": f"{record['source']} ({src_labels[0] if src_labels else 'Entity'})",
                    "target": f"{record['target']} ({tgt_labels[0] if tgt_labels else 'Entity'})",
                    "description": record["description"][:100] + "..." if len(record["description"]) > 100 else record["description"],
                    "weight": record["weight"]
                })
                
            summary["status"] = "Success 🟢 Connected to AuraDB"

        driver.close()
        return summary
        
    except Exception as e:
        print(f"[-] Failed to fetch data: {e}")
        return {"status": f"Error: {e}"}


if __name__ == "__main__":
    res = fetch_auradb_graph_summary()
    print("\n" + "="*50)
    print("      LIVE NEO4J AURADB GRAPH SUMMARY")
    print("="*50)
    print(f"Status              : {res['status']}")
    if "total_nodes" in res:
        print(f"Total Nodes         : {res['total_nodes']}")
        print(f"Total Relationships : {res['total_relationships']}")
        print("\n--- Entities by Type (Labels) ---")
        for label, count in res["labels"].items():
            if label != "Entity":
                print(f"  • {label:<15}: {count}")
        
        print("\n--- Sample Graph Connections (Sample Paths) ---")
        for idx, rel in enumerate(res["sample_relationships"]):
            print(f"  {idx+1}. {rel['source']} ──[RELATED_TO]──> {rel['target']}")
            print(f"     Description: {rel['description']}")
            print(f"     Weight     : {rel['weight']}\n")
    print("="*50)
