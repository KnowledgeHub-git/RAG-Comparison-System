"""
Neo4j Importer — Syncs LightRAG GraphML knowledge graph data directly to Neo4j AuraDB using optimized batch queries.
"""

import os
import sys
import networkx as nx
from neo4j import GraphDatabase

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config


def sanitize_label(label: str) -> str:
    """Sanitize entity types to be valid Neo4j labels (capitalized, alphanumeric/underscores)."""
    if not label:
        return "Entity"
    sanitized = "".join(c if c.isalnum() else "_" for c in label)
    sanitized = sanitized.strip("_").upper()
    return sanitized if sanitized else "ENTITY"


def import_graph_to_neo4j(graphml_path: str = None) -> dict:
    """
    Read the GraphML file and load nodes and edges into the Neo4j instance in batches.
    Returns a summary dictionary of imported counts.
    """
    if graphml_path is None:
        graphml_path = os.path.join(Config.LIGHTRAG_DIR, "graph_chunk_entity_relation.graphml")

    if not os.path.exists(graphml_path):
        print(f"[-] GraphML file not found at: {graphml_path}")
        return {"nodes": 0, "relationships": 0, "status": "Error: GraphML file not found"}

    print(f"[*] Reading GraphML file: {graphml_path}...")
    G = nx.read_graphml(graphml_path)
    print(f"[+] Loaded graph with {len(G.nodes)} nodes and {len(G.edges)} edges.")

    # Validate Neo4j configuration
    if not Config.NEO4J_URI or not Config.NEO4J_PASSWORD:
        print("[-] Neo4j configuration is missing in .env.")
        return {"nodes": 0, "relationships": 0, "status": "Error: Missing configuration"}

    print(f"[*] Connecting to Neo4j instance at {Config.NEO4J_URI}...")
    
    nodes_imported = 0
    relationships_imported = 0

    try:
        # Establish connection using the official driver
        driver = GraphDatabase.driver(
            Config.NEO4J_URI, 
            auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD)
        )
        
        with driver.session(database=Config.NEO4J_DATABASE) as session:
            # 1. Clear existing data
            print("[*] Clearing existing database nodes and relations...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # Create a constraint/index on name for fast lookups during relationship creation
            print("[*] Creating constraint on Name property...")
            try:
                session.run("CREATE CONSTRAINT unique_entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
            except Exception as e:
                print(f"[!] Note: Constraint creation skipped or already exists: {e}")

            # 2. Batch Nodes by Label
            print("[*] Grouping nodes by primary label for batch ingestion...")
            nodes_by_label = {}
            for node_name, data in G.nodes(data=True):
                entity_type = data.get("entity_type", "ENTITY")
                primary_label = sanitize_label(entity_type)
                
                if primary_label not in nodes_by_label:
                    nodes_by_label[primary_label] = []
                    
                nodes_by_label[primary_label].append({
                    "name": str(node_name),
                    "description": str(data.get("description", ""))
                })

            # Ingest grouped nodes
            for label, batch in nodes_by_label.items():
                print(f"[*] Uploading batch of {len(batch)} nodes for label: {label}...")
                
                # Standard MERGE on double labels to ensure fast indexing and exact labeling
                node_query = f"""
                UNWIND $batch AS row
                MERGE (n:Entity {{name: row.name}})
                MERGE (n2:{label} {{name: row.name}})
                SET n.description = row.description,
                    n2.description = row.description,
                    n.source = "LightRAG",
                    n2.source = "LightRAG"
                """
                session.run(node_query, batch=batch)
                nodes_imported += len(batch)

            # 3. Batch Ingest Relationships
            print("[*] Preparing relationships for batch ingestion...")
            rel_batch = []
            for source, target, data in G.edges(data=True):
                rel_batch.append({
                    "source": str(source),
                    "target": str(target),
                    "weight": float(data.get("weight", 1.0)),
                    "description": str(data.get("description", "")),
                    "keywords": str(data.get("keywords", ""))
                })

            if rel_batch:
                print(f"[*] Uploading batch of {len(rel_batch)} relationships...")
                rel_query = """
                UNWIND $batch AS row
                MATCH (a:Entity {name: row.source})
                MATCH (b:Entity {name: row.target})
                MERGE (a)-[r:RELATED_TO]->(b)
                SET r.weight = row.weight,
                    r.description = row.description,
                    r.keywords = row.keywords
                """
                session.run(rel_query, batch=rel_batch)
                relationships_imported += len(rel_batch)

        driver.close()
        print(f"[+] Successfully loaded {nodes_imported} nodes and {relationships_imported} relationships into Neo4j in batches.")
        return {
            "nodes": nodes_imported,
            "relationships": relationships_imported,
            "status": "Success"
        }
        
    except Exception as e:
        print(f"[-] Neo4j upload failed: {e}")
        return {
            "nodes": nodes_imported,
            "relationships": relationships_imported,
            "status": f"Error: {e}"
        }


if __name__ == "__main__":
    res = import_graph_to_neo4j()
    print("Sync Result:", res)
