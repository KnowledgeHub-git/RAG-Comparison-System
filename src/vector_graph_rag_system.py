"""
Zilliz Vector Graph RAG System Integration.
Pure vector-space Graph RAG using Milvus Lite and Google Gemini.
"""

import os
import sys
import time
from typing import List, Dict, Any, Union, Literal
from pathlib import Path
import numpy as np

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.pdf_loader import Document

# Set up environment variables to redirect OpenAI client to Google Gemini's OpenAI-compatible endpoint
os.environ["OPENAI_BASE_URL"] = "https://generativelanguage.googleapis.com/v1beta/openai/"
os.environ["OPENAI_API_KEY"] = Config.GEMINI_API_KEY

# ── Monkeypatching Zilliz library to support Gemini OpenAI quirks ──────────

import vector_graph_rag.storage.embeddings

# 1. Force treating gemini-embedding-2 as an OpenAI-compatible model
vector_graph_rag.storage.embeddings._is_openai_model = lambda x: True

# 2. Patch OpenAIEmbedding.encode to resolve the missing 'index' parameter bug in Gemini's OpenAI endpoint
def patched_encode(self, texts: Union[str, List[str]], normalize: bool = True, text_type: Literal["query", "document"] = "query") -> np.ndarray:
    if isinstance(texts, str):
        texts = [texts]

    valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
    valid_texts = [texts[i] for i in valid_indices]

    if not valid_texts:
        return np.zeros((len(texts), self._get_dimension()))

    response = self._call_api(valid_texts)
    
    # 💡 Gemini compatibility fix: dynamically inject sequential indexes if they are returned as None
    for idx, item in enumerate(response.data):
        if getattr(item, "index", None) is None:
            item.index = idx
            
    sorted_data = sorted(response.data, key=lambda x: x.index)
    valid_embeddings = np.array([item.embedding for item in sorted_data])

    if normalize:
        norms = np.linalg.norm(valid_embeddings, axis=1, keepdims=True)
        valid_embeddings = valid_embeddings / (norms + 1e-9)

    if len(valid_indices) == len(texts):
        return valid_embeddings

    dim = valid_embeddings.shape[1]
    embeddings = np.zeros((len(texts), dim))
    for idx, valid_idx in enumerate(valid_indices):
        embeddings[valid_idx] = valid_embeddings[idx]
    return embeddings

vector_graph_rag.storage.embeddings.OpenAIEmbedding.encode = patched_encode


# 3. Patch LLMReranker._parse_response to support Gemini conversational JSON wrapping
import vector_graph_rag.llm.reranker
import json

def patched_parse_response(
    self,
    response: str,
    valid_ids: set,
    relation_ids: List[str],
    relation_texts: List[str],
) -> List[str]:
    """Patched parser that extracts JSON strictly between '{' and '}' to neutralize Gemini thought text."""
    try:
        # Locate the first '{' and last '}' to extract valid JSON
        start_idx = response.find("{")
        end_idx = response.rfind("}")
        if start_idx != -1 and end_idx != -1:
            json_str = response[start_idx:end_idx+1]
        else:
            json_str = response

        data = json.loads(json_str)
        useful_relationships = data.get("useful_relations", [])

        selected_ids = []
        id_to_line = {}

        for line in useful_relationships:
            # Extract ID from format "[ID] text"
            if "[" in line and "]" in line:
                start = line.find("[") + 1
                end = line.find("]")
                rel_id = line[start:end].strip()
                id_to_line[rel_id] = line.strip()

                if rel_id in valid_ids and rel_id not in selected_ids:
                    selected_ids.append(rel_id)
                elif rel_id not in valid_ids:
                    # Try to correct the ID by matching text
                    from vector_graph_rag.llm.reranker import _correct_line
                    corrected_id = _correct_line(line, relation_texts, relation_ids)
                    if corrected_id is not None and corrected_id not in selected_ids:
                        selected_ids.append(corrected_id)

        return selected_ids
    except Exception as e:
        print(f"[!] Warning: Patched JSON Parse Failed: {e}. Raw response snippet: {response[:150]}...")
        return []

vector_graph_rag.llm.reranker.LLMReranker._parse_response = patched_parse_response


# 4. Patch LLMReranker.rerank to provide a top-K fallback if semantic filter is empty
from typing import Tuple

def patched_rerank(
    self,
    query: str,
    relation_ids: List[str],
    relation_texts: List[str],
) -> Tuple[List[str], List[str]]:
    if not relation_ids:
        return [], []

    # Format relations
    relation_descriptions = self._format_relations(relation_ids, relation_texts)

    # Call LLM
    response = self._call_llm(query, relation_descriptions)

    # Parse response
    valid_ids = set(relation_ids)
    selected_ids = self._parse_response(response, valid_ids, relation_ids, relation_texts)

    # 💡 Fallback: If no relations selected by reranker, use top candidate relations from vector DB
    if not selected_ids:
        print("[*] Patched Rerank Fallback: No relations selected by reranker. Using top candidate relations.")
        selected_ids = relation_ids[: self.settings.final_top_k]

    # Get corresponding texts
    id_to_text = dict(zip(relation_ids, relation_texts))
    selected_texts = [id_to_text[rid] for rid in selected_ids if rid in id_to_text]

    return selected_ids, selected_texts

vector_graph_rag.llm.reranker.LLMReranker.rerank = patched_rerank



class VectorGraphRAGSystem:
    """
    Zilliz Vector Graph RAG (Pure vector-space Graph RAG) wrapper.
    
    Achieves high-fidelity entity and relation extraction without requiring a graph database,
    indexing all triplets and texts straight into local Milvus Lite.
    """

    def __init__(self):
        Config.validate()
        
        self.milvus_uri = str(Path(Config.LIGHTRAG_DIR).parent / "vector_graph_rag" / "milvus.db")
        os.makedirs(os.path.dirname(self.milvus_uri), exist_ok=True)
        
        # Instantiate VectorGraphRAG using Zilliz package
        from vector_graph_rag import VectorGraphRAG
        
        self.rag = VectorGraphRAG(
            milvus_uri=self.milvus_uri,
            llm_model="gemini-2.5-flash",
            embedding_model="gemini-embedding-2", # Direct live Gemini embedding model name
            collection_prefix="comparison"
        )
        self._load_collections()

    def _load_collections(self):
        """Explicitly load Milvus collections to prevent 'released' state errors."""
        try:
            store = self.rag._store
            for col in [store.entity_collection, store.relation_collection, store.passage_collection]:
                if store.client.has_collection(col):
                    print(f"[*] Loading collection: {col}...")
                    store.client.load_collection(col)
        except Exception as e:
            print(f"[!] Warning: Failed to load Milvus collections: {e}")

    def ingest(self, documents: List[Document]) -> int:
        """
        Ingest documents by parsing pre-extracted triplets from LightRAG GraphML representation
        to save hundreds of dollars in Gemini LLM extraction tokens and avoid API rate limits.
        """
        import shutil
        import gc
        import networkx as nx
        
        # 💡 WinError 183 fix: Deleting the existing local database directory ensures
        # that Milvus Lite creates a completely fresh database without locking conflicts!
        if os.path.exists(self.milvus_uri):
            print("[*] Clearing existing Vector Graph RAG database to prevent file locks...")
            try:
                self.rag = None
                gc.collect()
                time.sleep(1.0) # Allow OS to release file locks
                if os.path.isdir(self.milvus_uri):
                    shutil.rmtree(self.milvus_uri)
                else:
                    os.remove(self.milvus_uri)
            except Exception as e:
                print(f"[!] Warning: Could not clear Milvus DB folder: {e}")

        # Re-initialize a fresh VectorGraphRAG client
        from vector_graph_rag import VectorGraphRAG
        self.rag = VectorGraphRAG(
            milvus_uri=self.milvus_uri,
            llm_model="gemini-2.5-flash",
            embedding_model="gemini-embedding-2",
            collection_prefix="comparison"
        )
        self._load_collections()

        graphml_path = os.path.join(Config.LIGHTRAG_DIR, "graph_chunk_entity_relation.graphml")
        
        if not os.path.exists(graphml_path):
            print(f"[-] GraphML file not found at: {graphml_path}. Falling back to text ingestion...")
            # Fallback to standard triplet extraction
            texts = [doc.page_content for doc in documents]
            self.rag.add_texts(texts)
            return len(texts)
            
        print(f"[*] Parsing pre-extracted triplets from GraphML: {graphml_path}...")
        G = nx.read_graphml(graphml_path)
        
        # Build document-triplet dictionaries
        vgr_documents = []
        for idx, (source, target, data) in enumerate(G.edges(data=True)):
            description = data.get("description", "is related to")
            keywords = data.get("keywords", "related")
            
            # Construct a clear descriptive passage from the relationship
            passage = f"{source} {description} {target}"
            vgr_documents.append({
                "id": f"trip_{idx}",
                "passage": passage,
                "triplets": [
                    [str(source), str(keywords), str(target)]
                ]
            })
            
        print(f"[*] Ingesting {len(vgr_documents)} pre-extracted triplets into Zilliz Vector Graph RAG...")
        self.rag.add_documents_with_triplets(vgr_documents)
        return len(vgr_documents)

    def query(self, question: str) -> Dict[str, Any]:
        """
        Run multi-hop subgraph vector query and return answer and latency metrics.
        """
        start = time.time()
        
        try:
            # Query the Zilliz engine
            result = self.rag.query(question)
            answer = result.answer
            
            # Retrieve source documents if available
            sources = []
            if hasattr(result, "contexts") and result.contexts:
                for idx, ctx in enumerate(result.contexts[:3]):
                    sources.append(f"Zilliz Context Chunk {idx+1}")
            else:
                sources = ["Milvus Vector Graph Subgraph"]
                
            latency_ms = round((time.time() - start) * 1000)
            
            # Extract subgraph data for React visualizer
            nodes_payload = []
            edges_payload = []
            seed_entities = []
            selected_relation_ids = []
            candidate_relation_ids = []
            
            if hasattr(result, "retrieval_detail") and result.retrieval_detail:
                seed_entities = result.retrieval_detail.entity_texts
                candidate_relation_ids = result.retrieval_detail.relation_ids
                
            if hasattr(result, "rerank_result") and result.rerank_result:
                selected_relation_ids = result.rerank_result.selected_relation_ids

            if hasattr(result, "subgraph") and result.subgraph and hasattr(result.subgraph, "graph"):
                G_sub = result.subgraph.graph
                for node_name, node_data in G_sub.nodes(data=True):
                    nodes_payload.append({
                        "id": node_name,
                        "label": node_name,
                        "entity_type": node_data.get("entity_type", "UNKNOWN"),
                        "description": node_data.get("description", "")
                    })
                for u, v, edge_data in G_sub.edges(data=True):
                    edges_payload.append({
                        "source": u,
                        "target": v,
                        "description": edge_data.get("description", ""),
                        "weight": float(edge_data.get("weight", 1.0))
                    })

            return {
                "answer": answer,
                "sources": sources,
                "latency_ms": latency_ms,
                "chunks_used": len(sources),
                "method": "vector_graph_rag",
                "subgraph": {
                    "nodes": nodes_payload,
                    "edges": edges_payload,
                    "seed_entities": seed_entities,
                    "selected_relation_ids": selected_relation_ids,
                    "candidate_relation_ids": candidate_relation_ids
                }
            }
        except Exception as e:
            print(f"[-] Zilliz Query Failed: {e}")
            return {
                "answer": f"Zilliz Query Failed: {e}",
                "sources": [],
                "latency_ms": round((time.time() - start) * 1000),
                "chunks_used": 0,
                "method": "vector_graph_rag",
            }

    def is_ingested(self) -> bool:
        """Check if vector index contains ingested entities."""
        if not os.path.exists(self.milvus_uri):
            return False
        if os.path.isdir(self.milvus_uri):
            # Check if directory exists and contains files
            return len(os.listdir(self.milvus_uri)) > 0
        return os.path.getsize(self.milvus_uri) > 1024



if __name__ == "__main__":
    # Sanity check
    print("[*] Instantiating VectorGraphRAGSystem...")
    vgr = VectorGraphRAGSystem()
    print("[+] Ingested Status:", vgr.is_ingested())
