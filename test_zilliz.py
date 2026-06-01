import os
from src.config import Config
from src.vector_graph_rag_system import VectorGraphRAGSystem

# Initialize configuration
Config.validate()

print("Initializing Vector Graph RAG System...")
vgr = VectorGraphRAGSystem()

print(f"Index loaded. Size: {os.path.getsize(vgr.milvus_uri)} bytes")

questions = [
    "What is Project Transcendence and which country initiated it?",
    "Compare the national AI investment pledges made by Canada, France, and India."
]

for q in questions:
    print("\n" + "="*50)
    print(f"QUESTION: {q}")
    print("="*50)
    res = vgr.query(q)
    print(f"ANSWER:\n{res['answer']}")
    print(f"\nSOURCES: {res['sources']}")
    print(f"LATENCY: {res['latency_ms']}ms")
